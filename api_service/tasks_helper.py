import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from quart import current_app

TASK_TTL_SECONDS = 60  # TTL for completed tasks

async def cleanup_tasks_periodically():
    while True:
        await asyncio.sleep(20)  # cleanup interval
        now = datetime.now(timezone.utc)
        to_delete = []
        for task_id, info in list(current_app.extensions['tasks'].items()):
            if info.get("status") == "done":
                completed_at = info.get("completed_at")
                if completed_at and now - completed_at > timedelta(seconds=TASK_TTL_SECONDS):
                    to_delete.append(task_id)
        for task_id in to_delete:
            current_app.extensions['tasks'].pop(task_id, None)

def start_cleanup_task():
    current_app.add_background_task(cleanup_tasks_periodically)

def get_task_info(task_id):
    """
    Returns the task info dict for the given task_id,
    or None if task_id is not found.
    """
    return current_app.extensions['tasks'].get(task_id)

def pop_task_info_if_done(task_id):
    """
    Returns the task info if found.
    If the task status is "done", removes it from the store.
    Otherwise, leaves it in place.
    Returns None if task_id not found.
    """
    task_info = current_app.extensions['tasks'].get(task_id)
    if not task_info:
        return None

    if task_info.get("status") == "done":
        return current_app.extensions['tasks'].pop(task_id)
    
    return task_info


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
    
    current_app.extensions['tasks'][task_id] = {
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
                result = await loop.run_in_executor(None, lambda: func(*args, **kwargs))

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
