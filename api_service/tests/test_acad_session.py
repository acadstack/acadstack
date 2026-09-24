"""Tests for acad_session.py: the timeline that effective-dated policy
resolution is built on.

Three things matter here beyond the obvious parsing checks:

* a session's ordinal is the month it STARTS, so sessions from different
  academic calendars that begin together are concurrent and share an
  ordinal. Ordering is strict within one calendar, not across them;
* chronology must have exactly one definition in the codebase, or a
  transcript could accumulate CGPA in one session order while policy
  resolved in another; and
* the Python ordinal and the SQL ordinal function
  (migrations/0001_baseline.sql) must agree, since the CHECK constraints
  use the SQL one to police what Python writes.
"""
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

def test_ordinal_is_strictly_increasing_within_one_calendar():
    """Within a single academic calendar the sessions really are
    consecutive, so the order is strict and collision-free."""
    for name in AS.SESSION_TYPES:
        sessions = [f"{y}-{s}" for y in (2020, 2021, 2022)
                    for s in AS.suffixes_for(name)]
        ords = [AS.ordinal(s) for s in sessions]
        assert ords == sorted(ords), name
        assert len(set(ords)) == len(ords), name


def test_concurrent_sessions_in_different_calendars_share_an_ordinal():
    """The whole point of the month-offset scheme. A quarter-based
    programme's T1 and a semester-based programme's I both begin the
    academic year, so policy in force that month governs both."""
    assert AS.ordinal("2021-T1") == AS.ordinal("2021-I")
    assert AS.ordinal("2021-T3") == AS.ordinal("2021-II")


def test_ordinal_is_readable_and_stable():
    # Documented shape: year * 12 + month offset into the academic year.
    # Pinned because the value is stored in a column and compared by DB
    # triggers -- changing it would silently reinterpret every stored row.
    assert AS.ordinal("2021-I") == 2021 * 12 + 0    # July
    assert AS.ordinal("2021-T1") == 2021 * 12 + 0   # July, concurrent
    assert AS.ordinal("2021-T2") == 2021 * 12 + 3   # October
    assert AS.ordinal("2021-II") == 2021 * 12 + 6   # January
    assert AS.ordinal("2021-T3") == 2021 * 12 + 6   # January, concurrent
    assert AS.ordinal("2021-T4") == 2021 * 12 + 9   # April
    assert AS.ordinal("2021-S") == 2021 * 12 + 10   # May
    assert AS.ordinal("2022-T1") == 2022 * 12 + 0


def test_year_boundary_orders_correctly():
    assert AS.ordinal("2021-S") < AS.ordinal("2022-T1")
    assert AS.ordinal("2021-S") < AS.ordinal("2022-I")
    assert AS.ordinal("2021-T4") < AS.ordinal("2022-T1")


def test_session_type_and_suffixes_for():
    assert AS.session_type("2021-I") == "semester"
    assert AS.session_type("2021-T3") == "quarter"
    assert AS.suffixes_for("semester") == ("I", "II", "S")
    assert AS.suffixes_for("quarter") == ("T1", "T2", "T3", "T4")
    with pytest.raises(AS.InvalidAcadSession):
        AS.suffixes_for("trimester")  # not declared (yet)


def test_a_change_mid_session_governs_the_next_session_not_the_running_one():
    """The rule that makes mid-session policy changes well defined: a
    session takes the ruleset in force at the month it BEGINS.

    With parallel calendars this case is unavoidable rather than exotic. A
    change effective from 2021-T2 is a clean quarter boundary, but it lands
    in the MIDDLE of semester I (which runs months 0-6). Semester I keeps
    the rules it started under; semester II picks the new ones up.
    """
    change = AS.ordinal("2021-T2")          # month 3, a quarter boundary

    # Semester I runs until semester II begins: the change lands mid-way.
    assert AS.ordinal("2021-I") < change < AS.ordinal("2021-II")

    # Semester I began before the change, so it is not governed by it.
    assert AS.ordinal("2021-I") < change
    # The next semester is.
    assert AS.ordinal("2021-II") > change
    # And for the calendar whose boundary it is, it applies immediately.
    assert AS.ordinal("2021-T2") == change


def test_sorted_sessions():
    given = ["2022-I", "2021-S", "2021-T1", "2022-T1", "2021-I"]
    # 2021-T1 and 2021-I tie on ordinal (both July 2021); the suffix
    # breaks the tie so sorting stays deterministic.
    assert AS.sorted_sessions(given) == [
        "2021-I", "2021-T1", "2021-S", "2022-I", "2022-T1"]
    assert AS.sorted_sessions(given, reverse=True) == [
        "2022-T1", "2022-I", "2021-S", "2021-T1", "2021-I"]


# ===================== Drift guards =====================

#: Modules that used to keep their own copy of session chronology.
TRANSCRIPT_SOURCE = API_SERVICE_DIR / "domain" / "transcript.py"


def test_transcript_code_keeps_no_private_session_chronology():
    """domain/transcript.py used to carry its own
    ``suffixes = ['T1','T2','T3','T4','I','II','S']`` list and sort a
    student's sessions by its index. That was a second, independent
    definition of "chronological": if it disagreed with the ordinal, a
    transcript would accumulate CGPA in one order while policy resolution
    used another, and a session could be graded under the rules of the
    session after it. Chronology now has exactly one home.
    """
    src = TRANSCRIPT_SOURCE.read_text()
    assert not re.search(r"^\s*suffixes\s*=\s*\[", src, re.MULTILINE), (
        "domain/transcript.py has grown its own suffix list again; session "
        "chronology belongs in acad_session.py only.")
    assert "AS.sorted_sessions(" in src, (
        "domain/transcript.py no longer sorts sessions via acad_session; "
        "update this guard to point at wherever chronology now comes from.")


def test_no_module_reimplements_the_suffix_order():
    """Nothing outside acad_session.py should enumerate the suffixes in
    order -- that is what SESSION_TYPES is for."""
    offenders = []
    for path in sorted(API_SERVICE_DIR.glob("**/*.py")):
        if path.name == "acad_session.py" or "tests" in path.parts:
            continue
        if re.search(r"""\[\s*['"]T1['"]\s*,\s*['"]T2['"]""",
                     path.read_text()):
            offenders.append(path.name)
    assert offenders == [], offenders


def test_sql_ordinal_function_agrees_with_python(db):
    """migrations/0001_baseline.sql reimplements ordinal() in SQL so it can
    be used in a CHECK constraint. The two implementations must not drift:
    the SQL one decides what may be stored, the Python one decides what is
    resolved."""
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
