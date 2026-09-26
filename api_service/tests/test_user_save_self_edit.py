"""user_save(): what a user may change on their own record without
user.edit_any."""
import pytest

import models as DB
from conftest import create_user, login_as


def _own_record(client, user_id):
    res = client.get(f"/acadstack/user/{user_id}")
    assert res.json["status"] == "OK", res.json
    return res.json["body"]


def test_student_self_edit_cannot_change_role(client, db):
    stu = create_user("STU", "stu1")
    with client:
        login_as(client, "stu1")
        rec = _own_record(client, stu.id)
        rec["role"] = "SUP"
        res = client.post("/acadstack/user_save", json=rec)
    assert res.json["status"] == "ERROR"
    assert "role" in res.json["body"]
    assert DB.User.get_by_id(stu.id).role == "STU"


def test_student_self_edit_cannot_change_academic_fields(client, db):
    stu = create_user("STU", "stu1")
    with client:
        login_as(client, "stu1")
        rec = _own_record(client, stu.id)
        rec["person"]["degree"] = "PHD"
        rec["person"]["current_status"] = "WTH"
        rec["is_locked"] = True
        res = client.post("/acadstack/user_save", json=rec)
    assert res.json["status"] == "ERROR"
    per = DB.Person.get_by_id(stu.person_id)
    assert per.degree == "BTE" and per.current_status == "REG"


def test_student_self_edit_cannot_repoint_person(client, db):
    stu = create_user("STU", "stu1")
    other = create_user("STU", "stu2")
    with client:
        login_as(client, "stu1")
        rec = _own_record(client, stu.id)
        rec["person"] = other.person_id
        res = client.post("/acadstack/user_save", json=rec)
    assert res.json["status"] == "ERROR"
    assert DB.User.get_by_id(stu.id).person_id == stu.person_id


def test_student_self_edit_cannot_target_another_person_row(client, db):
    stu = create_user("STU", "stu1")
    other = create_user("STU", "stu2")
    with client:
        login_as(client, "stu1")
        rec = _own_record(client, stu.id)
        rec["person"]["id"] = other.person_id
        rec["person"]["txn_no"] = other.person.txn_no
        res = client.post("/acadstack/user_save", json=rec)
    assert res.json["status"] == "ERROR"
    assert "id" in res.json["body"]
    assert DB.Person.get_by_id(other.person_id).org_id == "ORG-stu2"


def test_student_self_edit_can_change_profile_fields(client, db):
    stu = create_user("STU", "stu1")
    with client:
        login_as(client, "stu1")
        rec = _own_record(client, stu.id)
        rec["first_name"] = "Renamed"
        rec["email"] = "renamed@example.com"
        rec["person"]["gender"] = "F"
        res = client.post("/acadstack/user_save", json=rec)
    assert res.json["status"] == "OK", res.json
    u = DB.User.get_by_id(stu.id)
    assert (u.first_name, u.email, u.person.gender) == \
        ("Renamed", "renamed@example.com", "F")


def test_user_save_never_copies_password_hash_from_request(client, db):
    create_user("SUP", "admin1")
    stu = create_user("STU", "stu1")
    old_hash = stu.password_hashed
    with client:
        login_as(client, "admin1")
        rec = _own_record(client, stu.id)
        rec["password_hashed"] = "attacker-chosen"
        res = client.post("/acadstack/user_save", json=rec)
    assert res.json["status"] == "OK", res.json
    assert DB.User.get_by_id(stu.id).password_hashed == old_hash


def test_edit_any_holder_can_change_another_users_role(client, db):
    create_user("SUP", "admin1")
    stu = create_user("STU", "stu1")
    with client:
        login_as(client, "admin1")
        rec = _own_record(client, stu.id)
        rec["role"] = "RES"
        res = client.post("/acadstack/user_save", json=rec)
    assert res.json["status"] == "OK", res.json
    assert DB.User.get_by_id(stu.id).role == "RES"


# ===================== reference photo =====================

_PHOTO = "data:image/jpeg;base64,/9j/AAAA"


@pytest.fixture
def fake_face_service(monkeypatch):
    import api_auth
    monkeypatch.setattr(api_auth.fapi, "get_face_encoding_b64",
                        lambda b64: [0.1] * 128)


def test_student_cannot_change_own_reference_photo(client, db, fake_face_service):
    stu = create_user("STU", "stu1")
    with client:
        login_as(client, "stu1")
        rec = _own_record(client, stu.id)
        rec["photo_new"] = _PHOTO
        res = client.post("/acadstack/user_save", json=rec)
    assert res.json["status"] == "ERROR"
    assert not DB.KnownFace.select().where(DB.KnownFace.user == stu.id).exists()


def test_student_cannot_use_face_add(client, db):
    create_user("STU", "stu1")
    with client:
        login_as(client, "stu1")
        res = client.post("/acadstack/face_add")
    assert res.json["status"] == "ERROR"
    assert "permission" in res.json["body"].lower()


def test_photo_permission_holder_can_change_own_photo(client, db, fake_face_service):
    fac = create_user("FAC", "fac1")
    with client:
        login_as(client, "fac1")
        rec = _own_record(client, fac.id)
        rec["photo_new"] = _PHOTO
        res = client.post("/acadstack/user_save", json=rec)
    assert res.json["status"] == "OK", res.json
    assert DB.KnownFace.select().where(DB.KnownFace.user == fac.id).count() == 1


def test_photo_replace_cannot_delete_another_users_photo(client, db, fake_face_service):
    fac = create_user("FAC", "fac1")
    other = create_user("STU", "stu2")
    theirs = DB.KnownFace.create(user=other, face_enc="{}", photo="x")
    with client:
        login_as(client, "fac1")
        rec = _own_record(client, fac.id)
        rec["photo_new"] = _PHOTO
        rec["known_faces"] = [{"id": theirs.id}]
        res = client.post("/acadstack/user_save", json=rec)
    assert res.json["status"] == "OK", res.json
    assert DB.KnownFace.get_or_none(DB.KnownFace.id == theirs.id) is not None
