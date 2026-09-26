"""The grades_status_pending report query: a running offering is listed
while any enrolment still lacks a final grade."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import common as C  # noqa: E402
import models as DB  # noqa: E402
from conftest import create_user  # noqa: E402

SESSION = "2024-I"


def _pending_codes():
    cursor = DB.db.execute_sql(C.sql_by_id("grades_status_pending"), [SESSION])
    return [row[0] for row in cursor.fetchall()]


@pytest.mark.parametrize("grade,pending", [("NA", True), ("A", False),
                                           ("I", False), ("W", False)])
def test_only_offerings_with_ungraded_enrolments_are_pending(db, grade, pending):
    course = DB.Course.create(code="GS101", title="Grades", ltp="3-0-0-0-3",
                              status="APP")
    offering = DB.CourseOffering.create(course=course, acad_session=SESSION,
                                        status="R", slot="A", dept_name="CSE")
    DB.CourseInstructor.create(offering=offering,
                               instructor=create_user("FAC", "gs_fac"),
                               is_coordinator=True)
    DB.CourseEnrollment.create(course_offering=offering,
                               student=create_user("STU", "gs_stu"),
                               enrol_type="C", enrol_status="ENRO", grade=grade)
    assert (_pending_codes() == ["GS101"]) is pending
