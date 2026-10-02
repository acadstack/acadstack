"""Roll numbers, course codes and L-T-P-S-C values are not tied to one
university's format."""

import api_common as apiVC
import common as C
import models as M
import policy as P
from conftest import make_offering, make_user
from test_levels import _upload_courses


def test_entry_years_are_any_comma_separated_four_digit_years():
    assert all(apiVC.entry_years_valid(y) for y in ("2024", "2024, 2025", "1999,2031"))
    assert not any(apiVC.entry_years_valid(y) for y in ("", None, "24", "A,B"))


async def test_student_lookup_takes_any_prefix(client, auth):
    make_user("aca", role="ACA")
    make_user("s1", role="STU", org_id="B-77-1", current_status="REG")
    make_user("s2", role="STU", org_id="B-78-1", current_status="REG")
    await auth.login("aca")
    res = await (await client.get("/acadstack/student_lookup/B-77")).get_json()
    assert [r["org_id"] for r in res["body"]] == ["B-77-1"]


async def test_bulk_enrol_takes_any_prefix(client, auth):
    make_user("aca", role="ACA")
    s1 = make_user("s1", role="STU", org_id="B-77-1", current_status="REG")
    make_user("s2", role="STU", org_id="B-78-1", current_status="REG")
    make_user("s3", role="STU", org_id="B-77-2", current_status="GRD")
    co = make_offering()
    await auth.login("aca")
    res = await (await client.get(f"/acadstack/co_bulkenrol/B-77/{co.id}")).get_json()
    assert res["status"] == "OK", res
    assert [e.student_id for e in M.CourseEnrollment.select()] == [s1.id]


async def test_prefix_may_contain_a_slash(client, auth):
    make_user("aca", role="ACA")
    s1 = make_user("s1", role="STU", org_id="B/77/1", current_status="REG")
    make_user("s2", role="STU", org_id="B/78/1", current_status="REG")
    co = make_offering()
    await auth.login("aca")
    res = await (await client.get("/acadstack/student_lookup/B%2F77")).get_json()
    assert [r["org_id"] for r in res["body"]] == ["B/77/1"], res
    res = await (await client.get(f"/acadstack/co_bulkenrol/B%2F77/{co.id}")).get_json()
    assert res["status"] == "OK", res
    assert [e.student_id for e in M.CourseEnrollment.select()] == [s1.id]


async def test_course_csv_rejects_non_ascii_digits(client, auth):
    make_user("aca", role="ACA")
    await auth.login("aca")
    body = await _upload_courses(client, "code,title,ltp,level\nAB1,One,٣-0-0-6-3,UG\n")
    assert body["status"] == "ERROR" and "L-T-P-S-C" in body["body"], body
    assert M.Course.select().count() == 0


async def test_course_csv_requires_the_full_ltpsc(client, auth):
    make_user("aca", role="ACA")
    await auth.login("aca")
    body = await _upload_courses(client, "code,title,ltp,level\nAB1,One,3-0-0-6-3,UG\n"
                                         "AB2,Two,3-0-0,UG\n")
    assert body["status"] == "ERROR"
    assert "L-T-P-S-C" in body["body"] and "AB2" in body["body"], body
    assert M.Course.select().count() == 0


async def test_course_csv_keeps_the_given_ltpsc(client, auth):
    make_user("aca", role="ACA")
    await auth.login("aca")
    body = await _upload_courses(client, "code,title,ltp,level\nAB1,One,3-0-0-5-4,UG\n")
    assert body["status"] == "OK", body
    assert M.Course.get(M.Course.code == "AB1").ltp == "3-0-0-5-4"


def test_credit_hours_spent_reads_multi_digit_ltp(db):
    fac = make_user("fac", role="FAC")
    co = make_offering(code="CS900", ltp="10-0-2-21-11", acad_session="2026-I",
                       instructor=fac)
    rows = C.db.execute_sql(C.sql_by_id("credit_hours_spent"),
                            [co.acad_session, P.roles_with("roster.instructor")]).fetchall()
    assert [float(r[4]) for r in rows] == [231.0]


async def test_slot_times_must_be_hhmm(client, auth):
    make_user("aca", role="ACA")
    await auth.login("aca")
    for start, end in [(975, 1030), (900, 2575), (-100, 1000), ("9am", 1000)]:
        res = await client.post("/acadstack/save_slot", json={
            "slot": "A", "week_day": 1, "start_time": start, "end_time": end})
        body = await res.get_json()
        assert body["status"] == "ERROR" and "HHMM" in body["body"], (start, end, body)
    assert M.CourseSlotTiming.select().count() == 0
    res = await client.post("/acadstack/save_slot", json={
        "slot": "A", "week_day": 1, "start_time": 0, "end_time": 2359})
    assert (await res.get_json())["status"] == "OK"
