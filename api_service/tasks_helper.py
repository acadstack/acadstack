import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from quart import current_app

import common as C

TASK_TTL_SECONDS = 60  # TTL for completed tasks
CLEANUP_INTERVAL_SECONDS = 20


def purge_expired_tasks(tasks: dict, now=None) -> list:
    """Removes finished tasks whose result has been kept past
    TASK_TTL_SECONDS, whether or not anyone collected it. Returns the
    removed task ids."""
    now = now or datetime.now(timezone.utc)
    expired = [task_id for task_id, info in list(tasks.items())
               if info.get("status") == "done" and info.get("completed_at")
               and now - info["completed_at"] > timedelta(seconds=TASK_TTL_SECONDS)]
    for task_id in expired:
        tasks.pop(task_id, None)
    return expired


async def cleanup_tasks_periodically():
    """Purges expired tasks every CLEANUP_INTERVAL_SECONDS until the app
    shuts down."""
    shutdown = current_app.shutdown_event
    while not shutdown.is_set():
        try:
            await asyncio.wait_for(shutdown.wait(), CLEANUP_INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            purge_expired_tasks(current_app.extensions.get('tasks', {}))


async def start_cleanup_task():
    """Starts the purge loop; register with before_serving. Async so Quart
    runs it on the event loop, not an executor thread with no loop."""
    current_app.add_background_task(cleanup_tasks_periodically)


def get_task_info(task_id):
    """
    Returns the task info dict for the given task_id,
    or None if task_id is not found.
    """
    return current_app.extensions['tasks'].get(task_id)

def pop_task_info_if_done(task_id, owner=None):
    """
    Returns the task info if found.
    If the task status is "done", removes it from the store.
    Otherwise, leaves it in place.
    Returns None if task_id is not found, or if ``owner`` is given and
    the task was submitted by someone else.
    """
    task_info = current_app.extensions.get('tasks', {}).get(task_id)
    if not task_info:
        return None
    if owner is not None and task_info.get("owner") != owner:
        return None

    if task_info.get("status") == "done":
        return current_app.extensions['tasks'].pop(task_id)
    
    return task_info


def create_task(func, *args, task_id=None, owner=None, **kwargs):
    """
    Schedule a sync or async function `func` with args in background.
    A sync `func` runs on an executor thread with no app or request
    context, so it must take any config/session values as arguments.
    Returns a unique task_id.
    If `task_id` is provided, uses that instead of generating a new one.
    `owner` (a login id) restricts who may read the task's status/result.
    """
    if task_id is None:
        task_id = str(uuid.uuid4())

    if "tasks" not in current_app.extensions:
        current_app.extensions["tasks"] = {}
    
    current_app.extensions['tasks'][task_id] = {
        "owner": owner,
        "status": "running",
        "result": None,
        "completed_at": None,
        "error": None,
    }

    async def task_wrapper():
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, lambda: C.run_with_thread_db_connection(func, *args, **kwargs))

            current_app.extensions['tasks'][task_id].update({
                "status": "done",
                "result": result,
                "completed_at": datetime.now(timezone.utc),
                "error": None,
            })
        except Exception as e:
            current_app.extensions['tasks'][task_id].update({
                "status": "done",
                "result": None,
                "completed_at": datetime.now(timezone.utc),
                "error": str(e),
            })

    current_app.add_background_task(task_wrapper)

    return task_id
