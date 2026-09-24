"""Tests for the api_common.py helpers touched by the hard-coded-policy
audit: academic_session_valid/__next_acad_session (now delegating to
acad_session.py instead of a private succession map), entry_years_valid/
roll_number_valid (now configurable year bounds instead of a hard-coded
"20xx"), and domain.course.course_code_for_pg (configurable PG threshold
digit instead of a hard-coded 5).
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import api_common as apiVC  # noqa: E402
import settings_store as ST  # noqa: E402
from domain import course as CRS  # noqa: E402


# ===================== academic_session_valid =====================

def test_academic_session_valid_accepts_every_declared_suffix(db):
    for suffix in ("I", "II", "S", "T1", "T2", "T3", "T4"):
        assert apiVC.academic_session_valid(f"2021-{suffix}")


def test_academic_session_valid_rejects_malformed_input(db):
    assert not apiVC.academic_session_valid("2021-")
    assert not apiVC.academic_session_valid("2021")
    assert not apiVC.academic_session_valid("2021-X9")
    assert not apiVC.academic_session_valid(None)


def test_academic_session_valid_no_longer_assumes_the_21st_century(db):
    # acad_session.py's SESSION_RE has no century restriction; the old
    # "20\\d{2}" regex here would have rejected this.
    assert apiVC.academic_session_valid("2199-I")


# ===================== __next_acad_session (via module attribute) =====================

# Module-level dunder names are not class-mangled, just excluded from
# `import *`; this is the same function static_data_dict() calls.
_next_session = apiVC.__dict__["__next_acad_session"]


def test_next_acad_session_walks_the_semester_calendar():
    assert _next_session("2020-I") == "2020-II"
    assert _next_session("2020-II") == "2020-S"
    assert _next_session("2020-S") == "2021-I"


def test_next_acad_session_walks_the_quarter_calendar():
    assert _next_session("2020-T1") == "2020-T2"
    assert _next_session("2020-T4") == "2021-T1"


# ===================== entry_years_valid / roll_number_valid =====================

def test_entry_years_valid_uses_the_configured_bounds_by_default(db):
    assert apiVC.entry_years_valid("2021,2022")
    assert not apiVC.entry_years_valid("1999")
    assert not apiVC.entry_years_valid("2100")


def test_entry_years_valid_respects_a_narrowed_configured_range(db):
    ST.save_settings({"app.min_academic_year": 2020, "app.max_academic_year": 2025})
    assert apiVC.entry_years_valid("2021")
    assert not apiVC.entry_years_valid("2019")


def test_roll_number_valid_uses_the_configured_bounds_by_default(db):
    assert apiVC.roll_number_valid("2021CSB1234")
    assert not apiVC.roll_number_valid("1999CSB1234")


def test_roll_number_valid_respects_a_narrowed_configured_range(db):
    ST.save_settings({"app.min_academic_year": 2020, "app.max_academic_year": 2025})
    assert apiVC.roll_number_valid("2021CSB1234")
    assert not apiVC.roll_number_valid("2030CSB1234")


# ===================== course_code_for_pg =====================

def test_course_code_for_pg_uses_the_default_threshold(db):
    assert CRS.course_code_for_pg("CS504")
    assert not CRS.course_code_for_pg("CS404")


def test_course_code_for_pg_respects_a_configured_threshold(db):
    ST.save_settings({"course.pg_course_min_leading_digit": 7})
    assert not CRS.course_code_for_pg("CS504")  # was PG under the old default
    assert CRS.course_code_for_pg("CS704")
