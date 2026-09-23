"""Tests for the extracted enrolment domain layer.

The point of these is what they DON'T need: no Quart app, no test
client, no session, and -- for the state machine and the policy
injection -- no database either. That was impossible before the
extraction, when the same logic sat inside an async view function that
read quart.session.

The behaviour itself is already pinned end-to-end by
test_enrolment_state_machine.py (via real HTTP requests); these tests
pin the seams the extraction created.
"""
import ast
import dataclasses
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from domain import plugins  # noqa: E402
from domain import policy as POL  # noqa: E402
from domain import transcript as TR  # noqa: E402
from domain.context import Actor  # noqa: E402
from domain.enrolment import default_next_enrol_status  # noqa: E402
from domain.errors import PermissionDenied  # noqa: E402


def actor(role, user_id=1, login_id="tester"):
    return Actor(login_id=login_id, role=role, user_id=user_id)


INSTRUCTOR = [True, False]
ADVISOR = [False, True]
BOTH = [True, True]
NEITHER = [False, False]


# ===================== state machine, with no I/O at all =====================

@pytest.mark.parametrize("role", ["ACA", "DEA"])
@pytest.mark.parametrize("action,expected", [("approve", "ENRO"),
                                              ("reject", "ASREJ")])
def test_academic_section_decides_regardless_of_ownership(role, action, expected):
    assert default_next_enrol_status(actor(role), NEITHER, "IPEN",
                                     action) == expected


@pytest.mark.parametrize("ownership,current,action,expected", [
    (INSTRUCTOR, "IPEN", "approve", "APEN"),
    (INSTRUCTOR, "IPEN", "reject", "IREJ"),
    (ADVISOR, "IPEN", "approve", "ENRO"),   # skips instructor approval
    (ADVISOR, "APEN", "reject", "AREJ"),
    (BOTH, "IPEN", "approve", "APEN"),
    (BOTH, "IPEN", "reject", "AREJ"),
    (BOTH, "APEN", "approve", "ENRO"),
    (BOTH, "APEN", "reject", "AREJ"),
])
def test_faculty_transitions(ownership, current, action, expected):
    assert default_next_enrol_status(actor("FAC"), ownership, current,
                                     action) == expected


@pytest.mark.parametrize("action,expected", [("approve", "ENRO"),
                                              ("reject", "AREJ")])
def test_hod_can_act_on_advisor_pending_without_owning_anything(action, expected):
    assert default_next_enrol_status(actor("HOD"), NEITHER, "APEN",
                                     action) == expected


def test_hod_cannot_act_on_instructor_pending():
    with pytest.raises(PermissionDenied, match="privileges"):
        default_next_enrol_status(actor("HOD"), NEITHER, "IPEN", "approve")


def test_uninvolved_faculty_is_denied():
    with pytest.raises(PermissionDenied, match="privileges"):
        default_next_enrol_status(actor("FAC"), NEITHER, "IPEN", "approve")


def test_unexpected_role_is_denied():
    with pytest.raises(PermissionDenied, match="Unexpected user role"):
        default_next_enrol_status(actor("STU"), NEITHER, "IPEN", "approve")


def test_anything_other_than_approve_is_a_rejection():
    # The handler only ever distinguishes "approve" from everything
    # else; this is relied on by the frontend, which posts "reject".
    assert default_next_enrol_status(actor("ACA"), NEITHER, "IPEN",
                                     "anything else") == "ASREJ"


def test_system_actor_holds_no_role():
    assert Actor.system().has_role(["ACA", "DEA"]) is False
    with pytest.raises(PermissionDenied):
        default_next_enrol_status(Actor.system(), BOTH, "IPEN", "approve")


# ===================== policy arrives as data =====================

def _rules(grade_points, ec, cgpa):
    return POL.ProgrammeRules(grade_points=grade_points,
                              earned_credit_grades=frozenset(ec),
                              cgpa_grades=frozenset(cgpa))


def test_grading_policy_can_be_supplied_by_the_caller():
    # An institution where a "C" earns no credit and a "D" is worth 1
    # point: no DB, no settings rows, no stored policy -- just a different
    # ruleset object.
    points = {"A": 10, "C": 4, "D": 1}
    strict = POL.GradingPolicy(
        grade_points=points,
        degree_classes={"BTE": "UG"},
        default_degree_class="UG",
        programme_rules={"UG": _rules(points, ["A"], ["A"])},
    )
    courses = [{"acad_session": "2022-I", "ltp": "3-1-0-5-3",
                "enrol_type": "C", "enrol_status": "ENRO", "grade": "C",
                "code": "CS101"}]

    assert TR.compute_cgpa_sgpa_ec(courses, "BTE", policy=strict) == {
        "sgpa": 4.0, "ec": 0, "s_ec": 0, "creg": 3, "cgpa": 0, "pts_cgpa": 0}

    # Same courses under the shipped default: C earns credit and 6 points.
    default = TR.compute_cgpa_sgpa_ec(courses, "BTE")
    assert default["ec"] == 3 and default["sgpa"] == 6.0


def test_an_unlisted_degree_takes_the_default_programme_class():
    """The UG/PG/PhD split used to be `if degree == "BTE" ... elif degree
    == "PHD"`, with everything else falling through to PG. It is now a
    lookup, so an institution's own degree codes are configuration."""
    default = POL.DEFAULT_GRADING_POLICY
    assert default.class_for("BTE") == "UG"
    assert default.class_for("PHD") == "PHD"
    # Unlisted codes take the default class, which preserves the old
    # fall-through. BMD (B.Tech-M.Tech Dual) is one of them: it classified
    # as PG while "BTE" was hardcoded, and still does.
    assert default.class_for("MTE") == "PG"
    assert default.class_for("BMD") == "PG"
    assert default.class_for("NEW_PROGRAMME_2030") == "PG"


def test_a_degree_can_be_reclassified_without_touching_the_computation():
    """The point of making the classification configurable: moving BMD to
    UG is a ruleset change, not a code change."""
    default = POL.DEFAULT_GRADING_POLICY
    moved = dataclasses.replace(
        default, degree_classes={**default.degree_classes, "BMD": "UG"})

    # "NP" earns credit for UG but not for PG -- so the reclassification
    # is observable in the credit total, with no other change.
    courses = [{"acad_session": "2022-I", "ltp": "3-1-0-5-3",
                "enrol_type": "C", "enrol_status": "ENRO", "grade": "NP",
                "code": "CS101"}]
    assert TR.compute_cgpa_sgpa_ec(courses, "BMD", policy=default)["ec"] == 0
    assert TR.compute_cgpa_sgpa_ec(courses, "BMD", policy=moved)["ec"] == 3


def test_the_phd_grade_rules_are_policy_not_a_literal():
    """These used to be `if academic_session_year > 2021` inside the
    computation loop, then a `phd_amendment_year` field, then a table keyed
    per academic calendar. They are now just one programme's rules, so an
    institution states different ones by supplying a ruleset -- with no
    year arithmetic anywhere.
    """
    courses = [{"acad_session": "2022-I", "ltp": "3-1-0-5-3",
                "enrol_type": "C", "enrol_status": "ENRO", "grade": "C-",
                "code": "CS101"}]

    # Under the shipped rules a PhD "C-" earns credit and counts for CGPA.
    shipped = TR.compute_cgpa_sgpa_ec(courses, "PHD")
    assert shipped["ec"] == 3 and shipped["pts_cgpa"] > 0

    # An institution that does not recognise C- for a research degree says
    # so in its ruleset. Same session, same course, same code path.
    default = POL.DEFAULT_GRADING_POLICY
    stricter = dataclasses.replace(default, programme_rules={
        **default.programme_rules,
        "PHD": _rules(default.grade_points,
                      ["A", "A-", "B", "B-", "C"],
                      ["A", "A-", "B", "B-", "C"])})
    strict = TR.compute_cgpa_sgpa_ec(courses, "PHD", policy=stricter)
    assert strict["ec"] == 0 and strict["pts_cgpa"] == 0


def _code_constants(module):
    """Every literal in a module's actual CODE, with docstrings excluded.

    Scanning raw text would match the prose in the docstrings, which
    legitimately quotes the branch this guard is about.
    """
    tree = ast.parse(Path(module.__file__).read_text())
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            body = getattr(node, "body", None)
            if body and isinstance(body[0], ast.Expr) \
                    and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                docstrings.add(id(body[0].value))
    return [n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and id(n) not in docstrings]


def _code_names(module):
    tree = ast.parse(Path(module.__file__).read_text())
    return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | \
        {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)} | \
        {n.name for n in ast.walk(tree)
         if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def test_no_module_branches_on_an_academic_year():
    """A structural guard: the grade rules are data, so neither module does
    arithmetic on an academic year or names the old amendment helper."""
    assert "DEFAULT_GRADING_POLICY" in _code_names(POL)
    assert 2021 not in _code_constants(POL), (
        "domain/policy.py has a literal 2021 in its code; the PhD revision "
        "is supposed to be effective-dated data, not a branch on a year.")
    for banned in ("apply_phd_amendment", "phd_amendment_year",
                   "phd_amendment_first_sem", "phd_amendment_later_sems"):
        assert banned not in _code_names(POL), banned

    assert 2021 not in _code_constants(TR)


def test_the_computation_hardcodes_no_degree_code():
    """`if degree == "BTE"` / `elif degree == "PHD"` used to select the
    grade rules. Degree classification is configuration now, so no degree
    code appears in the computation at all."""
    constants = _code_constants(TR)
    for banned in ("BTE", "PHD", "MTE", "BMD"):
        assert banned not in constants, (
            f"domain/transcript.py still mentions the degree code {banned!r}; "
            f"classification comes off the ruleset now.")
    # ...nor the grade-set literals it used to carry.
    assert not [c for c in constants
                if isinstance(c, str) and "," in c and "A-" in c], \
        "domain/transcript.py still carries a comma-joined grade set"


# ===================== the plugin seam =====================

@pytest.fixture
def clean_registry():
    yield
    plugins.clear_overrides()


def test_core_registers_a_default_for_every_declared_point():
    assert plugins.implementation(plugins.ENROLMENT_NEXT_STATUS) is \
        default_next_enrol_status
    assert plugins.implementation(plugins.ENROLMENT_NOTIFY) is not None


def test_override_replaces_the_default_and_can_be_dropped(clean_registry):
    @plugins.override(plugins.ENROLMENT_NEXT_STATUS)
    def two_step_advisor(actor, ownership, current_status, action):
        return "APEN"

    assert plugins.is_overridden(plugins.ENROLMENT_NEXT_STATUS)
    assert plugins.call(plugins.ENROLMENT_NEXT_STATUS, actor("ACA"),
                        NEITHER, "IPEN", "approve") == "APEN"

    plugins.clear_overrides()
    assert not plugins.is_overridden(plugins.ENROLMENT_NEXT_STATUS)
    assert plugins.call(plugins.ENROLMENT_NEXT_STATUS, actor("ACA"),
                        NEITHER, "IPEN", "approve") == "ENRO"


def test_unknown_extension_point_is_an_error_not_a_silent_no_op():
    with pytest.raises(LookupError):
        plugins.call("enrolment.no_such_point")


def test_registered_reports_what_is_installed(clean_registry):
    @plugins.override(plugins.ENROLMENT_NOTIFY)
    def quiet(enrolment_id, old_record=None):
        return None

    entry = plugins.registered()[plugins.ENROLMENT_NOTIFY]
    assert entry["default"] == "default_notify_status_change"
    assert entry["override"].endswith("quiet")
