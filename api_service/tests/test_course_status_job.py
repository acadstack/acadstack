"""The scheduled move of course offerings from Enrolling to Running (on the
start of classes) and from Running to Completed (after the last day of grade
submission), driven by the academic calendar."""

from datetime import date, timedelta

import pytest

import api_course_offering as CO
import models as M
from conftest import make_offering

SESSION = "2026-I"


def set_event(code, days_from_today):
    M.AcademicCalendar.create(
        acad_session=SESSION, event_code=code,
        event_value=(date.today() + timedelta(days=days_from_today)).isoformat())


def status_after_job(co):
    CO.schedule_course_status()
    M.db.connect(reuse_if_open=True)
    return M.CourseOffering.get_by_id(co.id).status


# A date later this year, or earlier, must not be mistaken for the 1st of January
@pytest.mark.parametrize("days, expected", [(30, "R"), (0, "R"), (-1, "F"), (-300, "F")])
def test_running_offering_completes_the_day_after_grade_submission_ends(db, days, expected):
    co = make_offering(acad_session=SESSION, status="R")
    set_event("GRADE_SUB_E", days)
    assert status_after_job(co) == expected


@pytest.mark.parametrize("days, expected", [(30, "E"), (1, "E"), (0, "R"), (-1, "R")])
def test_enrolling_offering_starts_running_when_classes_start(db, days, expected):
    co = make_offering(acad_session=SESSION, status="E")
    set_event("CLASSES_S", days)
    assert status_after_job(co) == expected


def test_offering_of_a_session_without_the_event_is_left_alone(db):
    co = make_offering(acad_session=SESSION, status="R")
    assert status_after_job(co) == "R"
