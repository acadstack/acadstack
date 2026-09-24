"""Tests for the central error handlers registered in
acadstack_app.create_app(), which replaced the per-route
try/except AcadStackException/Exception boilerplate that used to be
repeated in (almost) every api_*.py route handler.

These exercise the two paths through a single representative route
(GET /acadstack/get_static_data) rather than duplicating the same
assertions once per route: every route now shares the exact same
errorhandler code, so the interesting behaviour lives there, not in any
individual handler.
"""
import logging

import api_common as apiVC
import common as C


def test_domain_exception_message_passes_through(client, auth, monkeypatch):
    def boom():
        raise C.AcadStackException("You do not have any static data today!")
    monkeypatch.setattr(apiVC, "static_data_dict", boom)

    with client:
        auth.login()
        res = client.get("/acadstack/get_static_data")

    assert res.status_code == 200
    assert res.json == {"status": "ERROR",
                        "body": "You do not have any static data today!"}


def test_unexpected_exception_gives_generic_message_and_is_logged(
        client, auth, monkeypatch, caplog):
    def boom():
        raise ValueError('relation "internal_table" does not exist')
    monkeypatch.setattr(apiVC, "static_data_dict", boom)

    with client:
        auth.login()
        with caplog.at_level(logging.ERROR):
            res = client.get("/acadstack/get_static_data")

    assert res.status_code == 200
    assert res.json["status"] == "ERROR"
    # The client must never see the raw exception text.
    assert "internal_table" not in res.json["body"]
    assert "unexpected error" in res.json["body"].lower()
    # But it must still be logged, with the original exception attached.
    assert any(rec.exc_info and "internal_table" in str(rec.exc_info[1])
               for rec in caplog.records)
