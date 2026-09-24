"""Database-backed system settings: accessor, cache and write-time validation.

This is the seam through which hard-coded academic policy moves into the
SystemSetting table (models.py) and, later, into an admin GUI. Reading is
deliberately trivial::

    from settings_store import setting

    if setting("enrolment.disable_fees_check", False):
        ...

A key is ``"<group>.<name>"``, mapping onto the SystemSetting row's
``group``/``name`` columns (the group is everything before the FIRST dot,
so names may themselves contain dots). Values are returned already typed:
the stored ``value_text``/``value_json`` column is converted according to
the setting's declared Spec (see DECLARATIONS at the bottom of this file).

Precedence when resolving a key: stored DB row > the ``default`` argument
passed by the caller > the declared Spec default > None. The caller's
argument deliberately wins over the declared default, so a call site can
be moved onto this accessor keeping its existing hard-coded fallback
verbatim, before the corresponding Spec/seed row exists.


Caching
-------
Reads must not cost a query each -- a single request can touch dozens of
settings -- yet we run hypercorn with several worker processes, so one
worker's cache goes stale the moment an admin saves a setting through
another worker. What is cached is therefore the whole settings table,
keyed by a single monotonically increasing ``_sys.policy_version`` row
that every write bumps *inside the writing transaction*. A request that
reads any setting issues one small indexed query for that row; the full
table is re-read only when the number changed.

The version row's bump being in the writer's transaction is what makes
this correct across workers: a reader that can see version N+1 can, by
definition, also see every value that transaction wrote, so a snapshot is
never a mix of old and new policy. Within one request the snapshot is
pinned on ``quart.g``, so all lookups in a request see one consistent set
of values even if an admin saves midway through -- which matters for
multi-step work like generating a transcript.

Alternatives considered:

* **Per-request full load** (no version row): simpler, equally correct,
  but pays a full-table read on every request that touches any setting,
  forever, growing with the number of settings and with JSON payload size
  (grade maps, category rules). The version row turns that into one
  single-row read that hits an index.
* **Time-based TTL only**: cheapest, but admin edits appear at a random
  time up to the TTL later and differ per worker, which is miserable to
  support ("I saved it, it didn't take effect, I saved it again").
  Retained only for code running outside a request (background jobs,
  scripts), where there is no request boundary to hang a check on; see
  NON_REQUEST_RECHECK_SECS.
* **Postgres LISTEN/NOTIFY invalidation**: no per-request query at all,
  but needs a dedicated long-lived connection per worker plus an async
  listener loop, and a missed notification (reconnect, restart) leaves a
  worker silently serving stale policy. Too much machinery, and too
  quiet a failure mode, for a saving of one indexed single-row read.
* **No cache**: a query per lookup, which is what the requirement rules
  out.

If reading settings fails (DB down, table missing pre-migration), the
last good snapshot is served, or an empty one if there is none, so call
sites fall back to their declared/passed defaults rather than raising.


Validation
----------
Every writable setting must be declared with a Spec, grouped by setting
group, optionally with a group-level cross-field validator. Saves are
validated and rejected at write time -- including a save of an undeclared
key -- so a bad value cannot surface later, halfway through generating a
student's transcript. Read-time conversion is total by construction: a
value that somehow fails to convert (a hand-edited row, a restored dump)
is logged and the declared default is used instead. ``setting()`` does
not raise.

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__status__ = "Development"
"""

import copy
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Optional, Sequence

from quart import g, has_app_context, has_request_context, session

import models as M
import vocab_defaults as VD
from common import AcadStackException

# The settings group reserved for this module's own bookkeeping. It is
# hidden from the read/describe APIs and cannot be written through them.
SYS_GROUP = "_sys"
POLICY_VERSION_NAME = "policy_version"

# Outside a request context (background jobs, CLI scripts) there is no
# request boundary on which to hang the version check, so the check is
# rate-limited to this interval instead. Keep it short: it only bounds how
# long a background job can act on stale policy.
NON_REQUEST_RECHECK_SECS = 5.0

_G_ATTR = "_acadstack_settings_snapshot"

JSON_TYPES = (list, dict)
SUPPORTED_TYPES = (bool, int, float, str, list, dict)


class _Unset:
    """Sentinel: distinguishes 'no default argument given' from None."""

    def __repr__(self):
        return "<unset>"


_UNSET = _Unset()


class SettingValidationError(AcadStackException):
    """Raised by the save path when a value fails its declared Spec. Carries
    every problem found, not just the first, so an admin GUI can show them
    all at once. Subclasses AcadStackException, so existing route handlers
    already surface its message to the client."""

    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


# ===================== Declaration =====================

@dataclass(frozen=True)
class Spec:
    """Declares one setting: its type, default, and what counts as valid.

    Args:
        name: the setting's name within its group (the part after the dot).
        type: one of bool, int, float, str, list, dict. list/dict are
            stored in value_json (is_json=True); the rest in value_text.
        default: value used when no row is stored. Must itself be valid.
        doc: human-readable description, for the admin GUI.
        choices: allowed values. For a list-typed setting this constrains
            every ITEM (e.g. a list of role codes), not the list itself.
        min_value/max_value: numeric bounds for int/float; length bounds
            for str/list/dict.
        item_type: for list/dict settings, the required type of each
            item/value.
        nullable: whether None is an acceptable stored value.
        validator: callable(value) for anything the fields above can't
            express. Report a problem by raising ValueError or by
            returning an error string (or list of strings); return None
            for "valid".
    """

    name: str
    type: type
    default: Any = None
    doc: str = ""
    choices: Optional[Sequence[Any]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    item_type: Optional[type] = None
    nullable: bool = False
    validator: Optional[Callable[[Any], Any]] = None

    def __post_init__(self):
        if self.type not in SUPPORTED_TYPES:
            raise ValueError(
                f"Spec '{self.name}': unsupported type {self.type!r}. "
                f"Supported: {[t.__name__ for t in SUPPORTED_TYPES]}")
        # split_key() only ever partitions on the FIRST '.' (the group is
        # always supplied separately, never re-derived from `name`), so an
        # interior dot in `name` is unambiguous -- only a leading/trailing/
        # doubled dot would produce an empty segment. Permission names
        # (the "permission" group) are hierarchical, e.g. "course.save".
        if self.name.startswith(".") or self.name.endswith(".") or ".." in self.name:
            raise ValueError(
                f"Spec '{self.name}': setting names may not start/end with "
                f"'.' or contain '..'")

    @property
    def is_json(self) -> bool:
        return self.type in JSON_TYPES


@dataclass(frozen=True)
class GroupSpec:
    name: str
    specs: dict = field(default_factory=dict)
    doc: str = ""
    validator: Optional[Callable[[dict], Any]] = None


_REGISTRY: dict[str, GroupSpec] = {}
# Keys already warned about as undeclared, so a typo'd key in a hot code
# path logs once rather than once per read.
_WARNED_UNDECLARED: set[str] = set()


def declare_group(group: str, specs: Iterable[Spec], doc: str = "",
                  validator: Optional[Callable[[dict], Any]] = None) -> GroupSpec:
    """Registers the schema for one setting group.

    Args:
        group: group name, as used in the "<group>.<name>" key.
        specs: the Specs belonging to the group.
        doc: description of the group, for the admin GUI.
        validator: optional cross-field check, called with the group's
            full effective values dict after a save is applied. Same
            reporting convention as Spec.validator.
    """
    if not group or "." in group or group == SYS_GROUP:
        raise ValueError(f"Invalid settings group name: {group!r}")
    by_name = {}
    for spec in specs:
        if spec.name in by_name:
            raise ValueError(f"Duplicate Spec '{group}.{spec.name}'")
        by_name[spec.name] = spec
    gs = GroupSpec(name=group, specs=by_name, doc=doc, validator=validator)
    # A declared default that is itself invalid would silently become the
    # value every call site sees, so catch it at import time -- before the
    # group is registered, so a rejected declaration leaves nothing behind.
    for spec in by_name.values():
        if spec.default is None and not spec.nullable:
            continue
        errors = _validate_value(group, spec, spec.default)
        if errors:
            raise ValueError(f"Invalid declared default: {'; '.join(errors)}")
    _REGISTRY[group] = gs
    _WARNED_UNDECLARED.clear()
    return gs


def split_key(key: str) -> tuple:
    """Splits "<group>.<name>" into (group, name)."""
    group, sep, name = key.partition(".")
    if not sep or not group or not name:
        raise ValueError(
            f"Invalid setting key {key!r}: expected '<group>.<name>'")
    return group, name


def spec_for(key: str) -> Optional[Spec]:
    group, name = split_key(key)
    gs = _REGISTRY.get(group)
    return gs.specs.get(name) if gs else None


def declared_groups() -> dict:
    """All declared groups, for the admin GUI and for startup validation."""
    return dict(_REGISTRY)


def describe_settings() -> list:
    """Machine-readable description of every declared setting, for the
    admin GUI to render an editing form from (Phase 10)."""
    out = []
    for group in sorted(_REGISTRY):
        gs = _REGISTRY[group]
        for name in sorted(gs.specs):
            spec = gs.specs[name]
            key = f"{group}.{name}"
            prov = provenance(key)
            out.append({
                "key": key,
                "group": group,
                "group_doc": gs.doc,
                "name": name,
                "type": spec.type.__name__,
                "is_json": spec.is_json,
                "default": spec.default,
                "doc": spec.doc,
                "choices": list(spec.choices) if spec.choices else None,
                "min_value": spec.min_value,
                "max_value": spec.max_value,
                "item_type": spec.item_type.__name__ if spec.item_type else None,
                "nullable": spec.nullable,
                "value": setting(key),
                # BaseModel provenance of the stored row, or None for both
                # when the setting has never been explicitly saved (still
                # at its declared default, so there is no row to attribute).
                "updated_by": prov["updated_by"] if prov else None,
                "updated_ts": prov["updated_ts"] if prov else None,
            })
    return out


# ===================== Validation =====================

def _coerce(spec: Spec, value: Any) -> Any:
    """Converts an incoming value to the declared type, accepting the
    string forms an HTML form / JSON body realistically sends. Raises
    ValueError if the value is not convertible."""
    if value is None:
        return None
    t = spec.type
    if t is bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            if value in (0, 1):
                return bool(value)
        elif isinstance(value, str):
            low = value.strip().lower()
            if low in ("true", "1", "yes", "on"):
                return True
            if low in ("false", "0", "no", "off"):
                return False
        raise ValueError(f"expected a boolean, got {value!r}")
    if t is int:
        # bool is an int subclass; accepting it here would silently turn
        # True into 1 for a numeric threshold.
        if isinstance(value, bool):
            raise ValueError(f"expected an integer, got {value!r}")
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if isinstance(value, str):
            try:
                return int(value.strip())
            except ValueError:
                pass
        raise ValueError(f"expected an integer, got {value!r}")
    if t is float:
        if isinstance(value, bool):
            raise ValueError(f"expected a number, got {value!r}")
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value.strip())
            except ValueError:
                pass
        raise ValueError(f"expected a number, got {value!r}")
    if t is str:
        if isinstance(value, str):
            return value
        raise ValueError(f"expected a string, got {value!r}")
    # list / dict: accept the parsed value, or raw JSON text from a form.
    if isinstance(value, t):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except ValueError:
            raise ValueError(f"expected JSON {t.__name__}, got {value!r}")
        if isinstance(parsed, t):
            return parsed
    raise ValueError(f"expected a JSON {t.__name__}, got {value!r}")


def _run_user_validator(fn: Callable, value: Any, label: str) -> list:
    """Applies the raise-or-return error reporting convention shared by
    Spec.validator and the group validator."""
    try:
        result = fn(value)
    except ValueError as ex:
        return [f"{label}: {ex}"]
    if result is None or result is True:
        return []
    if result is False:
        return [f"{label}: rejected by validator"]
    if isinstance(result, str):
        return [f"{label}: {result}"]
    if isinstance(result, (list, tuple)):
        return [f"{label}: {r}" for r in result]
    return []


def _validate_value(group: str, spec: Spec, value: Any) -> list:
    """Checks an ALREADY COERCED value against its Spec. Returns a list of
    error messages (empty when valid)."""
    label = f"{group}.{spec.name}"
    if value is None:
        if spec.nullable:
            return []
        return [f"{label}: value is required"]

    if spec.type is int and isinstance(value, bool):
        return [f"{label}: expected an integer, got {value!r}"]
    if not isinstance(value, spec.type):
        return [f"{label}: expected {spec.type.__name__}, got "
                f"{type(value).__name__}"]

    errors = []
    if spec.item_type is not None:
        items = value.values() if spec.type is dict else value
        for item in items:
            if not isinstance(item, spec.item_type) or (
                    spec.item_type is not bool and isinstance(item, bool)):
                errors.append(f"{label}: every item must be "
                              f"{spec.item_type.__name__}, got {item!r}")
                break

    if spec.choices is not None:
        allowed = list(spec.choices)
        # For a collection setting the choices constrain the items: a list
        # of role codes is the common shape here.
        bad = [v for v in value if v not in allowed] \
            if spec.type in JSON_TYPES else \
            ([] if value in allowed else [value])
        for v in bad:
            errors.append(f"{label}: {v!r} is not one of {allowed}")

    if spec.min_value is not None or spec.max_value is not None:
        measure = value if spec.type in (int, float) else len(value)
        what = "value" if spec.type in (int, float) else "length"
        if spec.min_value is not None and measure < spec.min_value:
            errors.append(f"{label}: {what} {measure} is below the minimum "
                          f"{spec.min_value}")
        if spec.max_value is not None and measure > spec.max_value:
            errors.append(f"{label}: {what} {measure} is above the maximum "
                          f"{spec.max_value}")

    if spec.validator is not None:
        errors.extend(_run_user_validator(spec.validator, value, label))

    return errors


def validate_values(values: dict) -> dict:
    """Validates a {key: value} mapping destined for the DB, WITHOUT
    writing anything. Returns the coerced values ready to store; raises
    SettingValidationError listing every problem found.

    Saving an undeclared key is an error: the declaration is what makes a
    setting safe to read later, so there is no way to sneak a value past
    it.
    """
    errors, coerced = [], {}
    by_group = {}

    for key, raw in values.items():
        try:
            group, name = split_key(key)
        except ValueError as ex:
            errors.append(str(ex))
            continue
        if group == SYS_GROUP:
            errors.append(f"{key}: '{SYS_GROUP}' is reserved for internal "
                          f"bookkeeping and cannot be written")
            continue
        gs = _REGISTRY.get(group)
        spec = gs.specs.get(name) if gs else None
        if spec is None:
            errors.append(f"{key}: no such setting is declared (declare it "
                          f"with declare_group() before saving a value)")
            continue
        try:
            value = _coerce(spec, raw)
        except ValueError as ex:
            errors.append(f"{key}: {ex}")
            continue
        value_errors = _validate_value(group, spec, value)
        if value_errors:
            errors.extend(value_errors)
            continue
        coerced[key] = value
        by_group.setdefault(group, {})[name] = value

    # Cross-field checks run against the group as it would look AFTER the
    # save, so a pair like min/max credits can be checked as a whole.
    for group, changed in by_group.items():
        gs = _REGISTRY[group]
        if gs.validator is None:
            continue
        effective = settings_in_group(group)
        effective.update(changed)
        errors.extend(_run_user_validator(gs.validator, effective, group))

    if errors:
        raise SettingValidationError(errors)
    return coerced


def validate_stored_settings() -> list:
    """Checks everything currently in the table against the declarations.
    Called at startup so a value that predates its Spec, or that was
    hand-edited in the DB, is reported in the log at boot instead of
    silently falling back to a default at read time. Returns the list of
    problems found.

    Values that cannot be converted to their declared type at all are
    reported by the loader itself (see _value_from_row), since by the time
    they reach here they have already become the declared default."""
    problems = []
    snap = _current_snapshot()
    for key, value in sorted(snap.values.items()):
        spec = spec_for(key)
        if spec is None:
            problems.append(f"{key}: stored but not declared")
            continue
        problems.extend(_validate_value(split_key(key)[0], spec, value))
    for p in problems:
        logging.warning(f"Stored system setting is invalid: {p}")
    return problems


# ===================== Cache =====================

class _Snapshot:
    __slots__ = ("version", "values", "provenance")

    def __init__(self, version: int, values: dict, provenance: dict = None):
        self.version = version
        self.values = values
        # key -> (txn_login_id, upd_ts) of the stored row, for the admin
        # GUI's provenance display. Absent for a key with no stored row.
        self.provenance = provenance if provenance is not None else {}


_EMPTY_SNAPSHOT = _Snapshot(-1, {})

_cache_lock = threading.RLock()
_cache: Optional[_Snapshot] = None
_last_check_ts = 0.0


def _read_policy_version() -> int:
    """One small indexed read of the single version row. Absent row (fresh
    install, nothing ever saved) counts as version 0."""
    cur = M.db.execute_sql(
        'SELECT value_text FROM systemsetting '
        'WHERE "group" = %s AND name = %s AND is_json = false '
        'AND is_deleted = false LIMIT 1',
        (SYS_GROUP, POLICY_VERSION_NAME))
    row = cur.fetchone()
    if not row or row[0] is None:
        return 0
    try:
        return int(row[0])
    except (TypeError, ValueError):
        # Self-healed by the next write (see _bump_policy_version), which
        # treats a non-numeric value as zero.
        logging.error(f"Corrupt {SYS_GROUP}.{POLICY_VERSION_NAME} value "
                      f"{row[0]!r}; reloading settings.")
        return -2


def _value_from_row(row) -> Any:
    """Converts one stored row to its typed value, falling back to the
    declared default if the stored text can't be converted. Read-time
    conversion never raises -- that is the whole point of validating on
    write."""
    key = f"{row.group}.{row.name}"
    spec = spec_for(key)
    # Reading whichever column the ROW was written to, not the one the Spec
    # expects: a row written before its Spec existed can sit in the other
    # column, and coercion below decides whether it is still usable.
    raw = row.value_json if row.is_json else row.value_text
    if spec is None:
        return raw
    try:
        return _coerce(spec, raw)
    except ValueError as ex:
        logging.error(f"Stored value for {key} is unusable ({ex}); using the "
                      f"declared default {spec.default!r} instead.")
        return spec.default


def _load_values(version: int) -> _Snapshot:
    values = {}
    seen_json = {}
    provenance = {}
    query = (M.SystemSetting.select()
             .where((M.SystemSetting.is_deleted == False) &  # noqa: E712
                    (M.SystemSetting.group != SYS_GROUP)))
    for row in query:
        key = f"{row.group}.{row.name}"
        if key in values:
            # The unique index is on (group, name, is_json), so the same
            # key CAN exist twice with different is_json. Prefer the row
            # whose storage matches the declaration; the save path deletes
            # the other variant, so this only happens for rows written
            # before a Spec existed.
            spec = spec_for(key)
            wanted = spec.is_json if spec else True
            logging.warning(f"Setting {key} has both a text and a JSON row; "
                            f"using the is_json={wanted} one.")
            if seen_json[key] == wanted:
                continue
        seen_json[key] = row.is_json
        values[key] = _value_from_row(row)
        provenance[key] = (row.txn_login_id, row.upd_ts)
    return _Snapshot(version, values, provenance)


def _refresh_snapshot() -> _Snapshot:
    """Checks the policy version and reloads the values only if it moved."""
    global _cache, _last_check_ts
    try:
        version = _read_policy_version()
    except Exception:
        logging.exception("Could not read the settings policy version; "
                          "serving the last known settings.")
        with _cache_lock:
            return _cache or _EMPTY_SNAPSHOT

    with _cache_lock:
        cached = _cache
    if cached is not None and cached.version == version:
        with _cache_lock:
            _last_check_ts = time.monotonic()
        return cached

    try:
        # Deliberately loaded outside the lock: two threads racing here
        # just do the same idempotent read twice.
        snapshot = _load_values(version)
    except Exception:
        logging.exception("Could not load system settings; serving the last "
                          "known settings.")
        with _cache_lock:
            return _cache or _EMPTY_SNAPSHOT

    with _cache_lock:
        _cache = snapshot
        _last_check_ts = time.monotonic()
    logging.info(f"Loaded {len(snapshot.values)} system setting(s) at policy "
                 f"version {version}.")
    return snapshot


def _pinned_snapshot() -> Optional[_Snapshot]:
    """The snapshot pinned on `g` for the request in flight, if any.

    `g` lives on the app context, so it is only reachable when BOTH
    contexts are pushed; a caller in a stray context still gets a correct
    (just unpinned) answer via the process cache rather than an error.
    """
    if not (has_request_context() and has_app_context()):
        return None
    try:
        return getattr(g, _G_ATTR, None)
    except RuntimeError:
        return None


def _pin_snapshot(snapshot: _Snapshot) -> None:
    if not (has_request_context() and has_app_context()):
        return
    try:
        setattr(g, _G_ATTR, snapshot)
    except RuntimeError:
        pass


def _current_snapshot() -> _Snapshot:
    if has_request_context() and has_app_context():
        snapshot = _pinned_snapshot()
        if snapshot is None:
            snapshot = _refresh_snapshot()
            _pin_snapshot(snapshot)
        return snapshot

    with _cache_lock:
        if _cache is not None and \
                (time.monotonic() - _last_check_ts) < NON_REQUEST_RECHECK_SECS:
            return _cache
    return _refresh_snapshot()


def invalidate_cache() -> None:
    """Drops this process's cached settings. Writes call this; other
    workers pick the change up via the policy version."""
    global _cache, _last_check_ts
    with _cache_lock:
        _cache = None
        _last_check_ts = 0.0
    if _pinned_snapshot() is not None:
        try:
            delattr(g, _G_ATTR)
        except (AttributeError, RuntimeError):
            pass


def policy_version() -> int:
    """The policy version behind the settings currently being served."""
    return _current_snapshot().version


# ===================== Read =====================

def setting(key: str, default: Any = _UNSET) -> Any:
    """Returns the effective value of a system setting.

    Args:
        key: "<group>.<name>", e.g. "enrolment.disable_fees_check".
        default: value to use when nothing is stored. Overrides the
            declared Spec default, so a call site can keep the fallback
            it already had.

    Returns:
        The stored value, converted to the declared type; otherwise the
        default above; otherwise the Spec's default; otherwise None.
        Never raises for a missing or unusable stored value.
    """
    spec = spec_for(key)
    if spec is None and key not in _WARNED_UNDECLARED:
        _WARNED_UNDECLARED.add(key)
        logging.warning(f"Setting {key!r} is read but not declared; it can "
                        f"only ever fall back to the caller's default.")

    values = _current_snapshot().values
    if key in values:
        value = values[key]
        # Callers get their own copy: a cached list/dict is shared by
        # every request this worker serves until the version changes.
        return copy.deepcopy(value) if isinstance(value, JSON_TYPES) else value

    if not isinstance(default, _Unset):
        return default
    return copy.deepcopy(spec.default) if spec else None


def provenance(key: str) -> Optional[dict]:
    """Who last saved this setting's stored row and when (BaseModel's
    txn_login_id/upd_ts), or None if it has never been explicitly saved --
    i.e. it is still serving its declared default, so there is no row to
    attribute a change to."""
    row = _current_snapshot().provenance.get(key)
    if row is None:
        return None
    login_id, upd_ts = row
    return {"updated_by": login_id, "updated_ts": upd_ts}


def settings_in_group(group: str) -> dict:
    """All effective values for one group as {name: value}: declared
    defaults overlaid with whatever is stored."""
    gs = _REGISTRY.get(group)
    out = {name: copy.deepcopy(spec.default)
           for name, spec in (gs.specs.items() if gs else [])}
    prefix = f"{group}."
    for key, value in _current_snapshot().values.items():
        if key.startswith(prefix):
            out[key[len(prefix):]] = \
                copy.deepcopy(value) if isinstance(value, JSON_TYPES) else value
    return out


def all_settings() -> dict:
    """Every effective setting as {group: {name: value}}, for the admin GUI."""
    groups = set(_REGISTRY)
    groups.update(split_key(k)[0] for k in _current_snapshot().values)
    return {group: settings_in_group(group) for group in sorted(groups)}


# ===================== Vocabularies =====================
#
# Controlled vocabularies (degrees, roles, statuses, grades, ...) are
# ordinary "vocab.<name>" settings: list-of-{code,label} values declared
# below with vocab_defaults.py's lists as their Spec defaults. These
# helpers are the read-side seam other modules use instead of reaching
# into `setting("vocab....")` directly.

def vocab(name: str) -> list:
    """Effective items for one controlled vocabulary: a list of
    {"code", "label", ...} dicts, DB-stored value if present, else the
    vocab_defaults.py default. See vocab_defaults.ALL for the valid
    names."""
    return setting(f"vocab.{name}")


def vocab_codes(name: str) -> list:
    """Just the codes for one controlled vocabulary, in effective order."""
    return [item["code"] for item in vocab(name)]


def valid_grade_codes() -> list:
    """All valid grade codes, DB-effective (replaces the old
    common.VALID_GRADES list)."""
    return vocab_codes("grades")


def valid_audit_grade_codes() -> list:
    """Grade codes valid for an audited ('A') enrolment, DB-effective
    (replaces the old common.VALID_AUDIT_GRADES list)."""
    return [g["code"] for g in vocab("grades") if g.get("audit_ok")]


# ===================== Write =====================

def _current_login_id():
    try:
        if has_request_context() and "user" in session:
            return session["user"].get("login_id")
    except RuntimeError:
        pass
    return None


def _bump_policy_version() -> int:
    """Increments the single version row, creating it if absent. MUST run
    inside the same transaction as the value writes: a reader that sees
    the new version must also see the new values."""
    cur = M.db.execute_sql(
        'INSERT INTO systemsetting ("group", name, is_json, value_text, '
        '  is_deleted, txn_no, ins_ts, upd_ts) '
        'VALUES (%s, %s, false, %s, false, 1, now(), now()) '
        'ON CONFLICT ("group", name, is_json) DO UPDATE SET '
        # A non-numeric value (hand-edited row) restarts the count rather
        # than failing the save, which would otherwise wedge every write.
        '  value_text = ((CASE WHEN systemsetting.value_text ~ \'^[0-9]+$\' '
        '                 THEN systemsetting.value_text::bigint ELSE 0 END) '
        '                + 1)::text, '
        '  txn_no = systemsetting.txn_no + 1, upd_ts = now() '
        'RETURNING value_text',
        (SYS_GROUP, POLICY_VERSION_NAME, "1"))
    return int(cur.fetchone()[0])


def bump_policy_version() -> int:
    """Bumps the shared configuration version counter.

    Public because ``policy_store`` (the effective-dated academic policy
    store) is keyed on the same counter: one number answers "is my cached
    configuration current?" for both stores, which is what makes a reader
    that sees version N+1 guaranteed to see everything that transaction
    wrote. Must be called inside the writing transaction.
    """
    return _bump_policy_version()


def current_login_id() -> Optional[str]:
    """The logged-in user's id when called during a request, else None.
    Public for the same reason as bump_policy_version()."""
    return _current_login_id()


def save_settings(values: dict, login_id: Optional[str] = None) -> dict:
    """Validates and stores several settings atomically.

    Either every value is written and the policy version bumped once, or
    nothing is (validation errors are raised before any write). Returns
    the coerced values as stored.

    Raises:
        SettingValidationError: if any value is invalid or undeclared.
    """
    coerced = validate_values(values)
    if not coerced:
        return {}

    login_id = login_id or _current_login_id()
    with M.db.atomic():
        for key, value in coerced.items():
            group, name = split_key(key)
            spec = _REGISTRY[group].specs[name]
            row = dict(group=group, name=name, is_json=spec.is_json,
                       value_text=None if spec.is_json else
                       (None if value is None else str(value)),
                       value_json=value if spec.is_json else None,
                       txn_login_id=login_id, is_deleted=False,
                       upd_ts=M.DT.now())
            (M.SystemSetting.insert(**row)
             .on_conflict(
                 conflict_target=[M.SystemSetting.group, M.SystemSetting.name,
                                  M.SystemSetting.is_json],
                 update={M.SystemSetting.value_text: row["value_text"],
                         M.SystemSetting.value_json: row["value_json"],
                         M.SystemSetting.is_deleted: False,
                         M.SystemSetting.txn_login_id: login_id,
                         M.SystemSetting.txn_no: M.SystemSetting.txn_no + 1,
                         M.SystemSetting.upd_ts: row["upd_ts"]})
             .execute())
            # The unique index allows a second row for the same key with
            # the other is_json flag (e.g. written before this Spec
            # existed); drop it so reads can't pick the wrong one.
            (M.SystemSetting.delete()
             .where((M.SystemSetting.group == group) &
                    (M.SystemSetting.name == name) &
                    (M.SystemSetting.is_json != spec.is_json)).execute())
        version = _bump_policy_version()

    invalidate_cache()
    logging.info(f"Saved system setting(s) {sorted(coerced)} by "
                 f"{login_id}; policy version now {version}.")
    return coerced


def save_setting(key: str, value: Any, login_id: Optional[str] = None) -> Any:
    """Validates and stores one setting. See save_settings()."""
    return save_settings({key: value}, login_id=login_id)[key]


def delete_setting(key: str, login_id: Optional[str] = None) -> bool:
    """Removes the stored row for a key, so it reverts to its declared
    default. Returns True if a row was actually removed."""
    group, name = split_key(key)
    if group == SYS_GROUP:
        raise SettingValidationError(
            [f"{key}: '{SYS_GROUP}' is reserved and cannot be modified"])
    with M.db.atomic():
        removed = (M.SystemSetting.delete()
                   .where((M.SystemSetting.group == group) &
                          (M.SystemSetting.name == name)).execute())
        if removed:
            version = _bump_policy_version()
            logging.info(f"Deleted system setting {key} by "
                         f"{login_id or _current_login_id()}; policy version "
                         f"now {version}.")
    if removed:
        invalidate_cache()
    return bool(removed)


# ===================== DECLARATIONS =====================
# Every writable setting is declared here, e.g.:
#
#     declare_group("enrolment", [
#         Spec("disable_fees_check", bool, default=False,
#              doc="Skip the outstanding-fees check when enrolling."),
#     ], doc="Course enrolment policy.")

declare_group(
    "enrolment",
    [
        Spec("disable_fees_check", bool, default=False,
             doc="Skip the outstanding-fees check when enrolling."),
        Spec("max_credits_per_session", int, default=24,
             min_value=1, max_value=60,
             doc="Maximum total credits a student may be enrolled in "
                 "within one academic session."),
    ],
    doc="Course enrolment policy."
)

declare_group(
    "course_offering",
    [
        Spec("hide_stats_from", list, default=["STU"], item_type=str,
             choices=VD.codes("roles"),
             doc="Roles for which course offering stats are hidden."),
    ],
    doc="Course offering policy."
)

declare_group(
    "auth",
    [
        Spec("password_reset_lockout_attempts", int, default=4, min_value=1,
             doc="Lock the account once more than this many password-reset "
                 "keys have been requested."),
    ],
    doc="Authentication and account-lockout policy."
)

declare_group(
    "app",
    [
        Spec("page_size", int, default=25, min_value=1, max_value=500,
             doc="Default page size for paginated list endpoints."),
        Spec("active_user_window_secs", int, default=1800, min_value=1,
             doc="How many seconds since last access a user still counts "
                 "as active."),
    ],
    doc="General application-wide operational settings."
)

declare_group(
    "faces",
    [
        Spec("match_tolerance", float, default=0.45,
             min_value=0.0, max_value=1.0,
             doc="Face-recognition match tolerance passed to frec_service; "
                 "lower is stricter."),
    ],
    doc="Photo-based attendance / face-recognition policy."
)


def _validate_vocab_items(items):
    """Shared Spec.validator for every "vocab.*" setting: each item must
    be a {"code": str, "label": str, ...} object, and codes must be
    unique within the list. Anything beyond code/label (e.g. grades'
    audit_ok) is the individual vocabulary's business, not checked here.
    """
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            return f"every item must be an object, got {item!r}"
        code, label = item.get("code"), item.get("label")
        if not isinstance(code, str) or not code:
            return f"item {item!r}: 'code' must be a non-empty string"
        if not isinstance(label, str) or not label:
            return f"item {item!r}: 'label' must be a non-empty string"
        if code in seen:
            return f"duplicate code {code!r}"
        seen.add(code)
    return None


declare_group(
    "vocab",
    [Spec(name, list, default=items, item_type=dict,
          validator=_validate_vocab_items,
          doc=f"Controlled vocabulary: {name}.")
     for name, items in VD.ALL.items()],
    doc="Controlled vocabularies (degrees, roles, statuses, grades, ...). "
        "Seeded from vocab_defaults.py by default_seed_data.py; served to "
        "the frontend by api_common.static_data_dict()."
)
