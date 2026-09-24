"""Tests for dates_save (api_wflow.py): now rejects an academic-calendar
event code outside vocab.acad_event_codes instead of silently storing it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conftest import create_user, login_as  # noqa: E402

import models as DB  # noqa: E402


def test_dates_save_accepts_known_event_codes(client):
    create_user("ACA", "aca1")
    login_as(client, "aca1")
    res = client.post("/acadstack/dates_save", json={
        "session": "2021-I",
        "eventDates": {"SESSION_S": "2021-07-01", "SESSION_E": "2021-11-30"}
    })
    assert res.status_code == 200
    assert res.json["status"] == "OK"
    assert DB.AcademicCalendar.select().where(
        (DB.AcademicCalendar.acad_session == "2021-I") &
        (DB.AcademicCalendar.event_code == "SESSION_S")).exists()


def test_dates_save_rejects_an_unknown_event_code(client):
    create_user("ACA", "aca2")
    login_as(client, "aca2")
    res = client.post("/acadstack/dates_save", json={
        "session": "2021-I",
        "eventDates": {"NOT_A_REAL_EVENT": "2021-07-01"}
    })
    assert res.json["status"] == "ERROR"
    assert "NOT_A_REAL_EVENT" in res.json["body"]
    assert not DB.AcademicCalendar.select().where(
        DB.AcademicCalendar.event_code == "NOT_A_REAL_EVENT").exists()
