"""Tests for nav.json + api_common.init_navbar_items() now that they key
off permissions (permissions.py) instead of raw role-list strings.

Every nav.json entry used to carry a "roles" string like "ACA,DEA,SUP",
"-STU,-PLA" (negation) or "-PLA,*" (wildcard + negation), matched with
substring containment. Phase 8 pre-resolves each entry's role set into a
named "permission" key, seeded to reproduce the old substring-matched
visibility exactly -- these tests pin that per-role equivalence for a
representative slice of entries, including the negation/wildcard forms
and the one pre-existing bug that got preserved rather than silently
fixed (see permissions.py's "nav.view_attendance" doc).
"""
import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import api_common as apiVC  # noqa: E402


@pytest.fixture
def hrefs_for(app):
    def _run(role_code, degree=None):
        async def _call():
            async with app.test_request_context("/acadstack/"):
                nav = apiVC.init_navbar_items(role_code, degree)
                out = set()
                for items in nav["menus"].values():
                    out.update(i["href"] for i in items)
                out.update(i["href"] for i in nav["links"])
                return out
        return asyncio.run(_call())
    return _run


def test_wildcard_entry_is_visible_to_every_role(hrefs_for):
    # "Academic Events" was roles="*".
    for role in ["STU", "ACA", "FAC", "HOD", "DEA", "SUP", "GUE", "PLA", "ADV", "RES"]:
        assert "#/add.dates" in hrefs_for(role, degree="BTE")


def test_negation_with_wildcard_excludes_only_the_negated_roles(hrefs_for):
    # "Courses Offered For Enrolment" was roles="-PLA,*".
    assert "#/co.find" in hrefs_for("STU", degree="BTE")
    assert "#/co.find" in hrefs_for("ACA")
    assert "#/co.find" not in hrefs_for("PLA")


def test_student_only_entries_are_hidden_from_everyone_else(hrefs_for):
    # "Student Record" was roles="STU".
    assert "#/std.detail" in hrefs_for("STU", degree="BTE")
    for role in ["ACA", "FAC", "HOD", "DEA", "SUP", "GUE", "PLA", "ADV", "RES"]:
        assert "#/std.detail" not in hrefs_for(role)


def test_exact_role_list_entry_matches_only_those_roles(hrefs_for):
    # "Mark Attendance" was roles=["ACA", "FAC"] (dc.mark_attendance).
    assert "#/att.mark" in hrefs_for("ACA")
    assert "#/att.mark" in hrefs_for("FAC")
    assert "#/att.mark" not in hrefs_for("HOD")
    assert "#/att.mark" not in hrefs_for("SUP")


def test_phd_menu_still_hidden_from_non_phd_students(hrefs_for):
    # Unrelated to the permission conversion -- init_navbar_items' own
    # STU/degree special case, left untouched -- pinned here since it
    # sits right next to the code this phase rewrote.
    assert "#/dc.form" not in hrefs_for("STU", degree="BTE")


def test_view_attendance_preserved_pre_existing_bug(hrefs_for):
    # roles was "-STU,-PLA" with no trailing "*", so under the OLD
    # substring-containment check no role code was ever a substring of
    # that literal string -- nobody could ever see this link. Preserved
    # exactly rather than silently granted to the evidently-intended
    # ALL_BUT_STU_PLA set; see permissions.py's "nav.view_attendance" doc.
    for role in ["STU", "ACA", "FAC", "HOD", "DEA", "SUP", "GUE", "PLA", "ADV", "RES"]:
        assert "#/att.find" not in hrefs_for(role)
