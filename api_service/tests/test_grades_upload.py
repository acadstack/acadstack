"""Characterization tests for the grades CSV upload (``/grades_upload``).

Most tests also put the same CSV in the uploader's folder first, which the
route overwrites with the uploaded file.
"""

import os
from io import BytesIO

import pytest
from quart.datastructures import FileStorage

import models as M
import settings
from conftest import enrol, make_offering, make_user, set_event_window, ten_point_scheme

SESSION = "2026-I"
HEADER = "first_name,last_name,roll_no,grade"

pytestmark = pytest.mark.usefixtures("grading_schemes")


@pytest.fixture
def setup(db):
    ins = make_user("ins", role="FAC")
    s1 = make_user("s1", role="STU", org_id="2024CSB1001")
    s2 = make_user("s2", role="STU", org_id="2024CSB1002")
    co = make_offering(acad_session=SESSION, status="R", instructor=ins)
    set_event_window(SESSION, "GRADE_SUB")
    return {"ins": ins, "co": co, "ce1": enrol(s1, co), "ce2": enrol(s2, co)}


async def upload(client, app, login_id, co_id, csv_text, seed_file=True):
    if seed_file:
        folder = os.path.join(app.config["upload_folder"], login_id)
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "grades.csv"), "w") as f:
            f.write(csv_text)
    fs = FileStorage(BytesIO(csv_text.encode()), filename="grades.csv",
                     content_type="text/csv")
    res = await client.post("/acadstack/grades_upload",
                            form={"course_offering": str(co_id)},
                            files={"grades_file": fs})
    return await res.get_json()


def grades(*ces):
    return [M.CourseEnrollment.get_by_id(ce.id).grade for ce in ces]


GOOD_CSV = f"{HEADER}\nA,B,2024CSB1001,A\nC,D,2024csb1002,b-\n"


async def test_fresh_upload_is_saved_and_processed(client, auth, app, setup):
    await auth.login("ins")
    body = await upload(client, app, "ins", setup["co"].id, GOOD_CSV, seed_file=False)
    assert body["status"] == "OK"
    assert grades(setup["ce1"], setup["ce2"]) == ["A", "B-"]


async def test_coordinator_uploads_grades(client, auth, app, setup):
    await auth.login("ins")
    body = await upload(client, app, "ins", setup["co"].id, GOOD_CSV)
    assert body["status"] == "OK"
    assert "updated 2 records" in body["body"]
    assert grades(setup["ce1"], setup["ce2"]) == ["A", "B-"]
    assert M.CourseEnrollment.get_by_id(setup["ce1"].id).txn_no == 2


async def test_unchanged_grades_are_not_counted(client, auth, app, setup):
    M.CourseEnrollment.update(grade="A").where(M.CourseEnrollment.id == setup["ce1"].id).execute()
    await auth.login("ins")
    body = await upload(client, app, "ins", setup["co"].id, GOOD_CSV)
    assert "updated 1 records" in body["body"]


async def test_academic_section_can_upload(client, auth, app, setup):
    make_user("aca", role="ACA")
    await auth.login("aca")
    assert (await upload(client, app, "aca", setup["co"].id, GOOD_CSV))["status"] == "OK"
    assert grades(setup["ce1"], setup["ce2"]) == ["A", "B-"]


async def test_non_coordinator_cannot_upload(client, auth, app, setup):
    other = make_user("other", role="FAC")
    M.CourseInstructor.create(offering=setup["co"], instructor=other, is_coordinator=False)
    await auth.login("other")
    body = await upload(client, app, "other", setup["co"].id, GOOD_CSV)
    assert body["status"] == "ERROR"
    assert "coordinator" in body["body"]
    assert grades(setup["ce1"], setup["ce2"]) == ["NA", "NA"]


async def test_upload_closed_outside_grade_submission_window(client, auth, app, setup):
    M.AcademicCalendar.delete().execute()
    set_event_window(SESSION, "GRADE_SUB", open_=False)
    await auth.login("ins")
    body = await upload(client, app, "ins", setup["co"].id, GOOD_CSV)
    assert body == {"status": "ERROR", "body": "Grades upload is not open!"}


async def test_faculty_cannot_upload_for_finished_offering(client, auth, app, setup):
    M.CourseOffering.update(status="F").execute()
    await auth.login("ins")
    body = await upload(client, app, "ins", setup["co"].id, GOOD_CSV)
    assert body["status"] == "ERROR"
    assert "ended/canceled" in body["body"]


async def test_missing_offering_id(client, auth, app, setup):
    await auth.login("ins")
    body = await upload(client, app, "ins", "", GOOD_CSV)
    assert body["status"] == "ERROR"
    assert "not selected the course" in body["body"]


async def test_bad_header(client, auth, app, setup):
    await auth.login("ins")
    body = await upload(client, app, "ins", setup["co"].id,
                        "roll_no,grade\n2024CSB1001,A\n2024CSB1002,A\n")
    assert "Invalid header row" in body["body"]


async def test_header_only_file(client, auth, app, setup):
    await auth.login("ins")
    body = await upload(client, app, "ins", setup["co"].id, HEADER + "\n")
    assert "No grades found" in body["body"]


async def test_invalid_grade(client, auth, app, setup):
    await auth.login("ins")
    body = await upload(client, app, "ins", setup["co"].id,
                        f"{HEADER}\nA,B,2024CSB1001,A+\nC,D,2024CSB1002,B\n")
    assert "Found invalid grades" in body["body"]
    assert grades(setup["ce1"], setup["ce2"]) == ["NA", "NA"]


async def test_grades_come_from_the_grading_schemes(client, auth, app, setup):
    s = ten_point_scheme("UG", name="Pass/fail")
    s["grades"] = [dict(s["grades"][0], grade="P", points=4), s["grades"][8]]
    settings.save("grading_schemes", [s])
    await auth.login("ins")
    body = await upload(client, app, "ins", setup["co"].id,
                        f"{HEADER}\nA,B,2024CSB1001,A\nC,D,2024CSB1002,P\n")
    assert "Found invalid grades" in body["body"]
    body = await upload(client, app, "ins", setup["co"].id,
                        f"{HEADER}\nA,B,2024CSB1001,P\nC,D,2024CSB1002,F\n")
    assert body["status"] == "OK"
    assert grades(setup["ce1"], setup["ce2"]) == ["P", "F"]


async def test_missing_enrolled_roll_number(client, auth, app, setup):
    await auth.login("ins")
    body = await upload(client, app, "ins", setup["co"].id, f"{HEADER}\nA,B,2024CSB1001,A\n")
    assert "missing" in body["body"] and "2024CSB1002" in body["body"]
    assert grades(setup["ce1"]) == ["NA"]


async def test_roll_number_not_enrolled(client, auth, app, setup):
    await auth.login("ins")
    body = await upload(client, app, "ins", setup["co"].id,
                        GOOD_CSV + "E,F,2024CSB9999,A\n")
    assert "not enrolled" in body["body"] and "2024CSB9999" in body["body"]


async def test_audit_enrolment_rejects_credit_grade_and_rolls_back(client, auth, app, setup):
    M.CourseEnrollment.update(enrol_type="A").where(
        M.CourseEnrollment.id == setup["ce2"].id).execute()
    await auth.login("ins")
    body = await upload(client, app, "ins", setup["co"].id, GOOD_CSV)
    assert body["status"] == "ERROR"
    assert "audited course" in body["body"]
    assert grades(setup["ce1"], setup["ce2"]) == ["NA", "NA"]


async def test_audit_enrolment_accepts_audit_grade(client, auth, app, setup):
    M.CourseEnrollment.update(enrol_type="A").where(
        M.CourseEnrollment.id == setup["ce2"].id).execute()
    await auth.login("ins")
    body = await upload(client, app, "ins", setup["co"].id,
                        f"{HEADER}\nA,B,2024CSB1001,A\nC,D,2024CSB1002,NP\n")
    assert body["status"] == "OK"
    assert grades(setup["ce1"], setup["ce2"]) == ["A", "NP"]


async def test_student_cannot_upload(client, auth, app, setup):
    await auth.login("s1")
    body = await upload(client, app, "s1", setup["co"].id, GOOD_CSV)
    assert body["status"] == "ERROR"
    assert grades(setup["ce1"], setup["ce2"]) == ["NA", "NA"]
