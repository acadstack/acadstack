"""Course enrolment: requesting, approving, dropping and listing.

This is the domain module the ``api_course_enrolment`` HTTP adapter
calls into. Everything here is synchronous, takes the acting
:class:`~domain.context.Actor` explicitly, and returns values rather
than HTTP responses.

Two things worth knowing before editing:

* **The transaction starts here, not in the adapter.** A use case such
  as "approve these twelve enrolments" is atomic because the domain says
  so, not because it arrived over HTTP; a job calling the same function
  must get the same atomicity. Adapters must not open one.
* **Some failures return, others raise.** Raising out of the
  ``db.atomic()`` block rolls the whole batch back; returning from
  inside it commits the work done so far. That distinction used to be
  implicit and got ``enroll_in_courses`` wrong: it returned an error
  response from inside the transaction on a slot clash, committing the
  courses it had already enrolled the student in.
  :func:`request_enrolment` now rolls back explicitly and still returns
  an outcome object rather than raising, because the response body is
  the list of clashes rather than a message.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional

import peewee as ORM
from playhouse.shortcuts import model_to_dict

import common as C
import models as DB
import validation_checks as VAL
from create_email import send_enrolment_email
from domain import academic_calendar as CAL
from domain import attendance as ATT
from domain import persistence
from domain import policy as POL
from domain import workflow as WF
from domain.context import Actor
from domain.errors import PermissionDenied, PolicyViolation, DomainError


# ============================== results ==============================

@dataclass
class EnrolmentRequestOutcome:
    """What came of a student's request to enrol in a set of courses."""

    #: Timetable clashes found. Non-empty means the request was
    #: abandoned at that course -- but note that enrolments created for
    #: earlier courses in the same request have already been committed.
    conflicts: List[str] = field(default_factory=list)

    #: One entry per accepted course offering; each entry is itself the
    #: list of course codes validate_course_categorization returned.
    allowed_courses: List = field(default_factory=list)

    #: Accumulated explanation of courses that were NOT accepted.
    message: str = ""


@dataclass
class SaveOutcome:
    """Result of an enrolment record edit."""
    enrolment_id: Optional[int] = None
    error: Optional[str] = None


# ========================== ownership / checks ==========================

def ownership_flags(actor: Actor, enrolment_ids) -> dict:
    """For each enrolment id, ``[is_instructor, is_batch_advisor]`` from
    the acting user's point of view.

    Only the *coordinating* instructor of the offering counts as the
    instructor, and a batch advisor matches on degree, entry year and
    department -- both encoded in the SQL fragments, not here.
    """
    sql1 = C.sql_by_id("frag_pending_enrollments")
    sql2 = C.sql_by_id("frag_ba_and_instructor")
    sql = "{0} {1}".format(sql1, sql2)
    param = tuple(enrolment_ids)
    cursor = DB.db.execute_sql(sql, [param])

    data = {}
    for row in _rows(cursor):
        is_instr = row["instructor_id"] == actor.user_id
        is_advisor = row["batch_adv_id"] == actor.user_id
        data[row["id"]] = [is_instr, is_advisor]
    return data


def check_student_fees_paid(actor: Actor):
    """Students must have a fees payment recorded for a current session
    before they may request enrolment. Non-students are unaffected."""
    if actor.has_role("STU"):
        qry = DB.FeesTransaction.select() \
            .where(
            (DB.FeesTransaction.student == actor.user_id) &
            (DB.FeesTransaction.acad_session.in_(
                CAL.current_acad_session_list())) &
            (DB.FeesTransaction.is_deleted != True) &
            (DB.FeesTransaction.fees_txn_amt > 0)
        )
        if not qry.exists():
            raise PolicyViolation(
                "Semester registration fees payment details/proof are "
                "required before submitting enrolment requests! Kindly "
                "submit the necessary details first.")


def slot_conflicts(co_id, student_id, static_data=None) -> list:
    """Timetable clashes between the offering and what the student is
    already enrolled in.

    Args:
        static_data: mapping used to turn slot codes into labels for the
            message. The adapter passes the frontend's "CourseSlots"
            vocabulary; when omitted the raw codes are shown.
    """
    stu = DB.User.get_or_none(int(student_id))
    if not stu:
        raise DomainError("User record not found for student.")
    slots = []
    # Statuses that occupy a timetable slot.
    for ce in stu.enrollments.where(
            DB.CourseEnrollment.enrol_status.in_(["IPEN", "APEN", "ENRO"])):
        if ce.course_offering.slot:
            slots.append(ce.course_offering.slot)

    cst_list = list(DB.CourseSlotTiming.select().where(
        (DB.CourseSlotTiming.slot.in_(slots))
        & (DB.CourseSlotTiming.is_deleted != True)))

    co = DB.CourseOffering.get_or_none(int(co_id))
    conflicts = []
    if co:
        cst_qry = DB.CourseSlotTiming.select().where(
            DB.CourseSlotTiming.slot == co.slot)
        if not cst_qry.exists():
            slot_nm = _slot_label(co.slot, static_data)
            raise DomainError(
                f"Slot timing not setup for slot: '{slot_nm}'. "
                "Please contact the administrator.")
        for x in cst_list:
            if cst_qry[0].week_day == x.week_day and \
                    ((x.start_time < cst_qry[0].start_time < x.end_time) or
                     (x.start_time < cst_qry[0].end_time < x.end_time)):
                slot = _slot_label(x.slot, static_data)
                msg = (f"{slot} : {C.WEEK_DAY_NAMES[x.week_day]} "
                       f"{x.start_time}-{x.end_time}")
                conflicts.append(msg)

    return conflicts


def existing_enrolment(co_id, student_id):
    """A prior, non-confirmed enrolment of this student in this offering,
    which a fresh request updates instead of inserting a duplicate."""
    qry = DB.CourseEnrollment.select().where(
        (DB.CourseEnrollment.course_offering == co_id) &
        (DB.CourseEnrollment.student == student_id) &
        (DB.CourseEnrollment.enrol_status != 'ENRO')
    )
    return qry[0] if qry.exists() else None


# ========================== the state machine ==========================
#
# The approval chain is the "enrolment" transition table below (stored
# and editable as data; see domain/workflow.py). What stays in code is
# what the rows refer to by name: the ownership guards, which need the
# batched SQL in ownership_flags(), the calendar/offering check, and the
# notification. An institution extends the chain by registering more of
# these from a plugin (domain/plugins.py) and naming them in its table.

ENROLMENT = "enrolment"


@WF.guard("enrolment.is_instructor")
def _is_instructor(ctx):
    return ctx.facts["is_instructor"]


@WF.guard("enrolment.is_advisor")
def _is_advisor(ctx):
    return ctx.facts["is_advisor"]


@WF.check("enrolment.change_allowed")
def _change_allowed(ctx):
    # Offering running/enrolling, add/drop (or withdraw) window open, and
    # the target a known status. Returns early for enrolment.override.
    VAL.validate_enrolment_change(ctx.record, ctx.to_status, actor=ctx.actor)


@WF.effect("notify.enrolment")
def _notify(ctx):
    notify_status_change(ctx.record.id)


def _decision(pri, frm, action, to, permission, guards=(), label=None,
              checks=(), effects=("notify.enrolment",)):
    return WF.Transition(
        priority=pri, from_status=frm, action=action, to_status=to,
        label=label or action.capitalize(), permission=permission,
        guards=tuple(guards), checks=tuple(WF.Step.of(c) for c in checks),
        effects=tuple(WF.Step.of(e) for e in effects))


_OWNER = "enrolment.decide_as_owner"

#: The approval chain as it has always behaved, as a table. The two
#: oddities tests/test_enrolment_state_machine.py pins are rows here, not
#: accidents of branch order: an advisor acting alone takes any status
#: (including a fresh IPEN) straight to ENRO (rows 30/31, from "*"), and
#: an HOD may decide any APEN enrolment with no ownership at all (60/61).
#:
#: The calendar/offering check is workflow-wide rather than per row so
#: that every move runs it, including rows an institution adds; it lets
#: enrolment.override holders (rows 10/11) through by itself.
BASELINE = WF.Workflow(
    name=ENROLMENT,
    status_vocab="enrolment_statuses",
    match_on=WF.MATCH_ON_ACTION,
    checks=(WF.Step("enrolment.change_allowed"),),
    locked_message="Unexpected user role: {role}",
    denied_message=("You do not have privileges to change one or more "
                    "enrollments!"),
    transitions=(
        # Academic section: decides outright, no ownership, no calendar.
        _decision(10, "*", "approve", "ENRO", "enrolment.override"),
        _decision(11, "*", "reject", "ASREJ", "enrolment.override"),
        # Coordinating instructor only.
        _decision(20, "*", "approve", "APEN", _OWNER,
                  ["enrolment.is_instructor", "!enrolment.is_advisor"]),
        _decision(21, "*", "reject", "IREJ", _OWNER,
                  ["enrolment.is_instructor", "!enrolment.is_advisor"]),
        # Batch advisor only.
        _decision(30, "*", "approve", "ENRO", _OWNER,
                  ["enrolment.is_advisor", "!enrolment.is_instructor"]),
        _decision(31, "*", "reject", "AREJ", _OWNER,
                  ["enrolment.is_advisor", "!enrolment.is_instructor"]),
        # Instructor AND advisor: the two steps collapse onto one user,
        # who still walks them one at a time.
        _decision(40, "IPEN", "approve", "APEN", _OWNER,
                  ["enrolment.is_instructor", "enrolment.is_advisor"]),
        _decision(41, "IPEN", "reject", "AREJ", _OWNER,
                  ["enrolment.is_instructor", "enrolment.is_advisor"]),
        _decision(50, "APEN", "approve", "ENRO", _OWNER,
                  ["enrolment.is_instructor", "enrolment.is_advisor"]),
        _decision(51, "APEN", "reject", "AREJ", _OWNER,
                  ["enrolment.is_instructor", "enrolment.is_advisor"]),
        # HOD standing in for the advisor.
        _decision(60, "APEN", "approve", "ENRO",
                  "enrolment.decide_advisor_pending"),
        _decision(61, "APEN", "reject", "AREJ",
                  "enrolment.decide_advisor_pending"),
    ),
)


def _status_counts() -> dict:
    qry = (DB.CourseEnrollment
           .select(DB.CourseEnrollment.enrol_status,
                   ORM.fn.COUNT(DB.CourseEnrollment.id).alias("n"))
           .group_by(DB.CourseEnrollment.enrol_status))
    return {r.enrol_status: r.n for r in qry}


WF.register_workflow(BASELINE, _status_counts)


def _context(actor, ownership, current_status, action, record=None):
    return WF.Context(
        actor=actor, from_status=current_status, record=record,
        # Anything other than "approve" has always meant reject.
        action="approve" if action == "approve" else "reject",
        facts={"is_instructor": bool(ownership[0]),
               "is_advisor": bool(ownership[1])})


def default_next_enrol_status(actor: Actor, ownership, current_status,
                              action, workflow=None) -> str:
    """The status an approve/reject moves an enrolment to.

    Resolves the request against the "enrolment" transition table
    (``workflow``, or the one in force) -- guards only, no checks and no
    effects, so it needs no database when a workflow is passed in.

    Args:
        actor: who is approving.
        ownership: ``[is_instructor, is_batch_advisor]`` for this
            enrolment, from :func:`ownership_flags`.
        current_status: the enrolment's status right now.
        action: "approve" or anything else, which means reject.
        workflow: the transition table to use; defaults to
            ``workflow.load("enrolment")``.

    Raises:
        PermissionDenied: when no transition grants this actor authority
            over an enrolment in this state.
    """
    wf = workflow or WF.load(ENROLMENT)
    ctx = _context(actor, ownership, current_status, action)
    return WF.select(wf, ctx).target(current_status)


def notify_status_change(enrolment_id, old_record=None):
    """Tells the student and instructor that an enrolment changed."""
    send_enrolment_email(enrolment_id, old_rec=old_record)


def enrolment_actions(actor: Actor, enrolment_id) -> list:
    """The approve/reject actions the actor may take on one enrolment."""
    ce = DB.CourseEnrollment.get_by_id(enrolment_id)
    ownership = ownership_flags(actor, [enrolment_id]).get(
        ce.id, [False, False])
    ctx = _context(actor, ownership, ce.enrol_status, None, record=ce)
    return WF.available(WF.load(ENROLMENT), ctx)


# ============================== use cases ==============================

def change_status(actor: Actor, enrolment_ids, action) -> list:
    """Approves or rejects a batch of enrolments, atomically.

    Each enrolment is moved by the "enrolment" transition table: the row
    chosen decides the new status, its checks run before the save and
    its effects (the notification email) after. Returns the ids whose
    status actually changed. An enrolment the actor may not act on, or a
    transition the academic calendar forbids, raises and rolls the whole
    batch back.
    """
    ownership = ownership_flags(actor, enrolment_ids)
    wf = WF.load(ENROLMENT)
    changed = []
    with DB.db.atomic() as txn:
        for eid in enrolment_ids:
            ce = DB.CourseEnrollment.get_by_id(eid)
            ctx = _context(actor, ownership[eid], ce.enrol_status, action,
                           record=ce)
            WF.decide(wf, ctx)
            ce.enrol_status = ctx.to_status
            if persistence.update(DB.CourseEnrollment, ce, actor) == 1:
                WF.run_effects(ctx)
                changed.append(eid)
        txn.commit()
    return changed


def request_enrolment(actor: Actor, student_id, co_ids, enrol_type,
                      policy=None, static_data=None) -> EnrolmentRequestOutcome:
    """Records a student's enrolment requests for a set of offerings.

    Each offering is checked against the calendar window, the offering's
    own status, the student's course categorization and their timetable
    before an enrolment row is written.
    """
    pol = policy or POL.load_enrolment_policy()

    VAL.is_current_user_in_role_and_id(
        "STU", "user_id", student_id,
        "Student attempted to enrol someone else in a course.", actor=actor)

    if not pol.disable_fees_check:
        check_student_fees_paid(actor)

    if not co_ids:
        raise PolicyViolation("Please select a course to enrol!")

    outcome = EnrolmentRequestOutcome()
    with DB.db.atomic() as txn:
        for co_id in co_ids:
            co = DB.CourseOffering.get_by_id(co_id)
            if enrol_type == "A":  # audit
                if not CAL.is_course_withdraw_open(co.acad_session):
                    raise PolicyViolation("Course enrolment/Audit not open for "
                                          + str(co.acad_session))
            else:
                if not CAL.is_course_add_drop_open(co.acad_session):
                    raise PolicyViolation("Course enrolment/add not open for "
                                          + str(co.acad_session))
            VAL.check_enrollment_allowed(co, actor=actor)
            ccode, msg = VAL.validate_course_categorization(co, student_id)
            outcome.message += msg
            if ccode:
                outcome.allowed_courses.append(ccode)
            conflicts = slot_conflicts(co_id, student_id, static_data)
            if len(conflicts) > 0:
                # The request is rejected as a whole. This used to return
                # straight out of the atomic block, which COMMITS -- so a
                # student enrolling in four courses where the third
                # clashed was told the request failed while keeping the
                # first two. Roll back explicitly, then return the
                # conflicts (rather than raising) so the response body
                # stays the list of clashes the frontend renders.
                outcome.conflicts = conflicts
                txn.rollback()
                return outcome

            coe = DB.CourseEnrollment()
            prior = existing_enrolment(co_id, student_id)
            if prior:
                coe = prior
            if ccode:
                coe.enrol_status = "IPEN"
                coe.enrol_type = enrol_type
                coe.course_offering = co_id
                coe.student = student_id
                if prior:
                    persistence.update(DB.CourseEnrollment, coe, actor)
                else:
                    persistence.save(coe, actor)
                logging.debug("Saved: {}".format(coe))
                VAL.check_enrolled_credits(student_id, co.acad_session)
                notify_status_change(coe.id)

        txn.commit()
    return outcome


def bulk_enrol(actor: Actor, entry_no_pattern, co_id) -> tuple:
    """Enrols every student whose org id starts with ``entry_no_pattern``
    in one offering, straight to confirmed. Returns
    ``(count, course_title)``."""

    query = DB.User.select(DB.User.id, DB.Person.org_id,
                           DB.User.role).join(DB.Person)
    query = query.where((DB.User.role == "STU") & (
        DB.Person.org_id.startswith(entry_no_pattern)))

    co = DB.CourseOffering.get_by_id(co_id)
    VAL.check_enrollment_allowed(co, actor=actor)
    num = 0
    with DB.db.atomic() as txn:
        for stu in query:
            coe = DB.CourseEnrollment()
            coe.course_offering = co
            coe.student = stu.id
            coe.enrol_type = "C"
            coe.enrol_status = "ENRO"
            persistence.save(coe, actor)
            num += 1
        txn.commit()

    return num, co.course.title


def drop_or_withdraw(actor: Actor, enrolment_id, status):
    """Drops or withdraws an enrolment. The academic section dropping a
    course records it as a rejection instead."""

    # Raises AcadStackException
    VAL.validate_enrolment_change(enrolment_id, status, actor=actor)

    if actor.can("enrolment.override"):
        status = "ASREJ"

    ce = DB.CourseEnrollment.get_by_id(enrolment_id)
    ce.enrol_status = status
    persistence.save(ce, actor)
    notify_status_change(enrolment_id)
    return ce


def save_enrolment(actor: Actor, form_data) -> SaveOutcome:
    """Creates or edits an enrolment record from submitted form data."""
    cid = int(form_data.get("id") or 0)
    coe = DB.CourseEnrollment()
    with DB.db.atomic() as txn:
        old_data = {}
        if cid:
            coe = DB.CourseEnrollment.get_by_id(cid)
            old_data = model_to_dict(coe)
            old_data["enrol_status"] = dict(
                DB.CourseEnrollment.ENROL_STATUSES)[old_data["enrol_status"]]
            # Raises AcadStackException
            VAL.validate_enrolment_change(coe, form_data.get("enrol_status"),
                                          actor=actor)

            if not VAL.is_enrollment_owner_valid(coe, actor=actor):
                return SaveOutcome(error="User not allowed to change enrollment!")

            C.update_model_skip_unknown(coe, form_data)
            if persistence.update(DB.CourseEnrollment, coe, actor) != 1:
                return SaveOutcome(error="Could not update. Please try again.")
            logging.debug(f"Updated DB.CourseEnrollment details: {coe}")
        else:
            C.update_model_skip_unknown(coe, form_data)
            persistence.save(coe, actor)
            logging.debug(f"Inserted DB.CourseEnrollment: {coe}")

        notify_status_change(coe.id, old_data)
        txn.commit()

    return SaveOutcome(enrolment_id=coe.id)


# ============================== queries ==============================

def enrolment_for_view(actor: Actor, enrolment_id):
    """One enrolment record, if the actor is entitled to see it.

    Returns None when there is no such record, so the caller can say so;
    raises when the record exists but is none of the actor's business.
    """
    res = DB.CourseEnrollment.get_or_none(enrolment_id)
    if not res:
        return None
    if not VAL.is_enrollment_owner_valid(res, actor=actor):
        raise PermissionDenied("You are not allowed to view this enrolment!")
    return res


def enrolments_for_offering(co_id, include_attendance=True) -> list:
    """Every enrolment in one offering, with the student's particulars."""
    res = DB.CourseEnrollment.select().where(
        DB.CourseEnrollment.course_offering == co_id)
    result = []
    for coe in res:
        obj = {"id": coe.id, "user_id": coe.student.id,
               "student": coe.student.get_full_name(),
               "org_id": coe.student.person.org_id,
               "enrol_type": coe.enrol_type,
               "enrol_status": coe.enrol_status,
               "year": coe.student.person.year_of_entry,
               "dep": coe.student.person.dept_name,
               "degree": coe.student.person.degree,
               "course": (coe.course_offering.course.code + ' ' +
                          coe.course_offering.course.title)}
        if include_attendance:
            obj["attendance"] = ATT.percent_for_enrolment(coe)
        result.append(obj)
    return result


def instructor_pending_enrolments(actor: Actor) -> list:
    """Enrolments awaiting the acting instructor's approval."""
    res = DB.CourseEnrollment.select(). \
        join(DB.CourseOffering).join(DB.CourseInstructor). \
        where(
        (DB.CourseInstructor.instructor_id == actor.user_id) &
        (DB.CourseEnrollment.enrol_status == 'IPEN')
    )
    result = []
    for coe in res:
        obj = {}
        obj["id"] = coe.id
        obj["user_id"] = coe.student.id
        obj["student"] = coe.student.get_full_name()
        obj["org_id"] = coe.student.person.org_id
        obj["enrol_type"] = coe.enrol_type
        obj["enrol_status"] = coe.enrol_status
        obj["acad_session"] = coe.course_offering.acad_session
        obj["year"] = coe.student.person.year_of_entry
        obj["dep"] = coe.student.person.dept_name
        obj["degree"] = coe.student.person.degree
        obj["course"] = (coe.course_offering.course.code + ' ' +
                         coe.course_offering.course.title)
        obj["for_instructor"] = True
        obj["attendance"] = ATT.percent_for_enrolment(coe)
        result.append(obj)
    return result


def advisor_action_items(actor: Actor) -> list:
    """Enrolments awaiting the acting user in their batch-advisor role."""
    qry1 = C.sql_by_id("frag_pending_enrollments")
    qry2 = C.sql_by_id("frag_ba_pending_enrollments")
    cursor = DB.db.execute_sql(f"{qry1} {qry2}", [actor.user_id])
    return _rows(cursor)


def pending_enrolments_for_approver(actor: Actor) -> list:
    """The advisor's (or, for an HOD, the department's) pending list."""
    qry = C.sql_by_id("pending_enrolments_advisor")
    if actor.has_role("HOD"):
        qry = C.sql_by_id("pending_enrolments_hod")

    cursor = DB.db.execute_sql(qry, [actor.user_id])
    return _rows(cursor)


def passed_course_codes(student_id, policy=None) -> list:
    """Course codes the student has a passing grade in, or None when
    there is no such student.

    Which grades count as a pass comes off the same versioned grading
    ruleset the transcript is computed from -- it used to be a second copy
    of the list, typed into the HTTP handler for this endpoint. The two
    sets are close but deliberately NOT identical: this one includes the
    satisfactory grade, which cannot count towards CGPA (it carries no
    points and is netted out of the denominator) yet plainly is a pass for
    prerequisite purposes. See GradingPolicy.passed_course_grades.

    Resolved per enrolment, so a course passed under an earlier ruleset
    stays passed under the rules of its own session.
    """
    stu = DB.User.get_or_none(student_id)
    if not stu:
        return None
    return [
        se.course_offering.course.code for se in stu.enrollments
        if se.grade in (policy or POL.load_grading_policy(
            se.course_offering.acad_session)).passed_course_grades]


def enrolment_export_rows(co_id, is_grades=False, actor: Actor = None) -> tuple:
    """Rows for the "download enrolments" CSVs.

    Which query runs depends on whether grades are wanted and on whether
    the actor may see other people's grades, so the choice belongs here
    rather than in the adapter. Returns ``(column_names, rows)``.
    """
    sql_id = "enrolled_students"
    if is_grades:
        if VAL.validate_course_instructor(co_id,
                                          allowed_role=["ACA", "DEA", "HOD"],
                                          coordinator_only=False, actor=actor):
            sql_id = "get_course_grades"
        else:
            sql_id = "enrolled_students_for_grades"

    cursor = DB.db.execute_sql(C.sql_by_id(sql_id), [int(co_id)])
    return _columns_and_rows(cursor)


def enrolments_by_dept_year_session(dept_name, entry_year, acad_session) -> tuple:
    """Rows for the department/year/session enrolment export."""
    cursor = DB.db.execute_sql(
        C.sql_by_id("generate_course_enrolments"),
        [str(entry_year), str(entry_year), str(dept_name), str(dept_name),
         str(acad_session)])
    return _columns_and_rows(cursor)


# ============================== helpers ==============================

def _rows(cursor) -> list:
    """Cursor -> list of dicts keyed by column name."""
    ncols = len(cursor.description)
    colnames = [cursor.description[i][0] for i in range(ncols)]
    return [{colnames[i]: row[i] for i in range(ncols)}
            for row in cursor.fetchall()]


def _columns_and_rows(cursor) -> tuple:
    ncols = len(cursor.description)
    colnames = [cursor.description[i][0] for i in range(ncols)]
    return colnames, [[row[i] for i in range(ncols)]
                      for row in cursor.fetchall()]


def _slot_label(slot_code, static_data):
    if not static_data:
        return slot_code
    for item in static_data:
        if slot_code == item["id"]:
            return item["value"]
    return slot_code
