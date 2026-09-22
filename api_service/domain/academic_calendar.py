"""Reads of the academic calendar: which session is current, and where
today sits relative to a session's configured events.

These moved out of ``api_common``/``validation_checks`` because the
transcript and enrolment domain modules need them and must not import
the HTTP layer. They were already session-free (pure DB reads); the
callers in ``api_common`` and ``validation_checks`` now delegate here so
there is one implementation.
"""

import common as C
import models as DB
from domain.errors import DomainError


def current_acad_sessions_with_dates(sem_only=True):
    """Rows of ``(acad_session, start_dt, end_dt)`` for the session(s)
    currently in progress, earliest-starting first."""
    cursor = DB.db.execute_sql(C.sql_by_id("current_acad_sessions"), [sem_only])
    return [(row[0], row[1], row[2]) for row in cursor.fetchall()]


def current_acad_session_list(sem_only=True):
    return [x[0] for x in current_acad_sessions_with_dates(sem_only)]


def current_acad_session():
    casd = current_acad_sessions_with_dates()
    # Return the earliest starting acad session
    return casd[0][0]


def is_today_between_events(event1, event2, for_acad_session=None):
    """Whether today falls within the [event1, event2] window configured
    for the session. False when either endpoint is not configured."""
    acad_session = for_acad_session or current_acad_session()
    if not acad_session:
        return False

    res1 = DB.AcademicCalendar.select(DB.AcademicCalendar.event_value).where(
        (DB.AcademicCalendar.acad_session == acad_session) &
        (DB.AcademicCalendar.event_code == event1))
    res2 = DB.AcademicCalendar.select(DB.AcademicCalendar.event_value).where(
        (DB.AcademicCalendar.acad_session == acad_session) &
        (DB.AcademicCalendar.event_code == event2))

    now_str = C.current_dt_str()
    if res1.exists() and res2.exists():
        if res1[0].event_value <= now_str <= res2[0].event_value:
            return True
    return False


def event_date(event_code, for_acad_session=None):
    """The configured date for one calendar event, raising when the
    event is not configured for the session."""
    acad_session = for_acad_session or current_acad_session()
    if not acad_session:
        raise DomainError("Current academic session not configured.")

    res1 = DB.AcademicCalendar.select(DB.AcademicCalendar.event_value).where(
        (DB.AcademicCalendar.acad_session == acad_session) &
        (DB.AcademicCalendar.event_code == event_code))

    if res1.exists():
        return res1[0].event_value
    else:
        raise DomainError("Event {0} not configured in {1}."
                          .format(event_code, acad_session))


def is_course_add_drop_open(for_acad_session):
    return is_today_between_events("COURSE_REG_S", "COURSE_REG_E",
                                   for_acad_session) or \
        is_today_between_events("ADD_DROP_S", "ADD_DROP_E", for_acad_session)


def is_course_withdraw_open(for_acad_session):
    return is_today_between_events("WITHDRAW_S", "WITHDRAW_E",
                                   for_acad_session)
