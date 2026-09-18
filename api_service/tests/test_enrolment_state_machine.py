"""Characterization tests for api_course_enrolment.change_enroll_status.

This locks in the CURRENT behavior of the enrolment approval state
machine -- who (ACA/DEA/FAC/HOD) can move an enrolment between statuses,
and what it moves to -- via real HTTP requests against the actual route
(so RBAC, the raw-SQL ownership lookup in sql_statements.toml, and
validation_checks.validate_enrolment_change are all exercised for real,
not mocked). A couple of oddities that look like bugs are called out and
locked in rather than fixed; see the "documented oddities" section.

Fixture domain notes (see conftest.py's `db`/`client` fixtures for the
schema-reset/truncate machinery this all sits on top of):

- The raw SQL in sql_statements.toml (frag_ba_and_instructor) only treats
  a CourseInstructor row as "the instructor" when is_coordinator=True; a
  non-coordinating instructor on the same offering is NOT an owner.
- A BatchAdvisors row only counts as "the advisor" when its user has role
  'FAC', and its (for_degree, year_of_entry) matches the student's
  Person (degree, year_of_entry) AND the advisor's OWN dept_name (from
  their Person) matches the student's dept_name.
- validate_enrolment_change() (validation_checks.py) additionally
  requires, for every FAC/HOD-driven transition, that the course
  offering status is "E" or "R", and that today falls within the
  ADD_DROP_S/ADD_DROP_E academic-calendar window for that offering's
  acad_session (since none of the state machine's target statuses are
  "WDRAW"). ACA/DEA transitions bypass this check entirely.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import models as DB  # noqa: E402
from conftest import create_user, login_as  # noqa: E402

ACAD_SESSION = "2024-I"


def _open_add_drop_window(acad_session=ACAD_SESSION):
    today = date.today()
    DB.AcademicCalendar.create(
        acad_session=acad_session, event_code="ADD_DROP_S",
        event_value=(today - timedelta(days=5)).strftime("%Y-%m-%d"))
    DB.AcademicCalendar.create(
        acad_session=acad_session, event_code="ADD_DROP_E",
        event_value=(today + timedelta(days=5)).strftime("%Y-%m-%d"))


_course_seq = 0


def _make_offering(status="E", acad_session=ACAD_SESSION):
    global _course_seq
    _course_seq += 1
    course = DB.Course.create(code=f"CS{100 + _course_seq}",
                               title="Test Course", status="APP")
    return DB.CourseOffering.create(course=course, acad_session=acad_session,
                                    status=status)


def _make_student(login_id, degree="BTE", dept="CSE", year="2022"):
    return create_user("STU", login_id, org_id=f"ORG-{login_id}",
                       dept_name=dept, degree=degree, year_of_entry=year)


def _make_enrollment(offering, student, enrol_type="C", enrol_status="IPEN"):
    return DB.CourseEnrollment.create(course_offering=offering, student=student,
                                      enrol_type=enrol_type,
                                      enrol_status=enrol_status)


def _assign_instructor(offering, instructor_user, coordinator=True):
    return DB.CourseInstructor.create(offering=offering, instructor=instructor_user,
                                      is_coordinator=coordinator)


def _assign_advisor(advisor_user, degree, year):
    return DB.BatchAdvisors.create(user=advisor_user, for_degree=degree,
                                   year_of_entry=year)


def _change_status(client, ids, status):
    return client.post("/acadstack/change_enroll_status",
                       json={"ids": ids, "status": status})


def _enrol_status(enrollment_id):
    return DB.CourseEnrollment.get_by_id(enrollment_id).enrol_status


# ===================== ACA / DEA: unconditional approval authority =====================

@pytest.mark.parametrize("role", ["ACA", "DEA"])
@pytest.mark.parametrize("action,expected", [("approve", "ENRO"), ("reject", "ASREJ")])
def test_aca_dea_bypass_ownership_and_calendar_checks(client, role, action, expected):
    # Deliberately: offering status "P" (Proposed, not E/R) and NO academic
    # calendar rows at all. ACA/DEA short-circuit validate_enrolment_change
    # before any of that is examined.
    offering = _make_offering(status="P")
    student = _make_student(f"stu_{role}_{action}")
    ce = _make_enrollment(offering, student, enrol_status="IPEN")
    approver = create_user(role, f"approver_{role}_{action}")
    login_as(client, approver.login_id)

    res = _change_status(client, [ce.id], action)

    assert res.json["status"] == "OK", res.json
    assert _enrol_status(ce.id) == expected


# ===================== FAC/HOD: instructor / advisor / both / plain-HOD =====================

def test_instructor_only_approve_sends_to_advisor_pending(client):
    _open_add_drop_window()
    offering = _make_offering(status="E")
    student = _make_student("stu_instr_appr")
    ce = _make_enrollment(offering, student, enrol_status="IPEN")
    instructor = create_user("FAC", "instr_appr")
    _assign_instructor(offering, instructor, coordinator=True)
    login_as(client, instructor.login_id)

    res = _change_status(client, [ce.id], "approve")

    assert res.json["status"] == "OK", res.json
    assert _enrol_status(ce.id) == "APEN"


def test_instructor_only_reject_sets_instructor_rejected(client):
    _open_add_drop_window()
    offering = _make_offering(status="E")
    student = _make_student("stu_instr_rej")
    ce = _make_enrollment(offering, student, enrol_status="IPEN")
    instructor = create_user("FAC", "instr_rej")
    _assign_instructor(offering, instructor, coordinator=True)
    login_as(client, instructor.login_id)

    res = _change_status(client, [ce.id], "reject")

    assert res.json["status"] == "OK", res.json
    assert _enrol_status(ce.id) == "IREJ"


def test_non_coordinating_instructor_is_not_treated_as_owner(client):
    # is_coordinator=False on the CourseInstructor row: the raw-SQL
    # ownership lookup only recognizes the coordinator as "instructor_id",
    # so this user has ceos == [False, False] and hits the final
    # "no privileges" branch.
    _open_add_drop_window()
    offering = _make_offering(status="E")
    student = _make_student("stu_noncoord")
    ce = _make_enrollment(offering, student, enrol_status="IPEN")
    instructor = create_user("FAC", "noncoord_instr")
    _assign_instructor(offering, instructor, coordinator=False)
    login_as(client, instructor.login_id)

    res = _change_status(client, [ce.id], "approve")

    assert res.json["status"] == "ERROR"
    assert "privileges" in res.json["body"]
    assert _enrol_status(ce.id) == "IPEN"  # unchanged


def test_advisor_only_approve_jumps_straight_to_enrolled(client):
    # Documented oddity: the advisor-only branch
    # (`elif ceos[1] and not ceos[0]`) does not check the enrolment's
    # current status at all. A batch advisor can approve a fresh "IPEN"
    # enrolment straight to "ENRO", completely skipping the instructor
    # approval stage. Characterized as-is, not fixed.
    _open_add_drop_window()
    offering = _make_offering(status="E")
    student = _make_student("stu_adv_appr", degree="BTE", dept="CSE", year="2022")
    ce = _make_enrollment(offering, student, enrol_status="IPEN")
    advisor = create_user("FAC", "advisor_appr", dept_name="CSE")
    _assign_advisor(advisor, degree="BTE", year="2022")
    login_as(client, advisor.login_id)

    res = _change_status(client, [ce.id], "approve")

    assert res.json["status"] == "OK", res.json
    assert _enrol_status(ce.id) == "ENRO"


def test_advisor_only_reject_sets_advisor_rejected(client):
    _open_add_drop_window()
    offering = _make_offering(status="E")
    student = _make_student("stu_adv_rej", degree="MTE", dept="EE", year="2021")
    ce = _make_enrollment(offering, student, enrol_status="APEN")
    advisor = create_user("FAC", "advisor_rej", dept_name="EE")
    _assign_advisor(advisor, degree="MTE", year="2021")
    login_as(client, advisor.login_id)

    res = _change_status(client, [ce.id], "reject")

    assert res.json["status"] == "OK", res.json
    assert _enrol_status(ce.id) == "AREJ"


@pytest.mark.parametrize("action,expected", [("approve", "APEN"), ("reject", "AREJ")])
def test_both_instructor_and_advisor_pending_status(client, action, expected):
    _open_add_drop_window()
    offering = _make_offering(status="E")
    student = _make_student(f"stu_both_ipen_{action}", degree="PHD", dept="ME", year="2020")
    ce = _make_enrollment(offering, student, enrol_status="IPEN")
    both = create_user("FAC", f"both_ipen_{action}", dept_name="ME")
    _assign_instructor(offering, both, coordinator=True)
    _assign_advisor(both, degree="PHD", year="2020")
    login_as(client, both.login_id)

    res = _change_status(client, [ce.id], action)

    assert res.json["status"] == "OK", res.json
    assert _enrol_status(ce.id) == expected


@pytest.mark.parametrize("action,expected", [("approve", "ENRO"), ("reject", "AREJ")])
def test_both_instructor_and_advisor_advisor_pending_status(client, action, expected):
    _open_add_drop_window()
    offering = _make_offering(status="E")
    student = _make_student(f"stu_both_apen_{action}", degree="PHD", dept="ME", year="2020")
    ce = _make_enrollment(offering, student, enrol_status="APEN")
    both = create_user("FAC", f"both_apen_{action}", dept_name="ME")
    _assign_instructor(offering, both, coordinator=True)
    _assign_advisor(both, degree="PHD", year="2020")
    login_as(client, both.login_id)

    res = _change_status(client, [ce.id], action)

    assert res.json["status"] == "OK", res.json
    assert _enrol_status(ce.id) == expected


@pytest.mark.parametrize("action,expected", [("approve", "ENRO"), ("reject", "AREJ")])
def test_hod_with_no_ownership_can_act_on_advisor_pending(client, action, expected):
    # The plain-HOD branch (`elif is_user_in_role("HOD") and enrol_status
    # == "APEN"`) has no department/offering ownership check at all -- any
    # HOD can act on any APEN enrolment.
    _open_add_drop_window()
    offering = _make_offering(status="E")
    student = _make_student(f"stu_hod_{action}")
    ce = _make_enrollment(offering, student, enrol_status="APEN")
    hod = create_user("HOD", f"hod_{action}")
    login_as(client, hod.login_id)

    res = _change_status(client, [ce.id], action)

    assert res.json["status"] == "OK", res.json
    assert _enrol_status(ce.id) == expected


def test_hod_with_no_ownership_cannot_act_on_instructor_pending(client):
    # Same HOD, but the enrolment is still "IPEN" (waiting on the
    # instructor). None of the FAC/HOD branches match (ceos is [False,
    # False] and enrol_status != "APEN"), so it falls to the final
    # "no privileges" else.
    _open_add_drop_window()
    offering = _make_offering(status="E")
    student = _make_student("stu_hod_ipen")
    ce = _make_enrollment(offering, student, enrol_status="IPEN")
    hod = create_user("HOD", "hod_ipen")
    login_as(client, hod.login_id)

    res = _change_status(client, [ce.id], "approve")

    assert res.json["status"] == "ERROR"
    assert "privileges" in res.json["body"]
    assert _enrol_status(ce.id) == "IPEN"


def test_uninvolved_faculty_gets_privileges_error(client):
    _open_add_drop_window()
    offering = _make_offering(status="E")
    student = _make_student("stu_uninvolved")
    ce = _make_enrollment(offering, student, enrol_status="IPEN")
    bystander = create_user("FAC", "bystander_fac")
    login_as(client, bystander.login_id)

    res = _change_status(client, [ce.id], "approve")

    assert res.json["status"] == "ERROR"
    assert "privileges" in res.json["body"]


# ===================== RBAC gate / input validation =====================

def test_student_role_is_rejected_by_rbac_before_reaching_state_machine(client):
    offering = _make_offering(status="E")
    student = _make_student("stu_self")
    ce = _make_enrollment(offering, student, enrol_status="IPEN")
    login_as(client, student.login_id)

    res = _change_status(client, [ce.id], "approve")

    assert res.status_code == 200
    assert res.json["status"] == "ERROR"
    assert res.json["body"] == "You do not have required permissions to access."
    assert _enrol_status(ce.id) == "IPEN"


def test_anonymous_request_is_rejected_by_rbac(client):
    res = _change_status(client, [1], "approve")

    assert res.status_code == 200
    assert res.json["status"] == "ERROR"
    assert res.json["body"] == "Login required to access this operation."


def test_empty_ids_list_is_rejected_before_any_db_lookup(client):
    aca = create_user("ACA", "aca_empty_ids")
    login_as(client, aca.login_id)

    res = _change_status(client, [], "approve")

    assert res.json["status"] == "ERROR"
    assert res.json["body"] == "Select students to enrol first!"


# ===================== Interaction with validate_enrolment_change =====================

def test_fac_hod_transition_blocked_when_add_drop_window_closed(client):
    # No academic-calendar rows at all for this acad session: the
    # instructor-only approve path reaches validate_enrolment_change,
    # which raises because the add/drop window isn't configured/open.
    offering = _make_offering(status="E", acad_session="2024-II")
    student = _make_student("stu_closed_window")
    ce = _make_enrollment(offering, student, enrol_status="IPEN")
    instructor = create_user("FAC", "instr_closed_window")
    _assign_instructor(offering, instructor, coordinator=True)
    login_as(client, instructor.login_id)

    res = _change_status(client, [ce.id], "approve")

    assert res.json["status"] == "ERROR"
    assert "add/drop not open" in res.json["body"]
    assert _enrol_status(ce.id) == "IPEN"


def test_fac_hod_transition_blocked_when_offering_not_running_or_enrolling(client):
    _open_add_drop_window()
    offering = _make_offering(status="F")  # Finished
    student = _make_student("stu_finished_offering")
    ce = _make_enrollment(offering, student, enrol_status="IPEN")
    instructor = create_user("FAC", "instr_finished_offering")
    _assign_instructor(offering, instructor, coordinator=True)
    login_as(client, instructor.login_id)

    res = _change_status(client, [ce.id], "approve")

    assert res.json["status"] == "ERROR"
    assert "running/enrolling" in res.json["body"]
    assert _enrol_status(ce.id) == "IPEN"


def test_aca_transition_still_works_when_offering_finished_and_window_closed(client):
    # Contrast with the two tests above: ACA bypasses
    # validate_enrolment_change's offering-status/calendar checks
    # entirely, so the same "hostile" fixture succeeds for ACA.
    offering = _make_offering(status="F")
    student = _make_student("stu_aca_override")
    ce = _make_enrollment(offering, student, enrol_status="IPEN")
    aca = create_user("ACA", "aca_override")
    login_as(client, aca.login_id)

    res = _change_status(client, [ce.id], "approve")

    assert res.json["status"] == "OK", res.json
    assert _enrol_status(ce.id) == "ENRO"
