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
