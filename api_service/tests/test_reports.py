"""Tests for the report queries in sql_statements.toml."""

import asyncio

import pytest

import api_grades
import models as M
from conftest import enrol, make_offering, make_user

SESSION = "2026-I"

pytestmark = pytest.mark.usefixtures("grading_schemes")


@pytest.fixture
def setup(db):
    make_user("aca", role="ACA")
    ins = make_user("ins", role="FAC")
    stu = make_user("stu", role="STU", degree="BTE", year_of_entry="2024")
    co = make_offering(ltp="3-1-2-7-4", acad_session=SESSION, status="R", instructor=ins)
    return {"stu": stu, "co": co, "ce": enrol(stu, co)}


async def report(client, url, payload):
    return await (await client.post(f"/acadstack/{url}", json=payload)).get_json()


@pytest.mark.parametrize("grade,pending", [("NA", True), ("I", False), ("A", False),
                                           ("S", False), ("U", False)])
async def test_grades_pending_report(client, auth, setup, grade, pending):
    M.CourseEnrollment.update(grade=grade).execute()
    await auth.login("aca")
    body = await report(client, "grades.status", {"selected": "GP", "acad_session": SESSION})
    assert body["status"] == "OK"
    assert [r["code"] for r in body["body"]["data"]] == (["CS101"] if pending else [])


async def test_credits_earned_report_sums_credits(client, auth, setup):
    M.CourseEnrollment.update(grade="A").execute()
    await auth.login("aca")
    body = await report(client, "credits_earned", {
        "acad_session": SESSION, "entry_year": "", "degree": "", "dept_name": ""})
    assert body["status"] == "OK"
    assert [float(r["credits"]) for r in body["body"]["data"]] == [4]


async def test_credits_earned_report_excludes_a_course(client, auth, setup):
    enrol(setup["stu"], make_offering("CS102", ltp="3-0-0-6-3", acad_session=SESSION, status="R"))
    M.CourseEnrollment.update(grade="A").execute()
    await auth.login("aca")
    body = await report(client, "credits_earned", {
        "acad_session": SESSION, "entry_year": "", "degree": "", "dept_name": "",
        "exclude_course": "CS101"})
    assert [float(r["credits"]) for r in body["body"]["data"]] == [3]


@pytest.mark.parametrize("grade", ["F", "E", "NA"])
async def test_credits_earned_report_leaves_out_grades_that_earn_no_credit(
        client, auth, setup, grade):
    enrol(setup["stu"], make_offering("CS102", ltp="3-0-0-6-3", acad_session=SESSION,
                                      status="R"), grade=grade)
    M.CourseEnrollment.update(grade="A").where(
        M.CourseEnrollment.id == setup["ce"].id).execute()
    await auth.login("aca")
    body = await report(client, "credits_earned", {
        "acad_session": SESSION, "entry_year": "", "degree": "", "dept_name": ""})
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


def test_bulk_grade_sheets_select_the_program_exactly(db):
    import api_grades
    make_user("s1", role="STU", org_id="S1", degree="BTE", dept_name="CSE", year_of_entry="2024")
    make_user("s2", role="STU", org_id="S2", degree="BTE_MC", dept_name="CSE", year_of_entry="2024")
    make_user("s3", role="STU", org_id="S3", degree="BTE", dept_name="CSE2", year_of_entry="2024")
    assert api_grades._get_student_entry_no_data("BTE", "CSE", "2024") == ["S1"]


# ---- bulk grade sheets ----

BULK = {"degree": "BTE", "dept_name": "CSE", "for_year": "2023", "enrol_type": "C",
        "acad_session": "2024-I"}


@pytest.fixture
def fake_pdf(monkeypatch):
    """Grade sheets written as stub files, so no PDF renderer is needed."""
    monkeypatch.setattr(api_grades, "_html_to_pdf",
                        lambda html, out=None: open(out, "wb").write(b"%PDF stub"))


async def submit_bulk(client, criteria=BULK):
    return await (await client.post("/acadstack/bulk_download_sem_grade",
                                    json=criteria)).get_json()


async def finished_bulk(client, job_key):
    """The status of a bulk grade sheet task, once it is done."""
    for _ in range(400):
        st = await (await client.get(f"/acadstack/bulk_gradesheets_status/{job_key}")).get_json()
        assert st["status"] == "OK"
        if st["body"]["status"] == "done":
            return st["body"]
        assert st["body"]["status"] == "running"
        await asyncio.sleep(0.05)
    raise AssertionError("The bulk grade sheet task did not finish")


async def test_bulk_grade_sheets_report_the_sheets_and_who_was_left_out(client, auth, fake_pdf):
    s1 = make_user("s1", role="STU", org_id="S1", degree="BTE", year_of_entry="2023")
    make_user("s2", role="STU", org_id="S2", degree="BTE", year_of_entry="2023")
    enrol(s1, make_offering(acad_session="2024-I", status="F"), grade="A")
    make_user("aca", role="ACA")
    await auth.login("aca")
    body = await submit_bulk(client)
    assert body["status"] == "OK"
    st = await finished_bulk(client, body["body"]["job_key"])
    assert st["error"] is None
    assert st["result"] == {"sheets": 1, "students": 2, "no_results": ["S2"],
                            "withheld": [], "feedback_pending": [], "errors": []}
    res = await client.get(f"/acadstack/get_gradesheets/{body['body']['job_key']}")
    assert res.status_code == 200
    assert (await res.get_data()).startswith(b"PK")


async def test_bulk_grade_sheets_leave_out_withheld_results(client, auth, fake_pdf):
    s1 = make_user("s1", role="STU", org_id="S1", degree="BTE", year_of_entry="2023")
    s2 = make_user("s2", role="STU", org_id="S2", degree="BTE", year_of_entry="2023")
    co = make_offering(acad_session="2024-I", status="F")
    enrol(s1, co, grade="A")
    enrol(s2, co, grade="B")
    M.ResultHold.create(student=s2, acad_session="2024-I", reason="Dues")
    make_user("aca", role="ACA")
    await auth.login("aca")
    st = await finished_bulk(client, (await submit_bulk(client))["body"]["job_key"])
    assert (st["result"]["sheets"], st["result"]["withheld"]) == (1, ["S2"])


async def test_bulk_grade_sheets_say_why_there_is_nothing_to_download(client, auth, fake_pdf):
    M.AcademicSession.create(code="2024-I")
    make_user("s2", role="STU", org_id="S2", degree="BTE", year_of_entry="2023")
    make_user("aca", role="ACA")
    await auth.login("aca")
    body = await submit_bulk(client)
    st = await finished_bulk(client, body["body"]["job_key"])
    assert st["error"].startswith("No grade sheets to download: of the 1 students, 1 have "
                                  "no 2024-I results")
    res = await (await client.get(f"/acadstack/get_gradesheets/{body['body']['job_key']}")
                 ).get_json()
    assert res["status"] == "ERROR"


async def test_bulk_grade_sheets_need_every_criterion(client, auth):
    make_user("aca", role="ACA")
    await auth.login("aca")
    body = await submit_bulk(client, dict(BULK, acad_session=""))
    assert body["status"] == "ERROR" and body["body"].startswith("Select the degree")


async def test_bulk_grade_sheet_status_of_an_unknown_request(client, auth):
    make_user("aca", role="ACA")
    await auth.login("aca")
    st = await (await client.get("/acadstack/bulk_gradesheets_status/nope")).get_json()
    assert st["status"] == "ERROR" and "submit it again" in st["body"]
