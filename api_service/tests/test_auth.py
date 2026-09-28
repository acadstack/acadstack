import common as C
import models as M
from conftest import make_user


async def test_login(client, auth):
    make_user("test")
    res = await auth.login()
    assert res.status_code == 200
    assert (await res.get_json())["status"] == "OK"
    async with client.session_transaction() as sess:
        assert sess["user"]["login_id"] == "test"


async def test_login_wrong_password(client, auth):
    make_user("test")
    res = await auth.login(password="wrong")
    assert (await res.get_json())["status"] == "ERROR"
    async with client.session_transaction() as sess:
        assert "user" not in sess


async def test_logout(client, auth):
    make_user("test")
    await auth.login()
    assert (await auth.logout()).status_code == 200
    async with client.session_transaction() as sess:
        assert "user" not in sess


async def test_load_user(client, auth):
    u = make_user("test")
    assert (await auth.login()).status_code == 200
    res = await client.get(f"/acadstack/user/{u.id}")
    assert res.status_code == 200
    body = await res.get_json()
    assert body["status"] == "OK"
    assert body["body"]["person"]["org_id"] == "TEST"
    assert "password_hashed" not in body["body"]


async def test_current_user(client, auth):
    make_user("test")
    assert (await auth.login()).status_code == 200
    res = await client.get("/acadstack/current_user")
    assert res.status_code == 200
    body = await res.get_json()
    assert body["status"] == "OK"
    assert body["body"]["user"]["login_id"] == "test"
    # The permissions come from the stored grants, not from the session.
    assert "students.academics:own" in body["body"]["user"]["perms"]


async def test_login_returns_permissions(client, auth):
    make_user("fac", role="FAC")
    body = await (await auth.login("fac")).get_json()
    perms = body["body"]["user"]["perms"]
    assert "grades.upload:own" in perms and "grades.upload:any" not in perms


# Hash of "abcd1234" as written by passlib's pbkdf2_sha256.
LEGACY_HASH = "$pbkdf2-sha256$29000$eo/x3nsPIWQshTCmtPa.1w$v7FS79OJtmraq0i0EGvyaenqwpGjWE6fxMCXwrVD12A"


async def test_login_with_legacy_hash_upgrades_it_to_argon2(client, auth):
    u = make_user("test")
    M.User.update(password_hashed=LEGACY_HASH).where(M.User.id == u.id).execute()
    res = await auth.login(password="abcd1234")
    assert (await res.get_json())["status"] == "OK"
    new_hash = M.User.get_by_id(u.id).password_hashed
    assert new_hash.startswith("$argon2")
    await auth.logout()
    assert (await (await auth.login(password="abcd1234")).get_json())["status"] == "OK"


async def test_login_with_legacy_hash_and_wrong_password(client, auth):
    u = make_user("test")
    M.User.update(password_hashed=LEGACY_HASH).where(M.User.id == u.id).execute()
    res = await auth.login(password="wrong")
    assert (await res.get_json())["status"] == "ERROR"
    assert M.User.get_by_id(u.id).password_hashed == LEGACY_HASH


def test_verify_password():
    assert C.verify_password("abcd1234", LEGACY_HASH)
    assert not C.verify_password("abcd1235", LEGACY_HASH)
    h = C.hash_password("s3cret")
    assert C.verify_password("s3cret", h) and not C.verify_password("s3cre", h)
    assert not C.verify_password("x", "not-a-hash")
    assert C.password_needs_rehash(LEGACY_HASH) and not C.password_needs_rehash(h)
