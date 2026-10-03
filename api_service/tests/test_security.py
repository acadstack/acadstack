"""Tests for the access-control and authentication fixes (S1-S12 in
docs/past-sessions-report.md) that the other test modules do not cover.
"""

import base64
import builtins
import os
import random
from datetime import datetime, timedelta
from io import BytesIO

import pytest
from quart import Blueprint
from quart.datastructures import FileStorage

import api_auth as apiAU
import api_common as apiVC
import common as C
import face_api_proxy as fapi
import models as M
import settings
from acadstack_app import create_app
from conftest import make_user


@pytest.fixture(autouse=True)
def no_prk_failures(app):
    app.prk_failures.clear()


async def post(client, url, payload):
    return await (await client.post(f"/acadstack/{url}", json=payload)).get_json()


# ---- S1: user_save mass assignment ----

async def test_student_cannot_make_self_superuser(client, auth, db):
    stu = make_user("stu", role="STU", degree="BTE")
    await auth.login("stu")
    await post(client, "user_save", {"id": stu.id, "role": "SUP", "is_locked": False,
                                     "password_hashed": "x", "first_name": "New",
                                     "person": {"id": stu.person_id, "degree": "PHD"},
                                     "txn_no": 1})
    u = M.User.get_by_id(stu.id)
    assert (u.role, u.person.degree, u.first_name) == ("STU", "BTE", "New")
    assert u.password_hashed != "x"


async def test_academic_section_cannot_grant_superuser(client, auth, db):
    make_user("aca", role="ACA")
    fac = make_user("fac", role="FAC")
    await auth.login("aca")
    body = await post(client, "user_save", {"id": fac.id, "role": "SUP", "txn_no": 1})
    assert body["status"] == "ERROR"
    assert M.User.get_by_id(fac.id).role == "FAC"


async def test_academic_section_cannot_edit_superuser(client, auth, db):
    make_user("aca", role="ACA")
    sup = make_user("sup", role="SUP")
    await auth.login("aca")
    body = await post(client, "user_save", {"id": sup.id, "email": "x@example.com",
                                            "txn_no": 1})
    assert body["status"] == "ERROR"
    assert M.User.get_by_id(sup.id).email == "sup@example.com"


async def test_academic_section_edits_user_and_person(client, auth, db):
    make_user("aca", role="ACA")
    stu = make_user("stu", role="STU", degree="BTE")
    other = make_user("other", role="STU")
    await auth.login("aca")
    body = await post(client, "user_save", {
        "id": stu.id, "role": "FAC", "first_name": "Renamed", "txn_no": 1,
        "password_hashed": "x",
        "person": {"id": other.person_id, "degree": "MTE", "txn_no": 1}})
    assert body["status"] == "OK"
    u = M.User.get_by_id(stu.id)
    assert (u.role, u.first_name, u.person_id, u.person.degree) == \
        ("FAC", "Renamed", stu.person_id, "MTE")
    assert u.password_hashed != "x"
    assert M.Person.get_by_id(other.person_id).degree is None


async def test_superuser_creates_user(client, auth, db):
    make_user("sup", role="SUP")
    await auth.login("sup")
    body = await post(client, "user_save", {
        "login_id": "new", "email": "new@example.com", "role": "FAC",
        "first_name": "New", "person": {"org_id": "NEW1", "dept_name": "CSE"}})
    assert body["status"] == "OK"
    u = M.User.get(M.User.login_id == "new")
    assert (u.role, u.person.org_id) == ("FAC", "NEW1")


async def test_user_save_rejects_unknown_role(client, auth, db):
    make_user("sup", role="SUP")
    fac = make_user("fac", role="FAC")
    await auth.login("sup")
    body = await post(client, "user_save", {"id": fac.id, "role": "XYZ", "txn_no": 1})
    assert body["status"] == "ERROR"


# ---- S9: face photos ----

PHOTO_B64 = apiVC.B64_HDR + base64.b64encode(b"\xff\xd8jpeg").decode()


async def test_user_save_does_not_delete_other_users_photo(client, auth, db, monkeypatch):
    monkeypatch.setattr(fapi, "get_face_encoding_b64", lambda b64: [0.0])
    make_user("aca", role="ACA")
    stu = make_user("stu", role="STU")
    other = make_user("other", role="STU")
    kf = M.KnownFace.create(user=other, face_enc="{}", photo="other.jpg")
    await auth.login("aca")
    body = await post(client, "user_save", {"id": stu.id, "txn_no": 1,
                                            "photo_new": PHOTO_B64,
                                            "known_faces": [{"id": kf.id}]})
    assert body["status"] == "OK"
    assert M.KnownFace.get_or_none(M.KnownFace.id == kf.id) is not None
    assert stu.known_faces.count() == 1


async def test_student_cannot_change_photo_through_user_save(client, auth, db):
    stu = make_user("stu", role="STU")
    await auth.login("stu")
    body = await post(client, "user_save", {"id": stu.id, "txn_no": 1,
                                            "photo_new": PHOTO_B64})
    assert body["status"] == "ERROR"
    assert stu.known_faces.count() == 0


async def upload_face(client):
    photo = FileStorage(BytesIO(b"\xff\xd8jpeg"), filename="p.jpg", content_type="image/jpeg")
    res = await client.post("/acadstack/face_add", files={"photo_file": photo})
    return await res.get_json()


async def test_student_adds_first_photo_but_cannot_replace_it(client, auth, db, monkeypatch):
    monkeypatch.setattr(fapi, "get_face_encoding", lambda buf: [0.0])
    stu = make_user("stu", role="STU")
    await auth.login("stu")
    assert (await upload_face(client))["status"] == "OK"
    photo = stu.known_faces.get().photo
    assert (await upload_face(client))["status"] == "ERROR"
    assert stu.known_faces.get().photo == photo


async def test_photo_without_one_face_shows_the_face_service_message(client, auth, db, monkeypatch):
    class NoFace:
        status_code = 422
        def json(self):
            return {"error": "The photo must show exactly one face, but 0 were found."}
    monkeypatch.setattr(fapi.requests, "post", lambda *a, **kw: NoFace())
    stu = make_user("stu", role="STU")
    await auth.login("stu")
    res = await upload_face(client)
    assert res == {"status": "ERROR",
                   "body": "The photo must show exactly one face, but 0 were found."}
    assert not stu.known_faces.exists()


async def test_student_can_fetch_only_own_photo(client, auth, app, db):
    stu = make_user("stu", role="STU")
    other = make_user("other", role="STU")
    photos = os.path.join(app.config["upload_folder"], "photos")
    os.makedirs(photos)
    for user, name in ((stu, "mine"), (other, "theirs")):
        M.KnownFace.create(user=user, face_enc="{}", photo=name)
        with open(os.path.join(photos, name), "wb") as f:
            f.write(b"\xff\xd8jpeg")
    await auth.login("stu")
    res = await client.get("/acadstack/get_image/theirs")
    assert (await res.get_json())["status"] == "ERROR"
    res = await client.get("/acadstack/get_image/mine")
    assert await res.get_data() == b"\xff\xd8jpeg"


# ---- S2: random values and the session secret ----

def test_random_strings_do_not_come_from_the_random_module():
    random.seed(1)
    a = C.get_rand_str(20)
    random.seed(1)
    assert C.get_rand_str(20) != a


def test_session_secret_is_read_from_environment(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "k" * 40)
    # create_app registers routes on the module-level blueprint; use a fresh one.
    monkeypatch.setattr(apiVC, "vbp", Blueprint("bp", "api_common"))
    assert create_app(is_testing=True).secret_key == "k" * 40


# ---- S3/S4: login and password reset ----

async def test_login_response_is_same_for_unknown_and_locked_users(client, auth, db):
    u = make_user("test")
    M.User.update(is_locked=True).where(M.User.id == u.id).execute()
    locked = await (await auth.login(password="wrong")).get_json()
    unknown = await (await auth.login(login_id="nobody", password="wrong")).get_json()
    assert locked == unknown == {"status": "ERROR", "body": "Invalid user/password."}


async def request_key(client, login_id="test", email="test@example.com"):
    return await post(client, "gen_prk", {"login_id": login_id, "email": email})


async def reset(client, key, login_id="test", email="test@example.com", password="newpass"):
    return await post(client, "reset_password", {"login_id": login_id, "email": email,
                                                 "key_code": key, "new_password": password})


def latest_key(login_id="test"):
    return M.PasswordResetKey.select().where(
        M.PasswordResetKey.login_id == login_id).order_by(-M.PasswordResetKey.id).get()


async def test_password_reset_with_valid_key(client, auth, db):
    make_user("test")
    assert (await request_key(client))["status"] == "OK"
    assert (await reset(client, latest_key().prk))["status"] == "OK"
    assert (await (await auth.login(password="newpass")).get_json())["status"] == "OK"
    assert M.PasswordResetKey.select().count() == 0


async def test_reset_key_request_response_does_not_reveal_account(client, db):
    make_user("test")
    known = await request_key(client)
    unknown = await request_key(client, login_id="nobody")
    wrong_email = await request_key(client, email="x@example.com")
    assert known == unknown == wrong_email
    assert M.PasswordResetKey.select().count() == 1


async def test_reset_response_does_not_reveal_account(client, db):
    u = make_user("test")
    wrong_key = await reset(client, "BADKEY")
    unknown = await reset(client, "BADKEY", login_id="nobody")
    M.User.update(is_locked=True).where(M.User.id == u.id).execute()
    locked = await reset(client, "BADKEY")
    assert wrong_key == unknown == locked == \
        {"status": "ERROR", "body": apiAU.PRK_INVALID_MSG}


async def test_expired_reset_key_is_rejected(client, db):
    make_user("test")
    await request_key(client)
    prk = latest_key()
    M.PasswordResetKey.update(ins_ts=datetime.now() - apiAU.PRK_TTL - timedelta(minutes=1)
                              ).where(M.PasswordResetKey.id == prk.id).execute()
    assert (await reset(client, prk.prk))["status"] == "ERROR"


async def test_wrong_keys_lock_out_password_reset(client, db):
    make_user("test")
    await request_key(client)
    key = latest_key().prk
    for _ in range(settings.get("lockout_limit")):
        assert (await reset(client, "BADKEY"))["status"] == "ERROR"
    # The correct key no longer works, and no new key is issued.
    assert (await reset(client, key))["status"] == "ERROR"
    await request_key(client)
    assert M.PasswordResetKey.select().count() == 0
    # The account itself is not locked.
    assert not M.User.get(M.User.login_id == "test").is_locked


async def test_repeated_key_requests_do_not_lock_account(client, db):
    make_user("test")
    for _ in range(settings.get("lockout_limit") + 2):
        assert (await request_key(client))["status"] == "OK"
    assert M.PasswordResetKey.select().count() == settings.get("lockout_limit")
    assert not M.User.get(M.User.login_id == "test").is_locked
    assert (await reset(client, latest_key().prk))["status"] == "OK"


# ---- S8: no deletes over GET ----

@pytest.mark.parametrize("url", ["delete_doc/1", "delete_fees_txn_data/1", "wfnote_delete/1"])
async def test_delete_routes_reject_get(client, auth, db, url):
    make_user("aca", role="ACA")
    await auth.login("aca")
    # No GET route matches, so the request falls through to the static files.
    assert (await client.get(f"/acadstack/{url}")).status_code == 404


async def test_workflow_note_deleted_over_post(client, auth, db):
    make_user("aca", role="ACA")
    note = M.WorkflowNote.create(entity_key=1, entity_name="offer", note="n",
                                 txn_login_id="aca")
    await auth.login("aca")
    body = await (await client.post(f"/acadstack/wfnote_delete/{note.id}")).get_json()
    assert body == {"status": "OK", "body": "Deleted 1 records."}


async def test_drop_withdraw_rejects_get(client, auth, db):
    make_user("stu", role="STU")
    await auth.login("stu")
    assert (await client.get("/acadstack/drop_withdraw_course/1/DROP")).status_code == 404


def make_fee(student):
    return M.FeesTransaction.create(student=student, acad_session="2026-I", fees_txn_amt=100,
                                    fees_txn_no="T1", fees_txn_dt="2026-07-01",
                                    fees_txn_bank="B", doc_file_name="f")


async def test_faculty_cannot_delete_student_fee_record(client, auth, db):
    fee = make_fee(make_user("stu", role="STU"))
    make_user("fac", role="FAC")
    await auth.login("fac")
    body = await (await client.post(f"/acadstack/delete_fees_txn_data/{fee.id}")).get_json()
    assert body["status"] == "ERROR"
    assert not M.FeesTransaction.get_by_id(fee.id).is_deleted


@pytest.mark.parametrize("login_id,role", [("stu", "STU"), ("aca", "ACA")])
async def test_owner_and_academic_section_delete_fee_record(client, auth, db, login_id, role):
    fee = make_fee(make_user("stu", role="STU"))
    if role != "STU":
        make_user(login_id, role=role)
    await auth.login(login_id)
    body = await (await client.post(f"/acadstack/delete_fees_txn_data/{fee.id}")).get_json()
    assert body["status"] == "OK"
    assert M.FeesTransaction.get_by_id(fee.id).is_deleted


# ---- DC chair lookup ----

async def test_dc_chair_lookup_only_for_self(client, auth, db):
    stu = make_user("stu", role="STU", degree="PHD")
    cp = make_user("cp", role="FAC")
    fac = make_user("fac", role="FAC")
    dc = M.DcForStudent.create(student=stu, status="DRA", effective_from="2026-01-01")
    M.DcMember.create(dc=dc, member=cp, role="CP")
    await auth.login("fac")
    body = await (await client.get(f"/acadstack/isdcc/{cp.id}/{stu.id}")).get_json()
    assert body["status"] == "ERROR"
    assert (await (await client.get(f"/acadstack/isdcc/{fac.id}/{stu.id}")).get_json()) == \
        {"status": "OK", "body": False}


# ---- course_save author ----

def make_course(author):
    return M.Course.create(code="CS300", title="Old", ltp="3-0-0-6-3", status="DRA",
                           author=author)


async def test_faculty_cannot_edit_others_course_by_claiming_authorship(client, auth, db):
    crs = make_course(make_user("fac1", role="FAC"))
    fac2 = make_user("fac2", role="FAC")
    await auth.login("fac2")
    body = await post(client, "cour_save", {"id": crs.id, "title": "New", "txn_no": 1,
                                            "author": {"id": fac2.id}})
    assert body["status"] == "ERROR"
    assert (M.Course.get_by_id(crs.id).title, M.Course.get_by_id(crs.id).author_id) == \
        ("Old", crs.author_id)


async def test_author_edits_course_but_cannot_reassign_it(client, auth, db):
    crs = make_course(make_user("fac1", role="FAC"))
    fac2 = make_user("fac2", role="FAC")
    await auth.login("fac1")
    body = await post(client, "cour_save", {"id": crs.id, "title": "New", "txn_no": 1,
                                            "author": {"id": fac2.id}})
    assert body["status"] == "OK"
    c = M.Course.get_by_id(crs.id)
    assert (c.title, c.author_id) == ("New", crs.author_id)


# ---- S10: background job results ----

async def test_job_status_only_for_the_job_owner(client, auth, app, db):
    make_user("aca1", role="ACA")
    make_user("aca2", role="ACA")
    app.extensions["tasks"]["job1"] = {"owner": "aca1", "status": "done",
                                       "result": "ok", "completed_at": None, "error": None}
    await auth.login("aca2")
    body = await (await client.get("/acadstack/job_status/job1")).get_json()
    assert body["status"] == "ERROR"
    await auth.logout()
    await auth.login("aca1")
    for _ in range(2):  # Polling does not remove the result.
        body = await (await client.get("/acadstack/job_status/job1")).get_json()
        assert body["body"]["result"] == "ok"
    assert "owner" not in body["body"]


async def test_bulk_grade_sheets_only_for_the_job_owner(client, auth, app, db):
    make_user("aca1", role="ACA")
    make_user("aca2", role="ACA")
    app.extensions["tasks"]["job2"] = {"owner": "aca1", "status": "done"}
    await auth.login("aca2")
    body = await (await client.get("/acadstack/get_gradesheets/job2")).get_json()
    assert body == {"status": "ERROR", "body": "Job info not found for job2"}


# ---- S11: parse_number ----

@pytest.mark.parametrize("sval,expected", [
    ("3", 3), (" -4 ", -4), ("2.345", 2.35), ("3.", 3.0), ("3/2", 1.5),
    ("4/2", 2.0), ("07", 7), ("x", None), ("1+1", None),
])
def test_parse_number(sval, expected, monkeypatch):
    def no_eval(*args):
        raise AssertionError("eval called")
    monkeypatch.setattr(builtins, "eval", no_eval)
    assert C.parse_number(sval) == expected


# ---- S12: no raw exception text in responses ----

async def test_course_save_error_does_not_leak_exception_text(client, auth, db):
    make_user("aca", role="ACA")
    await auth.login("aca")
    body = await post(client, "cour_save", {"id": 999, "author": {"id": 1}})
    assert body == {"status": "ERROR", "body": "Error when saving course details."}
