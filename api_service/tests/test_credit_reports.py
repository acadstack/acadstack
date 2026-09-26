"""The credit reports count by the grading policy in force for each session,
so they agree with transcripts before and after the policy is superseded."""
import dataclasses
import sys
from collections import defaultdict
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import api_reports  # noqa: E402
import models as DB  # noqa: E402
import policy_store as PS  # noqa: E402
from conftest import create_user  # noqa: E402
from domain import credit_reports as CR  # noqa: E402
from domain import policy as POL  # noqa: E402
from domain import transcript as TR  # noqa: E402

OLD, NEW = "2023-I", "2024-I"
total_credits_data = getattr(api_reports, "__get_total_credits_data")

#: Differs from the baseline in every rule the reports read: CC is no
#: longer credit, D and NP no longer earn credit, E does.
BASE = POL.baseline_grading_policy()
CHANGED = dataclasses.replace(
    BASE, credit_enrol_types=frozenset(("C", "CM")),
    programme_rules={
        name: dataclasses.replace(
            rules, earned_credit_grades=rules.earned_credit_grades
            - {"D", "NP"} | {"E"})
        for name, rules in BASE.programme_rules.items()})

# (course code, enrol_type, grade) per student, in each session.
ENROLMENTS = [("CS101", "C", "A"), ("CS102", "C", "D"), ("CS103", "CC", "B"),
              ("CS104", "C", "NP"), ("CS105", "C", "E"), ("CS106", "A", "A")]


@pytest.fixture
def students(db):
    stus = [create_user("STU", "cr_ug", degree="BTE", year_of_entry="2022"),
            create_user("STU", "cr_phd", degree="PHD", year_of_entry="2022")]
    for session in (OLD, NEW):
        for code, enrol_type, grade in ENROLMENTS:
            course, _ = DB.Course.get_or_create(
                code=code, defaults=dict(title=code, ltp="3-0-0-0-3",
                                         credits=3, status="APP"))
            offering = DB.CourseOffering.create(
                course=course, acad_session=session, status="F", slot="A",
                dept_name="CSE")
            for stu in stus:
                DB.CourseCategory.create(offering=offering, category="PC",
                                         degree=stu.person.degree,
                                         dept="CSE", for_entry_years="2022")
                DB.CourseEnrollment.create(
                    course_offering=offering, student=stu,
                    enrol_type=enrol_type, enrol_status="ENRO", grade=grade)
    return stus


def _report_ec():
    ec = defaultdict(float)
    for stu, session, cats in CR.categorized_earned_credits(
            "", "", "", "", "", 0, 9999):
        ec[(stu["login_id"], session)] += sum(cats.values())
    return dict(ec)


def _transcript_ec(students):
    ec = defaultdict(float)
    for stu in students:
        perf = TR.courses_perf(stu, False)
        for split in perf["enrollments"].values():
            for session, data in split["enrollments"].items():
                if data["ec"]:
                    ec[(stu.login_id, session)] += data["ec"]
    return dict(ec)


def _supersede_from_new():
    PS.supersede(POL.GRADING, "2000-T1", POL.grading_payload_from(BASE))
    PS.supersede(POL.GRADING, NEW, POL.grading_payload_from(CHANGED))
    PS.invalidate_cache()


def test_categorized_credits_agree_with_transcripts(students):
    assert _report_ec() == _transcript_ec(students) == {
        # A, D, CC-B, NP for UG; PhD earns only A and B.
        ("cr_ug", OLD): 12, ("cr_ug", NEW): 12,
        ("cr_phd", OLD): 6, ("cr_phd", NEW): 6}


def test_categorized_credits_follow_a_superseded_policy(students):
    _supersede_from_new()
    assert _report_ec() == _transcript_ec(students) == {
        # OLD keeps the baseline; NEW earns A and E only (CC is audit-like).
        ("cr_ug", OLD): 12, ("cr_ug", NEW): 6,
        ("cr_phd", OLD): 6, ("cr_phd", NEW): 6}


def test_categorized_credits_filter_by_category_and_range(students):
    rows = CR.categorized_earned_credits("", "BTE", "", OLD, "PC", 0, 9999)
    assert [(s["login_id"], sess, cats) for s, sess, cats in rows] == [
        ("cr_ug", OLD, {"PC": 12})]
    assert CR.categorized_earned_credits("", "", "", OLD, "SC", 0, 9999) == []
    assert CR.categorized_earned_credits("", "", "", OLD, "", 7, 9999)[0][0][
        "login_id"] == "cr_ug"


def _credits_earned(session):
    return {d["entry_no"]: d["credits"] for d in total_credits_data(
        {"acad_session": session, "degree": "", "dept_name": "",
         "entry_year": ""})}


def test_credits_earned_counts_credit_enrolment_types_per_session(students):
    # Every enrolment but the audit, whatever the grade.
    assert _credits_earned(OLD) == _credits_earned(NEW) == {
        "ORG-cr_ug": CR.round_credits(15), "ORG-cr_phd": CR.round_credits(15)}
    _supersede_from_new()
    assert _credits_earned(OLD)["ORG-cr_ug"] == CR.round_credits(15)
    assert _credits_earned(NEW)["ORG-cr_ug"] == CR.round_credits(12)
