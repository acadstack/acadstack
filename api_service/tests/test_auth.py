from io import BytesIO

import pytest
from quart.datastructures import FileStorage

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


USERS_HEADER = "org_id,login_id,first_name,last_name,role,department,degree,year_of_entry,email"


async def bulk_add_users(client, csv_text):
    fs = FileStorage(BytesIO(csv_text.encode()), filename="users.csv", content_type="text/csv")
    res = await client.post("/acadstack/add_users", files={"users_file": fs})
    return await res.get_json()


@pytest.fixture
def lists(db):
    M.VocabItem.create(vocab="Departments", code="PHY", label="Physics")
    M.VocabItem.create(vocab="Degrees", code="BSC", label="B.Sc.")


async def test_bulk_add_users_skips_bad_rows_and_saves_the_rest(client, auth, lists):
    make_user("acad", role="ACA", dept_name="PHY")
    make_user("taken", role="FAC", dept_name="PHY")
    await auth.login("acad")
    body = await bulk_add_users(client, f"{USERS_HEADER}\n"
        "E1,dup,A,B,FAC,PHY,,,taken@example.com\n"      # email already used
        "S1,s1,C,D,STU,ZZZ,BSC,2026,s1@example.com\n"    # unknown department
        "S2,s2,E,F,STU,PHY,BSC,26,s2@example.com\n"      # bad year
        "S3,s3,G,H,STU,PHY,BSC,2026,s3@example.com\n"
        "E2,e2,I,J,FAC,PHY,,,e2@example.com\n")
    assert body["status"] == "OK"
    assert "Created 2 new users" in body["body"] and "Failed 3 records" in body["body"]
    for frag in ("line 2:", "line 3: unknown department 'ZZZ'", "line 4: year_of_entry"):
        assert frag in body["body"]
    s3 = M.User.get(M.User.login_id == "s3").person
    assert (s3.current_status, s3.degree, s3.year_of_entry) == ("REG", "BSC", "2026")
    e2 = M.User.get(M.User.login_id == "e2").person
    assert (e2.current_status, e2.degree, e2.year_of_entry) == (None, None, None)
    assert not M.User.select().where(M.User.login_id << ["dup", "s1", "s2"]).exists()


async def test_bulk_add_users_refuses_a_file_with_a_missing_column(client, auth, lists):
    make_user("acad", role="ACA", dept_name="PHY")
    await auth.login("acad")
    body = await bulk_add_users(client, "org_id,login_id\nS1,s1\n")
    assert body["status"] == "ERROR" and "first_name" in body["body"]


async def test_bulk_add_users_keeps_the_status_of_an_existing_student(client, auth, lists):
    make_user("acad", role="ACA", dept_name="PHY")
    make_user("s1", role="STU", org_id="S1", dept_name="PHY", current_status="WTH")
    await auth.login("acad")
    body = await bulk_add_users(client, f"{USERS_HEADER}\nS1,s1,A,B,STU,PHY,BSC,2026,s1@example.com\n")
    assert "Updated 1 users" in body["body"]
    assert M.User.get(M.User.login_id == "s1").person.current_status == "WTH"


async def assign_advisor(client, user_id, dept_name):
    res = await client.post("/acadstack/assign_advisor", json={
        "for_degree": "BSC", "for_entry_year": "2026", "dept_name": dept_name, "user_id": user_id})
    return await res.get_json()


async def test_batch_advisor_must_be_from_the_batch_department(client, auth, db):
    make_user("acad", role="ACA")
    adv = make_user("adv", role="FAC", dept_name="PHY")
    await auth.login("acad")
    body = await assign_advisor(client, adv.id, "HIST")
    assert body["status"] == "ERROR" and "HIST" in body["body"]
    assert not M.BatchAdvisors.select().exists()
    assert (await assign_advisor(client, adv.id, "PHY"))["status"] == "OK"
    found = await (await client.post("/acadstack/find_advisor", json={
        "for_degree": "BSC", "for_entry_year": "2026", "dept_name": "PHY"})).get_json()
    assert found["body"]["user_id"] == adv.id
