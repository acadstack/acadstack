"""Scalar settings (settings.py) and the lists stored in the VocabItem table."""

from datetime import date, timedelta

import pytest

import api_common as apiVC
import api_dc
import common as C
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
    M.VocabItem.create(vocab="Departments", code="CSE", label="Computer Science")
    M.VocabItem.create(vocab="MinorConcSpecialization", code="MENG", label="Minor in English")
    M.VocabItem.create(vocab="PersonCategories", code="GEN", label="General")
    make_user("u")
    await auth.login("u")
    sd = (await (await client.get("/acadstack/get_static_data")).get_json())["body"]
    minors = [e["id"] for e in sd["MinorConcSpecialization"]]
    assert minors == ["", "MENG"]
    assert any(e["id"] == "CSE" for e in sd["Departments"])
    assert sd["PersonCategories"][1:] == [{"id": "GEN", "value": "General"}]
    assert sd["DegreeType"] == sd["CourseFreqs"] == sd["CalendarEvents"] == \
        [{"id": "", "value": "-Select-"}]
    assert sd["EnrolStatuses"]  # code-dependent lists still come from static_data.json

    M.VocabItem.update(is_deleted=True).where(
        (M.VocabItem.vocab == "Departments") & (M.VocabItem.code == "CSE")).execute()
    M.VocabItem.create(vocab="Degrees", code="BDS", label="B.Des", sort_order=99)
    sd = (await (await client.get("/acadstack/get_static_data")).get_json())["body"]
    assert all(e["id"] != "CSE" for e in sd["Departments"])
    assert sd["Degrees"][-1] == {"id": "BDS", "value": "B.Des"}


def test_baseline_seeds_only_the_all_department(db):
    assert [(v.vocab, v.code) for v in M.VocabItem.select()] == [("Departments", "ALL")]


# ---- editing the lists: /vocab and /vocab_save ----

async def _save_vocab(client, **item):
    return await (await client.post("/acadstack/vocab_save", json=item)).get_json()


@pytest.fixture
async def sup(client, auth):
    make_user("sup", role="SUP")
    await auth.login("sup")
    return client


async def test_vocab_items_are_added_edited_and_hidden(sup):
    res = await _save_vocab(sup, vocab="Degrees", code="BSC", label="B.Sc",
                            attrs={"level": "UG", "printed_name": "Bachelor of Science"})
    assert res["status"] == "OK", res
    item = next(v for v in res["body"]["items"]["Degrees"] if v["code"] == "BSC")
    assert item["attrs"] == {"level": "UG", "printed_name": "Bachelor of Science"}

    res = await _save_vocab(sup, id=item["id"], vocab="Degrees", code="BSC",
                            label="B.Sc.", sort_order=5, attrs={}, is_deleted=True)
    assert res["status"] == "OK", res
    row = M.VocabItem.get_by_id(item["id"])
    assert (row.label, row.sort_order, row.attrs, row.is_deleted) == ("B.Sc.", 5, {}, True)

    body = (await (await sup.get("/acadstack/vocab")).get_json())["body"]
    assert [v["code"] for v in body["items"]["Degrees"]] == ["BSC"]  # hidden ones included
    assert set(body["items"]) == set(apiVC.DB_VOCABS)
    assert body["attrs"]["CourseTypes"] == {"group": ["CORE", "ELECTIVE"]}


@pytest.mark.parametrize("item, error", [
    ({"vocab": "Nope", "code": "X", "label": "X"}, "Unknown list"),
    ({"vocab": "Degrees", "code": "", "label": "X"}, "code"),
    ({"vocab": "Degrees", "code": "X" * 21, "label": "X"}, "code"),
    ({"vocab": "Degrees", "code": "X", "label": " "}, "label"),
    ({"vocab": "Departments", "code": "CIVIL", "label": "Civil"}, "4 characters"),
    ({"vocab": "Departments", "code": "ALL", "label": "All"}, "already"),
    ({"vocab": "Degrees", "code": "X", "label": "X", "attrs": {"group": "CORE"}},
     "Unknown attribute"),
    ({"vocab": "Degrees", "code": "X", "label": "X", "attrs": {"level": "MBA"}}, "level"),
    ({"vocab": "Degrees", "code": "X", "label": "X", "attrs": {"printed_name": 3}},
     "printed_name"),
    ({"vocab": "Degrees", "code": "X", "label": "X", "sort_order": "1"}, "sort order"),
    ({"vocab": "CalendarEvents", "code": "GRADE_SUB", "label": "Grades"}, "workflow event"),
])
async def test_vocab_save_rejects_invalid_items(sup, item, error):
    res = await _save_vocab(sup, **item)
    assert res["status"] == "ERROR" and error in res["body"], res
    assert M.VocabItem.select().count() == 1


async def test_vocab_code_cannot_change_and_all_cannot_be_hidden(sup):
    deg = M.VocabItem.create(vocab="Degrees", code="BSC", label="B.Sc")
    res = await _save_vocab(sup, id=deg.id, vocab="Degrees", code="BS", label="B.Sc")
    assert res["status"] == "ERROR" and "code" in res["body"]
    res = await _save_vocab(sup, id=deg.id, vocab="Departments", code="BSC", label="B.Sc")
    assert res["status"] == "ERROR"
    assert M.VocabItem.get_by_id(deg.id).vocab == "Degrees"

    all_ = M.VocabItem.get((M.VocabItem.vocab == "Departments") & (M.VocabItem.code == "ALL"))
    res = await _save_vocab(sup, id=all_.id, vocab="Departments", code="ALL", label="All",
                            is_deleted=True)
    assert res["status"] == "ERROR" and "ALL" in res["body"]
    res = await _save_vocab(sup, id=all_.id, vocab="Departments", code="ALL",
                            label="Every department")
    assert res["status"] == "OK"


@pytest.mark.parametrize("role", ["ACA", "DEA", "STU"])
async def test_only_superuser_may_edit_lists(client, auth, role):
    make_user("u", role=role)
    await auth.login("u")
    assert (await _save_vocab(client, vocab="Degrees", code="X", label="X"))["status"] == "ERROR"
    assert (await (await client.get("/acadstack/vocab")).get_json())["status"] == "ERROR"
    assert M.VocabItem.select().count() == 1


# ---- label overrides and hidden enrolment types ----

async def test_label_overrides_and_hidden_enrol_types_apply_to_static_data(client, auth):
    settings.save("label_overrides", {"EnrolStatuses": {"ENRO": "Registered"},
                                      "WorkflowEvents": {"ADD_DROP": "Late registration"}})
    settings.save("hidden_enrol_types", ["CM", "CC"])
    make_user("u")
    await auth.login("u")
    sd = (await (await client.get("/acadstack/get_static_data")).get_json())["body"]
    assert {"id": "ENRO", "value": "Registered"} in sd["EnrolStatuses"]
    assert {"id": "ADD_DROP", "value": "Late registration"} in sd["WorkflowEvents"]
    assert [e["id"] for e in sd["EnrolTypes"]] == ["", "A", "C"]


@pytest.mark.parametrize("key, value", [
    ("label_overrides", []),
    ("label_overrides", {"NoSuchList": {"X": "Y"}}),
    ("label_overrides", {"Departments": {"ALL": "Every"}}),  # a DB list is edited directly
    ("label_overrides", {"EnrolStatuses": {"NOPE": "Y"}}),
    ("label_overrides", {"EnrolStatuses": {"ENRO": ""}}),
    ("label_overrides", {"EnrolStatuses": ["ENRO"]}),
    ("hidden_enrol_types", "CM"),
    ("hidden_enrol_types", ["ZZ"]),
    ("hidden_enrol_types", [["CM"]]),
])
def test_invalid_label_settings_are_rejected(db, key, value):
    with pytest.raises(ValueError):
        settings.save(key, value)


# ---- calendar events ----

async def test_university_calendar_event_is_dated_and_shown_open(client, auth):
    M.VocabItem.create(vocab="CalendarEvents", code="MINOR_EXAM", label="Mid-term exams")
    make_user("aca", role="ACA")
    await auth.login("aca")
    today = date.today()
    dates = {"MINOR_EXAM_S": (today - timedelta(days=1)).isoformat(),
             "MINOR_EXAM_E": (today + timedelta(days=1)).isoformat(),
             "RESULT_DECLARATION": today.isoformat()}
    res = await client.post("/acadstack/dates_save",
                            json={"session": "2026-I", "eventDates": dates})
    assert (await res.get_json())["status"] == "OK"
    open_ = (await (await client.get("/acadstack/open_events")).get_json())["body"]
    assert "2026-I:MINOR_EXAM" in open_


@pytest.mark.parametrize("code", ["MINOR_EXAM_S", "GRADE_SUB_X", "FOO"])
async def test_dates_save_rejects_unknown_events(client, auth, code):
    make_user("aca", role="ACA")
    await auth.login("aca")
    res = await client.post("/acadstack/dates_save", json={
        "session": "2026-I", "eventDates": {"SESSION_S": "2026-07-01", code: "2026-07-02"}})
    body = await res.get_json()
    assert body["status"] == "ERROR" and code in body["body"]
    assert M.AcademicCalendar.select().count() == 0


def test_upcoming_events_email_uses_labels(db, monkeypatch):
    M.VocabItem.create(vocab="CalendarEvents", code="MINOR_EXAM", label="Mid-term exams")
    settings.save("label_overrides", {"WorkflowEvents": {"GRADE_SUB": "Marks entry"}})
    today = date.today().isoformat()
    for code in ("MINOR_EXAM_S", "GRADE_SUB_E", "RESULT_DECLARATION"):
        M.AcademicCalendar.create(acad_session="2026-I", event_code=code, event_value=today)
    sent = []
    monkeypatch.setattr(C.emailer, "send_mail", lambda to, subj, body: sent.append(body))
    api_dc.schedule_event_alerts()
    assert len(sent) == 1
    for label in ("Mid-term exams starts", "Marks entry ends", "Result declaration"):
        assert f"'{label}'" in sent[0]
