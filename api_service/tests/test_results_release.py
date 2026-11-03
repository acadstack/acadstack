"""Releasing results: the order of a session's calendar dates, grades shown
before the result declaration date, withheld results, students' own grade
sheets, and the CGPA report's filters."""

from datetime import date, timedelta

import pytest

import models as M
from conftest import enrol, json_of, make_offering, make_user


def _days(n):
    return (date.today() + timedelta(days=n)).isoformat()


async def _save_dates(client, dates, session="2026-I"):
    return await json_of(await client.post("/acadstack/dates_save", json={
        "session": session,
        "eventDates": {"SESSION_S": _days(-100), "SESSION_E": _days(100), **dates}}))


def _declare(acad_session, days_from_today):
    M.AcademicSession.get_or_create(code=acad_session)
    M.AcademicCalendar.create(acad_session=acad_session, event_code="RESULT_DECLARATION",
                              event_value=_days(days_from_today))


async def _academics(client, stu):
    body = await json_of(await client.get(f"/acadstack/get_student_academics/{stu.id}"))
    return body["body"]["enrollments"]["C"]["enrollments"]["2026-I"]


# ---- Order of the calendar dates ----

@pytest.mark.parametrize("dates", [
    {"GRADE_SUB_S": _days(1), "GRADE_SUB_E": _days(20), "RESULT_DECLARATION": _days(10)},
    {"COURSE_REG_S": _days(5), "COURSE_REG_E": _days(9), "ADD_DROP_S": _days(1),
     "ADD_DROP_E": _days(9)},
    {"ADD_DROP_S": _days(5), "ADD_DROP_E": _days(9), "WITHDRAW_S": _days(1),
     "WITHDRAW_E": _days(9)},
    {"CLASSES_S": _days(5), "CLASSES_E": _days(50), "MINOR_EXAM_S": _days(1),
     "MINOR_EXAM_E": _days(3)},
    {"MINOR_EXAM_S": _days(1), "MINOR_EXAM_E": _days(10), "MAJOR_EXAM_S": _days(5),
     "MAJOR_EXAM_E": _days(20)},
    {"FEEDBACK_MID_S": _days(5), "FEEDBACK_MID_E": _days(9), "SHOW_MIDSEM_FB_S": _days(1)},
    {"FEEDBACK_S": _days(5), "FEEDBACK_E": _days(9), "SHOW_ENDSEM_FB_S": _days(1)},
    {"CLASSES_S": _days(9), "CLASSES_E": _days(1)},
])
async def test_dates_out_of_order_are_rejected(client, auth, dates):
    make_user("aca", role="ACA")
    await auth.login("aca")
    body = await _save_dates(client, dates)
    assert body["status"] == "ERROR" and "must not be after" in body["body"]
    assert M.AcademicCalendar.select().count() == 0


async def test_dates_in_order_are_saved(client, auth):
    make_user("aca", role="ACA")
    await auth.login("aca")
    body = await _save_dates(client, {
        "COURSE_REG_S": _days(-90), "COURSE_REG_E": _days(-80),
        "ADD_DROP_S": _days(-80), "ADD_DROP_E": _days(-70),
        "WITHDRAW_S": _days(-70), "WITHDRAW_E": _days(-10),
        "CLASSES_S": _days(-80), "CLASSES_E": _days(10),
        "MINOR_EXAM_S": _days(-40), "MINOR_EXAM_E": _days(-35),
        "MAJOR_EXAM_S": _days(12), "MAJOR_EXAM_E": _days(20),
        "GRADE_SUB_S": _days(15), "GRADE_SUB_E": _days(30), "RESULT_DECLARATION": _days(30)})
    assert body["status"] == "OK"


async def test_a_partial_save_is_checked_against_the_stored_dates(client, auth):
    make_user("aca", role="ACA")
    await auth.login("aca")
    assert (await _save_dates(client, {"RESULT_DECLARATION": _days(10)}))["status"] == "OK"
    body = await json_of(await client.post("/acadstack/dates_save", json={
        "session": "2026-I", "eventDates": {"GRADE_SUB_S": _days(1), "GRADE_SUB_E": _days(20)}}))
    assert body["status"] == "ERROR"
    # Clearing the declaration date lifts the rule
    body = await json_of(await client.post("/acadstack/dates_save", json={
        "session": "2026-I", "eventDates": {"GRADE_SUB_S": _days(1), "GRADE_SUB_E": _days(20),
                                            "RESULT_DECLARATION": ""}}))
    assert body["status"] == "OK"


# ---- Grades before the result declaration date ----

async def test_academic_section_sees_grades_before_declaration(client, auth, grading_schemes):
    stu = make_user("stu", role="STU", degree="BTE", year_of_entry="2023")
    enrol(stu, make_offering(ltp="3-0-0-6-4", status="F"), grade="A")
    _declare("2026-I", 10)

    make_user("aca", role="ACA")
    await auth.login("aca")
    sess = await _academics(client, stu)
    assert sess["courses"][0]["grade"] == "A"
    assert (sess["sgpa"], sess["ec"], sess["declared"]) == (10, 4, False)

    await auth.logout()
    await auth.login("stu")
    sess = await _academics(client, stu)
    assert sess["courses"][0]["grade"] == "NA" and sess["sgpa"] == 0


async def test_semester_grade_shows_grades_before_declaration(client, auth, grading_schemes):
    stu = make_user("stu", role="STU", org_id="2023CSB1001", degree="BTE",
                    year_of_entry="2023")
    enrol(stu, make_offering(ltp="3-0-0-6-4", status="F"), grade="A")
    _declare("2026-I", 10)
    make_user("aca", role="ACA")
    await auth.login("aca")
    body = await json_of(await client.post("/acadstack/generate_semester_grade", json={
        "entry_no": "2023CSB1001", "acad_session": "2026-I", "enrol_type": "C"}))
    assert body["body"]["courses"][0]["grade"] == "A"
    assert (body["body"]["sgpa"], body["body"]["cgpa"]) == (10, 10)


async def test_credits_data_waits_for_declaration(client, auth):
    _declare("2026-I", 10)
    make_user("aca", role="ACA")
    await auth.login("aca")
    body = await json_of(await client.get("/acadstack/gen_students_credits/2026-I"))
    assert body["status"] == "ERROR" and "not declared" in body["body"]


# ---- Withheld results ----

async def test_withheld_result_is_hidden_from_the_student(client, auth, grading_schemes):
    stu = make_user("stu", role="STU", degree="BTE", year_of_entry="2023")
    enrol(stu, make_offering(ltp="3-0-0-6-4", status="F"), grade="A")
    _declare("2026-I", -1)

    make_user("aca", role="ACA")
    await auth.login("aca")
    hold = {"user_id": stu.id, "acad_session": "2026-I", "hold": True, "reason": "Dues"}
    assert (await json_of(await client.post("/acadstack/result_hold", json=hold)))["status"] == "OK"
    assert M.ResultHold.get().reason == "Dues"
    sess = await _academics(client, stu)
    assert sess["withheld"] and sess["courses"][0]["grade"] == "A"

    await auth.logout()
    await auth.login("stu")
    sess = await _academics(client, stu)
    assert sess["withheld"] and sess["courses"][0]["grade"] == "NA"
    assert (await json_of(await client.post("/acadstack/result_hold", json=hold)))["status"] \
        == "ERROR"

    await auth.logout()
    await auth.login("aca")
    body = await json_of(await client.post("/acadstack/result_hold",
                                           json={**hold, "hold": False}))
    assert body["status"] == "OK" and M.ResultHold.select().count() == 0


async def test_only_students_results_are_withheld(client, auth):
    fac = make_user("fac", role="FAC")
    _declare("2026-I", -1)
    make_user("aca", role="ACA")
    await auth.login("aca")
    body = await json_of(await client.post("/acadstack/result_hold", json={
        "user_id": fac.id, "acad_session": "2026-I", "hold": True}))
    assert body["status"] == "ERROR"


# ---- A student's own grade sheet ----

@pytest.mark.parametrize("entry_no, declared_in, held, error", [
    ("2023CSB1002", -1, False, "only your own"),
    ("2023CSB1001", 10, False, "not declared"),
    ("2023CSB1001", -1, True, "withheld"),
])
async def test_student_grade_sheet_refusals(client, auth, grading_schemes,
                                            entry_no, declared_in, held, error):
    stu = make_user("stu", role="STU", org_id="2023CSB1001", degree="BTE",
                    year_of_entry="2023")
    make_user("other", role="STU", org_id="2023CSB1002", degree="BTE")
    enrol(stu, make_offering(status="F"), grade="A")
    _declare("2026-I", declared_in)
    if held:
        M.ResultHold.create(student=stu, acad_session="2026-I")
    await auth.login("stu")
    body = await json_of(await client.get(f"/acadstack/download_sem_grade/2026-I/{entry_no}/C"))
    assert body["status"] == "ERROR" and error in body["body"]


async def test_faculty_cannot_download_grade_sheets(client, auth):
    make_user("stu", role="STU", org_id="2023CSB1001")
    make_user("fac", role="FAC")
    await auth.login("fac")
    body = await json_of(await client.get("/acadstack/download_sem_grade/2026-I/2023CSB1001/C"))
    assert body["status"] == "ERROR"


async def test_student_downloads_own_grade_sheet(client, auth, grading_schemes):
    pytest.importorskip("weasyprint", exc_type=OSError)
    stu = make_user("stu", role="STU", org_id="2023CSB1001", degree="BTE",
                    year_of_entry="2023")
    enrol(stu, make_offering(status="F"), grade="A")
    _declare("2026-I", -1)
    await auth.login("stu")
    res = await client.get("/acadstack/download_sem_grade/2026-I/2023CSB1001/C")
    assert (await res.get_data()).startswith(b"%PDF")


# ---- CGPA report filters ----

async def test_cgpa_report_filters_by_degree_and_entry_year(client, auth):
    M.AcademicSession.get_or_create(code="2026-I")
    for login, degree, year in (("a", "BTE", "2025"), ("b", "BTE", "2024"),
                                ("c", "MTE", "2025")):
        stu = make_user(login, role="STU", org_id=login.upper(), degree=degree,
                        year_of_entry=year)
        M.StudentCredits.create(student=stu, acad_session="2026-I", cgpa=8, sgpa=8,
                                cred_earned=4, cred_registered=4, cred_earned_total=4)
    make_user("aca", role="ACA")
    await auth.login("aca")

    async def rolls(**filters):
        body = await json_of(await client.post("/acadstack/cgpa_sgpa",
                                               json={"acad_session": "2026-I", **filters}))
        return sorted(r["roll_no"] for r in body["body"]["data"])

    assert await rolls() == ["A", "B", "C"]
    assert await rolls(degree="BTE") == ["A", "B"]
    assert await rolls(degree="BTE", entry_year="2025") == ["A"]
    res = await client.get("/acadstack/download_cgpa_sgpa/2026-I/-/2025")
    assert res.status_code == 200


@pytest.mark.parametrize("role", ["FAC", "HOD", "PLA", "STU"])
async def test_cgpa_csv_needs_the_cgpa_report_permission(client, auth, role):
    make_user("u", role=role)
    await auth.login("u")
    body = await json_of(await client.get("/acadstack/download_cgpa_sgpa/2026-I/-/-"))
    assert body["status"] == "ERROR"


async def test_withheld_session_still_counts_in_later_cgpa(client, auth, grading_schemes):
    stu = make_user("stu", role="STU", degree="BTE", year_of_entry="2023")
    _declare("2025-I", -60)
    _declare("2025-II", -1)
    M.AcademicCalendar.create(acad_session="2025-I", event_code="SESSION_S", event_value="2025-07-01")
    M.AcademicCalendar.create(acad_session="2025-II", event_code="SESSION_S", event_value="2026-01-01")
    enrol(stu, make_offering("CS101", ltp="3-0-0-6-4", acad_session="2025-I", status="F"), grade="A")
    enrol(stu, make_offering("CS102", ltp="3-0-0-6-4", acad_session="2025-II", status="F"), grade="C")
    M.ResultHold.create(student=stu, acad_session="2025-I", reason="Dues")

    async def sessions():
        body = await json_of(await client.get(f"/acadstack/get_student_academics/{stu.id}"))
        return body["body"]["enrollments"]["C"]["enrollments"]

    make_user("aca", role="ACA")
    await auth.login("aca")
    staff = await sessions()
    assert staff["2025-I"]["hold_reason"] == "Dues"
    assert (staff["2025-II"]["cgpa"], staff["2025-II"]["cec"]) == (8, 8)

    await auth.logout()
    await auth.login("stu")
    own = await sessions()
    assert (own["2025-II"]["cgpa"], own["2025-II"]["cec"]) == (8, 8)
    assert own["2025-I"]["courses"][0]["grade"] == "NA"
    assert (own["2025-I"]["sgpa"], own["2025-I"]["cgpa"]) == ("NA", "NA")
    assert "hold_reason" not in own["2025-I"]


async def test_withholding_again_updates_the_reason(client, auth):
    stu = make_user("stu", role="STU")
    _declare("2026-I", -1)
    make_user("aca", role="ACA")
    await auth.login("aca")
    for reason in ("Fees due", "Disciplinary"):
        await client.post("/acadstack/result_hold", json={
            "user_id": stu.id, "acad_session": "2026-I", "hold": True, "reason": reason})
    assert [h.reason for h in M.ResultHold.select()] == ["Disciplinary"]


@pytest.mark.parametrize("days, declared", [(None, True), (1, False), (0, True), (-1, True)])
def test_is_result_declared(db, days, declared):
    import validation_checks as VAL
    if days is not None:
        _declare("2026-I", days)
    assert VAL.is_result_declared("2026-I") == declared


def test_demo_data_stores_the_codes_the_app_reads(db):
    import demo_data
    demo_data._create_acad_sessions()
    codes = {r.event_code for r in M.AcademicCalendar.select()}
    assert {"RESULT_DECLARATION", "SHOW_ENDSEM_FB_S", "GRADE_SUB_E"} <= codes
    assert not {"RESULT_DECLARATION_S", "RESULT_DECLARATION_E", "SHOW_ENDSEM_FB_E"} & codes
