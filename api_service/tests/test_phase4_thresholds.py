"""Tests for the Phase 4 scalar-threshold migration: hard-coded policy
literals (max credits per session, face-recognition tolerance,
password-reset lockout, active-user window, page size,
disable_fees_check, hide_stats_from) moved onto the settings_store
accessor built in Phase 2.

Every test below checks both ends of the migration: the DECLARED DEFAULT
reproduces the old hard-coded literal exactly (so nothing changes for an
institution that never touches the admin GUI), and saving a new value
through settings_store actually changes the call site's behavior without
a restart.
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import api_common as apiVC  # noqa: E402
import face_api_proxy as fapi  # noqa: E402
import models as DB  # noqa: E402
import settings_store as ST  # noqa: E402
import validation_checks as VAL  # noqa: E402
from common import AcadStackException  # noqa: E402
from conftest import (TEST_LOGIN_ID, create_user, login_as)  # noqa: E402

ACAD_SESSION = "2024-I"


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    """settings_store's process-wide cache is keyed off a DB row and, for
    code running outside a request context (as several calls below do --
    they call face_api_proxy/validation_checks functions directly, not
    through the HTTP client), is only rechecked once every
    NON_REQUEST_RECHECK_SECS. The `db` fixture's TRUNCATE between tests
    does not go through settings_store's own invalidation path, so
    without this a fast-running test can still see the previous test's
    saved value. Mirrors the `settings` fixture in test_settings_store.py.
    """
    ST.invalidate_cache()
    yield
    ST.invalidate_cache()


# ===================== enrolment.max_credits_per_session =====================

def _enrol_student_with_credits(student, credits, acad_session=ACAD_SESSION):
    course = DB.Course.create(code=f"CS{credits}00", title="Heavy Course",
                              status="APP", ltp=f"10-0-0-0-{credits}")
    offering = DB.CourseOffering.create(course=course, acad_session=acad_session,
                                        status="R")
    DB.CourseEnrollment.create(course_offering=offering, student=student,
                               enrol_type="C", enrol_status="ENRO")


def test_max_credits_default_matches_old_hardcoded_literal(db):
    stu = create_user("STU", "credtest1")
    _enrol_student_with_credits(stu, 25)
    with pytest.raises(AcadStackException) as exc:
        VAL.check_enrolled_credits(stu.id, ACAD_SESSION)
    assert "24" in str(exc.value)


def test_max_credits_respects_saved_setting_both_ways(db):
    stu = create_user("STU", "credtest2")
    _enrol_student_with_credits(stu, 25)

    ST.save_setting("enrolment.max_credits_per_session", 30)
    VAL.check_enrolled_credits(stu.id, ACAD_SESSION)  # 25 <= 30: no raise

    ST.save_setting("enrolment.max_credits_per_session", 20)
    with pytest.raises(AcadStackException) as exc:
        VAL.check_enrolled_credits(stu.id, ACAD_SESSION)
    assert "20" in str(exc.value)
    assert "24" not in str(exc.value)  # error no longer restates the old literal


# ===================== faces.match_tolerance =====================

class _FakeFaceResponse:
    def __init__(self, payload=None, content=b""):
        self._payload = payload or {}
        self.content = content

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


@pytest.fixture
def two_photos(tmp_path):
    p1 = tmp_path / "person.jpg"
    p2 = tmp_path / "group.jpg"
    p1.write_bytes(b"person")
    p2.write_bytes(b"group")
    return str(p1), str(p2)


def test_is_person_in_photo_uses_configured_tolerance(db, two_photos, monkeypatch):
    captured = {}

    def fake_post(url, files=None, data=None):
        captured["tolerance"] = data["tolerance"]
        return _FakeFaceResponse({"match": True})

    monkeypatch.setattr(fapi.requests, "post", fake_post)
    person, group = two_photos

    fapi.is_person_in_photo(person, group)
    assert captured["tolerance"] == 0.45  # matches the old hardcoded default

    ST.save_setting("faces.match_tolerance", 0.6)
    fapi.is_person_in_photo(person, group)
    assert captured["tolerance"] == 0.6

    # An explicit caller-supplied tolerance still overrides the setting.
    fapi.is_person_in_photo(person, group, tolerance=0.9)
    assert captured["tolerance"] == 0.9


def test_find_persons_in_photo_uses_configured_tolerance(db, two_photos, monkeypatch):
    captured = {}

    def fake_post(url, files=None, data=None):
        captured["tolerance"] = data["tolerance"]
        return _FakeFaceResponse({"names_found": [], "names_missing": [],
                                  "face_count": 0, "marked_image_b64": ""})

    monkeypatch.setattr(fapi.requests, "post", fake_post)
    _, group = two_photos

    fapi.find_persons_in_photo(group, ([], []))
    assert captured["tolerance"] == 0.45

    ST.save_setting("faces.match_tolerance", 0.3)
    fapi.find_persons_in_photo(group, ([], []))
    assert captured["tolerance"] == 0.3


def test_mark_person_in_photo_uses_configured_tolerance(db, two_photos, monkeypatch):
    captured = {}

    def fake_post(url, files=None, data=None):
        captured["tolerance"] = data["tolerance"]
        return _FakeFaceResponse(content=b"marked-image-bytes")

    monkeypatch.setattr(fapi.requests, "post", fake_post)
    person, group = two_photos

    fapi.mark_person_in_photo(person, group)
    assert captured["tolerance"] == 0.45

    ST.save_setting("faces.match_tolerance", 0.55)
    fapi.mark_person_in_photo(person, group)
    assert captured["tolerance"] == 0.55


# ===================== auth.password_reset_lockout_attempts =====================

def test_password_reset_lockout_threshold_is_configurable(client):
    # NOTE: gen_prk's success path (api_auth.py) currently crashes on an
    # unrelated pre-existing bug -- `C.C.random_str(...)` where `C` is the
    # `common` module, which has no nested `C` attribute -- so a request
    # that passes the lockout check never actually reaches "OK" today; it
    # falls through to the generic error handler instead, and no
    # PasswordResetKey row ever gets inserted via the live endpoint. That
    # bug is out of scope here (Phase 4 is the threshold migration, not a
    # bug fix), so attempts are seeded directly to exercise the lockout
    # threshold itself, independent of it.
    create_user("STU", "lockstu")
    email = "lockstu@example.com"

    ST.save_setting("auth.password_reset_lockout_attempts", 2)

    for _ in range(2):
        DB.PasswordResetKey.create(login_id="lockstu", prk="x")

    # attempts == 2, threshold == 2: not yet over the limit.
    res = client.post("/acadstack/gen_prk",
                      json={"login_id": "lockstu", "email": email})
    assert res.json["status"] == "ERROR"
    assert "locked" not in res.json["body"].lower()

    DB.PasswordResetKey.create(login_id="lockstu", prk="x")  # attempts == 3

    res2 = client.post("/acadstack/gen_prk",
                       json={"login_id": "lockstu", "email": email})
    assert res2.json["status"] == "ERROR"
    assert "more than 2" in res2.json["body"]

    locked = DB.User.get(DB.User.login_id == "lockstu")
    assert locked.is_locked is True


# ===================== app.active_user_window_secs =====================

def test_active_user_window_is_configurable(client, auth):
    auth.login()
    client.app.active_users["ghost"] = datetime.now() - timedelta(seconds=1700)

    res = client.get("/acadstack/auc")
    assert any(u.startswith("ghost.") for u in res.json["body"])

    ST.save_setting("app.active_user_window_secs", 60)
    client.app.active_users["ghost"] = datetime.now() - timedelta(seconds=1700)
    res2 = client.get("/acadstack/auc")
    assert all(not u.startswith("ghost.") for u in res2.json["body"])


# ===================== app.page_size =====================

def test_page_size_default_matches_old_hardcoded_literal(db):
    assert apiVC.page_size() == 25


def test_user_find_pagination_respects_saved_page_size(client, auth):
    auth.login()
    for i in range(5):
        create_user("STU", f"pgtest{i}")

    ST.save_setting("app.page_size", 2)
    res = client.post("/acadstack/user_find", json={})
    assert res.json["status"] == "OK"
    assert res.json["body"]["pg_size"] == 2
    assert len(res.json["body"]["users"]) == 2
    assert res.json["body"]["has_next"] is True


# ===================== course_offering.hide_stats_from =====================

def test_hide_stats_from_default_matches_old_hardcoded_literal(client):
    create_user("STU", "statstu")
    login_as(client, "statstu")

    res = client.get("/acadstack/fetch_stats/1")
    assert res.json["status"] == "ERROR"


def test_hide_stats_from_is_configurable(client):
    create_user("STU", "statstu2")
    login_as(client, "statstu2")

    ST.save_setting("course_offering.hide_stats_from", [])
    res = client.get("/acadstack/fetch_stats/1")
    assert res.json["status"] == "OK"


# ===================== enrolment.disable_fees_check =====================

def test_disable_fees_check_default_still_blocks_enrolment_without_fees(client):
    stu = create_user("STU", "feestu1")
    login_as(client, "feestu1")

    res = client.post("/acadstack/enroll_in_courses",
                      json={"user_id": stu.id, "co_ids": [], "enrol_type": "C"})
    assert res.json["status"] == "ERROR"
    assert "fees" in res.json["body"].lower()


def test_disable_fees_check_setting_skips_the_fees_gate(client):
    stu = create_user("STU", "feestu2")
    login_as(client, "feestu2")

    ST.save_setting("enrolment.disable_fees_check", True)
    res = client.post("/acadstack/enroll_in_courses",
                      json={"user_id": stu.id, "co_ids": [], "enrol_type": "C"})
    # Fees gate skipped -> falls through to the (unrelated) empty co_ids error.
    assert res.json["status"] == "ERROR"
    assert "select a course" in res.json["body"].lower()
