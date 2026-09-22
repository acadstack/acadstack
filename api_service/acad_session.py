"""Academic sessions as an ordered scale: parsing, validation, ordering.

An academic session is written ``YYYY-S``, where ``S`` is a suffix
belonging to one of the declared session types below. This module turns
that string into a position on a shared timeline, so that "which policy
was in force for session X" is a comparison rather than a special case
per suffix.

Why this is a module of its own, with no imports
------------------------------------------------
``models.py`` needs it (the policy tables store a session ordinal and
guard writes with it) and ``models`` is imported by ``common``, so
anything this module imported from ``common`` would be a cycle. It is
deliberately dependency-free: pure string/int work, no DB, no config.

Session types run in parallel, not in sequence
----------------------------------------------
An institution may run more than one academic calendar at once: a
semester-based B.Tech alongside a quarter-based programme, for instance.
Those calendars are **concurrent**, not consecutive. ``2021-T1`` and
``2021-I`` both begin the academic year; neither follows the other.

So a session's position is its **month offset into the academic year**,
declared per session type in :data:`SESSION_TYPES`, and its ordinal is
``year * 12 + offset``. Two sessions that begin in the same month get
**equal ordinals**, which is the correct answer to "which ruleset was in
force" -- policy in force in that month governs both.

This replaces an earlier scheme that ranked every suffix on one arbitrary
within-year order (``T1 < T2 < T3 < T4 < I < II < S``). That order was a
fiction: it placed ``2021-T1`` four ranks before ``2021-I`` though they
start together, which made a policy change landing partway through the
year look like it oscillated between tracks. Migration 0004 recomputes
the stored ordinals.

A session is governed by the policy in force at its START
--------------------------------------------------------
Because sessions span several months while the timeline is monthly, a
policy change can take effect *during* a session -- and with parallel
calendars it usually does, since a boundary in one track falls mid-session
in another. The rule is that a session takes the ruleset in force at the
month it begins. A change effective from month 6 of 2021 therefore governs
``2021-II`` and ``2021-T3`` (both begin at month 6) but not ``2021-T2``,
which began at month 3 and is already under way. That is also the right
academic answer: you do not restate the rules under which a student is
already being graded.

Why the order is derived from the session CODE, not from the calendar
---------------------------------------------------------------------
``AcademicCalendar`` already records a start date per session, and
ordering by that date would be the more "real" chronology. It is
nevertheless the wrong basis for effective-dated policy: an admin
correcting a calendar date years later would silently move the boundary
between two policy versions, and so change transcripts that have already
been issued. Deriving the order from the session code plus the fixed
table below makes the ordering a property of the session itself, which is
what immutability needs. See ``policy_store.py``.

:data:`SESSION_TYPES` is APPEND-ONLY
------------------------------------
Ordinals are stored in indexed columns and policed by a CHECK constraint.
Adding a session type, or a suffix to an existing one, is safe. Changing
the offset of a suffix already in use is not: it would silently move every
policy boundary around that suffix and reinterpret stored rows. Add a new
suffix instead.

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__status__ = "Development"
"""

import re

#: Calendar month the academic year starts in (July). Used only to map a
#: session onto a real month for display; ordering never consults it.
ACAD_YEAR_START_MONTH = 7

#: Months in a year, and therefore the multiplier between consecutive
#: academic years on the ordinal scale.
MONTHS_PER_YEAR = 12

#: The academic calendars this institution runs, each mapping its session
#: suffixes to the month they begin, counted from the start of the
#: academic year (0 = July). Declaration order is the tie-break used when
#: two types share an offset.
#:
#: APPEND-ONLY -- see the module docstring.
SESSION_TYPES = {
    # Semesters: I from July, II from January, Summer from May.
    "semester": {"I": 0, "II": 6, "S": 10},
    # Quarters: an even four-way split of the same year.
    "quarter": {"T1": 0, "T2": 3, "T3": 6, "T4": 9},
}

#: suffix -> month offset into the academic year.
SUFFIX_OFFSET = {suffix: offset
                 for offsets in SESSION_TYPES.values()
                 for suffix, offset in offsets.items()}

#: suffix -> the session type that declares it.
SUFFIX_TYPE = {suffix: name
               for name, offsets in SESSION_TYPES.items()
               for suffix in offsets}

#: Index of each session type in declaration order, for stable tie-breaks
#: between concurrent suffixes.
_TYPE_ORDER = {name: i for i, name in enumerate(SESSION_TYPES)}


def _suffix_sort_key(suffix):
    return (SUFFIX_OFFSET[suffix], _TYPE_ORDER[SUFFIX_TYPE[suffix]], suffix)


#: Every valid suffix, ordered by when it starts.
#:
#: NOTE this is not a rank list, and its index means nothing: concurrent
#: suffixes from different types sit next to each other here (``I`` and
#: ``T1`` both start at offset 0). Use :func:`ordinal` to compare
#: sessions, and :func:`suffixes_for` for one type's own sequence.
SUFFIXES = tuple(sorted(SUFFIX_OFFSET, key=_suffix_sort_key))

# Longest-first alternation: Python's `re` is leftmost-first, not
# leftmost-longest, so "I|II" would match only the first character of
# "2021-II" and then fail the anchor.
_SUFFIX_ALTERNATION = "|".join(
    sorted((re.escape(s) for s in SUFFIX_OFFSET), key=len, reverse=True))

SESSION_RE = re.compile(rf"^(?P<year>\d{{4}})-(?P<suffix>{_SUFFIX_ALTERNATION})$")


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


def session_type(acad_session):
    """Which declared academic calendar this session belongs to, e.g.
    ``"semester"`` or ``"quarter"``."""
    return SUFFIX_TYPE[parse(acad_session)[1]]


def suffixes_for(name):
    """One session type's suffixes, in the order they run within a year.

    Unlike :data:`SUFFIXES` this *is* a sequence: within a single calendar
    the sessions are consecutive.
    """
    if name not in SESSION_TYPES:
        raise InvalidAcadSession(
            f"Unknown session type {name!r}. Declared types: "
            f"{', '.join(SESSION_TYPES)}.")
    return tuple(sorted(SESSION_TYPES[name], key=_suffix_sort_key))


def month_offset(acad_session):
    """Months from the start of the academic year to this session's start."""
    return SUFFIX_OFFSET[parse(acad_session)[1]]


def ordinal(acad_session):
    """The session's start, as a month count on a shared timeline.

    ``ordinal("2021-I") == 2021 * 12 == 24252``, and ``ordinal("2021-T1")``
    is the same number: both begin the academic year. Ordinals are
    comparable across years AND across session types, and are what the
    policy tables store and index.
    """
    year, suffix = parse(acad_session)
    return year * MONTHS_PER_YEAR + SUFFIX_OFFSET[suffix]


def span(acad_session):
    """``(start_ordinal, end_ordinal)`` for a session, end exclusive.

    A session runs until the next one in its OWN calendar begins (the last
    one runs to the end of the academic year). This is what makes "the
    change landed mid-session" a statement you can check rather than a
    guess.
    """
    year, suffix = parse(acad_session)
    own = suffixes_for(SUFFIX_TYPE[suffix])
    start = SUFFIX_OFFSET[suffix]
    later = [SUFFIX_OFFSET[s] for s in own if SUFFIX_OFFSET[s] > start]
    end = min(later) if later else MONTHS_PER_YEAR
    base = year * MONTHS_PER_YEAR
    return base + start, base + end


def calendar_month(acad_session):
    """``(calendar_year, calendar_month)`` this session begins in.

    Display only -- ordering never uses it. An academic year labelled
    ``2021`` starts in :data:`ACAD_YEAR_START_MONTH` of calendar 2021, so
    sessions past December fall in the following calendar year.
    """
    year, suffix = parse(acad_session)
    month0 = (ACAD_YEAR_START_MONTH - 1) + SUFFIX_OFFSET[suffix]
    return year + month0 // MONTHS_PER_YEAR, month0 % MONTHS_PER_YEAR + 1


def sessions_at_ordinal(ord_value):
    """Every session sharing this ordinal, i.e. starting in that month.

    More than one means concurrent sessions in different calendars, which
    is normal. Empty means no declared session starts in that month.
    """
    if not isinstance(ord_value, int) or isinstance(ord_value, bool):
        raise InvalidAcadSession(
            f"Session ordinal must be an int, got {ord_value!r}")
    year, offset = divmod(ord_value, MONTHS_PER_YEAR)
    if year < 0 or year > 9999:
        raise InvalidAcadSession(
            f"{ord_value} is not a valid academic session ordinal")
    return tuple(f"{year:04d}-{s}" for s in SUFFIXES
                 if SUFFIX_OFFSET[s] == offset)


def from_ordinal(ord_value, session_type=None):
    """Inverse of :func:`ordinal`, within one calendar.

    ``session_type`` is required whenever more than one calendar starts a
    session in that month, because there is then no single right answer.
    Use :func:`sessions_at_ordinal` to get all of them, or
    :func:`label_for_ordinal` for a message.

    Raises:
        InvalidAcadSession: if the ordinal names no session, or names
            several and no session type was given to choose between them.
    """
    candidates = sessions_at_ordinal(ord_value)
    if session_type is not None:
        suffixes = suffixes_for(session_type)
        candidates = tuple(c for c in candidates
                           if c.split("-", 1)[1] in suffixes)
    if not candidates:
        raise InvalidAcadSession(
            f"{ord_value} is not a valid academic session ordinal"
            + (f" for session type {session_type!r}" if session_type else ""))
    if len(candidates) > 1:
        raise InvalidAcadSession(
            f"Ordinal {ord_value} is shared by concurrent sessions "
            f"{', '.join(candidates)}. Pass session_type= to choose one, or "
            f"use sessions_at_ordinal().")
    return candidates[0]


def label_for_ordinal(ord_value):
    """A human-readable name for a point on the timeline, for messages.

    Names every session starting there, so a seal line that covers two
    concurrent sessions says so instead of silently picking one.
    """
    at = sessions_at_ordinal(ord_value)
    if not at:
        year, offset = divmod(ord_value, MONTHS_PER_YEAR)
        return f"{year:04d} month {offset}"
    return " / ".join(at)


def sort_key(acad_session):
    """Key function for sorting session strings chronologically.

    Concurrent sessions tie on ordinal, so the suffix breaks the tie to
    keep sorting deterministic.
    """
    year, suffix = parse(acad_session)
    return (year * MONTHS_PER_YEAR + SUFFIX_OFFSET[suffix],
            _suffix_sort_key(suffix))


def sorted_sessions(sessions, reverse=False):
    """Session strings in chronological order."""
    return sorted(sessions, key=sort_key, reverse=reverse)
