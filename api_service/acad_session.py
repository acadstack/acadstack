"""Academic sessions as an ordered scale: parsing, validation, ordering.

An academic session is written ``YYYY-S``, where ``S`` is one of the
suffixes below. This module turns that string into a total order, so that
"which policy was in force for session X" is a comparison rather than a
special case per suffix.

Why this is a module of its own, with no imports
------------------------------------------------
``models.py`` needs it (the policy tables store a session ordinal and
guard writes with it) and ``models`` is imported by ``common``, so
anything this module imported from ``common`` would be a cycle. It is
deliberately dependency-free: pure string/int work, no DB, no config.

Why the order is derived from the session CODE, not from the calendar
---------------------------------------------------------------------
``AcademicCalendar`` already records a start date per session, and
ordering by that date would be the more "real" chronology. It is
nevertheless the wrong basis for effective-dated policy: an admin
correcting a calendar date years later would silently move the boundary
between two policy versions, and so change transcripts that have already
been issued. Deriving the order from the session code alone makes the
ordering a fixed property of the session, which is what immutability
needs. See ``policy_store.py``.

The suffix order
----------------
``T1 < T2 < T3 < T4 < I < II < S`` within a year. This is not invented
here: it is the order already used to sort a student's sessions before
CGPA accumulation (``domain/transcript.py``, the ``suffixes`` list).
Keeping one definition means the transcript's idea of "chronological" and
the policy store's idea of "in force from" cannot drift apart --
``tests/test_acad_session.py`` asserts the two lists are identical.

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__status__ = "Development"
"""

import re

#: Session suffixes in within-year chronological order. T1..T4 are
#: trimesters; I, II and S are the regular semesters (S = Summer).
SUFFIXES = ("T1", "T2", "T3", "T4", "I", "II", "S")

#: suffix -> rank within its year (0-based, matching SUFFIXES).
SUFFIX_RANK = {s: i for i, s in enumerate(SUFFIXES)}

#: Multiplier applied to the year when building an ordinal. Must exceed
#: the number of suffixes so that ordinals never collide across years;
#: 10 also makes the ordinal readable at a glance (2021-I -> 20214).
YEAR_SCALE = 10

# "II" must precede "I" in the alternation: Python's `re` is
# leftmost-first, not leftmost-longest, so "I|II" would match only the
# first character of "2021-II" and then fail the anchor.
SESSION_RE = re.compile(r"^(?P<year>\d{4})-(?P<suffix>T[1-4]|II|I|S)$")


class InvalidAcadSession(ValueError):
    """Raised for a string that is not a well-formed academic session."""


def parse(acad_session):
    """Splits a session string into ``(year, suffix)``.

    Raises:
        InvalidAcadSession: if the string is not ``YYYY-S`` with a known
            suffix.
    """
    if not isinstance(acad_session, str):
        raise InvalidAcadSession(
            f"Academic session must be a string, got "
            f"{type(acad_session).__name__}: {acad_session!r}")
    m = SESSION_RE.match(acad_session)
    if not m:
        raise InvalidAcadSession(
            f"Malformed academic session {acad_session!r}. Expected YYYY-S "
            f"where S is one of {', '.join(SUFFIXES)}.")
    return int(m.group("year")), m.group("suffix")


def is_valid(acad_session):
    """Whether the string is a well-formed academic session."""
    try:
        parse(acad_session)
    except InvalidAcadSession:
        return False
    return True


def ordinal(acad_session):
    """The session's position on the total order, as an int.

    ``ordinal("2021-I") == 20214``. Ordinals are comparable across years
    and suffixes, and are what the policy tables store and index.
    """
    year, suffix = parse(acad_session)
    return year * YEAR_SCALE + SUFFIX_RANK[suffix]


def from_ordinal(ord_value):
    """Inverse of :func:`ordinal`. Used for error messages and for
    reporting a version's effective range back to a caller."""
    if not isinstance(ord_value, int) or isinstance(ord_value, bool):
        raise InvalidAcadSession(
            f"Session ordinal must be an int, got {ord_value!r}")
    year, rank = divmod(ord_value, YEAR_SCALE)
    if rank >= len(SUFFIXES) or year < 0 or year > 9999:
        raise InvalidAcadSession(
            f"{ord_value} is not a valid academic session ordinal")
    return f"{year:04d}-{SUFFIXES[rank]}"


def sort_key(acad_session):
    """Key function for sorting session strings chronologically."""
    return ordinal(acad_session)


def sorted_sessions(sessions, reverse=False):
    """Session strings in chronological order."""
    return sorted(sessions, key=sort_key, reverse=reverse)
