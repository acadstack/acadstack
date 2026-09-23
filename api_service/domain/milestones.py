"""Academic milestones: the configured sequence, and recording one.

The PhD milestone sequence used to exist only as a comment on the
``AcademicMilestone`` model, while call sites wrote free-text strings
("DC Proposed", "DC Approved"). The sequence is now
``MilestoneDefinition`` rows; an ``AcademicMilestone`` stores one of
their codes, and recording an unknown or retired code is refused.

As with the workflows, :data:`BASELINE` is the sequence the code ships
with: it answers until definitions are stored, and ``default_seed_data``
stores it on first boot.
"""

import logging
from typing import List

import peewee as ORM

import models as M
from domain import persistence
from domain.context import Actor
from domain.errors import PermissionDenied, PolicyViolation

DC_PROPOSED = "DC_PROPOSED"
DC_APPROVED = "DC_APPROVED"

#: (code, label, sequence, applies_to)
BASELINE = [
    ("JOINING", "Joining", 10, "PHD"),
    (DC_PROPOSED, "DC Proposed", 20, "PHD"),
    (DC_APPROVED, "DC Approved", 30, "PHD"),
    ("COMPRE", "Comprehensive Exam", 40, "PHD"),
    ("TP", "TP", 50, "PHD"),
    ("OPEN_SEMINAR_1", "Open Seminar 1", 60, "PHD"),
    ("OPEN_SEMINAR_2", "Open Seminar 2", 70, "PHD"),
    ("SYNOPSIS", "Synopsis", 80, "PHD"),
    ("THESIS_SUBMITTED", "Thesis Submitted", 90, "PHD"),
    ("DEFENCE", "Defence", 100, "PHD"),
    ("AWARDED", "Degree Awarded", 110, "PHD"),
]


def seed_rows() -> list:
    return [dict(code=c, label=l, sequence=s, applies_to=a)
            for c, l, s, a in BASELINE]


def definitions() -> List[dict]:
    """Active milestone definitions in sequence order: stored ones if any
    are stored, else the baseline."""
    try:
        rows = list(M.MilestoneDefinition.select()
                    .where((M.MilestoneDefinition.is_deleted == False) &  # noqa: E712
                           (M.MilestoneDefinition.is_active == True))  # noqa: E712
                    .order_by(M.MilestoneDefinition.sequence))
        stored_any = M.MilestoneDefinition.select().exists()
    except ORM.InterfaceError:
        rows, stored_any = [], False
    if stored_any:
        return [dict(code=r.code, label=r.label, sequence=r.sequence,
                     applies_to=r.applies_to) for r in rows]
    return seed_rows()


def codes() -> List[str]:
    return [d["code"] for d in definitions()]


def record(actor: Actor, dc_id, student_id, code) -> M.AcademicMilestone:
    """Records that ``student_id`` reached milestone ``code``.

    Idempotent: a DC approved, returned and approved again has reached
    DC_APPROVED once, and the (dc, student, milestone) unique index
    would otherwise fail the second approval.
    """
    if code not in codes():
        raise PolicyViolation(f"Unknown academic milestone: {code}")
    existing = M.AcademicMilestone.get_or_none(
        (M.AcademicMilestone.dc == dc_id) &
        (M.AcademicMilestone.student == student_id) &
        (M.AcademicMilestone.milestone == code))
    if existing:
        return existing
    amo = M.AcademicMilestone(dc=dc_id, student=student_id, milestone=code)
    persistence.save(amo, actor)
    logging.debug(f"Recorded milestone {code} for student {student_id}.")
    return amo


def save_definitions(actor: Actor, items: list) -> List[dict]:
    """Replaces the milestone sequence. Refuses to drop a code that a
    student has already reached or that a workflow still records --
    retire it with ``is_active: false`` instead."""
    from domain import workflow as WF
    if not actor.can("system.manage_workflows"):
        raise PermissionDenied("You are not allowed to edit milestones.")

    seen, errors = set(), []
    for it in items:
        code = (it.get("code") or "").strip()
        if not code or not it.get("label") or it.get("sequence") is None:
            errors.append(f"Milestone {code or '?'}: code, label and "
                          f"sequence are required.")
        if code in seen:
            errors.append(f"Milestone {code}: duplicate code.")
        seen.add(code)

    stored = {r.code for r in M.MilestoneDefinition.select()}
    dropped = (stored or set(codes())) - seen
    used = {r.milestone for r in M.AcademicMilestone.select(
        M.AcademicMilestone.milestone).distinct()}
    for code in sorted(dropped & used):
        errors.append(f"Milestone {code} has been reached by students; "
                      f"mark it inactive instead of removing it.")
    active = {(it.get("code") or "").strip() for it in items
              if it.get("is_active", True)}
    for name in WF.names():
        for t in WF.load(name).transitions:
            for step in t.effects:
                code = step.params.get("code")
                if step.name == "milestone.record" and code not in active:
                    errors.append(f"Milestone {code} is recorded by the "
                                  f"'{name}' workflow, so it must stay "
                                  f"active.")
    if errors:
        raise PolicyViolation("; ".join(errors))

    with M.db.atomic():
        M.MilestoneDefinition.delete().execute()
        for it in items:
            M.MilestoneDefinition.create(
                code=it["code"].strip(), label=it["label"],
                sequence=int(it["sequence"]),
                applies_to=it.get("applies_to") or "PHD",
                is_active=bool(it.get("is_active", True)),
                txn_login_id=actor.login_id)
    return definitions()
