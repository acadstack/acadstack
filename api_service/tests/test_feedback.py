"""Course feedback: the sync feedback views work behind @C.rbac, and a
submission's status row belongs to the student's user record."""
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import models as DB  # noqa: E402
from conftest import create_user, login_as  # noqa: E402

SESSION = "2024-II"
#: Far above any user id the tests create, so no enrolment shares the
#: student's user id by coincidence.
ENROLMENT_ID = 5000


@pytest.fixture
def form(db):
    form = DB.FeedbackForm.create(form_name="End semester",
                                  form_type="END_SEM_FB", is_active=True)
    DB.FeedbackQuestion.create(form=form, question="Rate the course",
                               ans_options=["1", "2", "3"])
    return form


@pytest.fixture
def enrolment(form):
    """A running offering with open end-semester feedback, and a student
    enrolled in it."""
    today = date.today()
    for code, delta in (("FEEDBACK_S", -5), ("FEEDBACK_E", 5)):
        DB.AcademicCalendar.create(
            acad_session=SESSION, event_code=code,
            event_value=(today + timedelta(days=delta)).strftime("%Y-%m-%d"))
    course = DB.Course.create(code="FB101", title="Feedback", ltp="3-0-0-0-3",
                              credits=3, status="APP")
    offering = DB.CourseOffering.create(course=course, acad_session=SESSION,
                                        status="R", slot="A", dept_name="CSE")
    ci = DB.CourseInstructor.create(offering=offering,
                                    instructor=create_user("FAC", "fb_fac"),
                                    is_coordinator=True)
    student = create_user("STU", "fb_stu")
    ce = DB.CourseEnrollment.create(id=ENROLMENT_ID, course_offering=offering,
                                    student=student, enrol_type="C",
                                    enrol_status="ENRO", grade="NA")
    return ce, ci


def _submit(client, form, enrolment):
    ce, ci = enrolment
    question = DB.FeedbackQuestion.get(DB.FeedbackQuestion.form == form)
    return client.post("/acadstack/save_course_instructor_feedback", json={
        "enrolment_id": ce.id, "ci_id": ci.id,
        "form": {"id": form.id, "form_questions": [
            {"id": question.id, "is_optional": False, "answer": "3"}]}})


def test_sync_feedback_views_return_their_data(client, form):
    create_user("ACA", "fb_aca")
    login_as(client, "fb_aca")
    res = client.get("/acadstack/get_feedback_forms")
    assert res.json["status"] == "OK", res.json
    assert [f["id"] for f in res.json["body"]] == [form.id]

    res = client.get(f"/acadstack/load_feedback_form/{form.id}")
    assert res.json["status"] == "OK", res.json
    assert len(res.json["body"]["form_questions"]) == 1

    create_user("STU", "fb_reader")
    login_as(client, "fb_reader")
    res = client.get("/acadstack/get_active_feedback_form/END_SEM_FB")
    assert res.json["status"] == "OK", res.json
    assert res.json["body"]["id"] == form.id


def test_sync_feedback_views_still_require_login(client, form):
    res = client.get("/acadstack/get_feedback_forms")
    assert res.json == {"status": "ERROR",
                        "body": "Login required to access this operation."}


def test_submission_is_recorded_against_the_student(client, form, enrolment):
    ce, ci = enrolment
    assert not DB.CourseEnrollment.select().where(
        DB.CourseEnrollment.id == ce.student_id).exists()
    login_as(client, "fb_stu")

    res = _submit(client, form, enrolment)
    assert res.json["status"] == "OK", res.json
    status = DB.StudentFeedbackStatus.get()
    assert (status.student_id, status.course_instructor_id,
            status.is_submitted) == (ce.student_id, ci.id, True)

    res = _submit(client, form, enrolment)
    assert res.json["body"] == ("You have already submitted feedback for "
                                "this course and instructor.")


def test_deleting_another_enrolment_keeps_the_feedback_status(
        client, form, enrolment):
    ce, _ = enrolment
    # Another student's enrolment whose id equals our student's user id.
    other = DB.CourseEnrollment.create(
        id=ce.student_id, course_offering=ce.course_offering,
        student=create_user("STU", "fb_other"), enrol_type="C",
        enrol_status="ENRO", grade="NA")
    login_as(client, "fb_stu")
    assert _submit(client, form, enrolment).json["status"] == "OK"

    other.delete_instance()
    assert DB.StudentFeedbackStatus.select().count() == 1
    assert _submit(client, form, enrolment).json["status"] == "ERROR"
