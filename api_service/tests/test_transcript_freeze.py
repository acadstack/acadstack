"""Tests for closing a session (``/close_session``), which freezes the
enrolments' credits, and for the log of grade changes."""

from decimal import Decimal

import pytest

import models as M
from conftest import enrol, make_offering, make_user, set_event_window

SESSION = "2025-I"


@pytest.fixture
def setup(db):
    """A BTE student with an A in a 4-credit course and a B in a 3-credit
    course, both finished; ``ins`` coordinates the first."""
    make_user("aca", role="ACA")
    ins = make_user("ins", role="FAC")
    stu = make_user("stu", role="STU", degree="BTE", year_of_entry="2024")
    co1 = make_offering("CS101", ltp="3-0-2-7-4", acad_session=SESSION, status="F",
                        instructor=ins)
    co2 = make_offering("CS102", ltp="3-0-0-6-3", acad_session=SESSION, status="F")
    return {"stu": stu, "co1": co1, "co2": co2,
            "ce1": enrol(stu, co1, grade="A"), "ce2": enrol(stu, co2, grade="B")}


async def close(client, acad_session=SESSION):
    res = await client.post("/acadstack/close_session", json={"acad_session": acad_session})
    return await res.get_json()


async def cgpa(client, stu):
    body = await (await client.get(f"/acadstack/get_student_academics/{stu.id}")).get_json()
    return body["body"]["enrollments"]["C"]["enrollments"][SESSION]["cgpa"]


async def coe_save(client, ce, **fields):
    res = await client.post("/acadstack/coe_save",
                            json={"id": ce.id, "enrol_status": "ENRO", "txn_no": 1, **fields})
    return await res.get_json()


def credits(*ces):
    return [M.CourseEnrollment.get_by_id(ce.id).credits for ce in ces]


def is_closed():
    return M.AcademicCalendar.select().where(
        (M.AcademicCalendar.acad_session == SESSION) &
        (M.AcademicCalendar.event_code == "SESSION_CLOSED")).exists()


# ---- closing a session ----

async def test_closing_freezes_credits(client, auth, setup):
    await auth.login("aca")
    body = await close(client)
    assert body == {"status": "OK",
                    "body": f"Closed session {SESSION}: froze the credits of 2 enrolments."}
    assert credits(setup["ce1"], setup["ce2"]) == [Decimal("4.00"), Decimal("3.00")]
    assert is_closed()


async def test_course_change_after_closing_leaves_cgpa_unchanged(client, auth, setup):
    await auth.login("aca")
    assert await cgpa(client, setup["stu"]) == 9.14      # (40 + 24) / 7
    await close(client)
    M.Course.update(ltp="3-0-2-7-2").where(M.Course.code == "CS101").execute()
    assert await cgpa(client, setup["stu"]) == 9.14


async def test_course_change_before_closing_changes_cgpa(client, auth, setup):
    await auth.login("aca")
    M.Course.update(ltp="3-0-2-7-2").where(M.Course.code == "CS101").execute()
    assert await cgpa(client, setup["stu"]) == 8.8       # (20 + 24) / 5


async def test_closing_twice_is_refused(client, auth, setup):
    await auth.login("aca")
    await close(client)
    assert await close(client) == {"status": "ERROR",
                                   "body": f"Session {SESSION} is already closed."}


@pytest.mark.parametrize("status", ["E", "R"])
async def test_closing_with_running_offering_is_refused(client, auth, setup, status):
    make_offering("CS199", acad_session=SESSION, status=status)
    await auth.login("aca")
    body = await close(client)
    assert body == {"status": "ERROR",
                    "body": "These courses are still enrolling or running: CS199"}
    assert credits(setup["ce1"]) == [None]
    assert not is_closed()


async def test_closing_with_pending_grades_is_refused(client, auth, setup):
    M.CourseEnrollment.update(grade="NA").where(
        M.CourseEnrollment.id == setup["ce2"].id).execute()
    await auth.login("aca")
    assert await close(client) == {"status": "ERROR",
                                   "body": "Grades are pending in these courses: CS102"}
    assert not is_closed()


async def test_canceled_offering_does_not_block_closing(client, auth, setup):
    co = make_offering("CS198", acad_session=SESSION, status="C")
    enrol(setup["stu"], co)                              # grade NA
    await auth.login("aca")
    assert (await close(client))["status"] == "OK"


@pytest.mark.parametrize("session", ["", "2025", None])
async def test_invalid_session_is_refused(client, auth, setup, session):
    await auth.login("aca")
    assert (await close(client, session))["body"] == "Please supply a valid academic session!"


@pytest.mark.parametrize("role", ["DEA", "FAC", "STU"])
async def test_only_academic_section_closes(client, auth, setup, role):
    make_user("u", role=role)
    await auth.login("u")
    assert (await close(client))["status"] == "ERROR"
    assert not is_closed()


async def test_calendar_save_cannot_mark_session_closed(client, auth, setup):
    await auth.login("aca")
    res = await client.post("/acadstack/dates_save", json={
        "session": SESSION, "eventDates": {"SESSION_CLOSED": "2025-12-31"}})
    assert (await res.get_json())["status"] == "OK"
    assert not is_closed()


# ---- the log of grade changes ----

def changes(ce):
    return [(g.old_grade, g.new_grade, g.changed_by, g.reason)
            for g in M.GradeChange.select().where(M.GradeChange.enrolment == ce.id)
                                           .order_by(M.GradeChange.id)]


async def test_grade_change_is_logged(client, auth, setup):
    await auth.login("aca")
    body = await coe_save(client, setup["ce1"], grade="B")
    assert body["status"] == "OK"
    assert changes(setup["ce1"]) == [("A", "B", "aca", None)]


async def test_saving_without_grade_change_logs_nothing(client, auth, setup):
    await auth.login("aca")
    await coe_save(client, setup["ce1"], remarks="ok")
    assert changes(setup["ce1"]) == []


async def test_grade_change_after_closing_needs_a_reason(client, auth, setup):
    await auth.login("aca")
    await close(client)
    body = await coe_save(client, setup["ce1"], grade="B")
    assert body == {"status": "ERROR", "body": "The session is closed. Please give a "
                                               "reason for changing the grade."}
    assert M.CourseEnrollment.get_by_id(setup["ce1"].id).grade == "A"
    assert changes(setup["ce1"]) == []


async def test_grade_change_after_closing_with_reason(client, auth, setup):
    await auth.login("aca")
    await close(client)
    body = await coe_save(client, setup["ce1"], grade="B",
                          grade_change_reason="Re-evaluation")
    assert body["status"] == "OK"
    assert changes(setup["ce1"]) == [("A", "B", "aca", "Re-evaluation")]
    # The frozen credits stay
    assert credits(setup["ce1"]) == [Decimal("4.00")]


async def test_faculty_cannot_change_grade_after_closing(client, auth, setup):
    await auth.login("aca")
    await close(client)
    await auth.login("ins")
    body = await coe_save(client, setup["ce1"], grade="B", grade_change_reason="x")
    assert body["status"] == "ERROR"
    assert M.CourseEnrollment.get_by_id(setup["ce1"].id).grade == "A"


async def test_grade_upload_logs_changed_grades(client, auth, app, db):
    # Imported here: the upload helpers live with the upload tests.
    from test_grades_upload import GOOD_CSV, upload
    ins = make_user("ins", role="FAC")
    s1 = make_user("s1", role="STU", org_id="2024CSB1001")
    s2 = make_user("s2", role="STU", org_id="2024CSB1002")
    co = make_offering(acad_session="2026-I", status="R", instructor=ins)
    set_event_window("2026-I", "GRADE_SUB")
    ce1, ce2 = enrol(s1, co, grade="A"), enrol(s2, co)
    await auth.login("ins")
    body = await upload(client, app, "ins", co.id, GOOD_CSV)  # s1: A (unchanged), s2: B-
    assert body["status"] == "OK"
    assert changes(ce1) == []
    assert changes(ce2) == [("NA", "B-", "ins", None)]
