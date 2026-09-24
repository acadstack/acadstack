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
from domain import persistence  # noqa: E402
from domain import plugins  # noqa: E402
from domain import workflow as WF  # noqa: E402
from domain.context import Actor  # noqa: E402
from domain.errors import PermissionDenied, PolicyViolation  # noqa: E402

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


def test_plugin_check_is_enforced_by_the_http_route(client, monkeypatch):
    """An institution's plugin registers a workflow check; once its
    stored enrolment table names it, the real endpoint enforces it with
    no change to the route, the adapter or the domain module."""
    import dataclasses
    import importlib.metadata

    offering = _offering()
    student = _student("stu_plugin")
    ce = DB.CourseEnrollment.create(course_offering=offering, student=student,
                                    enrol_type="C", enrol_status="IPEN")
    aca = create_user("ACA", "aca_plugin")
    login_as(client, aca.login_id)

    def register():
        @WF.check("test.no_fresh_approvals")
        def no_fresh_approvals(ctx):
            # This deployment wants every request seen by the instructor
            # first, even when the academic section is the one acting.
            if ctx.from_status == "IPEN":
                raise PolicyViolation("Awaiting the instructor's review.")

    class EntryPoint:
        name, value = "inst", "tests:register"

        def load(self):
            return register

    monkeypatch.setattr(WF, "_CHECKS", dict(WF._CHECKS))
    monkeypatch.setattr(importlib.metadata, "entry_points",
                        lambda group: [EntryPoint()])
    assert plugins.load_plugins() == ["inst"]

    # The institution names the plugin's check in its stored table.
    wf = WF.load(ENR.ENROLMENT)
    WF.store(dataclasses.replace(
        wf, checks=wf.checks + (WF.Step("test.no_fresh_approvals"),)))

    res = client.post("/acadstack/change_enroll_status",
                      json={"ids": [ce.id], "status": "approve"})
    assert res.json["status"] == "ERROR", res.json
    assert "instructor's review" in res.json["body"]
    assert DB.CourseEnrollment.get_by_id(ce.id).enrol_status == "IPEN"

    # ...and the stock behaviour is back once the table no longer names it.
    WF.store(wf)
    res = client.post("/acadstack/change_enroll_status",
                      json={"ids": [ce.id], "status": "approve"})
    assert res.json["status"] == "OK", res.json
    assert DB.CourseEnrollment.get_by_id(ce.id).enrol_status == "ENRO"


def test_update_does_not_mutate_the_callers_exclude_list(db):
    """api_common.update_entity used to declare `exclude=[]` and append
    the model's ins_ts field to it, so the shared default list grew for
    the life of the process and a caller's own list came back longer
    than they passed it."""
    course = DB.Course.create(code="EXCL1", title="Exclude Test", status="APP")
    exclude = [DB.Course.title]

    persistence.update(DB.Course, course, Actor.system(), exclude)

    assert exclude == [DB.Course.title]
    # The insert timestamp is still excluded from the UPDATE itself.
    assert DB.Course.get_by_id(course.id).title == "Exclude Test"
