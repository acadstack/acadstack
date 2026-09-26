"""Characterization tests for api_course_enrolment.__compute_cgpa_sgpa_ec.

These tests pin down the function's behavior exactly, so that a refactor
of the policy it reads can be checked against them. Two oddities they used
to characterise have since been fixed deliberately, and the tests at the
bottom now expect the corrected behaviour: enrolment types were matched by
substring, and a malformed LTP string raised a raw IndexError (credits now
come from the stored Course.credits instead).

No app/DB fixtures are needed: __compute_cgpa_sgpa_ec is a pure function
over plain dicts, with no I/O.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import api_course_enrolment as ace

# The function has a double-leading-underscore name but lives at module
# level (not in a class), so it is NOT name-mangled -- plain getattr works.
compute = getattr(ace, "__compute_cgpa_sgpa_ec")


def course(acad_session="2022-I", credits=3, enrol_type="C",
           enrol_status="ENRO", grade="A", code="CS101"):
    return {"acad_session": acad_session, "credits": credits,
            "enrol_type": enrol_type, "enrol_status": enrol_status,
            "grade": grade, "code": code}


# ===================== Basic UG (BTE) behavior =====================

def test_ug_single_credit_course_grade_a():
    result = compute([course(grade="A")], "BTE")
    assert result == {"sgpa": 10.0, "ec": 3, "s_ec": 0, "creg": 3,
                       "cgpa": 10.0, "pts_cgpa": 30}


def test_ug_non_enrolled_status_is_ignored_entirely():
    # Only enrol_status == "ENRO" is counted; everything else is skipped.
    result = compute([course(enrol_status="IPEN", grade="A")], "BTE")
    assert result == {"sgpa": 0, "ec": 0, "s_ec": 0, "creg": 0,
                       "cgpa": 0, "pts_cgpa": 0}


def test_ug_fail_grade_counts_toward_registered_credits_only():
    # F is in the grade-points map (0 points) but not in the UG
    # earned-credits list, so it drags SGPA down without earning credit.
    result = compute([course(grade="F")], "BTE")
    assert result["creg"] == 3
    assert result["ec"] == 0
    assert result["sgpa"] == 0.0  # 0 points / 3 credits
    assert result["cgpa"] == 0
    assert result["pts_cgpa"] == 0


def test_ug_incomplete_grade_excluded_from_sgpa_denominator():
    # I/W/U grades are subtracted out of the SGPA denominator entirely
    # (as if the course was never registered for SGPA purposes), and earn
    # no credit.
    result = compute([course(grade="I")], "BTE")
    assert result["creg"] == 3
    assert result["ec"] == 0
    assert result["s_ec"] == 0
    assert result["sgpa"] == 0
    assert result["cgpa"] == 0


def test_ug_audit_course_excluded_from_gpa_and_earned_credit_but_not_creg():
    # enrol_type "A" (audit): counts toward total registered credits
    # (`creg`), but not creg_wo_audit/ec/sgpa/cgpa.
    result = compute([course(enrol_type="A", grade="A")], "BTE")
    assert result["creg"] == 3
    assert result["ec"] == 0
    assert result["sgpa"] == 0
    assert result["cgpa"] == 0
    assert result["pts_cgpa"] == 0


def test_ug_satisfactory_grade_counts_as_earned_credit_but_zeroes_gpa():
    # Grade "S" is in the UG earned-credit list AND counted in s_ec, so it
    # both earns ec credit and cancels itself out of the SGPA/CGPA
    # denominators (s_ec is subtracted from creg_wo_audit/ec). It has no
    # grade-point-map entry, so it contributes no points either.
    result = compute([course(grade="S")], "BTE")
    assert result["ec"] == 3          # ec counts S courses despite s_ec offset
    assert result["s_ec"] == 3
    assert result["creg"] == 3
    assert result["sgpa"] == 0        # creg_sgpa = (3 - 3) - 0 = 0
    assert result["cgpa"] == 0        # ec_cgpa = (3 - 3) = 0
    assert result["pts_cgpa"] == 0


def test_multiple_courses_accumulate():
    courses = [
        course(code="CS101", grade="A", credits=3),
        course(code="CS102", grade="B", credits=4),
        course(code="CS103", grade="F", credits=3, enrol_status="AREJ"),  # skipped
    ]
    result = compute(courses, "BTE")
    # CS103 is skipped entirely (not ENRO).
    assert result["creg"] == 7          # 3 + 4
    assert result["ec"] == 7
    assert result["pts_cgpa"] == 10 * 3 + 8 * 4   # A*3 + B*4 = 30 + 32 = 62
    assert result["cgpa"] == round(62 / 7, 2)
    assert result["sgpa"] == round(62 / 7, 2)


# ===================== PG (non-BTE, non-PHD) behavior =====================

def test_pg_uses_pg_earned_credit_list_and_default_pass_grades():
    # PG's earned-credit list has no "NP" (unlike UG's), and PG never
    # touches `pass_grades`, so it stays at its outer default
    # "A,A-,B,B-,C,C-,D" regardless of academic year -- unlike PHD.
    result = compute([course(grade="NP")], "MTE")
    assert result["ec"] == 0          # NP not in pg_ec_grades
    result_d = compute([course(grade="D")], "MTE")
    assert result_d["ec"] == 3        # D is in pg_ec_grades
    assert result_d["cgpa"] == 4.0    # D counts toward CGPA for PG (pass_grades has D)


# ===================== PHD behavior =====================
# __compute_cgpa_sgpa_ec used to carry a hand-rolled rule (introduced "in
# 2021") that changed which grades earn credit and which count toward CGPA
# for PhD students, keyed off the academic session's year and semester
# suffix. The two lists disagreed with each other in some branches, and the
# rule assigned different results to sessions that begin in the same month
# (2021-I vs 2021-T1) -- so it could not be expressed as effective-dated
# policy at all.
#
# test_phd_grade_c_minus_policy_matrix characterized all eight branches. It
# was retired deliberately, not accidentally: the product has never been
# deployed, so there are no transcripts computed under those branches to
# preserve, and the rule is now one ordinary ruleset with no year in it.
# See docs/versioned-policy.md section 7.1 for the full argument.

def test_phd_grade_d_never_counts_for_cgpa_in_any_branch():
    # Unlike UG/PG (whose pass_grades includes "D"), none of the PHD
    # phd_ec_pass_grades variants ever include "D" -- so a PhD student's
    # "D" grade always earns SGPA points but never counts toward CGPA,
    # regardless of academic session.
    for acad_session in ["2019-I", "2021-I", "2021-II", "2023-I"]:
        result = compute([course(acad_session=acad_session, grade="D")], "PHD")
        assert result["pts_cgpa"] == 0, acad_session
        assert result["sgpa"] == 4.0, acad_session  # gpm["D"] = 4


# ===================== Enrolment type and credits =====================

def test_enrol_type_is_matched_by_exact_membership():
    # The rule used to be `enrol_type in "C,CM,CC"`, a substring test on a
    # joined string, so a stray code like "M" counted as a credit course
    # because "M" appears inside "CM". It is now exact membership: an
    # unrecognised enrolment type earns nothing.
    result = compute([course(enrol_type="M", grade="A")], "BTE")
    assert result["ec"] == 0
    assert result["cgpa"] == 0
    assert result["creg"] == 3        # still registered, like an audit
    for real in ("C", "CM", "CC"):
        assert compute([course(enrol_type=real)], "BTE")["ec"] == 3, real


def test_credits_come_from_the_stored_course_value_not_the_ltp_string():
    # Course.credits is computed from L/T/P when the course is saved; the
    # transcript no longer re-parses the LTP string.
    result = compute([course(credits=4.5)], "BTE")
    assert result["creg"] == 4.5
    assert result["ec"] == 4.5


def test_a_course_with_no_stored_credits_raises_a_domain_error():
    # A course whose LTP could not be parsed at save time has no credits.
    from common import AcadStackException
    with pytest.raises(AcadStackException, match="Credits missing"):
        compute([course(credits=None)], "BTE")


# ============== Credit reports count by the same rule ==============

import dataclasses  # noqa: E402

from domain import credit_reports as CR  # noqa: E402
from domain import policy as POL  # noqa: E402

BASE = POL.baseline_grading_policy()
NARROW = dataclasses.replace(
    BASE, credit_enrol_types=frozenset(("C",)),
    programme_rules={name: dataclasses.replace(
        rules, earned_credit_grades=frozenset(("A", "E")))
        for name, rules in BASE.programme_rules.items()})

MIXED = [course(code=f"X{i}", enrol_type=t, grade=g)
         for i, (t, g) in enumerate([("C", "A"), ("C", "D"), ("CC", "B"),
                                     ("CM", "NP"), ("C", "E"), ("A", "A"),
                                     ("C", "S"), ("C", "F"), ("C", "I")])]


@pytest.mark.parametrize("policy", [BASE, NARROW], ids=["baseline", "narrow"])
@pytest.mark.parametrize("degree", ["BTE", "MTE", "PHD"])
def test_report_earned_credits_match_transcript_under_any_ruleset(policy,
                                                                  degree):
    rows = [dict(c, id=1, degree=degree, c_category="PC", offering_status="F")
            for c in MIXED]
    report = CR.earned_credits_by_category(rows, policy=policy)
    expected = compute(MIXED, degree, policy=policy)["ec"]
    assert sum(report.get((1, "2022-I"), {}).values()) == expected


@pytest.mark.parametrize("policy,expected", [(BASE, 24), (NARROW, 18)],
                         ids=["baseline", "narrow"])
def test_report_registered_credits_follow_credit_enrol_types(policy,
                                                             expected):
    rows = [dict(c, id=1, offering_status="F") for c in MIXED]
    assert CR.credit_enrolment_totals(rows, policy=policy) == {
        (1, "2022-I"): expected}
