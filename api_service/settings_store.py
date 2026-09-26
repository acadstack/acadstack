"""Database-backed system settings: accessor, cache and write-time validation.

Reading::

    from settings_store import setting

    if setting("enrolment.disable_fees_check", False):
        ...

A key is ``"<group>.<name>"``, mapping onto the SystemSetting row's
``group``/``name`` columns (the group is everything before the FIRST dot,
so names may themselves contain dots). The row's JSONB ``value`` comes
back typed according to the setting's declared Spec (see DECLARATIONS at
the bottom of this file).

Precedence when resolving a key: stored DB row > the ``default`` argument
passed by the caller > the declared Spec default > None.


Caching
-------
The whole table is cached in the process and loaded on first use. The app
runs as one hypercorn process (see docs/architecture.md), so every write
goes through this module and drops the cache itself; there is no other
process whose cache could go stale. Within one request the snapshot is
pinned on ``quart.g``, so multi-step work such as generating a transcript
sees one consistent set of values. A row edited directly in the database
is picked up on the next write through this module, or a restart.

If loading the settings fails (DB down, table missing), an empty snapshot
is served and not cached, so call sites fall back to their defaults
rather than raising and the next read retries.


Validation
----------
Every writable setting is declared with a Spec. Saves are validated at
write time -- a save of an undeclared key included -- and every problem is
reported at once. A stored value that fails to convert on read (a
hand-edited row) is logged and the declared default used; ``setting()``
never raises.

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__status__ = "Development"
"""

import copy
import json
import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Optional, Sequence

from quart import g, has_app_context, has_request_context, session

import models as M
import vocab_defaults as VD
from common import AcadStackException

_G_ATTR = "_acadstack_settings_snapshot"

JSON_TYPES = (list, dict)
SUPPORTED_TYPES = (bool, int, float, str, list, dict)


class _Unset:
    """Sentinel: distinguishes 'no default argument given' from None."""

    def __repr__(self):
        return "<unset>"


_UNSET = _Unset()


class SettingValidationError(AcadStackException):
    """A save failed validation. Carries every problem found, so an admin
    GUI can show them all at once."""

    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


# ===================== Declaration =====================

@dataclass(frozen=True)
class Spec:
    """Declares one setting.

    Args:
        name: the setting's name within its group (the part after the dot).
        type: one of bool, int, float, str, list, dict.
        default: value used when no row is stored. Must itself be valid.
        doc: description, for the admin GUI.
        choices: allowed values. For a list setting this constrains every
            ITEM (e.g. a list of role codes).
        min_value/max_value: bounds for int/float; length bounds for
            str/list/dict.
        validator: callable(value) for anything else. Raises ValueError to
            reject; one message per argument (``ValueError(*messages)``)
            to report several problems.
    """

    name: str
    type: type
    default: Any = None
    doc: str = ""
    choices: Optional[Sequence[Any]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    validator: Optional[Callable[[Any], None]] = None

    def __post_init__(self):
        if self.type not in SUPPORTED_TYPES:
            raise ValueError(
                f"Spec '{self.name}': unsupported type {self.type!r}. "
                f"Supported: {[t.__name__ for t in SUPPORTED_TYPES]}")
        # Names may contain interior dots (permission names such as
        # "course.save"), but no empty segment.
        if self.name.startswith(".") or self.name.endswith(".") or ".." in self.name:
            raise ValueError(
                f"Spec '{self.name}': setting names may not start/end with "
                f"'.' or contain '..'")


@dataclass(frozen=True)
class GroupSpec:
    name: str
    specs: dict = field(default_factory=dict)
    doc: str = ""


_REGISTRY: dict[str, GroupSpec] = {}
# Undeclared keys already warned about, so a typo logs once, not per read.
_WARNED_UNDECLARED: set[str] = set()


def declare_group(group: str, specs: Iterable[Spec], doc: str = "") -> GroupSpec:
    """Registers the Specs of one setting group. Every declared default is
    validated here, so an invalid one fails at import time."""
    if not group or "." in group:
        raise ValueError(f"Invalid settings group name: {group!r}")
    by_name = {}
    for spec in specs:
        if spec.name in by_name:
            raise ValueError(f"Duplicate Spec '{group}.{spec.name}'")
        by_name[spec.name] = spec
        _, errors = _check(f"{group}.{spec.name}", spec, spec.default)
        if errors:
            raise ValueError(f"Invalid declared default: {'; '.join(errors)}")
    gs = GroupSpec(name=group, specs=by_name, doc=doc)
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
    return dict(_REGISTRY)


def describe_settings() -> list:
    """Every declared setting with its schema and current value, for the
    admin GUI to render an editing form from."""
    snap = _current_snapshot()
    out = []
    for group in sorted(_REGISTRY):
        gs = _REGISTRY[group]
        for name in sorted(gs.specs):
            spec = gs.specs[name]
            key = f"{group}.{name}"
            # (login_id, upd_ts) of the stored row; none while the setting
            # still serves its declared default.
            updated_by, updated_ts = snap.provenance.get(key, (None, None))
            out.append({
                "key": key,
                "group": group,
                "group_doc": gs.doc,
                "name": name,
                "type": spec.type.__name__,
                "default": spec.default,
                "doc": spec.doc,
                "choices": list(spec.choices) if spec.choices else None,
                "min_value": spec.min_value,
                "max_value": spec.max_value,
                "value": setting(key),
                "updated_by": updated_by,
                "updated_ts": updated_ts,
            })
    return out


# ===================== Validation =====================

def _coerce(spec: Spec, value: Any) -> Any:
    """Converts a value to the declared type. A string for a non-str
    setting (an HTML form field) is parsed as JSON, so "true", " 21 " and
    '["STU"]' all work. Raises ValueError if not convertible."""
    t = spec.type
    if value is None:
        raise ValueError("value is required")
    if isinstance(value, str) and t is not str:
        try:
            value = json.loads(value.strip().lower() if t is bool else value)
        except ValueError:
            raise ValueError(f"expected {t.__name__}, got {value!r}")
    # bool is an int subclass; never let True through as 1.
    if isinstance(value, bool) and t is not bool:
        raise ValueError(f"expected {t.__name__}, got {value!r}")
    if t is float and isinstance(value, int):
        return float(value)
    if t is int and isinstance(value, float) and value.is_integer():
        return int(value)
    if not isinstance(value, t):
        raise ValueError(f"expected {t.__name__}, got {value!r}")
    return value


def run_validator(fn: Callable, value: Any, label: str) -> list:
    """Runs a validator under the shared convention (raise ValueError, one
    message per argument), returning labelled error messages. Also used by
    policy_store."""
    try:
        fn(value)
    except ValueError as ex:
        return [f"{label}: {m}" for m in ex.args] or [f"{label}: invalid"]
    return []


def _check(label: str, spec: Spec, raw: Any) -> tuple:
    """Coerces and validates one value. Returns (value, errors)."""
    try:
        value = _coerce(spec, raw)
    except ValueError as ex:
        return None, [f"{label}: {ex}"]

    errors = []
    if spec.choices is not None:
        allowed = list(spec.choices)
        items = value if spec.type in JSON_TYPES else [value]
        errors += [f"{label}: {v!r} is not one of {allowed}"
                   for v in items if v not in allowed]

    if spec.min_value is not None or spec.max_value is not None:
        numeric = spec.type in (int, float)
        measure = value if numeric else len(value)
        what = "value" if numeric else "length"
        if spec.min_value is not None and measure < spec.min_value:
            errors.append(f"{label}: {what} {measure} is below the minimum "
                          f"{spec.min_value}")
        if spec.max_value is not None and measure > spec.max_value:
            errors.append(f"{label}: {what} {measure} is above the maximum "
                          f"{spec.max_value}")

    if spec.validator is not None and not errors:
        errors += run_validator(spec.validator, value, label)
    return value, errors


def _validated(values: dict) -> dict:
    """Coerces and validates a {key: value} mapping without writing.
    Raises SettingValidationError listing every problem."""
    errors, coerced = [], {}
    for key, raw in values.items():
        try:
            split_key(key)
        except ValueError as ex:
            errors.append(str(ex))
            continue
        spec = spec_for(key)
        if spec is None:
            errors.append(f"{key}: no such setting is declared (declare it "
                          f"with declare_group() before saving a value)")
            continue
        value, value_errors = _check(key, spec, raw)
        errors += value_errors
        if not value_errors:
            coerced[key] = value
    if errors:
        raise SettingValidationError(errors)
    return coerced


def validate_stored_settings() -> list:
    """Checks everything stored against the declarations, logging each
    problem. Called at startup, so a hand-edited or stale row is reported
    at boot rather than silently replaced by a default at read time."""
    problems = []
    for key, value in sorted(_current_snapshot().values.items()):
        spec = spec_for(key)
        if spec is None:
            problems.append(f"{key}: stored but not declared")
        else:
            problems += _check(key, spec, value)[1]
    for p in problems:
        logging.warning(f"Stored system setting is invalid: {p}")
    return problems


# ===================== Cache =====================

class _Snapshot:
    __slots__ = ("values", "provenance")

    def __init__(self, values: dict, provenance: dict = None):
        self.values = values
        # key -> (txn_login_id, upd_ts) of the stored row.
        self.provenance = provenance or {}


_EMPTY_SNAPSHOT = _Snapshot({})

_cache_lock = threading.RLock()
_cache: Optional[_Snapshot] = None
# Bumped by every invalidation, so a load that raced a write (a background
# job's thread) is not stored over the write's invalidation.
_generation = 0


def _load_values() -> _Snapshot:
    values, provenance = {}, {}
    query = (M.SystemSetting.select()
             .where(M.SystemSetting.is_deleted == False))  # noqa: E712
    for row in query:
        key = f"{row.group}.{row.name}"
        spec = spec_for(key)
        value = row.value
        if spec is not None:
            try:
                value = _coerce(spec, value)
            except ValueError as ex:
                logging.error(f"Stored value for {key} is unusable ({ex}); "
                              f"using the declared default instead.")
                continue
        values[key] = value
        provenance[key] = (row.txn_login_id, row.upd_ts)
    return _Snapshot(values, provenance)


def _cached_snapshot() -> _Snapshot:
    """The process-wide snapshot, loading it if a write dropped it."""
    global _cache
    with _cache_lock:
        if _cache is not None:
            return _cache
        generation = _generation
    try:
        snapshot = _load_values()
    except Exception:
        logging.exception("Could not read system settings; serving defaults.")
        return _EMPTY_SNAPSHOT
    logging.info(f"Loaded {len(snapshot.values)} system setting(s).")
    with _cache_lock:
        if generation == _generation:
            _cache = snapshot
    return snapshot


def _in_request() -> bool:
    # `g` lives on the app context, so both contexts must be pushed.
    return has_request_context() and has_app_context()


def _current_snapshot() -> _Snapshot:
    if not _in_request():
        return _cached_snapshot()
    snapshot = getattr(g, _G_ATTR, None)
    if snapshot is None:
        snapshot = _cached_snapshot()
        setattr(g, _G_ATTR, snapshot)
    return snapshot


def invalidate_cache() -> None:
    """Drops the cached settings and the request's pinned snapshot, so the
    next read loads what is now stored."""
    global _cache, _generation
    with _cache_lock:
        _cache = None
        _generation += 1
    if _in_request():
        g.pop(_G_ATTR, None)


# ===================== Read =====================

def setting(key: str, default: Any = _UNSET) -> Any:
    """Returns the effective value of a system setting.

    Args:
        key: "<group>.<name>", e.g. "enrolment.disable_fees_check".
        default: value to use when nothing is stored. Overrides the
            declared Spec default.

    Returns:
        The stored value; otherwise the default above; otherwise the
        Spec's default; otherwise None. Never raises.
    """
    spec = spec_for(key)
    if spec is None and key not in _WARNED_UNDECLARED:
        _WARNED_UNDECLARED.add(key)
        logging.warning(f"Setting {key!r} is read but not declared; it can "
                        f"only ever fall back to the caller's default.")

    values = _current_snapshot().values
    if key in values:
        # A copy: the cached list/dict is shared by every request.
        return copy.deepcopy(values[key])
    if not isinstance(default, _Unset):
        return default
    return copy.deepcopy(spec.default) if spec else None


def settings_in_group(group: str) -> dict:
    """All effective values for one group as {name: value}: declared
    defaults overlaid with whatever is stored."""
    gs = _REGISTRY.get(group)
    out = {name: spec.default for name, spec in (gs.specs.items() if gs else [])}
    prefix = f"{group}."
    for key, value in _current_snapshot().values.items():
        if key.startswith(prefix):
            out[key[len(prefix):]] = value
    return copy.deepcopy(out)


# ===================== Vocabularies =====================
# Controlled vocabularies are ordinary "vocab.<name>" settings: lists of
# {code, label, ...} declared below with vocab_defaults.py's lists as
# their defaults.

def vocab(name: str) -> list:
    """Effective items for one controlled vocabulary (vocab_defaults.ALL
    names the valid ones)."""
    return setting(f"vocab.{name}")


def vocab_codes(name: str) -> list:
    """Just the codes for one controlled vocabulary, in effective order."""
    return [item["code"] for item in vocab(name)]


def valid_grade_codes() -> list:
    return vocab_codes("grades")


def valid_audit_grade_codes() -> list:
    """Grade codes valid for an audited ('A') enrolment."""
    return [g["code"] for g in vocab("grades") if g.get("audit_ok")]


# ===================== Write =====================

def current_login_id() -> Optional[str]:
    """The logged-in user's id when called during a request, else None."""
    try:
        if has_request_context() and "user" in session:
            return session["user"].get("login_id")
    except RuntimeError:
        pass
    return None


def save_settings(values: dict, login_id: Optional[str] = None) -> dict:
    """Validates and stores several settings atomically: either every value
    is written or nothing is. Returns the coerced values as stored.

    Raises:
        SettingValidationError: if any value is invalid or undeclared.
    """
    coerced = _validated(values)
    if not coerced:
        return {}

    login_id = login_id or current_login_id()
    now = M.DT.now()
    with M.db.atomic():
        for key, value in coerced.items():
            group, name = split_key(key)
            (M.SystemSetting
             .insert(group=group, name=name, value=value,
                     txn_login_id=login_id, upd_ts=now)
             .on_conflict(
                 conflict_target=[M.SystemSetting.group, M.SystemSetting.name],
                 update={M.SystemSetting.value: value,
                         M.SystemSetting.is_deleted: False,
                         M.SystemSetting.txn_login_id: login_id,
                         M.SystemSetting.txn_no: M.SystemSetting.txn_no + 1,
                         M.SystemSetting.upd_ts: now})
             .execute())

    invalidate_cache()
    logging.info(f"Saved system setting(s) {sorted(coerced)} by {login_id}.")
    return coerced


def save_setting(key: str, value: Any, login_id: Optional[str] = None) -> Any:
    """Validates and stores one setting. See save_settings()."""
    return save_settings({key: value}, login_id=login_id)[key]


def delete_setting(key: str, login_id: Optional[str] = None) -> bool:
    """Removes the stored row for a key, so it reverts to its declared
    default. Returns True if a row was actually removed."""
    group, name = split_key(key)
    removed = (M.SystemSetting.delete()
               .where((M.SystemSetting.group == group) &
                      (M.SystemSetting.name == name)).execute())
    if removed:
        invalidate_cache()
        logging.info(f"Deleted system setting {key} by "
                     f"{login_id or current_login_id()}.")
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
        Spec("hide_stats_from", list, default=["STU"],
             choices=VD.codes("roles"),
             doc="Roles for which course offering stats are hidden."),
    ],
    doc="Course offering policy."
)

declare_group(
    "auth",
    [
        Spec("password_reset_lockout_attempts", int, default=4, min_value=1,
             doc="Lock the account once more than this many wrong "
                 "password-reset keys have been entered since the last "
                 "successful reset or unlock."),
        Spec("password_reset_key_ttl_mins", int, default=30, min_value=1,
             max_value=1440,
             doc="Minutes a password-reset key stays valid after it is "
                 "emailed."),
        Spec("password_reset_max_active_keys", int, default=5, min_value=1,
             doc="Refuse new password-reset key requests while this many "
                 "unexpired keys are outstanding for the account. Never "
                 "locks the account."),
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
        Spec("min_academic_year", int, default=2000, min_value=1,
             doc="Earliest calendar year accepted in a student entry year "
                 "or roll number (api_common.entry_years_valid/"
                 "roll_number_valid)."),
        Spec("max_academic_year", int, default=2099, min_value=1,
             doc="Latest calendar year accepted in a student entry year "
                 "or roll number (api_common.entry_years_valid/"
                 "roll_number_valid)."),
    ],
    doc="General application-wide operational settings."
)

declare_group(
    "course",
    [
        Spec("pg_course_min_leading_digit", int, default=5,
             min_value=1, max_value=9,
             doc="A course code's number is treated as a PG course "
                 "(domain.course.course_code_for_pg) when its leading "
                 "digit is at or above this. E.g. CS504, EE677 are PG "
                 "courses under the default of 5."),
    ],
    doc="Course classification policy."
)

declare_group(
    "faces",
    [
        Spec("match_tolerance", float, default=0.45,
             min_value=0.0, max_value=1.0,
             doc="Face-recognition match tolerance passed to frec_service; "
                 "lower is stricter."),
        Spec("request_timeout_secs", int, default=10, min_value=1,
             max_value=300,
             doc="Seconds to wait for frec_service to answer a request "
                 "before failing it."),
    ],
    doc="Photo-based attendance / face-recognition policy."
)

declare_group(
    "attendance",
    [
        Spec("min_percent_required", float, default=75.0,
             min_value=0.0, max_value=100.0,
             doc="Minimum attendance percentage a student is expected to "
                 "maintain per course enrolment. Purely informational: "
                 "surfaced as a warning wherever attendance is displayed "
                 "(sent to the frontend via static_data_dict()'s "
                 "MinAttendancePercentRequired), nothing is blocked by it "
                 "-- see domain/attendance.py for why this is an "
                 "operational setting rather than versioned policy."),
    ],
    doc="Minimum attendance policy."
)


def _validate_vocab_items(items):
    """Spec.validator for every "vocab.*" setting: each item is a
    {"code": str, "label": str, ...} object, codes unique within the list.
    Extra keys (e.g. grades' audit_ok) are the vocabulary's own business."""
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError(f"every item must be an object, got {item!r}")
        code, label = item.get("code"), item.get("label")
        if not isinstance(code, str) or not code:
            raise ValueError(f"item {item!r}: 'code' must be a non-empty string")
        if not isinstance(label, str) or not label:
            raise ValueError(f"item {item!r}: 'label' must be a non-empty string")
        if code in seen:
            raise ValueError(f"duplicate code {code!r}")
        seen.add(code)


declare_group(
    "vocab",
    [Spec(name, list, default=items,
          validator=_validate_vocab_items,
          doc=f"Controlled vocabulary: {name}.")
     for name, items in VD.ALL.items()],
    doc="Controlled vocabularies (degrees, roles, statuses, grades, ...). "
        "Seeded from vocab_defaults.py by default_seed_data.py; served to "
        "the frontend by api_common.static_data_dict()."
)
