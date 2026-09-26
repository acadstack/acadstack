"""Tests for the DB connection lifecycle (common.py).

peewee keeps connection state per thread. Async handlers all run on the
event-loop thread and share its one long-lived connection; sync code on
executor/scheduler threads checks a connection out and returns it. In
these tests the event loop runs on the main thread, so DB.db.connection()
here is the handlers' connection.
"""
import asyncio
import sys
import threading
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import common as C  # noqa: E402
import models as DB  # noqa: E402
from conftest import TEST_CONFIG, TEST_PASSWORD, create_user  # noqa: E402


def _terminate_backend(pid):
    """Closes a connection from the server side, as a DB restart would."""
    conn = psycopg2.connect(dbname=TEST_CONFIG["db_name"],
                            **TEST_CONFIG["db_args"])
    conn.autocommit = True
    try:
        conn.cursor().execute("SELECT pg_terminate_backend(%s)", [pid])
    finally:
        conn.close()


async def _logged_in_client(app):
    create_user("ACA", "conn.user")
    client = app.test_client()
    res = await client.post("/acadstack/login", json={
        "login_id": "conn.user", "password": TEST_PASSWORD})
    assert res.status_code == 200
    return client


async def _static_data_ok(client):
    """A request that queries the DB on every call."""
    res = await client.get("/acadstack/get_static_data")
    return '"AcadEventCodes"' in await res.get_data(as_text=True)


def test_concurrent_requests_use_one_pooled_connection(app, db):
    async def run():
        client = await _logged_in_client(app)
        peak = 0
        done = False

        async def sample():
            nonlocal peak
            while not done:
                peak = max(peak, len(DB.db._in_use))
                await asyncio.sleep(0.002)

        sampler = asyncio.ensure_future(sample())
        reqs = [client.get("/acadstack/current_user") if i % 2 else
                client.get("/acadstack/get_static_data") for i in range(60)]
        results = await asyncio.gather(*reqs)
        done = True
        await sampler
        assert all(r.status_code == 200 for r in results)
        return peak, len(DB.db._in_use)

    peak, after = asyncio.run(run())
    assert peak == 1
    assert after == 1


def test_a_connection_dropped_by_the_server_is_replaced(app, db):
    async def run():
        client = await _logged_in_client(app)
        assert await _static_data_ok(client)
        _terminate_backend(DB.db.connection().get_backend_pid())
        # The request that finds the connection dead fails; the next one
        # gets a fresh connection instead of failing until a restart.
        await _static_data_ok(client)
        return [await _static_data_ok(client) for _ in range(3)]

    assert asyncio.run(run()) == [True, True, True]


def test_a_connection_dropped_mid_transaction_is_replaced(app, db):
    async def run():
        client = await _logged_in_client(app)
        try:
            with DB.db.atomic():
                DB.db.execute_sql("SELECT 1")
                _terminate_backend(DB.db.connection().get_backend_pid())
                DB.db.execute_sql("SELECT 1")
        except Exception:
            pass
        return [await _static_data_ok(client) for _ in range(2)]

    assert asyncio.run(run()) == [True, True]
    assert not DB.db.in_transaction()


def test_a_thread_connection_is_returned_even_if_its_transaction_fails(db):
    in_use_before = len(DB.db._in_use)
    errors = []

    def job():
        with DB.db.atomic():
            DB.db.execute_sql("SELECT 1")
            raise RuntimeError("job failed")

    def run():
        try:
            C.run_with_thread_db_connection(job)
        except RuntimeError as ex:
            errors.append(ex)

    t = threading.Thread(target=run)
    t.start()
    t.join()
    assert len(errors) == 1
    assert len(DB.db._in_use) == in_use_before


def test_a_sync_view_releases_its_thread_connection(db):
    in_use_before = len(DB.db._in_use)

    @C.releases_thread_db_connection
    def view():
        return DB.db.execute_sql("SELECT 1").fetchone()[0]

    results = []
    t = threading.Thread(target=lambda: results.append(view()))
    t.start()
    t.join()
    assert results == [1]
    assert len(DB.db._in_use) == in_use_before
