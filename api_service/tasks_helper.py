import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from quart import current_app, session
from common import AcadStackException
from models import db

# How long a completed task's outcome is kept; its owner fetches the outcome
# (e.g. downloads the bulk grade sheets) by its task id until then.
TASK_TTL_SECONDS = 3600

def _remove_expired_tasks():
    """Drops tasks completed more than TASK_TTL_SECONDS ago."""
    now = datetime.now(timezone.utc)
    for task_id, info in list(current_app.extensions['tasks'].items()):
        completed_at = info.get("completed_at")
        if completed_at and now - completed_at > timedelta(seconds=TASK_TTL_SECONDS):
            current_app.extensions['tasks'].pop(task_id, None)

def get_task_info(task_id):
    """
    Returns the task info dict for the given task_id,
    or None if task_id is not found.
    """
    return current_app.extensions['tasks'].get(task_id)

def get_own_task_info(task_id):
    """
    Returns the task info for the given task_id if the task was created by
    the logged-in user, else None.
    """
    task_info = get_task_info(task_id)
    if task_info and task_info.get("owner") == session.get("user", {}).get("login_id"):
        return task_info
    return None


def own_task_status(task_id):
    """The status ("running" or "done"), result and error of a task of the
    logged-in user, for showing to them; None if there is no such task."""
    task_info = get_own_task_info(task_id)
    if not task_info:
        return None
    if task_info["status"] != "done":
        return {"status": task_info["status"], "result": "Job not done yet.", "error": None}
    return {k: task_info[k] for k in ("status", "result", "error")}


def create_task(func, *args, task_id=None, **kwargs):
    """
    Schedule a sync or async function `func` with args in background.
    Returns a unique task_id.
    If `task_id` is provided, uses that instead of generating a new one.
    """
    if task_id is None:
        task_id = str(uuid.uuid4())

    if "tasks" not in current_app.extensions:
        current_app.extensions["tasks"] = {}
    _remove_expired_tasks()

    current_app.extensions['tasks'][task_id] = {
        "owner": session["user"]["login_id"],
        "status": "running",
        "result": None,
        "completed_at": None,
        "error": None,
    }

    def run_sync():
        # A worker thread gets its own DB connection, closed when done.
        with db.connection_context():
            return func(*args, **kwargs)

    async def task_wrapper():
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                # to_thread copies the context, so the app context is available.
                result = await asyncio.to_thread(run_sync)

            current_app.extensions['tasks'][task_id].update({
                "status": "done",
                "result": result,
                "completed_at": datetime.now(timezone.utc),
                "error": None,
            })
        except Exception as e:
            logging.exception(f"Background task {task_id} failed.")
            current_app.extensions['tasks'][task_id].update({
                "status": "done",
                "result": None,
                "completed_at": datetime.now(timezone.utc),
                "error": str(e) if isinstance(e, AcadStackException) else "Task failed.",
            })

    current_app.add_background_task(task_wrapper)

    return task_id
