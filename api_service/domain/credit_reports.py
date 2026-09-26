"""Credit totals for the credit reports.

The report queries return one row per enrolment and leave the grade and
enrolment-type codes out of SQL. Which rows count is decided here, off
the :class:`domain.policy.GradingPolicy` in force for each row's own
session, by the rule transcripts use, so a new policy version changes
reports and transcripts together.
"""

from decimal import ROUND_HALF_UP, Decimal

import common as C
import models as DB
from domain import policy as POL
from domain import transcript as TR


def _code(value):
    """A stored code as the transcript compares it."""
    return (value or "").strip().upper()


def round_credits(total):
    """Credits to two decimal places, as the reports display them."""
    return Decimal(str(total)).quantize(Decimal("0.01"), ROUND_HALF_UP)


def credit_enrolment_totals(rows, policy=None):
    """Registered credits per student and session, over credit-bearing
    enrolments regardless of grade.

    Args:
        rows: dicts with ``id`` (the student), ``acad_session``,
            ``credits`` and ``enrol_type``.
        policy: a ruleset to use for every row; by default each row's
            session resolves its own.

    Returns:
        ``{(student_id, acad_session): total}``, holding only students
        with at least one counted enrolment.
    """
    totals = {}
    for r in rows:
        pol = policy or POL.load_grading_policy(r["acad_session"])
        if r["credits"] is None or \
                _code(r["enrol_type"]) not in pol.credit_enrol_types:
            continue
        key = (r["id"], r["acad_session"])
        totals[key] = totals.get(key, 0) + r["credits"]
    return totals


def earned_credits_by_category(rows, category="", min_credits=0,
                               max_credits=9999, policy=None):
    """Earned credits per student, session and course category.

    Args:
        rows: dicts with ``id`` (the student), ``degree``,
            ``acad_session``, ``c_category``, ``credits``, ``enrol_type``
            and ``grade``.
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
        if r["credits"] is None or not TR.earns_credit(
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
                               [entry_year, entry_year, entry_year,
                                degree, degree, dept_name, dept_name,
                                acad_session, acad_session])
    names = [d[0] for d in cursor.description]
    rows = [dict(zip(names, row)) for row in cursor.fetchall()]
    students = {r["id"]: r for r in rows}
    totals = earned_credits_by_category(rows, category, min_credits,
                                        max_credits, policy)
    return [(students[sid], session, cats)
            for (sid, session), cats in totals.items()]
