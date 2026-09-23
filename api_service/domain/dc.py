"""Doctoral committee (DC) formation and approval.

Saving a DC runs it through the "dc" transition table
(:mod:`domain.workflow`): the supervisor drafts and submits it, the HoD
of the student's department forwards it to the Dean or returns it, the
Dean approves or returns it, and the academic section can move it
between any non-draft statuses. Which of those steps exist is data;
what is checked along the way -- committee composition, supervisor
eligibility, who may act for which student -- is registered here and
referenced from the table by name.

Creating a DC records the ``DC_PROPOSED`` milestone and approving it
records ``DC_APPROVED``; both are effects on the relevant rows, not
code paths.
"""

import logging

import peewee as ORM

import models as DB
from domain import milestones as MS
from domain import persistence
from domain import workflow as WF
from domain.context import Actor
from domain.errors import DomainError, PolicyViolation

DC = "dc"


# ============================== checks ==============================

@WF.check("dc.composition")
def _composition(ctx, rules=(), message="Invalid DC composition."):
    """Counts non-deleted members per DC role against ``rules``, each
    ``{"role": code, "min": n, "max": n}`` (either bound optional)."""
    members = [m for m in ctx.data.get("members") or []
               if not m.get("is_deleted")]
    for rule in rules:
        n = len([m for m in members if m.get("role") == rule["role"]])
        if n < rule.get("min", 0) or \
                ("max" in rule and n > rule["max"]):
            raise PolicyViolation(message)


@WF.check("dc.student_and_supervisor_selected")
def _selected(ctx):
    if not (ctx.data.get("sup_id") and ctx.data.get("stu_id")):
        raise PolicyViolation("Please select student AND supervisor!")


@WF.check("dc.supervisor_is_faculty")
def _supervisor_is_faculty(ctx, role="FAC"):
    if _user(ctx, "sup_id").role != role:
        raise PolicyViolation("Only a faculty can be the supervisor!")


@WF.check("dc.same_department")
def _same_department(ctx):
    if _user(ctx, "sup_id").person.dept_name != \
            _user(ctx, "stu_id").person.dept_name:
        raise PolicyViolation(
            "Supervisor and student must be from same department!")


@WF.check("dc.actor_is_supervisor")
def _actor_is_supervisor(ctx):
    if ctx.data.get("sup_id") != ctx.actor.user_id:
        raise PolicyViolation(
            "You must be the supervisor/HoD/Dean to make changes to this DC.")


@WF.check("dc.actor_in_student_dept")
def _actor_in_student_dept(ctx):
    if ctx.actor.dept_name != _user(ctx, "stu_id").person.dept_name:
        raise PolicyViolation(
            "Only HOD of student's own dept. can make changes!")


@WF.effect("milestone.record")
def _record_milestone(ctx, code):
    MS.record(ctx.actor, ctx.record.id, ctx.data["stu_id"], code)


def _user(ctx, key) -> DB.User:
    cache = ctx.facts.setdefault("_users", {})
    uid = ctx.data[key]
    if uid not in cache:
        cache[uid] = DB.User.get_by_id(uid)
    return cache[uid]


# ============================== the table ==============================

def _rows(start, permission, from_statuses, targets, checks=(), effects=None):
    """One row per (from, to) pair; ``targets`` maps status -> label."""
    effects = effects or {}
    rows, pri = [], start
    for f in from_statuses:
        for to, label in targets.items():
            if f == WF.NEW and to == WF.SAME:
                continue
            if f == to:
                continue  # covered by the "=" row, which records nothing
            eff = list(effects.get(to, ()))
            if f == WF.NEW:
                eff.append({"name": "milestone.record",
                            "params": {"code": MS.DC_PROPOSED}})
            rows.append(WF.Transition(
                priority=pri, from_status=f, to_status=to, label=label,
                permission=permission,
                checks=tuple(WF.Step.of(c) for c in checks),
                effects=tuple(WF.Step.of(e) for e in eff)))
            pri += 1
    return rows


_APPROVED = {"APP": [{"name": "milestone.record",
                      "params": {"code": MS.DC_APPROVED}}]}
_NON_DRAFT = ["SUB", "FTD", "RTS", "APP", "RTH", "DEL"]

BASELINE = WF.Workflow(
    name=DC,
    status_vocab="dc_statuses",
    match_on=WF.MATCH_ON_STATUS,
    locked_message=("Insufficient privileges to change this DC. "
                    "Please contact academic section."),
    denied_message="A DC in {from_label} cannot be moved to {to_label}.",
    pre_checks=(WF.Step("dc.composition", {
        "rules": [{"role": "SU", "min": 1, "max": 1},
                  {"role": "CP", "min": 1, "max": 1},
                  {"role": "ME", "min": 1}],
        "message": ("At least one DC member, supervisor and the DC "
                    "chairperson is required!")}),),
    checks=(WF.Step("dc.student_and_supervisor_selected"),
            WF.Step("dc.supervisor_is_faculty"),
            WF.Step("dc.same_department")),
    transitions=tuple(
        # Supervisor: drafts, submits to the HoD, deletes.
        _rows(100, "dc.edit_as_supervisor", [WF.NEW],
              {"DRA": "Save as Draft", "SUB": "Submit to HoD"},
              checks=["dc.actor_is_supervisor"])
        + _rows(110, "dc.edit_as_supervisor", ["DRA", "RTS"],
                {"DRA": "Save as Draft", "SUB": "Submit to HoD",
                 "DEL": "Delete", WF.SAME: "Save"},
                checks=["dc.actor_is_supervisor"])
        # HoD of the student's department: forwards or returns.
        + _rows(200, "dc.edit_as_hod", ["SUB", "RTH"],
                {"FTD": "Forward to Dean", "RTS": "Return to Supervisor",
                 WF.SAME: "Save"},
                checks=["dc.actor_in_student_dept"])
        # Dean: approves or returns to the HoD.
        + _rows(300, "dc.dean_approval", ["FTD"],
                {"APP": "Approve", "RTH": "Return to HoD", WF.SAME: "Save"},
                effects=_APPROVED)
        # Academic section: creates drafts, and moves any non-draft DC
        # to any other status.
        + _rows(400, "dc.override_status", [WF.NEW],
                {"DRA": "Save as Draft"})
        + _rows(410, "dc.override_status", _NON_DRAFT,
                {"APP": "Approve", "RTH": "Return to HoD",
                 "RTS": "Return to Supervisor", "DRA": "Save as Draft",
                 "DEL": "Delete", WF.SAME: "Save"},
                effects=_APPROVED)
    ),
)


def _status_counts() -> dict:
    qry = (DB.DcForStudent
           .select(DB.DcForStudent.status,
                   ORM.fn.COUNT(DB.DcForStudent.id).alias("n"))
           .group_by(DB.DcForStudent.status))
    return {r.status: r.n for r in qry}


WF.register_workflow(BASELINE, _status_counts)


# ============================== use cases ==============================

def _supervisor_id(members):
    sups = [m for m in members
            if m.get("role") == "SU" and not m.get("is_deleted")]
    return sups[0].get("user_id") if sups else None


def _raise_on_overlapping_dates(dc_id, stu_id, from_dt, to_dt):
    qry = DB.DcForStudent.select().where((DB.DcForStudent.id != dc_id) &
                                         (DB.DcForStudent.student == stu_id))
    if to_dt and to_dt != '0000-00-00':
        qry = qry.where(
            ((DB.DcForStudent.effective_from.between(from_dt, to_dt)) |
             (DB.DcForStudent.effective_to.between(from_dt, to_dt))))
    else:
        qry = qry.where((DB.DcForStudent.effective_to >= from_dt))

    if qry.exists():
        raise PolicyViolation(
            "DC dates overlap with an existing DC of the same student!")


def _save_members(actor, members, dc_id):
    for mem in members:
        is_del = mem.get("is_deleted") or False
        m_id = mem.get("id") or 0
        if is_del and m_id < 1:
            continue
        mod = DB.DcMember()
        mod.is_deleted = is_del
        mod.role = mem["role"]
        mod.is_external = mem.get("is_external") or False
        if mod.is_external:
            mod.ext_name = mem["ext_name"]
            mod.ext_contact = mem["ext_contact"]
        else:
            mod.member = int(mem["user_id"])
        mod.dc = dc_id
        mem_id_name = mem.get("org_id") or mem.get("ext_name")
        if m_id > 0:
            mod.id = int(m_id)
            mod.txn_no = int(mem["txn_no"])
            if persistence.update(DB.DcMember, mod, actor) != 1:
                raise DomainError(f"Could not update the DC member {mem_id_name}")
        else:
            persistence.save(mod, actor)
            if mod.id < 1:
                raise DomainError(f"Could not add the DC member {mem_id_name}")


def _context(actor, dc, members, stu_id, requested_status):
    old = dc.status if dc.id else None
    return WF.Context(
        actor=actor, from_status=old, record=dc,
        to_status=requested_status or old or "DRA",
        data={"members": members, "stu_id": stu_id,
              "sup_id": _supervisor_id(members)})


def save_dc(actor: Actor, form_data, update_model) -> int:
    """Creates or edits a DC, moving it through the "dc" workflow.

    Args:
        form_data: the submitted DC: ``id``, ``status``, ``student``
            ({"user_id"}), ``members``, effective dates, remarks.
        update_model: ``fn(model, dict)`` copying known fields from the
            form onto the model (``common.update_model_skip_unknown``).

    Returns the DC's id.
    """
    stu_id = (form_data.get("student") or {}).get("user_id")
    members = form_data.get("members") or []
    dc_id = int(form_data.get("id") or 0)
    dc = DB.DcForStudent.get_by_id(dc_id) if dc_id > 0 else DB.DcForStudent()

    wf = WF.load(DC)
    ctx = _context(actor, dc, members, stu_id, form_data.get("status"))
    WF.decide(wf, ctx)

    _raise_on_overlapping_dates(dc_id, stu_id, form_data.get("effective_from"),
                                form_data.get("effective_to"))

    logging.info("Saving DC details: {}".format(form_data))
    update_model(dc, form_data)
    dc.status = ctx.to_status
    dc.student = int(stu_id)

    with DB.db.atomic():
        if dc_id:
            if persistence.update(DB.DcForStudent, dc, actor) != 1:
                raise DomainError("Failed to save details. "
                                  "Please refresh and try again.")
        else:
            persistence.save(dc, actor)
        WF.run_effects(ctx)
        _save_members(actor, members, dc.id)
    return dc.id


def dc_actions(actor: Actor, dc_id) -> list:
    """Moves the actor may make on a DC (0 = a new one), for the UI."""
    dc = DB.DcForStudent.get_by_id(dc_id) if dc_id else DB.DcForStudent()
    ctx = WF.Context(actor=actor, from_status=dc.status if dc_id else None,
                     record=dc)
    return WF.available(WF.load(DC), ctx)
