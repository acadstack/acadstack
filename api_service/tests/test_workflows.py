"""Unit tests for the approval workflow functions. No database needed."""

import pytest

import policy as P
import workflows as WF
from common import AcadStackException


def actor(*perms):
    return P.Actor(1, "u", "X", "CSE", frozenset(perms))


# ---- enrolment approval ----

ACA = actor("enrolments.edit:any", "enrolments.approve:any")
FAC = actor("enrolments.approve:own")
HOD = actor("enrolments.approve:own", "enrolments.approve:any")


@pytest.mark.parametrize("who,status,action,instr,adv,expected", [
    (ACA, "IPEN", "approve", False, False, "ENRO"),
    (ACA, "APEN", "reject", False, False, "ASREJ"),
    (FAC, "IPEN", "approve", True, False, "APEN"),
    (FAC, "IPEN", "reject", True, False, "IREJ"),
    (FAC, "APEN", "approve", False, True, "ENRO"),
    (FAC, "APEN", "reject", False, True, "AREJ"),
    (FAC, "IPEN", "approve", False, True, "ENRO"),   # C11: advisor skips the instructor step
    (FAC, "IPEN", "approve", True, True, "APEN"),
    (FAC, "APEN", "approve", True, True, "ENRO"),
    (FAC, "IPEN", "reject", True, True, "AREJ"),
    (HOD, "APEN", "approve", False, False, "ENRO"),
    (HOD, "APEN", "reject", False, False, "AREJ"),
])
def test_enrolment_next_status(who, status, action, instr, adv, expected):
    assert WF.enrolment_next_status(who, status, action, instr, adv) == expected


@pytest.mark.parametrize("who,status,instr,adv", [
    (FAC, "IPEN", False, False),   # unrelated faculty
    (HOD, "IPEN", False, False),   # HoD cannot take the instructor's step
    (FAC, "ENRO", True, True),     # both roles, nothing pending
    (actor(), "APEN", True, True),  # related but without the permission
])
def test_enrolment_refused(who, status, instr, adv):
    with pytest.raises(AcadStackException, match="privileges"):
        WF.enrolment_next_status(who, status, "approve", instr, adv)


# ---- DC approval ----

SUP = actor("dc.edit:own")
DEPT = actor("dc.edit:dept")
DEAN = actor("dc.edit:any")


@pytest.mark.parametrize("who,old,new", [
    (SUP, None, "DRA"), (SUP, None, "SUB"), (SUP, "DRA", "DRA"), (SUP, "DRA", "SUB"),
    (SUP, "RTS", "SUB"), (SUP, "RTS", "RTS"), (SUP, "DRA", "DEL"),
    (DEPT, "SUB", "FTD"), (DEPT, "SUB", "RTS"), (DEPT, "RTH", "FTD"), (DEPT, "SUB", "SUB"),
    (DEAN, "FTD", "APP"), (DEAN, "FTD", "RTH"), (DEAN, "APP", "DEL"), (DEAN, "DRA", "APP"),
])
def test_dc_allowed(who, old, new):
    assert WF.dc_next_status(who, old, new) == new


@pytest.mark.parametrize("who,old,new", [
    (SUP, "DRA", "APP"), (SUP, "DRA", "FTD"), (SUP, None, "APP"), (SUP, "RTS", "RTH"),
    (DEPT, "SUB", "APP"), (DEPT, "SUB", "RTH"),
])
def test_dc_transition_refused(who, old, new):
    with pytest.raises(AcadStackException, match="Cannot change the DC status"):
        WF.dc_next_status(who, old, new)


@pytest.mark.parametrize("who,old", [(SUP, "SUB"), (SUP, "APP"), (DEPT, "FTD"),
                                     (DEPT, "DRA"), (DEPT, "APP")])
def test_dc_status_not_editable_by_scope(who, old):
    with pytest.raises(AcadStackException, match="Insufficient privileges"):
        WF.dc_next_status(who, old, old)


# ---- PhD progress report ----

MEMBER = actor("ppr.edit:own")
ACAD = actor("ppr.edit:any")


@pytest.mark.parametrize("who,old,new,chair", [
    (MEMBER, "DRA", "SUB", False), (MEMBER, "DRA", "DRA", False),
    (MEMBER, "SUB", "APP", True), (ACAD, "APP", "DRA", False), (ACAD, "SUB", "APP", True),
])
def test_ppr_allowed(who, old, new, chair):
    assert WF.ppr_next_status(who, old, new, chair) == new


@pytest.mark.parametrize("old,new", [("SUB", "DRA"), ("DRA", "APP"), ("APP", "DRA")])
def test_ppr_member_transition_refused(old, new):
    with pytest.raises(AcadStackException, match="Cannot change the report status"):
        WF.ppr_next_status(MEMBER, old, new, True)


@pytest.mark.parametrize("who", [MEMBER, ACAD])
def test_only_chair_approves_report(who):
    with pytest.raises(AcadStackException, match="Only DC chair"):
        WF.ppr_next_status(who, "SUB", "APP", False)
