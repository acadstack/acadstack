"""Course creation, editing and approval.

Saving a course runs it through the "course" transition table
(:mod:`domain.workflow`): the author submits a draft to the HoD, the HoD
forwards it to the council or returns it, and the Dean/academic section
approves it or returns it to the department. Approved and retired
courses can only be edited by holders of ``course.edit_locked_status``.
Which steps exist is data; the checks and the notification email are
registered here and referenced by name.
"""

import logging
import re

import peewee as ORM

import common as C
import models as DB
import settings_store as ST
from create_email import send_course_updated_email
from domain import persistence
from domain import workflow as WF
from domain.context import Actor
from domain.errors import DomainError, PermissionDenied, PolicyViolation

COURSE = "course"


def course_code_for_pg(code: str) -> bool:
    """Whether a course code represents a PG course: its number starts
    with a digit at or above the configured threshold (course.
    pg_course_min_leading_digit, default 5). E.g. CS504, EE677 are PG
    courses under the default.

    Args:
        code: course code in the format CCddd.
    """
    code = "" if not code else code
    min_digit = ST.setting("course.pg_course_min_leading_digit")
    return bool(re.match(
        rf"^[A-Za-z]{{2,3}}[{min_digit}-9]\d{{2}}$", code, re.IGNORECASE))


# ============================== checks / effects ==============================

@WF.check("course.author_or_permitted")
def _author_or_permitted(ctx, permission="course.edit_any",
                         dept_permission=None):
    """Only the author edits their course, unless the actor holds
    ``permission`` (any department) or ``dept_permission`` and the course
    is in their own department. Compares against the stored author, not
    the one the client sent back."""
    crs = ctx.record
    if ctx.from_status is None:
        return
    if crs.author_id == ctx.actor.user_id or ctx.actor.can(permission):
        return
    if dept_permission and ctx.actor.can(dept_permission):
        dept = _course_dept(crs)
        if dept and dept == ctx.actor.dept_name:
            return
        raise PermissionDenied(
            "You can edit only your own department's courses!")
    raise PermissionDenied("Cannot save course authored by another faculty!")


def _course_dept(crs):
    """A course's department is its author's -- as course search also
    takes it. None for a course with no author."""
    if crs.author_id and crs.author.person_id:
        return crs.author.person.dept_name
    return None


@WF.check("course.pg_only_for_roles")
def _pg_only_for_roles(ctx, roles=("RES",)):
    """The listed roles (the research section) may edit PG/PhD courses
    only."""
    if ctx.from_status is None:
        return
    if ctx.actor.has_role(list(roles)) and \
            not course_code_for_pg(ctx.record.code):
        raise PolicyViolation("You can edit only PG/PhD courses!")


@WF.check("course.actor_in_course_dept")
def _actor_in_course_dept(ctx):
    """The actor belongs to the course's department -- its author's, as
    course search also takes it. A course with no author belongs to no
    department, so nobody passes."""
    dept = _course_dept(ctx.record)
    if not dept or ctx.actor.dept_name != dept:
        raise PermissionDenied(
            "Only the HoD of the course's department can review it!")


@WF.effect("notify.course_updated")
def _notify(ctx):
    send_course_updated_email(ctx.record.id, ctx.from_status)


# ============================== the table ==============================

_NOTIFY = (WF.Step("notify.course_updated"),)


def _row(pri, frm, to, permission, label, effects=_NOTIFY, checks=()):
    return WF.Transition(priority=pri, from_status=frm, to_status=to,
                         permission=permission, label=label, effects=effects,
                         checks=tuple(WF.Step.of(c) for c in checks))


_HOD_DEPT = ("course.actor_in_course_dept",)
_OPEN = ["DRA", "HAP", "HAR", "CAP", "CAR"]
_LOCKED = ["APP", "RET"]

BASELINE = WF.Workflow(
    name=COURSE,
    status_vocab="course_statuses",
    match_on=WF.MATCH_ON_STATUS,
    locked_message=("This course is already in {from_label} state. "
                    "Please contact the academic section to edit it."),
    denied_message="A course in {from_label} cannot be moved to {to_label}.",
    pre_checks=(WF.Step("course.author_or_permitted",
                        {"permission": "course.edit_any",
                         "dept_permission": "course.edit_in_dept"}),),
    checks=(WF.Step("course.pg_only_for_roles", {"roles": ["RES"]}),),
    transitions=tuple(
        [_row(100, WF.NEW, "DRA", "course.save", "Create", effects=())]
        # Editing without moving: open to course editors until approved,
        # then only to those who may edit locked courses.
        + [_row(110 + i, s, WF.SAME, "course.save", "Save")
           for i, s in enumerate(_OPEN)]
        + [_row(120 + i, s, WF.SAME, "course.edit_locked_status", "Save")
           for i, s in enumerate(_LOCKED)]
        # Author submits to the HoD.
        + [_row(200 + i, s, "HAP", "course.submit", "Submit")
           for i, s in enumerate(["DRA", "HAR", "CAR"])]
        # HoD of the course's department forwards to the council, or
        # returns to the faculty.
        + [_row(300, "HAP", "CAP", "course.hod_review", "Forward",
                checks=_HOD_DEPT),
           _row(301, "HAP", "HAR", "course.hod_review", "Return to Faculty",
                checks=_HOD_DEPT)]
        # Dean / academic section approve, or return to the department.
        + [_row(400, "CAP", "APP", "course.final_approve", "Approve"),
           _row(401, "CAP", "CAR", "course.final_approve", "Return to Dept.")]
    ),
)


def _status_counts() -> dict:
    qry = (DB.Course
           .select(DB.Course.status, ORM.fn.COUNT(DB.Course.id).alias("n"))
           .group_by(DB.Course.status))
    return {r.status: r.n for r in qry}


WF.register_workflow(BASELINE, _status_counts)


# ============================== use cases ==============================

def save_course(actor: Actor, form_data, update_model) -> DB.Course:
    """Creates or edits a course, moving it through the "course"
    workflow.

    Args:
        form_data: the submitted course. ``status`` is the status asked
            for; omitted, the course stays where it is (or starts as a
            draft).
        update_model: ``fn(model, dict)`` copying known fields from the
            form onto the model (``common.update_model_skip_unknown``).
    """
    crs_id = int(form_data.get("id") or 0)
    crs = DB.Course.get_by_id(crs_id) if crs_id > 0 else DB.Course()
    old_status = crs.status if crs_id else None
    if not crs_id:
        # The author of a new course is whoever creates it.
        form_data["author"] = dict(form_data.get("author") or {},
                                   id=actor.user_id)

    wf = WF.load(COURSE)
    ctx = WF.Context(actor=actor, from_status=old_status, record=crs,
                     to_status=form_data.get("status") or old_status or "DRA")
    WF.decide(wf, ctx)

    update_model(crs, form_data)
    crs.status = ctx.to_status
    C.apply_computed_course_credits(crs)

    with DB.db.atomic():
        if crs_id:
            if persistence.update(DB.Course, crs, actor) != 1:
                raise DomainError("Could not update. Please try again.")
            logging.debug("Updated course details: {}".format(crs))
        else:
            persistence.save(crs, actor)
            logging.debug("Inserted course details: {}".format(crs))
    WF.run_effects(ctx)
    return crs


def course_actions(actor: Actor, course_id) -> list:
    """Moves the actor may make on a course (0 = a new one), for the UI."""
    crs = DB.Course.get_by_id(course_id) if course_id else DB.Course()
    ctx = WF.Context(actor=actor,
                     from_status=crs.status if course_id else None,
                     record=crs)
    return WF.available(WF.load(COURSE), ctx)
