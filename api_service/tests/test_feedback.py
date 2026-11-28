"""Tests for students submitting course feedback."""

import pytest

import models as M
from conftest import enrol, make_offering, make_user, set_event_window

SESSION = "2026-I"


@pytest.fixture
def setup(db):
    ins = make_user("ins", role="FAC")
    co = make_offering(acad_session=SESSION, status="R", instructor=ins)
    # Others first, so that no enrolment has the student's user id.
    for i in range(3):
        enrol(make_user(f"other{i}", role="STU"), co)
    stu = make_user("stu", role="STU")
    ce = enrol(stu, co)
    form = M.FeedbackForm.create(form_name="End sem", form_type="END_SEM_FB")
    q = M.FeedbackQuestion.create(form=form, question="Clear?", ans_options=["agree"])
    set_event_window(SESSION, "SESSION")
    set_event_window(SESSION, "FEEDBACK")
    return {"stu": stu, "ce": ce, "form": form, "q": q,
            "ci": M.CourseInstructor.get(M.CourseInstructor.offering == co)}


async def submit(client, s):
    res = await client.post("/acadstack/save_course_instructor_feedback", json={
        "form": {"id": s["form"].id,
                 "form_questions": [{"id": s["q"].id, "is_optional": False,
                                     "answer": "agree"}]},
        "enrolment_id": s["ce"].id, "ci_id": s["ci"].id})
    return await res.get_json()


async def pending_feedback(client):
    res = await client.get("/acadstack/student_enrolments_for_fb/END_SEM_FB")
    return await res.get_json()


async def test_c15_plain_function_views_respond(client, auth, setup):
    await auth.login("stu")
    body = await (await client.get("/acadstack/get_feedback_forms")).get_json()
    assert body["status"] == "OK"
    assert [f["id"] for f in body["body"]] == [setup["form"].id]
    body = await (await client.get("/acadstack/get_active_feedback_form/END_SEM_FB")).get_json()
    assert [q["id"] for q in body["body"]["form_questions"]] == [setup["q"].id]


async def test_c16_submission_is_recorded_against_the_student(client, auth, setup):
    assert not M.CourseEnrollment.select().where(
        M.CourseEnrollment.id == setup["stu"].id).exists()
    await auth.login("stu")
    assert (await submit(client, setup))["status"] == "OK"
    sfs = M.StudentFeedbackStatus.get()
    assert (sfs.student_id, sfs.is_submitted) == (setup["stu"].id, True)
    assert M.CourseInstructorFeedback.get().feedback == "agree"

    again = await submit(client, setup)
    assert again["status"] == "ERROR"
    assert "already submitted" in again["body"]


async def test_pending_feedback_lists_course_until_submitted(client, auth, setup):
    await auth.login("stu")
    body = await pending_feedback(client)
    assert body["status"] == "OK"
    assert [r["enrolment_id"] for r in body["body"]] == [setup["ce"].id]
    await submit(client, setup)
    assert (await pending_feedback(client))["body"] == []


async def test_instructor_feedback_without_scaled_answers(client, auth, setup):
    set_event_window(SESSION, "SHOW_ENDSEM_FB")
    M.CourseInstructorFeedback.create(acad_session=SESSION, submission_id="s1",
                                      instructor=setup["ci"], question=setup["q"],
                                      feedback="yes")
    await auth.login("ins")
    co_id = setup["ce"].course_offering_id
    res = await client.get(f"/acadstack/get_instructor_feedback/{co_id}/"
                           f"{setup['ci'].instructor_id}/END_SEM_FB")
    body = await res.get_json()
    assert body["status"] == "OK"
    assert body["body"]["score"] == "No questions on the 1 - 5 scale."


# ---- Students with pending feedback (report) ----

@pytest.fixture
def two_students(db):
    """stu1 and stu2 in a course of SESSION; only stu1 has given feedback."""
    ins = make_user("ins", role="FAC")
    co = make_offering(acad_session=SESSION, status="R", instructor=ins)
    M.Course.update(title="Data, Structures").execute()
    stu1 = make_user("stu1", role="STU", degree="BTE", year_of_entry="2024")
    stu2 = make_user("stu2", role="STU", degree="BTE", year_of_entry="2025")
    enrol(stu1, co)
    enrol(stu2, co)
    form = M.FeedbackForm.create(form_name="End sem", form_type="END_SEM_FB")
    M.StudentFeedbackStatus.create(
        feedback_form=form, student=stu1, is_submitted=True,
        course_instructor=M.CourseInstructor.get(M.CourseInstructor.offering == co))
    make_user("aca", role="ACA")


async def pending_report(client, **crit):
    res = await client.post("/acadstack/feedback_pending", json={
        "form_type": "END_SEM_FB", "acad_session": SESSION, **crit})
    return await res.get_json()


async def test_report_lists_the_students_who_owe_feedback(client, auth, two_students):
    await auth.login("aca")
    body = await pending_report(client)
    assert body["status"] == "OK"
    assert [(s["org_id"], s["pending"]) for s in body["body"]] == \
        [("STU2", ["CS101 Data, Structures (Ins User)"])]
    assert (await pending_report(client, form_type="MID_SEM_FB"))["body"].__len__() == 2


async def test_report_filters_by_entry_year(client, auth, two_students):
    await auth.login("aca")
    assert (await pending_report(client, entry_year="2024"))["body"] == []
    assert len((await pending_report(client, entry_year="2025", degree="BTE",
                                     dept_name="CSE"))["body"]) == 1


async def test_report_needs_a_feedback_type_and_session(client, auth, two_students):
    await auth.login("aca")
    assert (await pending_report(client, form_type="X"))["status"] == "ERROR"
    assert (await pending_report(client, acad_session="nope"))["status"] == "ERROR"


async def test_report_downloads_as_csv(client, auth, two_students):
    await auth.login("aca")
    res = await client.get(f"/acadstack/download_feedback_pending/END_SEM_FB/{SESSION}/-/-/-")
    lines = (await res.get_data(as_text=True)).splitlines()
    assert lines[0].startswith("org_id,first_name")
    assert lines[1:] == ['STU2,Stu2,User,stu2@example.com,BTE,CSE,2025,2026-I,CS101,'
                         '"Data, Structures",Ins User']
