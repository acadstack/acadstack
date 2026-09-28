"""Tests for request plumbing: role checks, DB connections per request, and
background tasks."""

import asyncio

from quart import current_app, session

import api_common as apiVC
import common as C
import models as M
import tasks_helper as TH
import validation_checks as VAL
from conftest import make_user


async def test_c4_role_checks_match_whole_codes(app):
    async with app.test_request_context("/"):
        session["user"] = {"role": "CA"}
        assert not apiVC.is_user_in_role("ACA,DEA")
        assert not apiVC.is_user_in_role("ACA")
        session["user"] = {"role": "DEA"}
        assert apiVC.is_user_in_role("ACA,DEA")
        assert apiVC.is_user_in_role(["ACA", "DEA"])


async def test_c4_course_status_check_matches_whole_codes(app):
    async with app.test_request_context("/"):
        session["user"] = {"role": "FAC"}
        assert VAL.is_course_status_valid_for_current_user("DRA")
        assert VAL.is_course_status_valid_for_current_user("")
        assert not VAL.is_course_status_valid_for_current_user("APP")


async def test_c4_rbac_roles_string_matches_whole_codes(app):
    @C.rbac(roles="ACA,DEA")
    def view():
        return "ran"

    async with app.test_request_context("/"):
        session["user"] = {"role": "CA"}
        assert (await (await view()).get_json())["status"] == "ERROR"
        session["user"] = {"role": "DEA"}
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
