"""Credit totals for the credit reports.

The report queries leave the grade and enrolment-type codes out of SQL.
Which rows count is decided here, by the rules transcripts use: the
:class:`domain.policy.GradingPolicy` in force for each row's own session,
the offerings transcripts leave off, the category a transcript shows and
grades hidden until result declaration. So reports and transcripts agree,
including after a new policy version.
"""

from decimal import ROUND_HALF_UP, Decimal
from itertools import groupby

import common as C
import models as DB
from domain import policy as POL
from domain import transcript as TR


#: Category reported for an enrolment with none.
UNCATEGORIZED = "UnCat"


def _code(value):
    """A stored code as the transcript compares it."""
    return (value or "").strip().upper()


def _counted(row):
    """Whether a row's offering appears on transcripts at all."""
    return row["credits"] is not None and \
        _code(row["offering_status"]) not in TR.EXCLUDED_OFFERING_STATUSES


#: Credit range used when a report's lower or upper bound is left blank.
DEFAULT_MIN_CREDITS, DEFAULT_MAX_CREDITS = 0, 9999


def credit_bounds(min_credits, max_credits):
    """A report's credit range as ints; blank or "-" means unbounded."""
    def bound(value, default):
        return default if value in (None, "", "-") else int(value)
    return (bound(min_credits, DEFAULT_MIN_CREDITS),
            bound(max_credits, DEFAULT_MAX_CREDITS))


def round_credits(total):
    """Credits to two decimal places, as the reports display them."""
    return Decimal(str(total)).quantize(Decimal("0.01"), ROUND_HALF_UP)


def credit_enrolment_totals(rows, policy=None):
    """Registered credits per student and session, over credit-bearing
    enrolments regardless of grade.

    Args:
        rows: dicts with ``id`` (the student), ``acad_session``,
            ``offering_status``, ``credits`` and ``enrol_type``.
        policy: a ruleset to use for every row; by default each row's
            session resolves its own.

    Returns:
        ``{(student_id, acad_session): total}``, holding only students
        with at least one counted enrolment.
    """
    totals = {}
    for r in rows:
        pol = policy or POL.load_grading_policy(r["acad_session"])
        if not _counted(r) or \
                _code(r["enrol_type"]) not in pol.credit_enrol_types:
            continue
        key = (r["id"], r["acad_session"])
        totals[key] = totals.get(key, 0) + r["credits"]
    return totals


def earned_credits_by_category(rows, category="",
                               min_credits=DEFAULT_MIN_CREDITS,
                               max_credits=DEFAULT_MAX_CREDITS, policy=None):
    """Earned credits per student, session and course category.

    Args:
        rows: one dict per enrolment, with ``id`` (the student),
            ``degree``, ``acad_session``, ``offering_status``,
            ``c_category``, ``credits``, ``enrol_type`` and ``grade`` (as
            released: "NA" before result declaration).
        category: keep only this category; empty keeps all.
        min_credits, max_credits: keep only category totals in this
            inclusive range.
        policy: as for :func:`credit_enrolment_totals`.

    Returns:
        ``{(student_id, acad_session): {category: total}}`` in first-seen
        row order, so the caller's ORDER BY carries through.
    """
    totals = {}
    for r in rows:
        pol = policy or POL.load_grading_policy(r["acad_session"])
        if not _counted(r) or not TR.earns_credit(
                _code(r["grade"]), _code(r["enrol_type"]), r["degree"], pol):
            continue
        cats = totals.setdefault((r["id"], r["acad_session"]), {})
        cat = r["c_category"]
        cats[cat] = cats.get(cat, 0) + r["credits"]

    kept = {}
    for key, cats in totals.items():
        cats = {c: t for c, t in sorted(cats.items())
                if (not category or c == category)
                and min_credits <= t <= max_credits}
        if cats:
            kept[key] = cats
    return kept


def categorized_earned_credits(entry_year, degree, dept_name, acad_session,
                               category, min_credits, max_credits,
                               policy=None):
    """Earned credits by category for the students matching the filters;
    an empty filter matches everything.

    Returns:
        ``[(student, acad_session, {category: total})]`` ordered by login
        id and session, where ``student`` is a row dict with id, login_id,
        first_name, last_name, email and dept_name.
    """
    cursor = DB.db.execute_sql(C.sql_by_id("categorized_credit_enrolments"),
                               [entry_year, entry_year, degree, degree,
                                dept_name, dept_name,
                                acad_session, acad_session])
    names = [d[0] for d in cursor.description]
    rows = _per_enrolment([dict(zip(names, row))
                           for row in cursor.fetchall()])
    students = {r["id"]: r for r in rows}
    totals = earned_credits_by_category(rows, category, min_credits,
                                        max_credits, policy)
    return [(students[sid], session, cats)
            for (sid, session), cats in totals.items()]


def _per_enrolment(join_rows):
    """Collapses the query's one row per applicable category into one row
    per enrolment, carrying the category and grade a transcript shows."""
    released = {}
    rows = []
    for _, group in groupby(join_rows, key=lambda r: r["enrolment_id"]):
        group = list(group)
        row = dict(group[0])
        category = TR.category_for(
            [(r["category"], r["category_dept"]) for r in group
             if r["category_dept"] is not None], row["dept_name"])
        row["c_category"] = (category or "").strip() or UNCATEGORIZED
        session = row["acad_session"]
        if session not in released:
            released[session] = TR.grade_released(session)
        if not released[session]:
            row["grade"] = "NA"
        rows.append(row)
    return rows
