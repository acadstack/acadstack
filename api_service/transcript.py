"""SGPA, CGPA and earned-credit computation for transcripts.

Pure functions: they work only on the course rows passed in and never touch
the database or the session.
"""

import logging
import math

import common as C
from common import AcadStackException

# Enrolment types that earn credit
CREDIT_ENROL_TYPES = ("C", "CM", "CC")

def sort_sessions(acad_sessions, start_dates):
    """The sessions in order of their start dates ({session: ISO date}); sessions
    without a start date go last, by name."""
    return sorted(acad_sessions,
                  key=lambda s: (s not in start_dates, start_dates.get(s, ""), s))


def scheme_range(scheme, order):
    """The positions (in order, {session: position}) of a grading scheme's first
    and last session; a range without a start or end is open at that end. A
    session missing from order gives None."""
    lo, hi = scheme["from_session"], scheme["until_session"]
    return (-math.inf if lo is None else order.get(lo),
            math.inf if hi is None else order.get(hi))


def resolve_scheme(schemes, level, acad_session, order):
    """The grade rules ({grade: entry}) of the scheme of this level whose
    session range contains the session, the narrowest one if several do; None
    if none does. order gives each session's position."""
    pos = order.get(acad_session)
    best, best_range = None, None
    for s in schemes:
        lo, hi = scheme_range(s, order)
        if s["level"] != level or lo is None or hi is None:
            continue
        covers = lo <= pos <= hi if pos is not None else (lo, hi) == (-math.inf, math.inf)
        if covers and (best is None or (lo, -hi) > (best_range[0], -best_range[1])):
            best, best_range = s, (lo, hi)
    return {g["grade"]: g for g in best["grades"]} if best else None


def course_credits(course):
    """The frozen credits of the enrolment, or else the C part of the
    course's L-T-P-S-C."""
    if course.get("credits") is not None:
        return round(float(course["credits"]), 2)
    ltp = course["ltp"].strip().split("-")
    if len(ltp) < 2 or not (ltp[0] and ltp[2]):
        raise AcadStackException(f"LTP data missing for course {course["code"]}")
    if len(ltp) != 5:
        raise AcadStackException(
            f"LTP data not in L-T-P-S-C format for course {course["code"]}")
    return round(C.parse_number(ltp[-1]), 2)


def session_gpa(courses, rules):
    """SGPA, earned credits and CGPA points of one session's course rows, under
    the grade rules ({grade: entry} of a grading scheme) of that session."""
    ec, s_ec, pts_sgpa, pts_cgpa, u_ec = 0, 0, 0, 0, 0
    creg, creg_wo_audit = 0, 0
    for c in courses:
        # Take only confirmed enrolments in finished courses
        if c["enrol_status"] != "ENRO":
            continue

        cc = course_credits(c)
        is_credit_course = c["enrol_type"] in CREDIT_ENROL_TYPES
        # Total registered credits
        creg += cc
        if is_credit_course:
            creg_wo_audit += cc

        # Rule of the grade secured in this course; a grade the scheme doesn't
        # have (such as NA, not graded yet) has no points and earns nothing.
        rule = rules.get(c["grade"], {})

        if rule.get("credit_without_gpa"):
            s_ec += cc
        if rule.get("excluded_from_gpa"):
            u_ec += cc
        if rule.get("earns_credit") and is_credit_course:
            ec += cc

        if rule.get("points") is not None and is_credit_course:
            pts_sgpa += rule["points"] * cc
            if rule["in_cgpa"]:
                pts_cgpa += rule["points"] * cc
        else:
            logging.debug(f"Points not mapped for grade {c['grade']}!")

    creg_sgpa = (creg_wo_audit - s_ec) - u_ec
    ec_cgpa = (ec - s_ec)
    sgpa = round(pts_sgpa / creg_sgpa, 2) if creg_sgpa > 0 else 0
    cgpa = round(pts_cgpa / ec_cgpa, 2) if ec_cgpa > 0 else 0

    return {"sgpa": sgpa, "ec": ec, "s_ec": s_ec,
            "creg": creg, "cgpa": cgpa, "pts_cgpa": pts_cgpa}


def cumulative_gpa(sessions, rules):
    """For each session's course rows, in chronological order: its SGPA,
    earned and registered credits, and the cumulative earned credits (cec)
    and CGPA up to and including it. rules holds each session's grade rules,
    in the same order."""
    ec, pts_cgpa, s_ec = 0, 0, 0
    results = []
    for courses, session_rules in zip(sessions, rules):
        cg = session_gpa(courses, session_rules)
        pts_cgpa += cg["pts_cgpa"]
        s_ec += cg["s_ec"]
        ec += cg["ec"]
        results.append({"sgpa": cg["sgpa"], "ec": cg["ec"], "creg": cg["creg"],
                        "cec": ec,
                        "cgpa": round(pts_cgpa / (ec - s_ec), 2) if (ec - s_ec) > 0 else 0})
    return results
