"""Tests for acad_session.py: the total order on academic sessions that
effective-dated policy resolution is built on.

Two things matter here beyond the obvious parsing checks:

* the suffix order must stay identical to the one the transcript code
  already sorts by, or "chronological" would mean two different things in
  one codebase; and
* the Python ordinal and the SQL ordinal function installed by migration
  0003 must agree, since the CHECK constraints use the SQL one to police
  what Python writes.
"""
import ast
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import acad_session as AS  # noqa: E402
import models as DB  # noqa: E402

API_SERVICE_DIR = Path(__file__).resolve().parent.parent


# ===================== Parsing =====================

@pytest.mark.parametrize("sess,expected", [
    ("2021-I", (2021, "I")),
    ("2021-II", (2021, "II")),
    ("2021-S", (2021, "S")),
    ("2021-T1", (2021, "T1")),
    ("2021-T4", (2021, "T4")),
    ("1999-T2", (1999, "T2")),
])
def test_parse_accepts_every_supported_suffix(sess, expected):
    assert AS.parse(sess) == expected


@pytest.mark.parametrize("bad", [
    "", "2021", "2021-", "-I", "2021I", "21-I", "20211-I",
    "2021-III", "2021-W", "2021-M", "2021-T0", "2021-T5", "2021-t1",
    "2021-i", " 2021-I", "2021-I ", "2021-I-II", None, 2021, ("2021", "I"),
])
def test_parse_rejects_malformed_sessions(bad):
    with pytest.raises(AS.InvalidAcadSession):
        AS.parse(bad)
    assert AS.is_valid(bad) is False


def test_ii_is_not_truncated_to_i():
    """Regression guard for the alternation order in SESSION_RE: a
    leftmost-first regex with 'I' before 'II' would match only the first
    character of '2021-II'."""
    assert AS.parse("2021-II")[1] == "II"
    assert AS.ordinal("2021-II") != AS.ordinal("2021-I")


# ===================== Ordering =====================

def test_ordinal_is_strictly_increasing_across_suffixes_and_years():
    sessions = [f"{y}-{s}" for y in (2020, 2021, 2022) for s in AS.SUFFIXES]
    ords = [AS.ordinal(s) for s in sessions]
    assert ords == sorted(ords)
    assert len(set(ords)) == len(ords)


def test_ordinal_is_readable_and_stable():
    # Documented shape: year * 10 + rank. Pinned because the value is
    # stored in a column and compared by DB triggers -- changing it would
    # silently reinterpret every stored row.
    assert AS.ordinal("2021-T1") == 20210
    assert AS.ordinal("2021-I") == 20214
    assert AS.ordinal("2021-II") == 20215
    assert AS.ordinal("2021-S") == 20216
    assert AS.ordinal("2022-T1") == 20220


def test_year_boundary_orders_correctly():
    assert AS.ordinal("2021-S") < AS.ordinal("2022-T1")
    assert AS.ordinal("2021-S") < AS.ordinal("2022-I")


def test_from_ordinal_round_trips():
    for year in (1990, 2021, 2100):
        for suffix in AS.SUFFIXES:
            sess = f"{year}-{suffix}"
            assert AS.from_ordinal(AS.ordinal(sess)) == sess


@pytest.mark.parametrize("bad", [-1, 20217, 20219, True, "20214", 1.0])
def test_from_ordinal_rejects_non_ordinals(bad):
    with pytest.raises(AS.InvalidAcadSession):
        AS.from_ordinal(bad)


def test_sorted_sessions():
    given = ["2022-I", "2021-S", "2021-T1", "2022-T1", "2021-I"]
    assert AS.sorted_sessions(given) == [
        "2021-T1", "2021-I", "2021-S", "2022-T1", "2022-I"]
    assert AS.sorted_sessions(given, reverse=True) == [
        "2022-I", "2022-T1", "2021-S", "2021-I", "2021-T1"]


# ===================== Drift guards =====================

#: Where the transcript code keeps its own session chronology. Read from
#: source rather than imported, so this guard states the location
#: explicitly and fails loudly if the list moves again.
TRANSCRIPT_SUFFIX_SOURCE = API_SERVICE_DIR / "domain" / "transcript.py"


def _suffixes_used_by_transcript_code():
    """The `suffixes` list domain/transcript.py sorts a student's sessions
    by before accumulating CGPA."""
    src = TRANSCRIPT_SUFFIX_SOURCE.read_text()
    m = re.search(r"^\s*suffixes\s*=\s*(\[[^\]]*\])", src, re.MULTILINE)
    assert m, (f"{TRANSCRIPT_SUFFIX_SOURCE.name} no longer has a "
               f"`suffixes = [...]` list; update this guard to point at "
               f"wherever session chronology now lives.")
    return tuple(ast.literal_eval(m.group(1)))


def test_suffix_order_matches_the_transcript_sort_order():
    """If these ever disagree, a transcript would accumulate CGPA in one
    session order while policy resolution used another -- so the rules
    applied to a session could be the ones from the session after it."""
    assert AS.SUFFIXES == _suffixes_used_by_transcript_code()


def test_ordinal_orders_sessions_the_same_way_the_transcript_code_does():
    suffixes = list(_suffixes_used_by_transcript_code())
    sessions = [f"{y}-{s}" for y in (2019, 2020, 2021) for s in suffixes]

    legacy_key = lambda item: "{0}{1}".format(  # noqa: E731
        item[:4], suffixes.index(item[5:]))

    assert sorted(sessions, key=legacy_key) == \
        sorted(sessions, key=AS.sort_key)


def test_sql_ordinal_function_agrees_with_python(db):
    """Migration 0003 reimplements ordinal() in SQL so it can be used in a
    CHECK constraint. The two implementations must not drift: the SQL one
    decides what may be stored, the Python one decides what is resolved."""
    sessions = [f"{y}-{s}" for y in (1999, 2021, 2024) for s in AS.SUFFIXES]
    cur = db.execute_sql(
        "SELECT s, acadstack_session_ordinal(s) FROM unnest(%s::text[]) AS s",
        (sessions,))
    rows = cur.fetchall()
    assert len(rows) == len(sessions)
    for sess, sql_ord in rows:
        assert sql_ord == AS.ordinal(sess), sess


@pytest.mark.parametrize("bad", ["2021-W", "2021", "21-I", "2021-III"])
def test_sql_ordinal_function_rejects_what_python_rejects(db, bad):
    import peewee
    with pytest.raises(peewee.PeeweeException):
        db.execute_sql("SELECT acadstack_session_ordinal(%s)", (bad,))
