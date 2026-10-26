"""The messages users get after saving courses and offerings and after
approving or dropping enrolments say what happened and what to do next."""

import models as M
from conftest import enrol, make_offering, make_user, set_event_window

SESSION = "2026-I"


async def post(client, route, data):
    res = await client.post(f"/acadstack/{route}", json=data)
    return await res.get_json()


async def test_saving_a_course_with_an_existing_code_names_the_code(client, auth, db):
    make_user("aca", role="ACA")
    await auth.login("aca")
    course = {"code": "AB1", "title": "T", "ltp": "3-0-0-6-3", "level": "ALL"}
    assert (await post(client, "cour_save", course))["status"] == "OK"
    body = await post(client, "cour_save", course)
    assert body["status"] == "ERROR"
    assert "code AB1 already exists" in body["body"]


async def test_stale_course_save_asks_to_reload(client, auth, db):
    make_user("aca", role="ACA")
    await auth.login("aca")
    crs = make_offering().course
    body = await post(client, "cour_save", {"id": crs.id, "title": "New", "txn_no": 99})
    assert body["status"] == "ERROR" and "Reload the page" in body["body"]


async def test_offering_of_an_unapproved_course_says_what_to_do(client, auth, db):
    make_user("aca", role="ACA")
    await auth.login("aca")
    crs = M.Course.create(code="AB1", title="T", ltp="3-0-0-6-3", status="DRA")
    M.AcademicSession.get_or_create(code=SESSION)
    body = await post(client, "co_save", {"acad_session": SESSION, "course": {"id": crs.id}})
    assert body["status"] == "ERROR"
    assert "Ask the Dean's office to approve the course" in body["body"]


async def test_approval_message_counts_the_requests(client, auth, db):
    ins = make_user("ins", role="FAC")
    stu = make_user("stu", role="STU")
    co = make_offering(acad_session=SESSION, instructor=ins)
    enrol(stu, co, enrol_status="IPEN")
    set_event_window(SESSION, "COURSE_REG")
    ce = M.CourseEnrollment.get()
    await auth.login("ins")
    body = await post(client, "change_enroll_status", {"ids": [ce.id], "status": "approve"})
    assert body == {"status": "OK", "body": "Approved 1 enrolment request(s)."}
    body = await post(client, "change_enroll_status", {"ids": [], "status": "approve"})
    assert body["status"] == "ERROR" and "Select at least one" in body["body"]


async def test_drop_message_names_the_course(client, auth, db):
    stu = make_user("stu", role="STU")
    co = make_offering(acad_session=SESSION)
    ce = enrol(stu, co)
    set_event_window(SESSION, "ADD_DROP")
    await auth.login("stu")
    res = await client.post(f"/acadstack/drop_withdraw_course/{ce.id}/DROP")
    assert await res.get_json() == {"status": "OK", "body": "Course CS101 dropped."}
