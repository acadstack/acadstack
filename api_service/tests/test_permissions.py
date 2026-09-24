"""Tests for the permission->role mapping (permissions.py): reading it
(roles_for_permission, role_has_permission, permissions_for_role,
Actor.can), the self-lockout guard on save_permission_mapping(), and the
real-membership behaviour of is_user_in_role()/Actor.has_role() and
locked-status checks against comma-joined role/status strings.
"""
import asyncio
import sys
from pathlib import Path

import pytest
from quart import session

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import api_common as apiVC  # noqa: E402
import permissions as PERM  # noqa: E402
import settings_store as ST  # noqa: E402
from common import AcadStackException  # noqa: E402
from domain.context import Actor  # noqa: E402
import models as DB  # noqa: E402
from domain import course as CRS  # noqa: E402
from domain import workflow as WF  # noqa: E402


def run_in_request(app, fn, path="/acadstack/"):
    """Calls fn() inside a Quart request context (same helper shape as
    test_settings_store.py's), so session-backed code runs the way a
    route handler would exercise it."""
    async def _run():
        async with app.test_request_context(path):
            return fn()
    return asyncio.run(_run())


# ===================== read API =====================

def test_roles_for_permission_returns_the_seeded_default():
    assert PERM.roles_for_permission("course.save") == \
        ["ACA", "FAC", "DEA", "HOD", "RES"]


def test_role_has_permission():
    assert PERM.role_has_permission("SUP", "user.delete") is True
    assert PERM.role_has_permission("STU", "user.delete") is False


def test_permissions_for_role_lists_every_permission_that_role_holds():
    stu_perms = PERM.permissions_for_role("STU")
    assert "enrolment.request" in stu_perms
    assert "feedback.submit" in stu_perms
    assert "user.delete" not in stu_perms


def test_every_declared_permission_choice_is_a_real_role():
    import vocab_defaults as VD
    role_codes = set(VD.codes("roles"))
    for name, spec in ST.declared_groups()[PERM.GROUP].specs.items():
        for code in spec.default:
            assert code in role_codes, \
                f"permission '{name}' grants unknown role {code!r}"


# ===================== Actor.can() =====================

def test_actor_can_reflects_the_permission_mapping():
    sup = Actor(login_id="s", role="SUP", user_id=1)
    stu = Actor(login_id="t", role="STU", user_id=2)
    assert sup.can("user.delete") is True
    assert stu.can("user.delete") is False


# ===================== lockout guard =====================

def test_save_permission_mapping_rejects_a_self_lockout(db):
    sup = Actor(login_id="admin1", role="SUP", user_id=1)
    with pytest.raises(AcadStackException):
        PERM.save_permission_mapping(
            {"system.manage_permissions": ["ACA"]}, actor=sup)
    # Rejected -- the stored/effective value must be untouched.
    assert "SUP" in PERM.roles_for_permission("system.manage_permissions")


def test_save_permission_mapping_allows_a_legitimate_change(db):
    sup = Actor(login_id="admin1", role="SUP", user_id=1)
    PERM.save_permission_mapping(
        {"system.manage_permissions": ["SUP", "DEA"]}, actor=sup)
    assert PERM.roles_for_permission("system.manage_permissions") == \
        ["SUP", "DEA"]


def test_save_permission_mapping_ignores_unrelated_permissions_when_locking_out(db):
    # A save that doesn't touch system.manage_permissions at all must
    # never be blocked by the lockout guard.
    sup = Actor(login_id="admin1", role="SUP", user_id=1)
    PERM.save_permission_mapping({"user.delete": ["SUP", "ACA"]}, actor=sup)
    assert PERM.roles_for_permission("user.delete") == ["SUP", "ACA"]


# ===================== bug fixes: substring matching =====================

def test_is_user_in_role_string_form_is_not_substring_matching(app):
    # Regression for the bug where u["role"] in "DEA,ACA,RES" matched any
    # role whose code is a substring of that string.
    def _check():
        session["user"] = {"role": "RES"}
        assert apiVC.is_user_in_role("DEA,ACA,RES") is True
        assert apiVC.is_user_in_role("DEA,ACA") is False
    run_in_request(app, _check)


def test_actor_has_role_string_form_is_not_substring_matching():
    actor = Actor(login_id="x", role="RES", user_id=1)
    assert actor.has_role("DEA,ACA,RES") is True
    assert actor.has_role("DEA,ACA") is False


def test_locked_course_statuses_use_real_membership():
    # Regression for `status_old in "APP,RET"`, under which "A", "P" and
    # "RE" would each match as substrings. The lock is now the course
    # workflow's "=" rows: APP/RET need course.edit_locked_status.
    granted = Actor(login_id="a", role="ACA", user_id=1)
    denied = Actor(login_id="f", role="FAC", user_id=2)

    def can_edit(actor, status):
        course = DB.Course(status=status, author=actor.user_id, code="CS101")
        ctx = WF.Context(actor=actor, from_status=status, record=course,
                         to_status=status)
        try:
            WF.select(CRS.BASELINE, ctx)
            return True
        except WF.PermissionDenied:
            return False

    assert can_edit(granted, "APP") is True
    assert can_edit(denied, "APP") is False
    # A status that merely looks like a substring of "APP,RET" must not
    # be treated as locked.
    assert can_edit(denied, "DRA") is True
