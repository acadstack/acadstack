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

def test_grading_policy_can_be_supplied_by_the_caller():
    # An institution where a "C" earns no credit and a "D" is worth 1
    # point: no DB, no settings rows, just a different policy object.
    strict = POL.GradingPolicy(
        grade_points={"A": 10, "C": 4, "D": 1},
        ug_ec_grades="A",
        pg_ec_grades="A",
        pass_grades="A",
        phd_ec_grades="A",
        phd_ec_pass_grades="A",
        phd_ec_grades_amended="A",
        phd_ec_pass_grades_amended="A",
    )
    courses = [{"acad_session": "2022-I", "ltp": "3-1-0-5-3",
                "enrol_type": "C", "enrol_status": "ENRO", "grade": "C",
                "code": "CS101"}]

    assert TR.compute_cgpa_sgpa_ec(courses, "BTE", policy=strict) == {
        "sgpa": 4.0, "ec": 0, "s_ec": 0, "creg": 3, "cgpa": 0, "pts_cgpa": 0}

    # Same courses under the shipped default: C earns credit and 6 points.
    default = TR.compute_cgpa_sgpa_ec(courses, "BTE")
    assert default["ec"] == 3 and default["sgpa"] == 6.0


def test_phd_amendment_year_is_policy_not_a_literal():
    # Move the amendment to 2030 and the 2022 session behaves like a
    # pre-amendment one (C- stops earning credit).
    shifted = dataclasses.replace(POL.DEFAULT_GRADING_POLICY,
                                  phd_amendment_year=2030)
    courses = [{"acad_session": "2022-I", "ltp": "3-1-0-5-3",
                "enrol_type": "C", "enrol_status": "ENRO", "grade": "C-",
                "code": "CS101"}]

    assert TR.compute_cgpa_sgpa_ec(courses, "PHD")["ec"] == 3
    assert TR.compute_cgpa_sgpa_ec(courses, "PHD", policy=shifted)["ec"] == 0


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
