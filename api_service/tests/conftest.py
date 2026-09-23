"""Shared pytest fixtures for the api_service backend test suite.

Test database strategy
-----------------------
These tests run against a REAL, throwaway PostgreSQL schema rather than
mocks or an in-process substitute (e.g. sqlite). A lot of this app's
business logic (RBAC ownership checks, credit totals, enrolment lookups)
lives in hand-written SQL in ``sql_statements.toml`` and is executed via
``DB.db.execute_sql(...)``. An in-process/sqlite stand-in would not
exercise that SQL (different dialect, different join/aggregate behaviour)
and would silently stop testing the riskiest part of the code. Real
Postgres, reset between tests, is the only option that keeps these tests
honest.

You need a reachable Postgres server with credentials matching
``tests/config_test.json`` (defaults: role/db "acadstack_test" on
localhost:5432, password "acadstack_test"). E.g.:

    createuser -P acadstack_test   # set password: acadstack_test
    createdb -O acadstack_test acadstack_test

The test session fixture below drops and recreates the "public" schema
once per test session (mirroring demo_data.py's recreate_db(), minus the
CREATE/DROP DATABASE step, since the db/role are provisioned up front)
and then truncates all tables before every individual test function that
asks for the ``db`` fixture (directly or via ``client``/``auth``), so
tests are isolated from one another without paying for a schema rebuild
each time.
"""
import contextvars
import json
import os
import shutil
import sys
from pathlib import Path

import pytest
from passlib.handlers.pbkdf2 import pbkdf2_sha256

API_SERVICE_DIR = Path(__file__).resolve().parent.parent

# Several modules under test load files using relative paths (
# sql_statements.toml, static_data.json, nav.json, email_templates/), so
# the working directory must be api_service/ for the whole test session,
# regardless of where `pytest` was invoked from.
os.chdir(API_SERVICE_DIR)
sys.path.insert(0, str(API_SERVICE_DIR))

TEST_CONFIG_PATH = API_SERVICE_DIR / "tests" / "config_test.json"
with open(TEST_CONFIG_PATH) as f:
    TEST_CONFIG = json.load(f)

TEST_USER_ID = 23  # test_auth.py::test_load_user hard-codes GET /app/user/23
TEST_LOGIN_ID = "test"
TEST_PASSWORD = "test123"


def _apply_env_from_test_config():
    """Populate the same env vars acadstack_app._load_config_from_env()
    reads, from tests/config_test.json, so create_app() picks up the test
    DB/email settings exactly the way it would pick up real settings in
    dev/prod (via app_env_vars.env)."""
    db_args = TEST_CONFIG["db_args"]
    email = TEST_CONFIG["email"]
    os.environ["APP_HOST"] = TEST_CONFIG.get("host", "localhost")
    os.environ["APP_PORT"] = str(TEST_CONFIG.get("port", 5300))
    os.environ["POSTGRES_DB"] = TEST_CONFIG["db_name"]
    os.environ["POSTGRES_USER"] = db_args["user"]
    os.environ["POSTGRES_PASSWORD"] = db_args["password"]
    os.environ["DB_HOST"] = db_args["host"]
    os.environ["DB_PORT"] = str(db_args["port"])
    os.environ["EMAIL_USER"] = email.get("user", "")
    os.environ["EMAIL_PASSWORD"] = email.get("password", "")
    os.environ["EMAIL_HOST"] = email.get("host", "")
    os.environ["EMAIL_PORT"] = str(email.get("port", ""))
    # Any non-empty string is truthy where this is read (see email_client.py).
    os.environ["EMAIL_DRYRUN"] = "1" if email.get("dryrun") else ""
    os.environ["UPLOAD_FOLDER"] = TEST_CONFIG.get("upload_folder", "./tests/tmp_uploads")
    # See the matching guard at the bottom of acadstack_app.py: create_app()
    # mutates a process-wide Blueprint singleton that can only be registered
    # once, so we must be the only ones calling it (via the `app` fixture
    # below), not the module's own unconditional top-level call.
    os.environ["ACADSTACK_SKIP_APP_INIT"] = "1"


_apply_env_from_test_config()

# These imports must happen after chdir/env setup above, since importing
# acadstack_app / api_common triggers module-level file reads (nav.json
# etc.) relative to cwd, and models.db is a module-level singleton that
# every other module imports a reference to.
import models as DB  # noqa: E402
from acadstack_app import create_app  # noqa: E402
from schema_migrations import run_pending_migrations  # noqa: E402


# ===================== DB schema lifecycle =====================

@pytest.fixture(scope="session")
def _db_schema():
    """Creates the schema once per test session against the real test DB."""
    db_args = TEST_CONFIG["db_args"]
    DB.db.init(TEST_CONFIG["db_name"], **db_args)
    DB.db.connect()
    DB.db.execute_sql("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    DB.create_schema()
    # Same order production uses (acadstack_app.run_startup_db_tasks,
    # demo_data.recreate_db, migrate.py): create_schema() first, then the
    # versioned migrations. Without this the test schema would be missing
    # everything peewee cannot express -- CHECK constraints, functions and
    # the triggers that enforce policy immutability -- so tests would pass
    # against a schema no deployment actually runs.
    run_pending_migrations()
    yield DB.db
    DB.db.close()


@pytest.fixture
def db(_db_schema):
    """Function-scoped: truncates all app tables before the test runs, so
    every test starts from an empty, known DB state."""
    models_to_truncate = [
        DB.User, DB.KnownFace, DB.Person, DB.Course, DB.PasswordResetKey,
        DB.CourseOffering, DB.CourseCategory, DB.UserDoc,
        DB.CourseEnrollment, DB.StudentAttendance, DB.CourseInstructor,
        DB.WorkflowNote, DB.BatchAdvisors, DB.AcademicCalendar,
        DB.FeedbackForm, DB.FeedbackQuestion, DB.CourseInstructorFeedback,
        DB.StudentFeedbackStatus, DB.StudentSupervisor, DB.CourseSlotTiming,
        DB.FeesTransaction, DB.StudentCredits, DB.DcForStudent,
        DB.DcMember, DB.PhDProgressReport, DB.AcademicMilestone,
        DB.AttendancePhoto, DB.SystemSetting,
        DB.PolicyVersion, DB.ClosedAcademicSession,
        DB.MilestoneDefinition, DB.WorkflowDefinition,
        DB.WorkflowTransition, DB.SchemaMigration,
    ]
    quoted = ", ".join(f'"{m._meta.table_name}"' for m in models_to_truncate)
    _db_schema.execute_sql(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE;")
    yield _db_schema


def seed_test_user(role="ACA", **person_kwargs):
    """Creates the 'test' user that test_auth.py logs in as, forcing its
    id to TEST_USER_ID (23) because test_load_user hard-codes
    GET /app/user/23. Self-view bypasses the STU-can-only-view-self RBAC
    check in user_view(), so this works no matter which role is passed."""
    person_defaults = dict(org_id="TESTORG0001", dept_name="CSE",
                            degree="BTE", deg_type="REG",
                            deg_type_spec="NA", current_status="REG")
    person_defaults.update(person_kwargs)
    p = DB.Person.create(**person_defaults)
    u = DB.User.create(id=TEST_USER_ID, login_id=TEST_LOGIN_ID,
                       password_hashed=pbkdf2_sha256.hash(TEST_PASSWORD),
                       email="test.user@example.com", first_name="Test",
                       last_name="User", role=role, person=p)
    # Bump the identity sequence past the id we forced, so subsequent
    # auto-assigned ids in the same test don't collide with it.
    DB.db.execute_sql(
        "SELECT setval(pg_get_serial_sequence('\"user\"', 'id'), "
        "(SELECT MAX(id) FROM \"user\"));"
    )
    return u


# ===================== Sync Quart test client =====================

class _SyncResponse:
    """Adapts a Quart Response (whose .json is an async property) so
    test code can do `res.json["..."]` synchronously, Flask-style."""

    def __init__(self, raw, json_value):
        self._raw = raw
        self.status_code = raw.status_code
        self.json = json_value

    def __getattr__(self, name):
        return getattr(self._raw, name)


class SyncQuartClient:
    """Wraps Quart's async QuartClient so plain, non-async test functions
    can call client.get(...)/post(...) and get back a Response directly,
    and can use `with client:` the way Flask's test client works -- i.e.
    quart.session stays readable via a plain `from quart import session`
    after the request completes.

    Quart's session support relies on a contextvars.ContextVar. Normally,
    asyncio.Task copies the current context on creation, so mutations a
    request makes to that ContextVar wouldn't be visible to code outside
    the coroutine. To work around that, every request this wraps runs as
    a Task pinned to the same contextvars.Context object (`self.context`,
    accumulated across calls), and after each call we replay that
    context's bindings into the ambient context via plain `var.set(...)`
    calls -- so a plain `session[...]` read in the test body right after
    `client.get(...)` sees exactly what the request set. (We can't just
    wrap the whole test call in `self.context.run(...)`: a Context can't
    be re-entered while a Task using it is already running inside that
    same `run()` call -- contextvars raises "already entered".)
    """

    def __init__(self, app):
        self.app = app
        self._client = app.test_client()
        self._loop = None
        self.context = contextvars.Context()

    def _get_loop(self):
        import asyncio
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
        return self._loop

    def _run(self, coro):
        loop = self._get_loop()
        task = loop.create_task(coro, context=self.context)
        result = loop.run_until_complete(task)
        for var, value in self.context.items():
            var.set(value)
        return result

    def __enter__(self):
        self._run(self._client.__aenter__())
        return self

    def __exit__(self, exc_type, exc, tb):
        return self._run(self._client.__aexit__(exc_type, exc, tb))

    async def _request_and_parse(self, method, *args, **kwargs):
        raw = await getattr(self._client, method)(*args, **kwargs)
        try:
            json_value = await raw.json
        except Exception:
            json_value = None
        return _SyncResponse(raw, json_value)

    def get(self, *args, **kwargs):
        return self._run(self._request_and_parse("get", *args, **kwargs))

    def post(self, *args, **kwargs):
        return self._run(self._request_and_parse("post", *args, **kwargs))

    def close(self):
        if self._loop is not None and not self._loop.is_closed():
            self._loop.close()


@pytest.fixture(scope="session")
def app(_db_schema):
    # Session-scoped: create_app() can only run once per process (see the
    # guard in acadstack_app.py). Per-test isolation instead comes from the
    # `db` fixture (truncates tables) and from `client` building a fresh
    # cookie jar per test.
    application = create_app(is_testing=True)
    yield application


@pytest.fixture
def client(app, db):
    c = SyncQuartClient(app)
    yield c
    c.close()


class AuthActions:
    def __init__(self, client):
        self.client = client

    def login(self, login_id=TEST_LOGIN_ID, password=TEST_PASSWORD):
        return self.client.post("/acadstack/login", json={
            "login_id": login_id, "password": password})

    def logout(self):
        return self.client.get("/acadstack/logout")


@pytest.fixture
def auth(client):
    seed_test_user()
    return AuthActions(client)


def create_user(role, login_id, password=TEST_PASSWORD, **person_kwargs):
    """Creates a User (+ backing Person) with the given role, for tests
    that need to log in as several different roles in one test."""
    person_defaults = dict(org_id=f"ORG-{login_id}", dept_name="CSE",
                            degree="BTE", deg_type="REG", deg_type_spec="NA",
                            current_status="REG")
    person_defaults.update(person_kwargs)
    p = DB.Person.create(**person_defaults)
    return DB.User.create(login_id=login_id,
                          password_hashed=pbkdf2_sha256.hash(password),
                          email=f"{login_id}@example.com", first_name=login_id,
                          last_name="User", role=role, person=p)


def login_as(client, login_id, password=TEST_PASSWORD):
    res = client.post("/acadstack/login", json={
        "login_id": login_id, "password": password})
    assert res.status_code == 200, res.json
    return res


@pytest.fixture(scope="session", autouse=True)
def _cleanup_upload_folder():
    yield
    upload_dir = API_SERVICE_DIR / TEST_CONFIG.get("upload_folder", "./tests/tmp_uploads")
    shutil.rmtree(upload_dir, ignore_errors=True)
