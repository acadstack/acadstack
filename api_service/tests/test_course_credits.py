"""Tests for the institution's credit formula (S = 2L - T + 0.5P,
C = L + 0.5P): common.compute_course_ltp() is the ONLY place it runs.
Course.s_hours/credits (models.py) store the result, computed server-side
whenever a course is created or edited (api_course.py course_save/
bulk_add_courses, demo_data.py), and every SQL site reads those columns
instead of re-deriving them from ltp.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import common as C  # noqa: E402
import models as DB  # noqa: E402
from schema_migrations import run_pending_migrations  # noqa: E402


# ===================== common.compute_course_ltp =====================

def test_compute_course_ltp_matches_the_institution_formula():
    ltpsc, s, c = C.compute_course_ltp("3-1-2")
    assert (s, c) == (6.0, 4.0)  # S = 2*3-1+0.5*2 = 6, C = 3+0.5*2 = 4
    assert ltpsc == "3-1-2-6.0-4.0"


def test_compute_course_ltp_ignores_and_overwrites_a_stale_suffix():
    # This exact input is the demo_data.py "HS102" row: its hand-typed
    # suffix (3-6) does not match what the formula gives for L=2,T=3,P=2
    # (2-3) -- the input is trusted only for its L/T/P prefix.
    ltpsc, s, c = C.compute_course_ltp("2-3-2-3-6")
    assert (s, c) == (2.0, 3.0)
    assert ltpsc == "2-3-2-2.0-3.0"


def test_compute_course_ltp_returns_none_for_unparseable_input():
    assert C.compute_course_ltp("") is None
    assert C.compute_course_ltp(None) is None
    assert C.compute_course_ltp("3-1") is None  # fewer than 3 fields
    assert C.compute_course_ltp("x-y-z") is None  # not numbers


def test_apply_computed_course_credits_sets_ltp_s_hours_and_credits():
    course = DB.Course(ltp="3-1-2")
    C.apply_computed_course_credits(course)
    assert course.ltp == "3-1-2-6.0-4.0"
    assert course.s_hours == 6.0
    assert course.credits == 4.0


def test_apply_computed_course_credits_is_a_noop_for_bad_ltp():
    course = DB.Course(ltp=None)
    C.apply_computed_course_credits(course)
    assert course.ltp is None
    assert course.s_hours is None
    assert course.credits is None


# ===================== course_save (HTTP) =====================

def test_course_save_recomputes_credits_server_side_on_create(client, auth):
    auth.login()
    # The client sends a bogus S/C suffix (as if its own JS math were
    # wrong, or it were tampered with); the server must not trust it.
    res = client.post("/acadstack/cour_save", json={
        "code": "CRTEST1", "title": "Credit Test Course",
        "ltp": "3-1-2-999-999",
    })
    assert res.json["status"] == "OK", res.json
    body = res.json["body"]
    assert body["ltp"] == "3-1-2-6.0-4.0"
    assert body["s_hours"] == 6.0
    assert body["credits"] == 4.0

    row = DB.Course.get(DB.Course.code == "CRTEST1")
    assert row.s_hours == 6.0
    assert row.credits == 4.0


def test_course_save_recomputes_credits_server_side_on_edit(client, auth):
    auth.login()
    created = client.post("/acadstack/cour_save", json={
        "code": "CRTEST2", "title": "Credit Test Course", "ltp": "2-0-0",
        "status": "DRA",
    }).json["body"]
    assert created["credits"] == 2.0  # L=2,T=0,P=0 -> C = 2 + 0 = 2

    edited = client.post("/acadstack/cour_save", json={
        "id": created["id"], "code": "CRTEST2", "title": "Credit Test Course",
        "status": "DRA", "ltp": "4-0-0-1-1",  # client again sends wrong S/C
        "author": {"id": created["author"]["id"]},
    }).json["body"]
    assert edited["ltp"] == "4-0-0-8.0-4.0"
    assert edited["s_hours"] == 8.0
    assert edited["credits"] == 4.0


# ===================== migration 0002 backfill =====================

def test_migration_0002_backfills_existing_courses_from_ltp(db):
    # Simulates a pre-migration row: ltp set (with a stale suffix, like
    # the real demo_data.py rows had), s_hours/credits still NULL --
    # i.e. exactly what an upgrading (not fresh) deployment has before
    # this migration runs.
    DB.Course.create(code="MIGTEST1", title="Migration Test", status="APP",
                     ltp="2-3-2-3-6")

    applied = run_pending_migrations()
    assert "0002_add_course_credit_columns.sql" in applied

    row = DB.Course.get(DB.Course.code == "MIGTEST1")
    assert row.s_hours == 2.0
    assert row.credits == 3.0


def test_migration_0002_leaves_unparseable_ltp_null(db):
    DB.Course.create(code="MIGTEST2", title="Migration Test 2", status="APP",
                     ltp=None)

    run_pending_migrations()

    row = DB.Course.get(DB.Course.code == "MIGTEST2")
    assert row.s_hours is None
    assert row.credits is None
