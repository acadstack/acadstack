"""The enrolment domain, exercised with a database but no HTTP request.

This is the concrete payoff of the extraction: the same approval logic
the /change_enroll_status route runs can be driven from a script, a
scheduled job or a test with nothing but a database connection and an
Actor. Before it, the only way in was an authenticated POST.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import models as DB  # noqa: E402
from conftest import create_user, login_as  # noqa: E402
from domain import enrolment as ENR  # noqa: E402
from domain import plugins  # noqa: E402
from domain.context import Actor  # noqa: E402
from domain.errors import PermissionDenied  # noqa: E402

ACAD_SESSION = "2024-I"
_seq = 0


def _offering(status="E"):
    global _seq
    _seq += 1
    course = DB.Course.create(code=f"DM{100 + _seq}", title="Test Course",
                              status="APP")
    return DB.CourseOffering.create(course=course, acad_session=ACAD_SESSION,
                                    status=status)


def _student(login_id):
    return create_user("STU", login_id, org_id=f"ORG-{login_id}",
                       dept_name="CSE", degree="BTE", year_of_entry="2022")


def _actor_for(user, role=None):
    return Actor(login_id=user.login_id, role=role or user.role,
                 user_id=user.id)


def _open_add_drop():
    today = date.today()
    DB.AcademicCalendar.create(acad_session=ACAD_SESSION, event_code="ADD_DROP_S",
                               event_value=(today - timedelta(days=5)).strftime("%Y-%m-%d"))
    DB.AcademicCalendar.create(acad_session=ACAD_SESSION, event_code="ADD_DROP_E",
                               event_value=(today + timedelta(days=5)).strftime("%Y-%m-%d"))


def test_approval_runs_with_no_request_context(db):
    offering = _offering()
    student = _student("stu_nohttp")
    ce = DB.CourseEnrollment.create(course_offering=offering, student=student,
                                    enrol_type="C", enrol_status="IPEN")
    aca = create_user("ACA", "aca_nohttp")

    changed = ENR.change_status(_actor_for(aca), [ce.id], "approve")

    assert changed == [ce.id]
    assert DB.CourseEnrollment.get_by_id(ce.id).enrol_status == "ENRO"
    # The audit column was stamped from the Actor, not from the session.
    assert DB.CourseEnrollment.get_by_id(ce.id).txn_login_id == "aca_nohttp"


def test_batch_rolls_back_entirely_when_one_enrolment_is_forbidden(db):
    # Two enrolments, the second of which the instructor does not own:
    # the transaction the DOMAIN opened covers both, so neither moves.
    _open_add_drop()
    offering = _offering()
    other_offering = _offering()
    mine = DB.CourseEnrollment.create(course_offering=offering,
                                      student=_student("stu_batch_a"),
                                      enrol_type="C", enrol_status="IPEN")
    not_mine = DB.CourseEnrollment.create(course_offering=other_offering,
                                          student=_student("stu_batch_b"),
                                          enrol_type="C", enrol_status="IPEN")
    instructor = create_user("FAC", "instr_batch")
    DB.CourseInstructor.create(offering=offering, instructor=instructor,
                               is_coordinator=True)

    with pytest.raises(PermissionDenied):
        ENR.change_status(_actor_for(instructor), [mine.id, not_mine.id],
                          "approve")

    assert DB.CourseEnrollment.get_by_id(mine.id).enrol_status == "IPEN"
    assert DB.CourseEnrollment.get_by_id(not_mine.id).enrol_status == "IPEN"


def test_plugin_override_changes_what_the_http_route_does(client):
    """An institution's override is in force for the real endpoint, with
    no change to the route, the adapter or the domain module."""
    offering = _offering()
    student = _student("stu_plugin")
    ce = DB.CourseEnrollment.create(course_offering=offering, student=student,
                                    enrol_type="C", enrol_status="IPEN")
    aca = create_user("ACA", "aca_plugin")
    login_as(client, aca.login_id)

    @plugins.override(plugins.ENROLMENT_NEXT_STATUS)
    def always_park_for_advisor(actor, ownership, current_status, action):
        # This deployment routes even academic-section approvals through
        # the batch advisor.
        return "APEN" if action == "approve" else "ASREJ"

    try:
        res = client.post("/acadstack/change_enroll_status",
                          json={"ids": [ce.id], "status": "approve"})
        assert res.json["status"] == "OK", res.json
        assert DB.CourseEnrollment.get_by_id(ce.id).enrol_status == "APEN"
    finally:
        plugins.clear_overrides()

    # ...and the stock behaviour is back once the override is gone.
    res = client.post("/acadstack/change_enroll_status",
                      json={"ids": [ce.id], "status": "approve"})
    assert res.json["status"] == "OK", res.json
    assert DB.CourseEnrollment.get_by_id(ce.id).enrol_status == "ENRO"
