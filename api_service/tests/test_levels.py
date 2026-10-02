"""A program's level comes from its attrs, and a course's level from its own
column, never from the codes themselves."""

from io import BytesIO
from pathlib import Path

import pytest
from quart.datastructures import FileStorage

import api_common as apiVC
import models as M
from conftest import enrol, make_offering, make_user


def program(code, level):
    return M.VocabItem.create(vocab="Degrees", code=code, label=code,
                              attrs={"level": level} if level else {})


def test_degree_level_reads_the_program_attrs(db):
    program("BSC", "UG")
    hidden = program("DPH", "PHD")
    hidden.is_deleted = True
    hidden.save()
    program("NOLV", None)
    assert [apiVC.degree_level(c) for c in ("BSC", "DPH", "NOLV", "XYZ", None)] == \
        ["UG", "PHD", None, None, None]


async def test_login_and_current_user_carry_degree_level(client, auth):
    program("BSC", "UG")
    make_user("stu", role="STU", degree="BSC")
    body = await (await auth.login("stu")).get_json()
    assert body["body"]["user"]["degree_level"] == "UG"
    body = await (await client.get("/acadstack/current_user")).get_json()
    assert body["body"]["user"]["degree_level"] == "UG"


@pytest.mark.parametrize("level, sees", [("PHD", True), ("UG", False), ("PG", False)])
async def test_phd_menu_follows_the_program_level(client, auth, level, sees):
    program("DOC", level)
    make_user("stu", role="STU", degree="DOC")
    await auth.login("stu")
    body = await (await client.get("/acadstack/current_user")).get_json()
    assert ("PhD" in body["body"]["nav"]["menus"]) == sees


@pytest.mark.parametrize("level, ec", [("UG", 6), ("PG", 4)])
async def test_gpa_rules_follow_the_program_level(client, auth, level, ec, grading_schemes):
    # NP earns credit under the UG rules only
    program("BSC", level)
    stu = make_user("stu", role="STU", degree="BSC", year_of_entry="2023")
    enrol(stu, make_offering("CS101", ltp="3-0-2-7-4", acad_session="2023-I", status="F"),
          grade="A")
    enrol(stu, make_offering("CS102", ltp="1-0-2-3-2", acad_session="2023-I", status="F"),
          grade="NP")
    await auth.login("stu")
    body = await (await client.get(f"/acadstack/get_student_academics/{stu.id}")).get_json()
    assert body["body"]["enrollments"]["C"]["enrollments"]["2023-I"]["ec"] == ec


@pytest.mark.parametrize("level, listed", [("PHD", True), ("PG", False)])
async def test_hod_sees_pending_enrolments_of_phd_level_students(client, auth, level, listed):
    program("DOC", level)
    make_user("hod", role="HOD", dept_name="CSE")
    stu = make_user("stu", role="STU", degree="DOC", dept_name="CSE")
    enrol(stu, make_offering(), enrol_status="APEN")
    await auth.login("hod")
    body = await (await client.get("/acadstack/get_advisor_courses_enrol")).get_json()
    assert body["status"] == "OK"
    assert (len(body["body"]) == 1) == listed


async def _post(client, url, payload):
    return await (await client.post(f"/acadstack/{url}", json=payload)).get_json()


async def test_course_save_stores_the_level(client, auth):
    make_user("aca", role="ACA")
    await auth.login("aca")
    body = await _post(client, "cour_save", {"code": "AB1", "title": "T", "ltp": "3-0-0-6-3",
                                             "level": "ALL"})
    assert body["status"] == "OK", body
    assert M.Course.get(M.Course.code == "AB1").level == "ALL"


async def test_course_save_rejects_an_unknown_level(client, auth):
    make_user("aca", role="ACA")
    await auth.login("aca")
    body = await _post(client, "cour_save", {"code": "AB1", "title": "T", "ltp": "3-0-0-6-3",
                                             "level": "PHD"})
    assert body["status"] == "ERROR"
    assert M.Course.select().count() == 0


@pytest.mark.parametrize("level, ok", [("PG", True), ("ALL", True), ("UG", False)])
async def test_pg_scope_creates_only_pg_or_all_level_courses(client, auth, level, ok):
    make_user("res", role="RES")
    await auth.login("res")
    body = await _post(client, "cour_save", {"code": "AB1", "title": "T", "ltp": "3-0-0-6-3",
                                             "level": level})
    assert (body["status"] == "OK") == ok, body
    assert M.Course.select().count() == (1 if ok else 0)


async def test_pg_scope_cannot_move_a_course_to_ug(client, auth):
    crs = M.Course.create(code="AB1", title="T", ltp="3-0-0-6-3", level="PG", status="DRA",
                          author=make_user("fac", role="FAC"))
    make_user("res", role="RES")
    await auth.login("res")
    body = await _post(client, "cour_save", {"id": crs.id, "level": "UG", "txn_no": 1})
    assert body["status"] == "ERROR"
    assert M.Course.get_by_id(crs.id).level == "PG"
    body = await _post(client, "cour_save", {"id": crs.id, "title": "New", "txn_no": 1})
    assert body["status"] == "OK", body


@pytest.mark.parametrize("ltp", ["3-0-2", "3-0-2-6-x", "", None])
async def test_course_save_needs_the_full_ltpsc(client, auth, ltp):
    make_user("aca", role="ACA")
    await auth.login("aca")
    body = await _post(client, "cour_save", {"code": "AB1", "title": "T", "ltp": ltp,
                                             "level": "UG"})
    assert body["status"] == "ERROR" and "L-T-P-S-C" in body["body"]
    assert M.Course.select().count() == 0


async def _upload_courses(client, csv_text):
    fs = FileStorage(BytesIO(csv_text.encode()), filename="courses.csv",
                     content_type="text/csv")
    res = await client.post("/acadstack/cour_add", files={"courses_file": fs})
    return await res.get_json()


async def test_course_csv_sets_the_level(client, auth):
    make_user("aca", role="ACA")
    await auth.login("aca")
    body = await _upload_courses(client, "code,title,ltp,level\n"
                                         "AB1,One,3-0-0-6-3, ug\nAB2,Two,3-0-0-6-3,ALL\n")
    assert body["status"] == "OK", body
    assert {c.code: c.level for c in M.Course.select()} == {"AB1": "UG", "AB2": "ALL"}


@pytest.mark.parametrize("csv_text", ["code,title,ltp,level\nAB1,One,3-0-0-6-3,UG\nAB2,Two,3-0-0-6-3,XX\n",
                                      "code,title,ltp\nAB1,One,3-0-0-6-3\n"])
async def test_course_csv_rejects_a_missing_or_unknown_level(app, client, auth, csv_text):
    make_user("aca", role="ACA")
    await auth.login("aca")
    body = await _upload_courses(client, csv_text)
    assert body["status"] == "ERROR"
    assert "level must be one of UG, PG, ALL" in body["body"], body
    assert M.Course.select().count() == 0
    # The rejected upload is not left on disk
    assert not any(Path(app.config["upload_folder"]).rglob("*.csv"))


async def test_course_csv_sets_the_freq_and_blank_leaves_it_unset(client, auth):
    M.VocabItem.create(vocab="CourseFreqs", code="E", label="Even")
    make_user("aca", role="ACA")
    await auth.login("aca")
    body = await _upload_courses(client, "code,title,ltp,level,freq\n"
                                         "AB1,One,3-0-0-6-3,UG,e\nAB2,Two,3-0-0-6-3,UG,\n")
    assert body["status"] == "OK", body
    assert {c.code: c.freq for c in M.Course.select()} == {"AB1": "E", "AB2": None}


async def test_course_csv_rejects_an_unknown_freq(client, auth):
    M.VocabItem.create(vocab="CourseFreqs", code="E", label="Even")
    make_user("aca", role="ACA")
    await auth.login("aca")
    body = await _upload_courses(client, "code,title,ltp,level,freq\nAB1,One,3-0-0-6-3,UG,X\n")
    assert body["status"] == "ERROR"
    assert "freq must be one of E" in body["body"], body
    assert M.Course.select().count() == 0


async def test_academics_of_a_student_without_entry_year(client, auth, grading_schemes):
    program("BSC", "UG")
    stu = make_user("stu", role="STU", degree="BSC")
    enrol(stu, make_offering("CS101", ltp="3-0-2-7-4", acad_session="2023-I", status="F"),
          grade="A")
    await auth.login("stu")
    body = await (await client.get(f"/acadstack/get_student_academics/{stu.id}")).get_json()
    assert body["status"] == "OK"
    assert body["body"]["enrollments"]["C"]["enrollments"]["2023-I"]["ec"] == 4
