"""Pytest fixtures for the API tests.

The tests run against a real Postgres, because much of the logic is raw SQL
in ``sql_statements.toml``. That SQL names tables as ``public.<table>``, so the
suite needs a database of its own: connection settings come from
``tests/config_test.json``, and each run drops and recreates the ``public``
schema of that database. Every test starts with empty tables.

Local setup (once):
    createuser acadstack_test
    createdb -O acadstack_test acadstack_test
The database name must end with ``_test``; the fixtures refuse anything else.

Run from ``api_service/``:  ``pytest``
"""

import json
import os
from concurrent.futures import wait
from datetime import date, timedelta

import psycopg2 as pg
import pytest

import common as C
import migrate
import models as M
import settings
from acadstack_app import create_app

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_PASSWORD = "test"


def _load_test_config():
    with open(os.path.join(TESTS_DIR, "config_test.json")) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def app():
    cfg = _load_test_config()
    # The schema is dropped below, so refuse to run against a non-test database.
    assert cfg["db_name"].endswith("_test"), "Test database name must end with _test"

    with pg.connect(dbname=cfg["db_name"], **cfg["db_args"]) as conn:
        conn.cursor().execute("DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public")
    conn.close()

    myapp = create_app(is_testing=True)
    myapp.config.update(cfg)
    myapp.config["TESTING"] = True

    M.db.init(cfg["db_name"], **cfg["db_args"])
    migrate.migrate()
    yield myapp
    M.db.close_all()


@pytest.fixture
def db(app):
    """The model database bound to the test schema, with all tables but the
    default list entries empty."""
    # The default list entries come from the baseline migration; keep them.
    tables = ", ".join(f'"{m._meta.table_name}"' for m in M.BaseModel.__subclasses__()
                       if m is not M.VocabItem)
    M.db.connect(reuse_if_open=True)
    M.db.execute_sql(f'TRUNCATE {tables} RESTART IDENTITY CASCADE')
    settings._cache.clear()
    yield M.db
    M.db.close()


@pytest.fixture
async def client(app, db, tmp_path):
    app.config["upload_folder"] = str(tmp_path)
    async with app.test_app() as test_app:
        yield test_app.test_client()
    # Emails are sent (dry-run) on a thread pool; let them finish inside the test.
    wait(C.emailer.pending_tasks)


def make_user(login_id="test", role="STU", password=TEST_PASSWORD, **person_fields):
    """Creates a user with a linked person record and returns the user."""
    person = M.Person.create(org_id=person_fields.pop("org_id", login_id.upper()),
                             dept_name=person_fields.pop("dept_name", "CSE"),
                             **person_fields)
    return M.User.create(login_id=login_id, role=role,
                         password_hashed=C.hash_password(password),
                         email=f"{login_id}@example.com",
                         first_name=login_id.capitalize(), last_name="User",
                         person=person)


class AuthActions:
    def __init__(self, client):
        self._client = client

    async def login(self, login_id="test", password=TEST_PASSWORD):
        return await self._client.post("/acadstack/login",
                                       json={"login_id": login_id, "password": password})

    async def logout(self):
        return await self._client.get("/acadstack/logout")


@pytest.fixture
def auth(client):
    return AuthActions(client)


def make_offering(code="CS101", ltp="3-0-2-7-4", acad_session="2026-I", status="E",
                  instructor=None, is_coordinator=True, **fields):
    """Creates a course and an offering of it, optionally with one instructor."""
    course = M.Course.create(code=code, title=f"{code} title", ltp=ltp, status="APP")
    co = M.CourseOffering.create(course=course, acad_session=acad_session,
                                 status=status, **fields)
    if instructor:
        M.CourseInstructor.create(offering=co, instructor=instructor,
                                  is_coordinator=is_coordinator)
    return co


def enrol(student, co, enrol_type="C", enrol_status="ENRO", grade="NA"):
    return M.CourseEnrollment.create(student=student, course_offering=co,
                                     enrol_type=enrol_type,
                                     enrol_status=enrol_status, grade=grade)


def set_event_window(acad_session, event, open_=True):
    """Adds the ``<event>_S``/``<event>_E`` calendar rows for a session, as a
    window around today when ``open_``, else as a window that ended yesterday."""
    today = date.today()
    start, end = ((today - timedelta(days=5), today + timedelta(days=5)) if open_
                  else (today - timedelta(days=10), today - timedelta(days=1)))
    for suffix, dt in (("S", start), ("E", end)):
        M.AcademicCalendar.create(acad_session=acad_session,
                                  event_code=f"{event}_{suffix}",
                                  event_value=dt.isoformat())


async def json_of(res):
    return await res.get_json()
