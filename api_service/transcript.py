"""SGPA, CGPA and earned-credit computation for transcripts.

Pure functions: they work only on the course rows passed in and never touch
the database or the session.
"""

import logging

import common as C
from common import AcadStackException

# Mapping of grade letter to points
GRADE_POINTS = {"A": 10, "A-": 9, "B": 8, "B-": 7, "C": 6, "C-": 5,
                "D": 4, "E": 2, "F": 0}

# Grades counted for earned credits for UG students
UG_EC_GRADES = frozenset({"A", "A-", "B", "B-", "C", "C-", "D", "S", "NP"})

# Grades counted for earned credits for PG students
PG_EC_GRADES = frozenset({"A", "A-", "B", "B-", "C", "C-", "D", "S"})

# Passing grades (UG+PG) used in CGPA calculation
PASS_GRADES = frozenset({"A", "A-", "B", "B-", "C", "C-", "D"})

# Grades counted for earned credits, and passing grades, for PhD students
PHD_EC_GRADES = frozenset({"A", "A-", "B", "B-", "C", "C-"})
PHD_PASS_GRADES = frozenset({"A", "A-", "B", "B-", "C", "C-"})

# Enrolment types that earn credit
CREDIT_ENROL_TYPES = ("C", "CM", "CC")

def sort_sessions(acad_sessions, start_dates):
    """The sessions in order of their start dates ({session: ISO date}); sessions
    without a start date go last, by name."""
    return sorted(acad_sessions,
                  key=lambda s: (s not in start_dates, start_dates.get(s, ""), s))


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


def session_gpa(courses, level):
    """SGPA, earned credits and CGPA points of one session's course rows, for
    a student whose program has the given level (UG, PG or PHD)."""
    ec, s_ec, pts_sgpa, pts_cgpa, u_ec = 0, 0, 0, 0, 0
    creg, creg_wo_audit = 0, 0
    pass_grades = PASS_GRADES
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

        # Grades that are counted towards earned credits
        if level == "UG":
            ec_grades = UG_EC_GRADES
        elif level == "PHD":
            ec_grades, pass_grades = PHD_EC_GRADES, PHD_PASS_GRADES
        else:
            ec_grades = PG_EC_GRADES

        # Grade secured in this course
        grade = c["grade"]

        if grade == "S":
            s_ec += cc
        if grade in ("U", "I", "W"):
            u_ec += cc
        if grade in ec_grades and is_credit_course:
            ec += cc

        if grade in GRADE_POINTS and is_credit_course:
            pts_sgpa += GRADE_POINTS[grade] * cc
            if grade in pass_grades:
                pts_cgpa += GRADE_POINTS[grade] * cc
        else:
            logging.debug(f"Points not mapped for grade {grade}!")

    creg_sgpa = (creg_wo_audit - s_ec) - u_ec
    ec_cgpa = (ec - s_ec)
    sgpa = round(pts_sgpa / creg_sgpa, 2) if creg_sgpa > 0 else 0
    cgpa = round(pts_cgpa / ec_cgpa, 2) if ec_cgpa > 0 else 0

    return {"sgpa": sgpa, "ec": ec, "s_ec": s_ec,
            "creg": creg, "cgpa": cgpa, "pts_cgpa": pts_cgpa}


def cumulative_gpa(sessions, level):
    """For each session's course rows, in chronological order: its SGPA,
    earned and registered credits, and the cumulative earned credits (cec)
    and CGPA up to and including it."""
    ec, pts_cgpa, s_ec = 0, 0, 0
    results = []
    for courses in sessions:
        cg = session_gpa(courses, level)
        pts_cgpa += cg["pts_cgpa"]
        s_ec += cg["s_ec"]
        ec += cg["ec"]
        results.append({"sgpa": cg["sgpa"], "ec": cg["ec"], "creg": cg["creg"],
                        "cec": ec,
                        "cgpa": round(pts_cgpa / (ec - s_ec), 2) if (ec - s_ec) > 0 else 0})
    return results
