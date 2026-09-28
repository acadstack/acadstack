"""Scalar settings (settings.py) and the lists stored in the VocabItem table."""

import pytest

import models as M
import settings
import validation_checks as VAL
from common import AcadStackException
from conftest import enrol, make_offering, make_user


def test_defaults_without_rows(db):
    assert {s["key"]: s["value"] for s in settings.all_settings()} == \
        {k: d for k, (d, _, _) in settings.SETTINGS.items()}


def test_save_stores_value_and_clears_cache(db):
    assert settings.get("max_credits") == 24
    settings.save("max_credits", 30)
    assert settings.get("max_credits") == 30
    settings.save("max_credits", 20)
    assert settings.get("max_credits") == 20
    assert M.Setting.get(M.Setting.key == "max_credits").value == 20


@pytest.mark.parametrize("key, value", [
    ("max_credits", 0), ("max_credits", True), ("max_credits", "24"),
    ("face_match_tolerance", 1.5), ("fees_check_enabled", 1), ("no_such_key", 1),
])
def test_save_rejects_invalid_values(db, key, value):
    with pytest.raises(ValueError):
        settings.save(key, value)
    assert M.Setting.select().count() == 0


def test_invalid_stored_value_falls_back_to_default(db):
    M.Setting.create(key="page_size", value="lots")
    assert settings.get("page_size") == 25


def test_max_credits_setting_is_enforced(db):
    stu = make_user("stu")
    enrol(stu, make_offering(ltp="3-0-2-7-4"))
    VAL.check_enrolled_credits(stu.id, "2026-I")
    settings.save("max_credits", 3)
    with pytest.raises(AcadStackException, match="Max. 3 credits"):
        VAL.check_enrolled_credits(stu.id, "2026-I")


async def test_page_size_setting_is_used(client, auth):
    make_user("sup", role="SUP")
    for i in range(3):
        make_user(f"u{i}")
    settings.save("page_size", 2)
    await auth.login("sup")
    body = (await (await client.post("/acadstack/user_find", json={})).get_json())["body"]
    assert body["pg_size"] == 2 and len(body["users"]) == 2


async def test_superuser_reads_and_saves_settings(client, auth):
    make_user("sup", role="SUP")
    await auth.login("sup")
    res = await (await client.post("/acadstack/setting_save",
                                   json={"key": "lockout_limit", "value": 3})).get_json()
    assert res["status"] == "OK"
    res = await (await client.get("/acadstack/settings")).get_json()
    assert {s["key"]: s["value"] for s in res["body"]}["lockout_limit"] == 3

    res = await (await client.post("/acadstack/setting_save",
                                   json={"key": "lockout_limit", "value": -1})).get_json()
    assert res["status"] == "ERROR"
    assert settings.get("lockout_limit") == 3


@pytest.mark.parametrize("role", ["ACA", "DEA", "STU"])
async def test_only_superuser_may_change_settings(client, auth, role):
    make_user("u", role=role)
    await auth.login("u")
    res = await (await client.post("/acadstack/setting_save",
                                   json={"key": "max_credits", "value": 50})).get_json()
    assert res["status"] == "ERROR"
    assert (await (await client.get("/acadstack/settings")).get_json())["status"] == "ERROR"
    assert settings.get("max_credits") == 24


async def test_institutional_lists_come_from_the_database(client, auth):
    make_user("u")
    await auth.login("u")
    sd = (await (await client.get("/acadstack/get_static_data")).get_json())["body"]
    minors = [e["id"] for e in sd["MinorConcSpecialization"]]
    assert minors[0] == "" and len(minors) == len(set(minors))
    assert "MENG" in minors
    assert any(e["id"] == "CSE" for e in sd["Departments"])
    assert sd["EnrolStatuses"]  # code-dependent lists still come from static_data.json

    M.VocabItem.update(is_deleted=True).where(
        (M.VocabItem.vocab == "Departments") & (M.VocabItem.code == "CSE")).execute()
    M.VocabItem.create(vocab="Degrees", code="BDS", label="B.Des", sort_order=99)
    try:
        sd = (await (await client.get("/acadstack/get_static_data")).get_json())["body"]
        assert all(e["id"] != "CSE" for e in sd["Departments"])
        assert sd["Degrees"][-1] == {"id": "BDS", "value": "B.Des"}
    finally:
        M.VocabItem.update(is_deleted=False).where(M.VocabItem.code == "CSE").execute()
        M.VocabItem.delete().where(M.VocabItem.code == "BDS").execute()
