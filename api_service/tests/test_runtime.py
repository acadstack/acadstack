"""Tests for request plumbing: permission checks, DB connections per request, and
background tasks."""

import asyncio

from quart import current_app, session

import api_common as apiVC
import common as C
import models as M
import policy as P
import tasks_helper as TH
import validation_checks as VAL
from conftest import make_user


def _session_user(role):
    return {"id": 1, "login_id": "u", "role": role, "dept": "CSE"}


async def test_permission_checks_match_whole_names(app):
    actor = P.Actor(1, "u", "X", "CSE", frozenset({"users.view:any", "fees.view:own"}))
    assert actor.can("users.view") and actor.can("fees.view")
    assert not actor.can("users") and not actor.can("users.vie")
    assert actor.allowed("users.view")
    assert not actor.allowed("fees.view")
    assert actor.allowed("fees.view", own=lambda: True)
    assert not actor.allowed("fees.view", dept=lambda: True)


async def test_c4_course_status_check_matches_whole_codes(app, db):
    async with app.test_request_context("/"):
        session["user"] = _session_user("FAC")
        assert VAL.is_course_status_valid_for_current_user("DRA")
        assert VAL.is_course_status_valid_for_current_user("")
        assert not VAL.is_course_status_valid_for_current_user("APP")


async def test_require_checks_the_role_permissions(app, db):
    @P.require("users.find")
    def view():
        return "ran"

    async with app.test_request_context("/"):
        session["user"] = _session_user("STU")
        assert (await (await view()).get_json())["status"] == "ERROR"
        session["user"] = _session_user("DEA")
        assert await view() == "ran"


async def test_c26_request_closes_its_db_connection(client, auth):
    make_user("stu")
    await auth.login("stu")
    assert M.db.is_closed()
    res = await client.get("/acadstack/get_static_data")
    assert (await res.get_json())["status"] == "OK"
    assert M.db.is_closed()


async def test_c25_sync_background_task_has_app_context_and_db(client, auth, app):
    make_user("stu")

    def job():
        return current_app.name, M.User.select().count(), M.db.is_closed()

    async with app.test_request_context("/"):
        session["user"] = {"login_id": "stu"}
        task_id = TH.create_task(job)
        for _ in range(100):
            info = TH.get_task_info(task_id)
            if info["status"] == "done":
                break
            await asyncio.sleep(0.05)
    assert info["error"] is None
    assert info["result"] == (app.name, 1, False)


async def test_c25_expired_tasks_are_removed(client, app):
    from datetime import datetime, timedelta, timezone
    old = datetime.now(timezone.utc) - timedelta(seconds=TH.TASK_TTL_SECONDS + 1)
    async with app.test_request_context("/"):
        session["user"] = {"login_id": "stu"}
        app.extensions["tasks"] = {"old": {"status": "done", "completed_at": old},
                                   "running": {"status": "running", "completed_at": None}}
        TH.create_task(lambda: None, task_id="new")
        assert sorted(app.extensions["tasks"]) == ["new", "running"]
