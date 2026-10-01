"""The grading_schemes setting: which scheme applies to a level in a session,
the checks on saving it, and the grade lists and reports that follow it."""

import pytest

import api_common as apiVC
import models as M
import settings
from conftest import enrol, make_offering, make_user, ten_point_scheme

SESSIONS = (("Spring 25", "2025-01-05"), ("Fall 25", "2025-08-01"),
            ("Spring 26", "2026-01-05"), ("Fall 26", "2026-08-01"))


@pytest.fixture
def sessions(db):
    for code, start in SESSIONS:
        M.AcademicSession.create(code=code)
        M.AcademicCalendar.create(acad_session=code, event_code="SESSION_S",
                                  event_value=start)


def pass_fail(name="Pass/fail", level="UG", from_session=None, until_session=None):
    """A scheme whose only grades are P (4 points, earns credit) and F."""
    s = ten_point_scheme(level, from_session, until_session, name)
    a, f = s["grades"][0], s["grades"][8]
    s["grades"] = [dict(a, grade="P", points=4), f]
    return s


def program(code, level):
    M.VocabItem.create(vocab="Degrees", code=code, label=code, attrs={"level": level})


async def academics(client, stu):
    return await (await client.get(f"/acadstack/get_student_academics/{stu.id}")).get_json()


async def save(client, value):
    res = await client.post("/acadstack/setting_save",
                            json={"key": "grading_schemes", "value": value})
    return await res.get_json()


# ---- choosing the scheme ----

async def test_one_session_override_applies_to_that_session_only(client, auth, sessions):
    settings.save("grading_schemes", [ten_point_scheme("UG"),
                                      pass_fail(from_session="Spring 26",
                                                until_session="Spring 26")])
    program("BTE", "UG")
    stu = make_user("stu", role="STU", degree="BTE", year_of_entry="2024")
    for code, sess, grade in (("CS101", "Fall 25", "A"), ("CS102", "Spring 26", "P"),
                              ("CS103", "Fall 26", "A")):
        enrol(stu, make_offering(code, acad_session=sess, status="F"), grade=grade)

    await auth.login("stu")
    body = await academics(client, stu)
    assert body["status"] == "OK"
    perf = body["body"]["enrollments"]["C"]["enrollments"]
    assert [perf[s]["sgpa"] for s in ("Fall 25", "Spring 26", "Fall 26")] == [10, 4, 10]


def test_narrowest_range_wins(sessions):
    settings.save("grading_schemes", [
        ten_point_scheme("UG"),
        pass_fail(from_session="Fall 25", until_session="Fall 26"),
        ten_point_scheme("UG", "Spring 26", "Spring 26", "Inner")])
    rules = apiVC.grading_rules("UG", [s for s, _ in SESSIONS])
    assert ["P" in rules[s] for s, _ in SESSIONS] == [False, True, False, True]


def test_scheme_of_the_students_level_is_used(sessions):
    settings.save("grading_schemes", [ten_point_scheme("UG"), pass_fail(level="PG")])
    assert "P" in apiVC.grading_rules("PG", ["Fall 25"])["Fall 25"]
    assert "P" not in apiVC.grading_rules("UG", ["Fall 25"])["Fall 25"]


async def test_session_without_a_scheme_is_reported(client, auth, sessions):
    settings.save("grading_schemes", [ten_point_scheme("UG", until_session="Fall 25")])
    program("BTE", "UG")
    stu = make_user("stu", role="STU", degree="BTE", year_of_entry="2024")
    enrol(stu, make_offering(acad_session="Spring 26", status="F"), grade="A")
    await auth.login("stu")
    body = await academics(client, stu)
    assert body == {"status": "ERROR",
                    "body": "No grading scheme applies to UG students in session Spring 26."}


async def test_program_without_a_level_is_reported(client, auth, grading_schemes):
    program("XYZ", None)
    stu = make_user("stu", role="STU", degree="XYZ", year_of_entry="2024")
    enrol(stu, make_offering(status="F"), grade="A")
    await auth.login("stu")
    body = await academics(client, stu)
    assert body == {"status": "ERROR",
                    "body": "The student's program has no level (UG, PG or PHD)."}


# ---- saving ----

@pytest.fixture
async def sup(client, auth, sessions):
    make_user("sup", role="SUP")
    await auth.login("sup")


def close(acad_session):
    M.AcademicCalendar.create(acad_session=acad_session, event_code="SESSION_CLOSED",
                              event_value="2026-01-01")


async def test_change_to_a_closed_sessions_rules_is_refused(client, sup):
    settings.save("grading_schemes", [ten_point_scheme("UG")])
    close("Fall 25")
    changed = ten_point_scheme("UG")
    changed["grades"][0]["points"] = 12

    for value in ([changed],
                  [ten_point_scheme("UG"), pass_fail(from_session="Fall 25",
                                                     until_session="Fall 25")]):
        body = await save(client, value)
        assert body["status"] == "ERROR"
        assert "Fall 25" in body["body"] and "closed" in body["body"]
    assert settings.get("grading_schemes") == [ten_point_scheme("UG")]


async def test_change_after_the_closed_sessions_is_saved(client, sup):
    settings.save("grading_schemes", [ten_point_scheme("UG")])
    close("Fall 25")
    changed = ten_point_scheme("UG", "Spring 26", name="New")
    changed["grades"][0]["points"] = 12
    # A PG scheme gives rules where there were none, which changes nothing.
    value = [ten_point_scheme("UG", until_session="Fall 25"), changed,
             ten_point_scheme("PG")]
    body = await save(client, value)
    assert body["status"] == "OK"
    assert settings.get("grading_schemes") == value


def renamed(grade, index=0):
    s = ten_point_scheme("UG")
    s["grades"][index]["grade"] = grade
    return [s]


@pytest.mark.parametrize("value", [
    [ten_point_scheme("UG", "Fall 30")],
    [ten_point_scheme("UG", "Fall 26", "Fall 25")],
    [ten_point_scheme("UG", until_session="Spring 26"),
     ten_point_scheme("UG", "Fall 25", name="Overlapping")],
    [ten_point_scheme("UG"), ten_point_scheme("UG", name="Same range")],
    [ten_point_scheme("XX")],
    [dict(ten_point_scheme("UG"), name=" ")],
    [dict(ten_point_scheme("UG"), grades=[])],
    renamed("NA"), renamed("ABC"), renamed("a"), renamed("A-", index=0),
    [dict(ten_point_scheme("UG"), extra=1)],
    "10-point",
], ids=["unknown session", "ends before it starts", "overlap", "same range",
        "unknown level", "blank name", "no grades", "NA", "3 characters",
        "lower case", "duplicate grade", "unknown key", "not a list"])
async def test_invalid_schemes_are_refused(client, sup, value):
    body = await save(client, value)
    assert body["status"] == "ERROR"
    assert settings.get("grading_schemes") == []


async def test_negative_points_are_refused(client, sup):
    s = ten_point_scheme("UG")
    s["grades"][0]["points"] = -1
    assert (await save(client, [s]))["status"] == "ERROR"


# ---- what follows from the schemes ----

async def test_course_grades_follow_the_schemes(client, auth, grading_schemes):
    make_user("u")
    await auth.login("u")

    async def course_grades():
        sd = (await (await client.get("/acadstack/get_static_data")).get_json())["body"]
        return [g["id"] for g in sd["CourseGrades"]]

    assert await course_grades() == ["", "NA", "A", "A-", "B", "B-", "C", "C-", "D", "E",
                                     "F", "NP", "NF", "I", "W", "S", "U"]
    settings.save("grading_schemes", [pass_fail()])
    assert await course_grades() == ["", "NA", "P", "F"]
    assert apiVC.valid_audit_grades() == ["NA"]


async def test_earned_credit_report_agrees_with_transcripts(client, auth, grading_schemes):
    # NP earns no credit for PG students, nor D for PhD students.
    program("MTE", "PG")
    program("PHD", "PHD")
    make_user("aca", role="ACA")
    pg = make_user("pg", role="STU", degree="MTE", year_of_entry="2024")
    phd = make_user("phd", role="STU", degree="PHD", year_of_entry="2024")
    co1 = make_offering("CS501", ltp="3-0-2-7-4", acad_session="2026-I", status="F")
    co2 = make_offering("CS502", ltp="3-0-0-6-3", acad_session="2026-I", status="F")
    for stu, grade in ((pg, "NP"), (phd, "D")):
        enrol(stu, co1, grade="A")
        enrol(stu, co2, grade=grade)

    await auth.login("aca")
    body = await (await client.post("/acadstack/earned_credit_check", json={
        "acad_session": "2026-I", "degree": "-", "dept_name": "-", "course_type": "-",
        "for_year": "-"})).get_json()
    assert body["status"] == "OK"
    assert {r["entry_no"]: r["credits"] for r in body["body"]["data"]} == \
        {"pg": "UnCat=4.00", "phd": "UnCat=4.00"}
    for stu in (pg, phd):
        perf = (await academics(client, stu))["body"]["enrollments"]["C"]
        assert perf["enrollments"]["2026-I"]["ec"] == 4
