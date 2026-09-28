"""Tests for the report queries in sql_statements.toml."""

import pytest

import models as M
from conftest import enrol, make_offering, make_user

SESSION = "2026-I"


@pytest.fixture
def setup(db):
    make_user("aca", role="ACA")
    ins = make_user("ins", role="FAC")
    stu = make_user("stu", role="STU", degree="BTE", year_of_entry="2024")
    co = make_offering(ltp="3-1-2-7-4", acad_session=SESSION, status="R", instructor=ins)
    return {"stu": stu, "co": co, "ce": enrol(stu, co)}


async def report(client, url, payload):
    return await (await client.post(f"/acadstack/{url}", json=payload)).get_json()


@pytest.mark.parametrize("grade,pending", [("NA", True), ("I", False), ("A", False)])
async def test_grades_pending_report(client, auth, setup, grade, pending):
    M.CourseEnrollment.update(grade=grade).execute()
    await auth.login("aca")
    body = await report(client, "grades.status", {"selected": "GP", "acad_session": SESSION})
    assert body["status"] == "OK"
    assert [r["code"] for r in body["body"]["data"]] == (["CS101"] if pending else [])


async def test_credits_earned_report_sums_credits(client, auth, setup):
    await auth.login("aca")
    body = await report(client, "credits_earned", {
        "acad_session": SESSION, "entry_year": "", "degree": "", "dept_name": ""})
    assert body["status"] == "OK"
    assert [float(r["credits"]) for r in body["body"]["data"]] == [4]


async def test_category_credits_report_sums_credits(client, auth, setup):
    M.CourseEnrollment.update(grade="A").execute()
    M.CourseCategory.create(offering=setup["co"], degree="BTE", dept="CSE",
                            category="PC", for_entry_years="2024")
    await auth.login("aca")
    res = await client.get(f"/acadstack/download_catwise_earned_credits/{SESSION}"
                           "/BTE/-/-/2024/0/100")
    lines = (await res.get_data(as_text=True)).splitlines()
    assert lines[1].split(",")[:2] == ["PC=4.00", "4"]


async def test_course_enrolments_report(client, auth, setup):
    await auth.login("aca")
    body = await report(client, "course.enrolments",
                        {"dept_name": "-", "entry_year": "-", "acad_session": SESSION})
    assert body["status"] == "OK"
    assert [(r["code"], r["user_id"]) for r in body["body"]["data"]] == \
        [("CS101", setup["stu"].id)]
