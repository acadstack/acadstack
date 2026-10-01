"""Academic sessions: created on Academic Events, valid when they exist, and
ordered and chosen as current by their dates, whatever they are named."""

from datetime import date, timedelta

import api_common as apiVC
import models as M
import transcript as TR
from conftest import enrol, make_offering, make_user


def _days(n):
    return (date.today() + timedelta(days=n)).isoformat()


async def _save_session(client, session, start, end, **extra):
    res = await client.post("/acadstack/dates_save", json={
        "session": session, "eventDates": {"SESSION_S": start, "SESSION_E": end}, **extra})
    return await res.get_json()


async def test_fall_2027_is_created_validated_and_current(client, auth):
    make_user("aca", role="ACA")
    await auth.login("aca")
    assert not apiVC.academic_session_valid("Fall 2027")

    assert (await _save_session(client, "Fall 2027", _days(-30), _days(60)))["status"] == "OK"
    assert (await _save_session(client, "Spring 28", _days(90), _days(200)))["status"] == "OK"
    # An additional term that started earlier and overlaps Fall 2027.
    assert (await _save_session(client, "Summer 27", _days(-40), _days(10),
                                is_additional=True))["status"] == "OK"

    assert apiVC.academic_session_valid("Fall 2027")
    assert M.AcademicSession.get(M.AcademicSession.code == "Summer 27").is_additional
    assert apiVC.current_acad_session() == "Fall 2027"
    assert set(apiVC.current_acad_session_list(sem_only=False)) == {"Fall 2027", "Summer 27"}

    sd = (await (await client.get("/acadstack/get_static_data")).get_json())["body"]
    assert [s["id"] for s in sd["AcademicSessions"]] == ["Fall 2027", "Spring 28"]


async def test_upcoming_sessions_include_additional_ones(client, auth):
    make_user("aca", role="ACA")
    await auth.login("aca")
    await _save_session(client, "Fall 2027", _days(-30), _days(60))
    await _save_session(client, "Spring 28", _days(150), _days(250))
    await _save_session(client, "Winter 27", _days(70), _days(100), is_additional=True)
    await _save_session(client, "Fall 2028", _days(300), _days(400))

    sessions = apiVC.static_data_dict()["AcademicSessions"]
    assert [s["id"] for s in sessions] == ["Fall 2027", "Winter 27", "Spring 28"]
    assert "(additional)" in sessions[1]["value"]


async def test_session_names_are_checked_for_length_only(client, auth):
    make_user("aca", role="ACA")
    await auth.login("aca")
    for name in ("", "   ", "Autumn 2027"):
        body = await _save_session(client, name, _days(0), _days(1))
        assert body["status"] == "ERROR"
    assert M.AcademicSession.select().count() == 0
    assert M.AcademicCalendar.select().count() == 0


async def test_resaving_dates_keeps_is_additional(client, auth):
    make_user("aca", role="ACA")
    await auth.login("aca")
    await _save_session(client, "Summer 27", _days(0), _days(30), is_additional=True)
    await _save_session(client, "Summer 27", _days(1), _days(30))
    assert M.AcademicSession.get(M.AcademicSession.code == "Summer 27").is_additional

    res = await client.post("/acadstack/dates_search", json={"session": "Summer 27"})
    assert (await res.get_json())["body"]["is_additional"] is True


def test_sessions_sort_by_start_date():
    starts = {"Spring 28": "2028-01-10", "Fall 2027": "2027-08-01"}
    assert TR.sort_sessions(["X", "Spring 28", "Fall 2027"], starts) \
        == ["Fall 2027", "Spring 28", "X"]


async def test_transcript_sessions_follow_their_dates(client, auth):
    for code, start in (("Fall 2027", "2027-08-01"), ("Spring 28", "2028-01-10")):
        M.AcademicSession.create(code=code)
        M.AcademicCalendar.create(acad_session=code, event_code="SESSION_S", event_value=start)
    stu = make_user("stu", role="STU", degree="BTE", year_of_entry="2027")
    enrol(stu, make_offering("CS102", acad_session="Spring 28", status="F"), grade="B")
    enrol(stu, make_offering("CS101", acad_session="Fall 2027", status="F"), grade="A")

    await auth.login("stu")
    body = await (await client.get(f"/acadstack/get_student_academics/{stu.id}")).get_json()
    perf = body["body"]["enrollments"]["C"]
    assert perf["acad_sessions"] == ["Fall 2027", "Spring 28"]
    assert perf["enrollments"]["Spring 28"]["cgpa"] == 9
