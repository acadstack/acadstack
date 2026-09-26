"""Tests for tasks_helper.py: purging finished background jobs, the
periodic cleanup loop, and the DB connection a sync job runs with.
"""
import asyncio
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import api_grades  # noqa: E402
import models as DB  # noqa: E402
import tasks_helper as TH  # noqa: E402
from common import AcadStackException  # noqa: E402
from domain.context import Actor  # noqa: E402


def _done(seconds_ago):
    return {"status": "done",
            "completed_at": datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)}


def test_purge_removes_only_expired_finished_tasks():
    tasks = {
        "old": _done(TH.TASK_TTL_SECONDS + 5),
        "recent": _done(1),
        "running": {"status": "running", "completed_at": None},
    }
    assert TH.purge_expired_tasks(tasks) == ["old"]
    assert set(tasks) == {"recent", "running"}


def test_start_cleanup_task_runs_the_loop_until_shutdown(app, monkeypatch):
    monkeypatch.setattr(TH, "CLEANUP_INTERVAL_SECONDS", 0.01)
    # Restored afterwards; the real event is created inside the loop below.
    monkeypatch.setattr(app, "shutdown_event", None, raising=False)
    tasks = {"old": _done(TH.TASK_TTL_SECONDS + 5)}
    monkeypatch.setitem(app.extensions, "tasks", tasks)

    async def run():
        app.shutdown_event = asyncio.Event()
        async with app.app_context():
            # Through Quart's own wrapper, as before_serving calls it.
            await app.ensure_async(TH.start_cleanup_task)()
        started = set(app.background_tasks)
        assert started, "cleanup loop was not scheduled"
        for _ in range(100):
            if not tasks:
                break
            await asyncio.sleep(0.01)
        app.shutdown_event.set()
        await asyncio.wait_for(asyncio.gather(*started), timeout=1)

    asyncio.run(run())
    assert tasks == {}
    assert not app.background_tasks


def test_a_sync_job_returns_its_db_connection_to_the_pool(db):
    in_use_before = len(DB.db._in_use)
    results = []

    def job():
        return DB.db.execute_sql("SELECT 1").fetchone()[0]

    t = threading.Thread(
        target=lambda: results.append(TH._run_with_db_connection(job)))
    t.start()
    t.join()
    assert results == [1]
    assert len(DB.db._in_use) == in_use_before


def test_grade_sheet_data_runs_outside_a_request_with_an_explicit_actor(db):
    """The bulk grade-sheet job calls this on an executor thread, where
    there is no session to read the acting user from."""
    errors = []

    def job():
        try:
            api_grades._get_semester_grade_data(
                "NO-SUCH-ENTRY", "2024-I", "C",
                actor=Actor(login_id="acad", role="ACA"))
        except Exception as ex:
            errors.append(ex)
        finally:
            DB.db.close()

    t = threading.Thread(target=job)
    t.start()
    t.join()
    assert len(errors) == 1
    assert isinstance(errors[0], AcadStackException)
    assert "not found" in str(errors[0])
