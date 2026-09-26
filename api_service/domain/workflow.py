"""Declarative approval workflows: transitions as data, logic by name.

An approval workflow (enrolment, doctoral committee, course) is a table:
each row says *from* which status a record may move *to* which status,
which named permission that takes, which guards must hold for the row to
apply, which checks must pass before the move is made, and what happens
afterwards. An institution adds or removes an approval step by editing
rows (see :func:`save_workflow`), not code.

What stays in code, referenced from the rows by name:

* **Guards** -- ``fn(ctx) -> bool``. Decide whether a row *applies*
  ("is this user the course's coordinating instructor?"). A guard that
  fails just means "try the next row". Prefix a name with ``!`` to negate
  it.
* **Checks** -- ``fn(ctx, **params) -> None``, raising with a
  user-facing message. Decide whether an applicable move is *allowed
  right now* ("is the add/drop window open?"). A failed check ends the
  request; no other row is tried.
* **Effects** -- ``fn(ctx, **params) -> None``. Run after the record has
  been saved (emails, milestones).

Guards, checks and effects that need real queries live in the domain
module that owns the workflow and are registered with the decorators
below; institutions can register more from a plugin (see
:mod:`domain.plugins`).

How a request is resolved (:func:`select` then :func:`run_checks`):

1. The workflow's ``pre_checks`` run.
2. The rows leaving the record's current status whose permission the
   actor holds are collected. None at all: ``locked_message`` -- the
   record is not the actor's to change in this state.
3. The first of those, by ``priority``, that matches the request (the
   action named, or the status asked for) and whose guards all hold is
   taken. None: ``denied_message``.
4. The workflow's ``checks`` run, then the row's own ``checks``.

Each workflow ships a baseline table in code (the ``BASELINE`` its domain
module registers), which reproduces the pre-table behaviour. It is what
:func:`load` returns until a definition is stored, and what
``default_seed_data`` stores on first boot.
"""

import logging
from dataclasses import dataclass, field, replace
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import peewee as ORM

import models as M
import permissions as PERM
import settings_store as ST
from domain.context import Actor
from domain.errors import DomainError, PermissionDenied

#: ``from_status`` matching any existing status (never a new record).
ANY = "*"
#: ``from_status`` of a record that is being created.
NEW = "_new"
#: ``to_status`` meaning "stays where it is" (an edit, not a move).
SAME = "="

MATCH_ON_ACTION = "action"
MATCH_ON_STATUS = "to_status"


# ============================== data ==============================

@dataclass(frozen=True)
class Step:
    """A reference to a registered check or effect, with its parameters."""
    name: str
    params: dict = field(default_factory=dict)

    @classmethod
    def of(cls, raw) -> "Step":
        if isinstance(raw, Step):
            return raw
        if isinstance(raw, str):
            return cls(raw)
        return cls(raw["name"], dict(raw.get("params") or {}))

    def to_json(self) -> dict:
        return {"name": self.name, "params": dict(self.params)} \
            if self.params else {"name": self.name}


@dataclass(frozen=True)
class Transition:
    priority: int
    from_status: str
    to_status: str
    label: str
    permission: str
    action: Optional[str] = None
    guards: Tuple[str, ...] = ()
    checks: Tuple[Step, ...] = ()
    effects: Tuple[Step, ...] = ()
    is_active: bool = True

    def leaves(self, from_status: Optional[str]) -> bool:
        """Whether this row starts from ``from_status`` (None = new)."""
        if from_status is None:
            return self.from_status == NEW
        return self.from_status in (ANY, from_status)

    def target(self, from_status: Optional[str]) -> str:
        return from_status if self.to_status == SAME else self.to_status

    def changes_status(self) -> bool:
        return self.to_status != SAME

    def to_json(self) -> dict:
        return {
            "priority": self.priority, "from_status": self.from_status,
            "to_status": self.to_status, "action": self.action,
            "label": self.label, "permission": self.permission,
            "guards": list(self.guards),
            "checks": [s.to_json() for s in self.checks],
            "effects": [s.to_json() for s in self.effects],
            "is_active": self.is_active,
        }

    @classmethod
    def from_json(cls, d: dict) -> "Transition":
        return cls(
            priority=int(d["priority"]), from_status=d["from_status"],
            to_status=d["to_status"], action=d.get("action") or None,
            label=d.get("label") or "", permission=d["permission"],
            guards=tuple(d.get("guards") or ()),
            checks=tuple(Step.of(s) for s in d.get("checks") or ()),
            effects=tuple(Step.of(s) for s in d.get("effects") or ()),
            is_active=bool(d.get("is_active", True)))


@dataclass(frozen=True)
class Workflow:
    name: str
    status_vocab: str
    match_on: str
    locked_message: str
    denied_message: str
    transitions: Tuple[Transition, ...]
    pre_checks: Tuple[Step, ...] = ()
    checks: Tuple[Step, ...] = ()

    def active(self) -> List[Transition]:
        return sorted((t for t in self.transitions if t.is_active),
                      key=lambda t: t.priority)

    def to_json(self) -> dict:
        return {
            "name": self.name, "status_vocab": self.status_vocab,
            "match_on": self.match_on,
            "locked_message": self.locked_message,
            "denied_message": self.denied_message,
            "pre_checks": [s.to_json() for s in self.pre_checks],
            "checks": [s.to_json() for s in self.checks],
            "transitions": [t.to_json() for t in
                            sorted(self.transitions, key=lambda t: t.priority)],
        }

    @classmethod
    def from_json(cls, d: dict) -> "Workflow":
        return cls(
            name=d["name"], status_vocab=d["status_vocab"],
            match_on=d["match_on"], locked_message=d["locked_message"],
            denied_message=d["denied_message"],
            pre_checks=tuple(Step.of(s) for s in d.get("pre_checks") or ()),
            checks=tuple(Step.of(s) for s in d.get("checks") or ()),
            transitions=tuple(Transition.from_json(t)
                              for t in d.get("transitions") or ()))


@dataclass
class Context:
    """Everything a guard, check or effect may look at.

    ``facts`` carries values the owning domain module computed up front
    -- typically in one batched query for many records -- so guards stay
    cheap. ``data`` carries the request's payload (e.g. DC members).
    """
    actor: Actor
    from_status: Optional[str]
    record: object = None
    action: Optional[str] = None
    to_status: Optional[str] = None
    facts: dict = field(default_factory=dict)
    data: dict = field(default_factory=dict)
    transition: Optional[Transition] = None


# ============================== registries ==============================

_GUARDS: Dict[str, Callable] = {}
_CHECKS: Dict[str, Callable] = {}
_EFFECTS: Dict[str, Callable] = {}
_BASELINES: Dict[str, Workflow] = {}
_STATUS_COUNTERS: Dict[str, Callable] = {}


def guard(name: str) -> Callable:
    """Registers ``fn(ctx) -> bool`` under ``name``."""
    def decorate(fn):
        _GUARDS[name] = fn
        return fn
    return decorate


def check(name: str) -> Callable:
    """Registers ``fn(ctx, **params)``, which raises to refuse a move."""
    def decorate(fn):
        _CHECKS[name] = fn
        return fn
    return decorate


def effect(name: str) -> Callable:
    """Registers ``fn(ctx, **params)``, run after the record is saved."""
    def decorate(fn):
        _EFFECTS[name] = fn
        return fn
    return decorate


def register_workflow(baseline: Workflow,
                      status_counter: Callable[[], Dict[str, int]]) -> None:
    """Declares a workflow: its shipped baseline table, and a function
    returning ``{status: number of records in it}`` so edits that would
    strand records can be refused."""
    _BASELINES[baseline.name] = baseline
    _STATUS_COUNTERS[baseline.name] = status_counter


def _ensure_registered() -> None:
    # The workflows register themselves on import of their domain
    # module; importing them here (lazily -- they import this module)
    # guarantees the registries are complete wherever we are called from.
    from domain import course, dc, enrolment  # noqa: F401


def names() -> List[str]:
    _ensure_registered()
    return sorted(_BASELINES)


def registered_steps() -> dict:
    """Names available to a transition table, for the admin screen."""
    _ensure_registered()
    return {"guards": sorted(_GUARDS), "checks": sorted(_CHECKS),
            "effects": sorted(_EFFECTS)}


def baseline(name: str) -> Workflow:
    _ensure_registered()
    try:
        return _BASELINES[name]
    except KeyError:
        raise DomainError(f"Unknown workflow: {name}")


# ============================== loading ==============================

def load(name: str) -> Workflow:
    """The workflow in force: the stored definition if there is one,
    otherwise the baseline the code ships with (a fresh install before
    seeding, or a test database)."""
    base = baseline(name)
    try:
        wd = M.WorkflowDefinition.get_or_none(
            (M.WorkflowDefinition.name == name) &
            (M.WorkflowDefinition.is_deleted == False))  # noqa: E712
    except ORM.InterfaceError:
        # No database configured at all (pure unit tests, scripts).
        logging.warning(f"No database; using the baseline '{name}' workflow.")
        return base
    if wd is None:
        return base

    rows = (M.WorkflowTransition.select()
            .where((M.WorkflowTransition.workflow == name) &
                   (M.WorkflowTransition.is_deleted == False))  # noqa: E712
            .order_by(M.WorkflowTransition.priority))
    return Workflow(
        name=name, status_vocab=wd.status_vocab, match_on=wd.match_on,
        locked_message=wd.locked_message, denied_message=wd.denied_message,
        pre_checks=tuple(Step.of(s) for s in wd.pre_checks or ()),
        checks=tuple(Step.of(s) for s in wd.checks or ()),
        transitions=tuple(Transition(
            priority=r.priority, from_status=r.from_status,
            to_status=r.to_status, action=r.action, label=r.label,
            permission=r.permission, guards=tuple(r.guards or ()),
            checks=tuple(Step.of(s) for s in r.checks or ()),
            effects=tuple(Step.of(s) for s in r.effects or ()),
            is_active=r.is_active) for r in rows))


# ============================== resolving ==============================

def _guards_hold(t: Transition, ctx: Context) -> bool:
    for name in t.guards:
        negate = name.startswith("!")
        fn = _GUARDS[name.lstrip("!")]
        if bool(fn(ctx)) == negate:
            return False
    return True


def _matches_request(wf: Workflow, t: Transition, ctx: Context) -> bool:
    if wf.match_on == MATCH_ON_ACTION:
        return t.action == ctx.action
    return t.target(ctx.from_status) == ctx.to_status


def _run(steps: Sequence[Step], registry: Dict[str, Callable], ctx: Context):
    for step in steps:
        registry[step.name](ctx, **step.params)


def _message(template: str, ctx: Context, vocab: str) -> str:
    labels = {i["code"]: i["label"] for i in ST.vocab(vocab) or []}
    values = {
        "role": ctx.actor.role,
        "from_status": ctx.from_status or "",
        "to_status": ctx.to_status or "",
        "from_label": labels.get(ctx.from_status, ctx.from_status or "new"),
        "to_label": labels.get(ctx.to_status, ctx.to_status or ""),
    }
    try:
        return template.format(**values)
    except (KeyError, IndexError, ValueError):
        return template


def select(wf: Workflow, ctx: Context) -> Transition:
    """Steps 1-3 above: the transition this request takes.

    Sets ``ctx.transition`` and ``ctx.to_status``. Raises
    :class:`PermissionDenied` when no row applies.
    """
    _ensure_registered()
    _run(wf.pre_checks, _CHECKS, ctx)

    leaving = [t for t in wf.active()
               if t.leaves(ctx.from_status) and ctx.actor.can(t.permission)]
    if not leaving:
        raise PermissionDenied(_message(wf.locked_message, ctx,
                                        wf.status_vocab))

    for t in leaving:
        if _matches_request(wf, t, ctx) and _guards_hold(t, ctx):
            ctx.transition = t
            ctx.to_status = t.target(ctx.from_status)
            return t
    raise PermissionDenied(_message(wf.denied_message, ctx, wf.status_vocab))


def run_checks(wf: Workflow, ctx: Context) -> None:
    """Step 4 above: the workflow's checks, then the chosen row's."""
    _run(wf.checks, _CHECKS, ctx)
    _run(ctx.transition.checks, _CHECKS, ctx)


def decide(wf: Workflow, ctx: Context) -> Transition:
    """:func:`select` followed by :func:`run_checks`."""
    t = select(wf, ctx)
    run_checks(wf, ctx)
    return t


def run_effects(ctx: Context) -> None:
    """The chosen row's effects. Call after the record is saved."""
    _run(ctx.transition.effects, _EFFECTS, ctx)


def available(wf: Workflow, ctx: Context) -> List[dict]:
    """Moves the actor could make from the record's current status, for
    the frontend's action buttons. Guards are applied; checks are not
    (they may depend on what the user is about to submit)."""
    _ensure_registered()
    seen, out = set(), []
    for t in wf.active():
        if not (t.leaves(ctx.from_status) and ctx.actor.can(t.permission)):
            continue
        if not _guards_hold(t, ctx):
            continue
        key = t.action if wf.match_on == MATCH_ON_ACTION \
            else t.target(ctx.from_status)
        if key in seen:
            continue  # an earlier row already answers this request
        seen.add(key)
        out.append({"label": t.label, "action": t.action,
                    "to_status": t.target(ctx.from_status),
                    "changes_status": t.changes_status()})
    return out


# ============================== editing ==============================

def validate(wf: Workflow) -> List[str]:
    """Everything wrong with a workflow definition, as messages."""
    return [message for _, message in problems(wf)]


def problems(wf: Workflow) -> List[Tuple[Optional[int], str]]:
    """:func:`validate`'s messages, each paired with the index into
    ``wf.transitions`` of the row it is about (None for the workflow as a
    whole), so an editor can show it against that row."""
    _ensure_registered()
    errors = []
    if wf.name not in _BASELINES:
        errors.append((None, f"Unknown workflow: {wf.name}"))
    if wf.match_on not in (MATCH_ON_ACTION, MATCH_ON_STATUS):
        errors.append((None, f"match_on must be '{MATCH_ON_ACTION}' or "
                             f"'{MATCH_ON_STATUS}', not {wf.match_on!r}."))
    codes = set(ST.vocab_codes(wf.status_vocab) or [])
    if not codes:
        errors.append((None, f"Unknown status vocabulary: {wf.status_vocab}"))
    permissions = set(ST.declared_groups()[PERM.GROUP].specs)

    for step in wf.pre_checks + wf.checks:
        if step.name not in _CHECKS:
            errors.append((None, f"Unknown check: {step.name}"))

    priorities = set()
    for i, t in enumerate(wf.transitions):
        where = f"Transition {t.priority} ({t.from_status}->{t.to_status})"
        if t.priority in priorities:
            errors.append((i, f"{where}: duplicate priority."))
        priorities.add(t.priority)
        if t.from_status not in codes | {ANY, NEW}:
            errors.append((i, f"{where}: unknown from_status."))
        if t.to_status not in codes | {SAME}:
            errors.append((i, f"{where}: unknown to_status."))
        if t.to_status == SAME and t.from_status == NEW:
            errors.append((i, f"{where}: a new record has no status to keep."))
        if wf.match_on == MATCH_ON_ACTION and not t.action:
            errors.append((i, f"{where}: an action is required."))
        if t.permission not in permissions:
            errors.append((i, f"{where}: unknown permission {t.permission!r}."))
        for g in t.guards:
            if g.lstrip("!") not in _GUARDS:
                errors.append((i, f"{where}: unknown guard {g!r}."))
        for step in t.checks:
            if step.name not in _CHECKS:
                errors.append((i, f"{where}: unknown check {step.name!r}."))
        for step in t.effects:
            if step.name not in _EFFECTS:
                errors.append((i, f"{where}: unknown effect {step.name!r}."))
            elif step.name == "milestone.record":
                from domain import milestones as MS
                code = step.params.get("code")
                if code not in MS.codes():
                    errors.append((i, f"{where}: unknown milestone {code!r}."))
    return errors


def _exits(wf: Workflow) -> set:
    """Statuses a record can currently be moved out of."""
    out = set()
    for t in wf.active():
        if t.changes_status() and t.from_status not in (ANY, NEW):
            out.add(t.from_status)
    if any(t.changes_status() and t.from_status == ANY for t in wf.active()):
        out.add(ANY)
    return out


def stranded_statuses(old: Workflow, new: Workflow) -> Dict[str, int]:
    """Statuses that records sit in today, that could be left under the
    old table but cannot under the new one. Removing an approval step
    must not leave records stuck in it."""
    before, after = _exits(old), _exits(new)
    if ANY in after:
        return {}
    counts = _STATUS_COUNTERS[old.name]()
    return {s: n for s, n in counts.items()
            if n and (s in before or ANY in before) and s not in after}


class InvalidWorkflow(DomainError):
    """``errors`` are the messages; ``problems`` the same, each with the
    row it is about (see :func:`problems`); ``stranded`` the
    ``{status: record count}`` a refused edit would have stranded."""

    def __init__(self, errors, problems=None, stranded=None):
        self.errors = list(errors)
        self.problems = list(problems) if problems is not None \
            else [(None, e) for e in self.errors]
        self.stranded = dict(stranded or {})
        super().__init__("Invalid workflow definition: " + "; ".join(errors))


def store(wf: Workflow, login_id: str = "SYSTEM") -> None:
    """Writes ``wf`` as the stored definition, replacing any previous
    one. No validation or authorization -- see :func:`save_workflow`."""
    with M.db.atomic():
        M.WorkflowTransition.delete().where(
            M.WorkflowTransition.workflow == wf.name).execute()
        M.WorkflowDefinition.delete().where(
            M.WorkflowDefinition.name == wf.name).execute()
        M.WorkflowDefinition.create(
            name=wf.name, status_vocab=wf.status_vocab, match_on=wf.match_on,
            pre_checks=[s.to_json() for s in wf.pre_checks],
            checks=[s.to_json() for s in wf.checks],
            locked_message=wf.locked_message,
            denied_message=wf.denied_message, txn_login_id=login_id)
        for t in wf.transitions:
            row = t.to_json()
            M.WorkflowTransition.create(workflow=wf.name,
                                        txn_login_id=login_id, **row)


def _parse(definition: dict) -> Workflow:
    """:meth:`Workflow.from_json`, raising :class:`InvalidWorkflow` naming
    the row at fault (a missing field, a non-numeric priority) rather
    than a bare KeyError/ValueError."""
    found = []
    for i, row in enumerate(definition.get("transitions") or ()):
        if not isinstance(row, dict):
            found.append((i, f"Row {i + 1}: expected an object."))
            continue
        try:
            int(row.get("priority"))
        except (TypeError, ValueError):
            found.append((i, f"Row {i + 1}: priority must be a whole "
                             f"number."))
            continue
        try:
            Transition.from_json(row)
        except KeyError as ex:
            found.append((i, f"Row {i + 1}: '{ex.args[0]}' is required."))
        except (TypeError, ValueError) as ex:
            found.append((i, f"Row {i + 1}: {ex}"))
    if not found:
        try:
            return Workflow.from_json(definition)
        except KeyError as ex:
            found.append((None, f"'{ex.args[0]}' is required."))
        except (TypeError, ValueError) as ex:
            found.append((None, str(ex)))
    raise InvalidWorkflow([m for _, m in found], problems=found)


def save_workflow(actor: Actor, definition: dict) -> Workflow:
    """Replaces a workflow's stored definition, after validating it and
    refusing any edit that would strand records in a status they could
    no longer leave."""
    if not actor.can("system.manage_workflows"):
        raise PermissionDenied("You are not allowed to edit workflows.")
    wf = _parse(definition)
    found = problems(wf)
    if found:
        raise InvalidWorkflow([m for _, m in found], problems=found)
    stranded = stranded_statuses(load(wf.name), wf)
    if stranded:
        detail = ", ".join(f"{s} ({n})" for s, n in sorted(stranded.items()))
        raise InvalidWorkflow([
            f"Records would be left in a status they can no longer leave: "
            f"{detail}. Move them on first, or keep a transition out of "
            f"that status."], stranded=stranded)
    store(wf, login_id=actor.login_id)
    logging.info(f"Workflow '{wf.name}' updated by {actor.describe()}.")
    return load(wf.name)


def expand(template: dict, from_statuses: Sequence[str],
           to_statuses: Sequence[str], start: int, step: int = 1,
           labels: Optional[dict] = None) -> List[Transition]:
    """Builds one row per (from, to) pair from a template, numbering
    priorities from ``start``. For writing baselines compactly."""
    rows, pri = [], start
    for f in from_statuses:
        for t in to_statuses:
            d = dict(template, from_status=f, to_status=t, priority=pri)
            if labels and t in labels:
                d["label"] = labels[t]
            rows.append(Transition.from_json(d))
            pri += step
    return rows


def with_effects(t: Transition, *effects) -> Transition:
    return replace(t, effects=t.effects + tuple(Step.of(e) for e in effects))
