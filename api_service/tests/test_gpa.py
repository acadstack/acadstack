"""Characterization tests for SGPA/CGPA/earned-credit computation.

These pin the current behaviour of ``transcript.session_gpa`` and of the
cumulative CGPA built on top of it. Tests whose name starts with a bug code
(C4, C12, C13, ...) pin behaviour that looks wrong; flip them when fixing it.
"""

import pytest

import common as C
import models as M
import transcript as TR
from conftest import enrol, make_offering, make_user

compute = TR.session_gpa


def course(grade, credits=4, enrol_type="C", enrol_status="ENRO",
           acad_session="2024-I", ltp=None, code="XX101"):
    return {"code": code, "grade": grade, "enrol_type": enrol_type,
            "enrol_status": enrol_status, "acad_session": acad_session,
            "ltp": ltp or f"3-0-2-7-{credits}"}


def test_single_a_grade():
    r = compute([course("A")], "UG")
    assert r == {"sgpa": 10, "ec": 4, "s_ec": 0, "creg": 4, "cgpa": 10, "pts_cgpa": 40}


def test_mixed_grades_are_credit_weighted():
    r = compute([course("A", 4), course("B", 3)], "UG")
    assert r["sgpa"] == 9.14
    assert r["cgpa"] == 9.14
    assert r["ec"] == 7


def test_f_grade_counts_in_sgpa_but_not_cgpa_or_earned_credits():
    r = compute([course("A", 4), course("F", 3)], "UG")
    assert r["sgpa"] == 5.71
    assert r["cgpa"] == 10
    assert r["ec"] == 4
    assert r["creg"] == 7


def test_e_grade_counts_in_sgpa_but_not_cgpa_or_earned_credits():
    r = compute([course("A", 4), course("E", 3)], "UG")
    assert r["sgpa"] == 6.57
    assert r["cgpa"] == 10
    assert r["ec"] == 4


def test_only_enrolled_rows_are_counted():
    rows = [course("A", 4)] + [course("F", 3, enrol_status=s)
                               for s in ("IPEN", "APEN", "DROP", "WDRAW", "IREJ")]
    assert compute(rows, "UG") == compute([course("A", 4)], "UG")


def test_audit_course_counts_in_registered_credits_only():
    r = compute([course("A", 4), course("A", 3, enrol_type="A")], "UG")
    assert r["creg"] == 7
    assert r["ec"] == 4
    assert r["sgpa"] == 10


@pytest.mark.parametrize("enrol_type", ["C", "CM", "CC"])
def test_credit_enrol_types(enrol_type):
    assert compute([course("B", enrol_type=enrol_type)], "UG")["ec"] == 4


def test_c4_enrol_type_must_match_a_credit_type_exactly():
    assert compute([course("B", enrol_type="")], "UG")["ec"] == 0
    assert compute([course("B", enrol_type="M")], "UG")["ec"] == 0


def test_s_grade_earns_credit_but_is_excluded_from_gpa():
    r = compute([course("A", 4), course("S", 2)], "UG")
    assert r["ec"] == 6
    assert r["s_ec"] == 2
    assert r["sgpa"] == 10
    assert r["cgpa"] == 10


@pytest.mark.parametrize("grade", ["U", "I", "W"])
def test_u_i_w_grades_are_excluded_from_sgpa_denominator(grade):
    r = compute([course("A", 4), course(grade, 3)], "UG")
    assert r["sgpa"] == 10
    assert r["ec"] == 4
    assert r["creg"] == 7


def test_ug_np_grade_earns_credit_and_dilutes_gpa():
    # NP is an earned-credit grade for UG but has no grade points, so it
    # lowers both SGPA and CGPA.
    r = compute([course("A", 4), course("NP", 2)], "UG")
    assert r["ec"] == 6
    assert r["sgpa"] == 6.67
    assert r["cgpa"] == 6.67


def test_pg_np_grade_does_not_earn_credit():
    r = compute([course("A", 4), course("NP", 2)], "PG")
    assert r["ec"] == 4
    assert r["sgpa"] == 6.67
    assert r["cgpa"] == 10


def test_ungraded_na_course_counts_in_sgpa_denominator():
    r = compute([course("A", 4), course("NA", 3)], "UG")
    assert r["sgpa"] == 5.71
    assert r["cgpa"] == 10
    assert r["ec"] == 4


def test_pg_d_grade_earns_credit():
    r = compute([course("D", 4)], "PG")
    assert r["ec"] == 4
    assert r["sgpa"] == 4
    assert r["cgpa"] == 4


def test_phd_after_2021_c_minus_earns_credit_and_counts_in_cgpa():
    r = compute([course("C-", 4, acad_session="2022-I")], "PHD")
    assert r["ec"] == 4
    assert r["sgpa"] == 5
    assert r["cgpa"] == 5


def test_phd_after_2021_d_grade_does_not_earn_credit():
    r = compute([course("D", 4, acad_session="2023-II")], "PHD")
    assert r["ec"] == 0
    assert r["sgpa"] == 4
    assert r["cgpa"] == 0


def test_phd_before_2021_c_minus_neither_earns_credit_nor_counts_in_cgpa():
    r = compute([course("C-", 4, acad_session="2020-II")], "PHD")
    assert r["ec"] == 0
    assert r["pts_cgpa"] == 0
    assert r["sgpa"] == 5
    assert r["cgpa"] == 0


def test_c12_phd_2021_I_c_minus_earns_credit_without_cgpa_points():
    r = compute([course("A", 4, acad_session="2021-I"),
                 course("C-", 4, acad_session="2021-I")], "PHD")
    assert r["ec"] == 8
    assert r["pts_cgpa"] == 40
    assert r["cgpa"] == 5


def test_c12_phd_2021_unknown_suffix_c_minus_gets_cgpa_points_without_credit():
    r = compute([course("C-", 4, acad_session="2021-T3")], "PHD")
    assert r["ec"] == 0
    assert r["pts_cgpa"] == 20
    assert r["cgpa"] == 0


def test_fractional_credits():
    r = compute([course("A", ltp="1-0-1-2-1.5")], "UG")
    assert r["ec"] == 1.5
    assert r["sgpa"] == 10


def test_ltp_without_five_parts_is_rejected():
    with pytest.raises(C.AcadStackException, match="L-T-P-S-C"):
        compute([course("A", ltp="3-0-2-4")], "UG")


def test_c13_malformed_ltp_raises_index_error():
    with pytest.raises(IndexError):
        compute([course("A", ltp="3-1")], "UG")


def test_empty_grade_earns_no_credit():
    # Grades were once matched by substring of "A,A-,...", which matched "".
    assert compute([course("")], "UG")["ec"] == 0


def test_frozen_credits_are_used_instead_of_ltp():
    frozen = dict(course("A", 4), credits=3)
    assert compute([frozen], "UG")["creg"] == 3


def test_cumulative_gpa_carries_earned_credits_and_points():
    r = TR.cumulative_gpa([[course("A", 4)], [course("B", 4, acad_session="2024-II")]],
                          "UG")
    assert [x["cec"] for x in r] == [4, 8]
    assert [x["cgpa"] for x in r] == [10, 9]
    assert [x["sgpa"] for x in r] == [10, 8]


def test_sessions_sort_chronologically():
    assert sorted(["2024-II", "2023-S", "2024-I", "2024-T1"], key=TR.session_sort_key) \
        == ["2023-S", "2024-T1", "2024-I", "2024-II"]


def test_empty_course_list():
    assert compute([], "UG") == {"sgpa": 0, "ec": 0, "s_ec": 0, "creg": 0,
                                  "cgpa": 0, "pts_cgpa": 0}


# ---- Cumulative CGPA over sessions, through the student academics route ----

async def test_cumulative_cgpa_across_sessions(client, auth):
    stu = make_user("stu", role="STU", degree="BTE", year_of_entry="2023")
    co1 = make_offering("CS101", ltp="3-0-2-7-4", acad_session="2023-I", status="F")
    co2 = make_offering("CS102", ltp="3-0-0-6-3", acad_session="2023-II", status="F")
    co3 = make_offering("CS103", ltp="3-0-0-6-3", acad_session="2023-II", status="F")
    enrol(stu, co1, grade="A")    # 40 pts / 4 cr
    enrol(stu, co2, grade="B")    # 24 pts / 3 cr
    enrol(stu, co3, grade="F")    #  0 pts / 3 cr, not earned

    await auth.login("stu")
    body = await (await client.get(f"/acadstack/get_student_academics/{stu.id}")).get_json()
    assert body["status"] == "OK"
    perf = body["body"]["enrollments"]["C"]
    assert perf["acad_sessions"] == ["2023-I", "2023-II"]
    s1, s2 = perf["enrollments"]["2023-I"], perf["enrollments"]["2023-II"]
    assert (s1["sgpa"], s1["cgpa"], s1["ec"], s1["cec"]) == (10, 10, 4, 4)
    assert (s2["sgpa"], s2["ec"], s2["creg"], s2["cec"]) == (4, 3, 6, 7)
    assert s2["cgpa"] == 9.14


async def test_grade_hidden_until_result_declaration(client, auth):
    stu = make_user("stu", role="STU", degree="BTE", year_of_entry="2023")
    enrol(stu, make_offering(acad_session="2026-I", status="R"), grade="A")
    M.AcademicCalendar.create(acad_session="2026-I", event_code="RESULT_DECLARATION",
                              event_value="2099-01-01")

    await auth.login("stu")
    body = await (await client.get(f"/acadstack/get_student_academics/{stu.id}")).get_json()
    sess = body["body"]["enrollments"]["C"]["enrollments"]["2026-I"]
    assert sess["courses"][0]["grade"] == "NA"
    assert sess["sgpa"] == 0


async def test_student_cannot_read_other_students_academics(client, auth):
    make_user("stu", role="STU")
    other = make_user("other", role="STU")
    await auth.login("stu")
    body = await (await client.get(f"/acadstack/get_student_academics/{other.id}")).get_json()
    assert body["status"] == "ERROR"
