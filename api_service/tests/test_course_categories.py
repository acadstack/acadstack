"""Course-offering categorization rows: each names the degree it counts
towards, matched exactly against a student's degree."""
import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import api_course_offering as ACO  # noqa: E402
import models as DB  # noqa: E402
from common import AcadStackException  # noqa: E402


def _save(app, rows, offering_id):
    """Runs the save the way the /co_save route does, inside a request."""
    async def run():
        async with app.test_request_context("/acadstack/"):
            ACO._save_co_categorization(rows, offering_id)
    asyncio.run(run())


@pytest.fixture
def offering(db):
    course = DB.Course.create(code="CC101", title="Cats", ltp="3-0-0-0-3",
                              status="APP")
    return DB.CourseOffering.create(course=course, acad_session="2024-I",
                                    status="E", slot="A", dept_name="CSE")


def test_a_categorization_is_saved_for_a_known_degree(app, offering):
    _save(app, [{"degree": "BTE", "dept": "CSE", "category": "PC",
                 "for_entry_years": "2022"}], offering.id)
    assert [c.degree for c in offering.course_categories] == ["BTE"]


@pytest.mark.parametrize("row", [{"dept": "CSE", "category": "PC"},
                                 {"degree": "ALL", "dept": "CSE",
                                  "category": "PC"}])
def test_a_categorization_needs_a_known_degree(app, offering, row):
    with pytest.raises(AcadStackException, match="not a known degree"):
        _save(app, [row], offering.id)
    assert not offering.course_categories.exists()
