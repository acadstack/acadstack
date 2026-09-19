"""Tests for the sql_statements.toml cache in common.py.

sql_by_id() is called by nearly every DB-backed route in the app, and used
to re-parse the whole ~1000-line TOML file on each call. These tests pin
both the caching and the fact that the statements it hands back are
unchanged.
"""
import os
import sys
from pathlib import Path

import pytest
import toml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import common as C  # noqa: E402

API_SERVICE_DIR = Path(__file__).resolve().parent.parent
SQL_FILE = API_SERVICE_DIR / "sql_statements.toml"


@pytest.fixture(autouse=True)
def restore_sql_cache():
    """Each test here fiddles with the module-level cache, so put the real
    file back afterwards for everything else in the session."""
    yield
    C._SQL_STATEMENTS_PATH = SQL_FILE
    C.reload_sql_statements()


def test_statements_are_identical_to_parsing_the_file_directly():
    expected = toml.load(SQL_FILE)
    assert C.sql_statements() == expected
    for sid in list(expected)[:10]:
        assert C.sql_by_id(sid) == expected[sid]


def test_the_toml_file_is_parsed_once_however_many_lookups_happen(monkeypatch):
    C.reload_sql_statements()  # cache is now warm
    calls = []
    monkeypatch.setattr(C.toml, "load",
                        lambda *a, **kw: calls.append(a) or {})
    for _ in range(50):
        C.sql_by_id("current_acad_sessions")
    assert calls == []

    # ... and exactly once from cold.
    C._sql_statements = None
    monkeypatch.setattr(C.toml, "load", lambda *a, **kw: (calls.append(a) or
                                                          {"x": "SELECT 1"}))
    for _ in range(50):
        assert C.sql_by_id("x") == "SELECT 1"
    assert len(calls) == 1


def test_an_unknown_statement_id_still_raises_key_error():
    with pytest.raises(KeyError):
        C.sql_by_id("no_such_statement_id")


def test_reload_picks_up_an_edited_file(tmp_path, monkeypatch):
    sql_file = tmp_path / "sql_statements.toml"
    sql_file.write_text('my_query = "SELECT 1"\n')
    monkeypatch.setattr(C, "_SQL_STATEMENTS_PATH", sql_file)
    C.reload_sql_statements()
    assert C.sql_by_id("my_query") == "SELECT 1"

    sql_file.write_text('my_query = "SELECT 2"\n')
    assert C.sql_by_id("my_query") == "SELECT 1"  # still cached
    C.reload_sql_statements()
    assert C.sql_by_id("my_query") == "SELECT 2"


def test_statements_load_regardless_of_the_working_directory(tmp_path,
                                                             monkeypatch):
    """Background jobs and scripts don't necessarily run from
    api_service/, which the old cwd-relative load depended on."""
    C._sql_statements = None
    monkeypatch.chdir(tmp_path)
    assert "SELECT" in C.sql_by_id("current_acad_sessions").upper()
