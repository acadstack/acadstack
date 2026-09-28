"""Characterization tests for attendance: class-photo upload, the photo
processing task, and the attendance read routes.

Tests whose name starts with a bug code (C22, ...) pin behaviour that
looks wrong; flip them when fixing it.
"""

import os
from datetime import date
from io import BytesIO

import pytest
from quart import session
from quart.datastructures import FileStorage

import api_attendance as apiAT
import models as M
from conftest import enrol, make_offering, make_user

SESSION = "2026-I"


@pytest.fixture
def setup(db):
    ins = make_user("ins", role="FAC")
    s1 = make_user("s1", role="STU", org_id="2024CSB1001")
    s2 = make_user("s2", role="STU", org_id="2024CSB1002")
    co = make_offering(acad_session=SESSION, status="R", instructor=ins)
    return {"ins": ins, "s1": s1, "s2": s2, "co": co,
            "ce1": enrol(s1, co), "ce2": enrol(s2, co)}


@pytest.fixture
def queued(monkeypatch):
    """Records background photo-processing jobs instead of running them."""
    ids = []
    monkeypatch.setattr(apiAT, "_process_attendance_photos", ids.append)
    return ids


async def post_photos(client, co_id):
    photo = FileStorage(BytesIO(b"\xff\xd8jpeg"), filename="p.jpg", content_type="image/jpeg")
    res = await client.post("/acadstack/mark_attendance",
                            form={"course_offering": str(co_id)},
                            files={"group_photos": photo})
    return await res.get_json()


# ---- /mark_attendance ----

async def test_coordinator_uploads_photo_and_job_is_queued(client, auth, app, setup, queued):
    await auth.login("ins")
    body = await post_photos(client, setup["co"].id)
    assert body == {"status": "OK", "body": "Saved 1 photos for processing."}
    ap = M.AttendancePhoto.get()
    assert (ap.offering_id, ap.status, ap.attend_dt) == (setup["co"].id, "PENDING", date.today())
    assert queued == [ap.id]


async def test_photo_file_is_written(client, auth, app, setup, queued):
    await auth.login("ins")
    await post_photos(client, setup["co"].id)
    ap = M.AttendancePhoto.get()
    assert os.path.exists(os.path.join(app.config["upload_folder"], "photos", ap.file_name))


async def test_no_photo(client, auth, setup, queued):
    await auth.login("ins")
    res = await client.post("/acadstack/mark_attendance",
                            form={"course_offering": str(setup["co"].id)})
    assert (await res.get_json())["body"] == "Please select at least one photo."


async def test_non_coordinator_cannot_upload(client, auth, setup, queued):
    make_user("fac", role="FAC")
    await auth.login("fac")
    body = await post_photos(client, setup["co"].id)
    assert body["status"] == "ERROR"
    assert M.AttendancePhoto.select().count() == 0
    assert queued == []


async def test_faculty_cannot_upload_for_finished_offering(client, auth, setup, queued):
    M.CourseOffering.update(status="F").execute()
    await auth.login("ins")
    assert (await post_photos(client, setup["co"].id))["status"] == "ERROR"
    assert M.AttendancePhoto.select().count() == 0


async def test_student_cannot_upload(client, auth, setup, queued):
    await auth.login("s1")
    assert (await post_photos(client, setup["co"].id))["status"] == "ERROR"


# ---- photo processing task ----

def _stub_face_matching(monkeypatch, found, missing):
    monkeypatch.setattr(apiAT, "_get_face_enc_and_user_info", lambda ap: ([], []))
    monkeypatch.setattr(apiAT.fapi, "find_persons_in_photo",
                        lambda path, known, tolerance: (found, missing, len(found) + len(missing), ""))


def _process_as(app, login_id, ap_id):
    """Runs the photo task inside a request whose session has ``login_id``
    logged in, which is what its save/update helpers need."""
    async def run():
        async with app.test_request_context("/"):
            session["user"] = {"login_id": login_id}
            apiAT._process_attendance_photos(ap_id)
    return run()


async def test_c22_photo_processing_works_outside_a_request(app, setup, monkeypatch):
    # Background tasks run with the app context but without a request.
    ap = M.AttendancePhoto.create(offering=setup["co"], file_name="x.jpg")
    _stub_face_matching(monkeypatch, [{"enrollment_id": setup["ce1"].id}],
                        [{"enrollment_id": setup["ce2"].id}])
    async with app.app_context():
        apiAT._process_attendance_photos(ap.id)
    att = {a.enrollment_id: a.attend for a in M.StudentAttendance.select()}
    assert att == {setup["ce1"].id: "P", setup["ce2"].id: "A"}
    assert M.AttendancePhoto.get_by_id(ap.id).status == "DONE"


async def test_photo_processing_marks_present_and_absent(app, setup, monkeypatch):
    ap = M.AttendancePhoto.create(offering=setup["co"], file_name="x.jpg")
    # A prior "P" for s2 on the same day is kept even though the face is missing.
    M.StudentAttendance.create(enrollment=setup["ce2"], attend_dt=ap.attend_dt, attend="P")
    _stub_face_matching(monkeypatch, [{"enrollment_id": setup["ce1"].id}],
                        [{"enrollment_id": setup["ce2"].id}])
    await _process_as(app, "ins", ap.id)
    att = {a.enrollment_id: a.attend for a in M.StudentAttendance.select()}
    assert att == {setup["ce1"].id: "P", setup["ce2"].id: "P"}
    assert M.AttendancePhoto.get_by_id(ap.id).status == "DONE"


async def test_photo_processing_marks_missing_face_absent(app, setup, monkeypatch):
    ap = M.AttendancePhoto.create(offering=setup["co"], file_name="x.jpg")
    _stub_face_matching(monkeypatch, [{"enrollment_id": setup["ce1"].id}],
                        [{"enrollment_id": setup["ce2"].id}])
    await _process_as(app, "ins", ap.id)
    att = {a.enrollment_id: a.attend for a in M.StudentAttendance.select()}
    assert att == {setup["ce1"].id: "P", setup["ce2"].id: "A"}


async def test_photo_processing_skips_done_photo(app, setup, monkeypatch):
    ap = M.AttendancePhoto.create(offering=setup["co"], file_name="x.jpg", status="DONE")
    _stub_face_matching(monkeypatch, [{"enrollment_id": setup["ce1"].id}], [])
    await _process_as(app, "ins", ap.id)
    assert M.StudentAttendance.select().count() == 0


# ---- read routes ----

async def test_student_reads_own_attendance(client, auth, setup):
    M.StudentAttendance.create(enrollment=setup["ce1"], attend_dt=date(2026, 8, 1), attend="P")
    M.StudentAttendance.create(enrollment=setup["ce1"], attend_dt=date(2026, 8, 2), attend="A")
    await auth.login("s1")
    body = await (await client.get(f"/acadstack/get_student_att_details/{setup['ce1'].id}")).get_json()
    assert body["status"] == "OK"
    assert body["body"]["rollNo"] == "2024CSB1001"
    assert sorted(r["attendance"] for r in body["body"]["records"]) == ["A", "P"]


async def test_student_cannot_read_others_attendance(client, auth, setup):
    await auth.login("s1")
    body = await (await client.get(f"/acadstack/get_student_att_details/{setup['ce2'].id}")).get_json()
    assert body["status"] == "ERROR"


async def test_student_cannot_read_class_attendance_on_date(client, auth, setup):
    M.StudentAttendance.create(enrollment=setup["ce2"], attend_dt=date(2026, 8, 1), attend="P")
    make_user("outsider", role="STU")
    await auth.login("outsider")
    body = await (await client.get(
        f"/acadstack/course_attd_on_date/{setup['co'].id}/2026-08-01")).get_json()
    assert body["status"] == "ERROR"


async def test_instructor_reads_class_attendance_on_date(client, auth, setup):
    M.StudentAttendance.create(enrollment=setup["ce2"], attend_dt=date(2026, 8, 1), attend="P")
    await auth.login("ins")
    body = await (await client.get(
        f"/acadstack/course_attd_on_date/{setup['co'].id}/2026-08-01")).get_json()
    assert body["status"] == "OK"
    assert body["body"][0]["roll_no"] == "2024CSB1002"


async def test_student_sees_only_own_row_of_class_roster(client, auth, setup):
    await auth.login("s1")
    body = await (await client.get(
        f"/acadstack/get_course_enrollments/{setup['co'].id}")).get_json()
    assert [r["org_id"] for r in body["body"]] == ["2024CSB1001"]


async def test_instructor_sees_whole_class_roster(client, auth, setup):
    await auth.login("ins")
    body = await (await client.get(
        f"/acadstack/get_course_enrollments/{setup['co'].id}")).get_json()
    assert sorted(r["org_id"] for r in body["body"]) == ["2024CSB1001", "2024CSB1002"]


async def test_daywise_attendance_sql_missing_group_by_so_route_always_fails(client, auth, setup):
    # The daywise_attendance query selects f.total without grouping by it,
    # which Postgres rejects.
    for ce, mark in ((setup["ce1"], "P"), (setup["ce2"], "A")):
        M.StudentAttendance.create(enrollment=ce, attend_dt=date(2026, 8, 1), attend=mark)
    await auth.login("ins")
    body = await (await client.get(f"/acadstack/daywise_att/{setup['co'].id}")).get_json()
    assert body == {"status": "ERROR",
                    "body": "Error occurred when fetching daywise attendance for course."}


async def test_daywise_attendance_denied_to_student(client, auth, setup):
    await auth.login("s1")
    body = await (await client.get(f"/acadstack/daywise_att/{setup['co'].id}")).get_json()
    assert body["status"] == "ERROR"


# ---- face service proxy ----

import base64
import json

import face_api_proxy as fapi


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def raise_for_status(self):
        pass

    def json(self):
        return self.body


def fake_service(monkeypatch, body):
    """Replaces the HTTP call to the face service; returns the recorded calls."""
    calls = []

    def post(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse(body)
    monkeypatch.setattr(fapi.requests, "post", post)
    return calls


def test_c24_known_faces_are_sent_and_results_mapped_back(monkeypatch, tmp_path):
    photo = tmp_path / "group.jpg"
    photo.write_bytes(b"jpeg")
    calls = fake_service(monkeypatch, {"found": [1], "missing": [0], "total_faces": 3,
                                       "marked_image": "data:image/jpeg;base64,"})
    infos = [{"enrollment_id": 10}, {"enrollment_id": 11}]
    found, missing, faces, _ = fapi.find_persons_in_photo(
        str(photo), ([[0.1, 0.2], [0.3, 0.4]], infos))
    assert (found, missing, faces) == ([infos[1]], [infos[0]], 3)
    url, kwargs = calls[0]
    assert url.endswith("/find_persons_in_photo")
    assert json.loads(kwargs["data"]["known_encodings"]) == [[0.1, 0.2], [0.3, 0.4]]
    assert json.loads(kwargs["data"]["known_names"]) == [0, 1]
    assert kwargs["timeout"] == fapi.TIMEOUT


def test_c24_marked_photo_is_decoded(monkeypatch, tmp_path):
    for name in ("person.jpg", "group.jpg"):
        (tmp_path / name).write_bytes(b"jpeg")
    args = (str(tmp_path / "person.jpg"), str(tmp_path / "group.jpg"))
    fake_service(monkeypatch, {"marked_image": "data:image/jpeg;base64,"
                               + base64.b64encode(b"marked").decode()})
    assert fapi.mark_person_in_photo(*args).getvalue() == b"marked"
    fake_service(monkeypatch, {"marked_image": None, "message": "Person not found"})
    assert fapi.mark_person_in_photo(*args) is None


def test_c24_text_is_written_on_the_image_field(monkeypatch, tmp_path):
    (tmp_path / "p.jpg").write_bytes(b"jpeg")
    calls = fake_service(monkeypatch, {"marked_image": "data:image/jpeg;base64,"
                                       + base64.b64encode(b"texted").decode()})
    assert fapi.write_text_on_image(str(tmp_path / "p.jpg"), "hi", (1, 2)).getvalue() == b"texted"
    assert list(calls[0][1]["files"]) == ["image"]
