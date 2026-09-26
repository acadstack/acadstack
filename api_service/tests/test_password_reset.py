"""Password reset: key expiry, failed-verification lockout, and that bare
reset-key requests cannot lock an account."""
from datetime import datetime as DT, timedelta

import pytest

import create_email as CM
import models as DB
import settings_store as ST
from conftest import create_user


@pytest.fixture
def sent_keys(monkeypatch):
    keys = []
    monkeypatch.setattr(CM, "send_password_reset_code",
                        lambda email, code: keys.append(code))
    monkeypatch.setattr(CM, "send_password_changed_alert",
                        lambda email, name: None)
    return keys


def _gen_prk(client, login_id="stu1"):
    return client.post("/acadstack/gen_prk", json={
        "login_id": login_id, "email": f"{login_id}@example.com"})


def _reset(client, key_code, login_id="stu1", new_password="newpass123"):
    return client.post("/acadstack/reset_password", json={
        "login_id": login_id, "email": f"{login_id}@example.com",
        "key_code": key_code, "new_password": new_password})


def test_reset_with_valid_key_changes_password(client, db, sent_keys):
    create_user("STU", "stu1")
    assert _gen_prk(client).json["status"] == "OK"
    res = _reset(client, sent_keys[-1])
    assert res.json["status"] == "OK", res.json
    assert client.post("/acadstack/login", json={
        "login_id": "stu1", "password": "newpass123"}).json["status"] == "OK"


def test_expired_reset_key_is_rejected(client, db, sent_keys):
    u = create_user("STU", "stu1")
    old_hash = u.password_hashed
    _gen_prk(client)
    DB.PasswordResetKey.update(
        expires_at=DT.now() - timedelta(minutes=1)).execute()
    res = _reset(client, sent_keys[-1])
    assert res.json["status"] == "ERROR"
    assert "expired" in res.json["body"].lower()
    assert DB.User.get_by_id(u.id).password_hashed == old_hash


def test_reset_key_expiry_uses_configured_ttl(client, db, sent_keys):
    create_user("STU", "stu1")
    before = DT.now()
    _gen_prk(client)
    prk = DB.PasswordResetKey.get()
    ttl = ST.setting("auth.password_reset_key_ttl_mins")
    assert before + timedelta(minutes=ttl) <= prk.expires_at \
        <= DT.now() + timedelta(minutes=ttl)


def test_wrong_keys_lock_account_after_configured_limit(client, db, sent_keys):
    u = create_user("STU", "stu1")
    _gen_prk(client)
    limit = ST.setting("auth.password_reset_lockout_attempts")
    for _ in range(limit):
        assert _reset(client, "WRONGKEY").json["status"] == "ERROR"
    assert not DB.User.get_by_id(u.id).is_locked
    res = _reset(client, "WRONGKEY")
    assert res.json["status"] == "ERROR"
    assert DB.User.get_by_id(u.id).is_locked
    # Locked: even the right key no longer works.
    assert _reset(client, sent_keys[-1]).json["status"] == "ERROR"


def test_failed_attempts_survive_requesting_a_new_key(client, db, sent_keys):
    u = create_user("STU", "stu1")
    limit = ST.setting("auth.password_reset_lockout_attempts")
    for _ in range(limit + 1):
        _gen_prk(client)
        _reset(client, "WRONGKEY")
    assert DB.User.get_by_id(u.id).is_locked


def test_gen_prk_alone_cannot_lock_account(client, db, sent_keys):
    u = create_user("STU", "stu1")
    limit = max(ST.setting("auth.password_reset_lockout_attempts"),
                ST.setting("auth.password_reset_max_active_keys"))
    for _ in range(limit * 3):
        _gen_prk(client)
    assert not DB.User.get_by_id(u.id).is_locked
    assert client.post("/acadstack/login", json={
        "login_id": "stu1", "password": "test123"}).json["status"] == "OK"


def test_gen_prk_caps_outstanding_keys(client, db, sent_keys):
    create_user("STU", "stu1")
    cap = ST.setting("auth.password_reset_max_active_keys")
    for _ in range(cap):
        assert _gen_prk(client).json["status"] == "OK"
    res = _gen_prk(client)
    assert res.json["status"] == "ERROR"
    assert len(sent_keys) == cap
    # Expired keys no longer count toward the cap.
    DB.PasswordResetKey.update(
        expires_at=DT.now() - timedelta(minutes=1)).execute()
    assert _gen_prk(client).json["status"] == "OK"
