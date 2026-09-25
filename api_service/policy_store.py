"""Effective-dated academic policy: versioned rulesets keyed on session.

The problem this exists for
---------------------------
``compute_cgpa_sgpa_ec`` (domain/transcript.py) carries a grade ->
point map, three earned-credit grade sets, and a policy amendment
implemented as a hardcoded branch on the year ("Adjustment for PhD
passing grades introduced in 2021"). That branch is the proof that
academic policy cannot simply be *replaced*: a 2019 transcript must keep
computing under the 2019 rules forever. Policy is therefore not a
setting you overwrite, it is a series of versions each of which owns a
range of academic sessions.

The model
---------
A **policy group** (e.g. ``"grading"``) has an ordered series of
**versions**. Each version states the session it takes effect from and
carries the whole ruleset as one JSON document. A version is in force
until the next version of the same group begins.

A version is in force for an **instant** on the shared monthly timeline
``acad_session.py`` defines, not for a named session, and a session takes
the ruleset in force at the month it begins. That is what lets one version
govern concurrent sessions in different academic calendars (``2021-I`` and
``2021-T1`` begin together), and what makes a change landing mid-session
well defined: the running session keeps its rules, the next one picks the
new ones up.

    grading @ 2000-T1  ---------------------------> [ in force ]
    grading @ 2021-I   ------------> [ in force from 2021-I ]
    grading @ 2024-II  --> [ in force from 2024-II, open-ended ]

The end of a range is **derived, never stored**. That is not a
space-saving trick, it is the whole immutability mechanism: adding a
version inserts exactly one row and updates none, so no existing row's
content ever changes. Storing an ``effective_to`` would force every
supersede to UPDATE its predecessor -- the very mutation we are
preventing.

Immutability
------------
Closing an academic session (:func:`close_session`) draws a **seal line**
at that session's ordinal. From then on:

* policy effective from at or before the line cannot be updated or
  deleted, and
* no new policy may be introduced effective from at or before it.

Everything after the line stays editable, so next year's not-yet-
effective ruleset can still be corrected. Closure records are append-only
too, so the line only ever advances. The rule is enforced twice:

1. here, in :func:`supersede`, before anything is written, with the
   message an admin should see;
2. in Postgres triggers (``migrations/0001_baseline.sql``), which nothing
   can go around: hand-written SQL (which this codebase does execute),
   ORM ``save()``/``delete_instance()`` on any model instance, bulk
   ``.update()``/``.delete()`` queries, and psql.

A trigger refusal is reported as :class:`PolicyImmutableError` by
:func:`_trigger_refusals_as_policy_errors`, the one place that
translation happens.

An admin editing the grade point map through the GUI therefore cannot
silently recompute historical transcripts. The worst they can do is
introduce a version effective from an open session.

Resolution cost
---------------
Transcript building calls resolution per course, so it must not query.
The whole policy table is tiny and append-only (tens of rows for the
life of an institution), so the entire set is cached in the process and
resolution is a binary search over an ordinal list -- no query, no
allocation. The cache is keyed on the same monotonic
``_sys.policy_version`` counter that ``settings_store`` uses, and every
policy write bumps it inside the writing transaction, so a worker that
can see the new version can by definition see the rows it wrote. Sharing
one counter across both stores means one extra (tiny) reload when the
other store is written; that is the price of having a single answer to
"is my cached configuration current?".

Relationship to SystemSetting
-----------------------------
Separate concept, separate table. The test for where something belongs:
*if an admin changes this, must already-issued documents change too?* If
no, it is an operational knob and belongs in ``settings_store``. If yes,
and that would be wrong, it is policy of record and belongs here. See
docs/versioned-policy.md for the full argument.

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__status__ = "Development"
"""

import bisect
import contextlib
import copy
import logging
import threading
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable, Mapping, Optional

import peewee

import acad_session as AS
import models as M
import settings_store as SS
from common import AcadStackException


# ===================== Errors =====================

class PolicyError(AcadStackException):
    """Base for policy-store failures. Subclasses AcadStackException, so
    existing route handlers already surface the message to the client."""


class PolicyImmutableError(PolicyError):
    """A write was refused because it would alter sealed history, whether
    :func:`supersede` refused it or a database trigger did."""


class PolicyNotFoundError(PolicyError):
    """No version of the requested group is in force for that session."""


class PolicyValidationError(PolicyError):
    """A proposed ruleset failed its group's declared validation. Carries
    every problem found, so an admin GUI can show them all at once."""

    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


# ===================== Declaration =====================

@dataclass(frozen=True)
class PolicyGroupSpec:
    """Declares one policy group.

    Args:
        name: group name as stored in ``PolicyVersion.policy_group``.
        doc: human-readable description, for an admin GUI.
        builder: ``callable(payload) -> object`` turning a stored JSON
            payload into the typed, immutable object domain code wants
            (e.g. a frozen dataclass). Called with a deeply read-only
            view of the payload. Its success is part of write-time
            validation: a payload that cannot be built is not stored.
        validator: ``callable(payload)`` for checks the builder does not
            make. Raises ValueError to reject, one message per argument --
            the settings_store.Spec.validator convention.
    """

    name: str
    doc: str = ""
    builder: Optional[Callable[[Mapping], Any]] = None
    validator: Optional[Callable[[Mapping], Any]] = None


_REGISTRY: dict = {}


def declare_policy_group(name: str, doc: str = "",
                         builder: Optional[Callable] = None,
                         validator: Optional[Callable] = None
                         ) -> PolicyGroupSpec:
    """Registers a policy group. Call at import time, from the module
    that owns the typed policy object the builder produces."""
    if not name or not isinstance(name, str):
        raise ValueError(f"Invalid policy group name: {name!r}")
    spec = PolicyGroupSpec(name=name, doc=doc, builder=builder,
                           validator=validator)
    _REGISTRY[name] = spec
    # A group declared after a snapshot was built would otherwise serve
    # unbuilt values until the next version bump.
    invalidate_cache()
    return spec


def declared_groups() -> dict:
    return dict(_REGISTRY)


def spec_for(group: str) -> Optional[PolicyGroupSpec]:
    return _REGISTRY.get(group)


# ===================== Read-only payload views =====================

def _freeze(value):
    """Deep read-only view of a JSON-shaped value.

    Resolution is on the per-course hot path, so it must not deep-copy a
    payload per call. Handing out a shared mutable dict instead would let
    one caller's edit leak into every later resolution in the worker, so
    what is shared is frozen: dicts become mapping proxies and lists
    become tuples, once, when the snapshot loads.
    """
    if isinstance(value, dict):
        return MappingProxyType({k: _freeze(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v) for v in value)
    return value


def _thaw(value):
    """Mutable deep copy of a frozen payload, for a caller that wants to
    edit a ruleset before superseding with it."""
    if isinstance(value, (MappingProxyType, dict)):
        return {k: _thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_thaw(v) for v in value]
    return copy.deepcopy(value)


@dataclass(frozen=True)
class ResolvedPolicy:
    """One version of a group, with the session range it governs.

    ``effective_to`` is the session at which the NEXT version takes over
    (exclusive), or None when this is the latest version and the range is
    still open. It is computed from the neighbouring rows, never stored.
    """

    group: str
    version_id: int
    effective_from: str
    effective_from_ord: int
    effective_to: Optional[str]
    effective_to_ord: Optional[int]
    payload: Mapping
    note: Optional[str] = None
    recorded_by: Optional[str] = None
    recorded_ts: Any = None
    is_sealed: bool = False

    def payload_dict(self) -> dict:
        """A mutable deep copy of the payload, safe to edit and pass back
        to :func:`supersede`."""
        return _thaw(self.payload)

    def covers(self, acad_session: str) -> bool:
        o = AS.ordinal(acad_session)
        return (o >= self.effective_from_ord and
                (self.effective_to_ord is None or o < self.effective_to_ord))

    def __str__(self):
        to = self.effective_to or "(open)"
        return f"{self.group}[{self.effective_from} -> {to})"


# ===================== Cache =====================

class _Snapshot:
    """Every policy version and closed session, as of one policy version
    number. Small enough to hold entirely: policy rows accumulate at the
    rate an institution amends its regulations."""

    __slots__ = ("version", "by_group", "ords_by_group", "closed",
                 "closed_set", "seal_ord", "_built", "_build_lock")

    def __init__(self, version):
        self.version = version
        # group -> list[ResolvedPolicy], ascending by effective_from_ord
        self.by_group: dict = {}
        # group -> list[int], the same rows' ordinals (for bisect)
        self.ords_by_group: dict = {}
        self.closed: list = []
        # Session STRINGS, not ordinals: concurrent sessions in different
        # academic calendars share an ordinal, so an ordinal set would
        # report 2021-T1 as closed because 2021-I was.
        self.closed_set: set = set()
        self.seal_ord = None
        # version_id -> built typed object. Built on demand so that an
        # unused group's builder never runs, and a broken builder cannot
        # poison the whole snapshot at load time.
        self._built: dict = {}
        self._build_lock = threading.Lock()


_EMPTY_SNAPSHOT = _Snapshot(-1)

_cache_lock = threading.RLock()
_cache: Optional[_Snapshot] = None


def _load_snapshot(version: int) -> _Snapshot:
    snap = _Snapshot(version)

    closed_rows = M.ClosedAcademicSession.select()
    for row in closed_rows:
        snap.closed_set.add(row.acad_session)
        if snap.seal_ord is None or row.session_ord > snap.seal_ord:
            snap.seal_ord = row.session_ord
    # Sorted in Python: ordering by session_ord alone is not deterministic
    # now that concurrent sessions tie on it.
    snap.closed = AS.sorted_sessions(snap.closed_set)

    rows = (M.PolicyVersion
            .select()
            .where(M.PolicyVersion.is_deleted == False)  # noqa: E712
            .order_by(M.PolicyVersion.policy_group,
                      M.PolicyVersion.effective_from_ord))
    grouped: dict = {}
    for row in rows:
        grouped.setdefault(row.policy_group, []).append(row)

    for group, group_rows in grouped.items():
        resolved = []
        for i, row in enumerate(group_rows):
            nxt = group_rows[i + 1] if i + 1 < len(group_rows) else None
            resolved.append(ResolvedPolicy(
                group=group,
                version_id=row.id,
                effective_from=row.effective_from_session,
                effective_from_ord=row.effective_from_ord,
                effective_to=nxt.effective_from_session if nxt else None,
                effective_to_ord=nxt.effective_from_ord if nxt else None,
                payload=_freeze(row.payload or {}),
                note=row.note,
                recorded_by=row.txn_login_id,
                recorded_ts=row.ins_ts,
                is_sealed=(snap.seal_ord is not None and
                           snap.seal_ord >= row.effective_from_ord),
            ))
        snap.by_group[group] = resolved
        snap.ords_by_group[group] = [r.effective_from_ord for r in resolved]

    return snap


def _current_snapshot() -> _Snapshot:
    """The policy set matching the configuration version currently being
    served.

    The version number comes from ``settings_store``, which already pins
    it on ``quart.g`` for the duration of a request and rate-limits the
    check outside one -- so on the per-course hot path this costs a dict
    lookup, not a query.
    """
    global _cache
    try:
        version = SS.policy_version()
    except Exception:
        logging.exception("Could not read the policy version; serving the "
                          "last known policy.")
        with _cache_lock:
            return _cache or _EMPTY_SNAPSHOT

    with _cache_lock:
        cached = _cache
    if cached is not None and cached.version == version:
        return cached

    try:
        # Loaded outside the lock: two threads racing here just do the
        # same idempotent read twice.
        snap = _load_snapshot(version)
    except Exception:
        logging.exception("Could not load versioned policy; serving the last "
                          "known policy.")
        with _cache_lock:
            return _cache or _EMPTY_SNAPSHOT

    with _cache_lock:
        _cache = snap
    logging.info(f"Loaded policy versions for {len(snap.by_group)} group(s) "
                 f"at policy version {version}.")
    return snap


def invalidate_cache() -> None:
    """Drops this process's cached policy. Writes call this; other workers
    pick the change up via the shared policy version."""
    global _cache
    with _cache_lock:
        _cache = None


# ===================== Read =====================

def resolve(group: str, acad_session: str) -> ResolvedPolicy:
    """The version of ``group`` in force for ``acad_session``.

    Binary search over the group's effective-from ordinals: no query, and
    no dependence on how many versions exist.

    Raises:
        InvalidAcadSession: if the session string is malformed.
        PolicyNotFoundError: if the group has no version covering it.
    """
    ord_value = AS.ordinal(acad_session)
    snap = _current_snapshot()

    ords = snap.ords_by_group.get(group)
    if not ords:
        raise PolicyNotFoundError(
            f"No policy is recorded for group {group!r}.")

    # bisect_right - 1 gives the last version whose effective_from is at
    # or before this session: exactly "the one in force".
    idx = bisect.bisect_right(ords, ord_value) - 1
    if idx < 0:
        first = snap.by_group[group][0].effective_from
        raise PolicyNotFoundError(
            f"No policy for group {group!r} is in force for {acad_session}: "
            f"the earliest recorded version takes effect from {first}.")

    return snap.by_group[group][idx]


def policy_for(group: str, acad_session: str) -> Any:
    """The group's ruleset for a session, as the typed object the group's
    builder produces (or the read-only payload if it declared none).

    This is the call transcript building makes per course. The built
    object is memoised per version, so the builder runs at most once per
    version per worker, not once per course.
    """
    resolved = resolve(group, acad_session)
    return built_value(resolved)


def built_value(resolved: ResolvedPolicy) -> Any:
    """The typed object for an already-resolved version, memoised."""
    spec = _REGISTRY.get(resolved.group)
    if spec is None or spec.builder is None:
        return resolved.payload

    snap = _current_snapshot()
    key = resolved.version_id
    built = snap._built.get(key)
    if built is not None:
        return built

    with snap._build_lock:
        built = snap._built.get(key)
        if built is None:
            try:
                built = spec.builder(resolved.payload)
            except Exception as ex:
                # Stored payloads are builder-validated on write, so this
                # means the builder changed under existing data.
                raise PolicyValidationError(
                    [f"Stored policy {resolved} cannot be built into its "
                     f"typed form: {ex}"]) from ex
            snap._built[key] = built
    return built


def versions(group: str) -> list:
    """Every recorded version of a group, oldest first, each with the
    session range it governs."""
    return list(_current_snapshot().by_group.get(group, []))


# ===================== Session closure =====================

def closed_sessions() -> list:
    """Closed sessions, chronologically."""
    return list(_current_snapshot().closed)


def is_session_closed(acad_session: str) -> bool:
    """Whether THIS session has been closed.

    Matched on the session itself, not its ordinal: a concurrent session
    in another calendar shares the ordinal but is closed separately. For
    "is policy from here already final", which IS an ordinal question, use
    :func:`is_sealed`.
    """
    AS.parse(acad_session)  # reject malformed input rather than say "no"
    return acad_session in _current_snapshot().closed_set


def seal_line() -> Optional[str]:
    """Every closed session sitting on the seal line, named, or None.

    The seal is a point on the timeline rather than one session, so more
    than one session can be on it (see acad_session.py).
    """
    snap = _current_snapshot()
    if snap.seal_ord is None:
        return None
    at_seal = [s for s in snap.closed if AS.ordinal(s) == snap.seal_ord]
    return " / ".join(at_seal) if at_seal else None


def is_sealed(acad_session: str) -> bool:
    """Whether policy effective from this session is already final,
    i.e. whether this session is at or before the seal line."""
    seal = _current_snapshot().seal_ord
    return seal is not None and AS.ordinal(acad_session) <= seal


def close_session(acad_session: str, note: Optional[str] = None,
                  login_id: Optional[str] = None):
    """Records an academic session as closed, sealing the policy that was
    in force for it.

    Idempotent: closing an already-closed session returns the existing
    record. Closure is irreversible by design (see the append-only
    trigger in migrations/0001_baseline.sql), so this is the one call in
    the module that cannot be undone.
    """
    ord_value = _session_ordinal_or_error(acad_session)

    existing = M.ClosedAcademicSession.get_or_none(
        M.ClosedAcademicSession.acad_session == acad_session)
    if existing is not None:
        return existing

    login_id = login_id or SS.current_login_id()
    with M.db.atomic():
        row = M.ClosedAcademicSession.create(
            acad_session=acad_session, session_ord=ord_value, note=note,
            txn_login_id=login_id)
        version = SS.bump_policy_version()

    _invalidate_all()
    sealed = [g for g in _current_snapshot().by_group]
    logging.info(f"Academic session {acad_session} closed by {login_id}; "
                 f"policy for group(s) {sorted(sealed)} effective up to it is "
                 f"now final. Policy version {version}.")
    return row


# ===================== Write =====================

#: SQLSTATE of plpgsql's bare ``RAISE EXCEPTION`` ("raise_exception").
#: The sealing triggers in migrations/0001_baseline.sql are the only code
#: in the schema that raises it; everything else there names a specific
#: SQLSTATE (check_violation, invalid_parameter_value, ...).
_TRIGGER_REFUSAL_SQLSTATE = "P0001"


@contextlib.contextmanager
def _trigger_refusals_as_policy_errors():
    """Reports a sealing trigger's refusal as :class:`PolicyImmutableError`,
    carrying the trigger's own message, so it reaches the client like any
    other rejected admin input instead of as an unexpected server error.

    Enter it OUTSIDE the ``atomic()`` block, so the failed transaction has
    been rolled back before the error propagates.
    """
    try:
        yield
    except peewee.DatabaseError as ex:
        # peewee re-raises the psycopg2 error as its own type while
        # handling it, so the original is the implicit context.
        orig = ex.__context__
        if getattr(orig, "pgcode", None) != _TRIGGER_REFUSAL_SQLSTATE:
            raise
        raise PolicyImmutableError(orig.diag.message_primary) from ex


def _invalidate_all() -> None:
    """Both stores share the version counter, so both caches drop."""
    SS.invalidate_cache()
    invalidate_cache()


def _session_ordinal_or_error(acad_session: str) -> int:
    """Session ordinal, reporting a malformed session as a PolicyError.

    Read paths let ``InvalidAcadSession`` (a ValueError) through, because
    there it means stored data or caller code is wrong. On the two write
    paths the session string comes from a human, so it is reported the
    way every other rejected admin input is.
    """
    try:
        return AS.ordinal(acad_session)
    except AS.InvalidAcadSession as ex:
        raise PolicyValidationError([str(ex)]) from ex


def validate_payload(group: str, payload) -> Mapping:
    """Checks a proposed ruleset without storing it. Returns the frozen
    payload that would be stored.

    Raises:
        PolicyValidationError: with every problem found.
    """
    spec = _REGISTRY.get(group)
    if spec is None:
        raise PolicyValidationError(
            [f"Policy group {group!r} is not declared. Declare it with "
             f"declare_policy_group() before storing versions of it."])

    if not isinstance(payload, dict):
        raise PolicyValidationError(
            [f"{group}: a policy payload must be a JSON object, got "
             f"{type(payload).__name__}."])

    frozen = _freeze(payload)
    errors = []

    # The validator goes first and lists every problem; the builder only
    # runs on a payload the validator passed, so a builder is free to
    # assume the shape and a problem is not reported twice.
    if spec.validator is not None:
        errors.extend(SS.run_validator(spec.validator, frozen, group))

    if spec.builder is not None and not errors:
        try:
            spec.builder(frozen)
        except Exception as ex:
            errors.append(f"{group}: payload cannot be built into its typed "
                          f"form: {ex}")

    if errors:
        raise PolicyValidationError(errors)
    return frozen


def supersede(group: str, effective_from_session: str, payload: dict,
              note: Optional[str] = None, login_id: Optional[str] = None):
    """Adds a new version of a policy group, in force from a session.

    This is the ONLY write operation on policy. There is no update and no
    delete: superseding inserts one row and leaves every existing row
    untouched, so the ruleset any already-computed result was produced
    under is still there, unchanged, and still resolvable.

    Args:
        group: a declared policy group.
        effective_from_session: the session this ruleset takes effect
            from. Must be after the last closed session.
        payload: the complete ruleset, as a JSON object. Complete, not a
            patch: a version has to be independently resolvable years
            later without replaying the ones before it.
        note: the authority for the change (circular/minute number).

    Raises:
        InvalidAcadSession: malformed session string.
        PolicyValidationError: payload rejected by the group's builder or
            validator, or the group is undeclared.
        PolicyImmutableError: the session is at or before the seal line,
            or a version already exists at that session for this group.
    """
    ord_value = _session_ordinal_or_error(effective_from_session)
    validate_payload(group, payload)

    if is_sealed(effective_from_session):
        raise PolicyImmutableError(
            f"Cannot make policy for group {group!r} effective from "
            f"{effective_from_session}: academic sessions up to "
            f"{seal_line()} are closed and their results were "
            f"computed under the policy then in force. New policy must take "
            f"effect from a session that is still open.")

    clash = M.PolicyVersion.get_or_none(
        (M.PolicyVersion.policy_group == group) &
        (M.PolicyVersion.effective_from_ord == ord_value))
    if clash is not None:
        raise PolicyImmutableError(
            f"A version of {group!r} effective from "
            f"{effective_from_session} already exists (id {clash.id}). "
            f"Supersede it from a later session rather than replacing it.")

    login_id = login_id or SS.current_login_id()
    # The check above reads this worker's cached snapshot, so a session
    # closed by another worker a moment ago can slip past it; the insert
    # trigger still refuses the row, and this reports it the same way.
    with _trigger_refusals_as_policy_errors(), M.db.atomic():
        row = M.PolicyVersion.create(
            policy_group=group,
            effective_from_session=effective_from_session,
            effective_from_ord=ord_value,
            payload=payload,
            note=note,
            txn_login_id=login_id)
        version = SS.bump_policy_version()

    _invalidate_all()
    logging.info(f"Stored policy {group!r} effective from "
                 f"{effective_from_session} (id {row.id}) by {login_id}; "
                 f"policy version now {version}.")
    return row
