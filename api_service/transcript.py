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

# Enrolment types that earn credit
CREDIT_ENROL_TYPES = ("C", "CM", "CC")

# We use these suffixies for academic sessions. Change them as needed.
# T1, T2 etc. are for trimesters, I, II and S are for regular semesters.
SESSION_SUFFIXES = ['T1', 'T2', 'T3', 'T4', 'I', 'II', 'S']


def session_sort_key(acad_session):
    """Sort key putting academic sessions such as ``2024-II`` in chronological order."""
    return "{0}{1}".format(acad_session[:4],
                           SESSION_SUFFIXES.index(acad_session[5:]))


def _phd_grade_sets(acad_session):
    """PhD (earned-credit grades, passing grades) for a session: the passing
    grades changed in 2021."""
    ec_grades = {"A", "A-", "B", "B-", "C"}
    pass_grades = {"A", "A-", "B", "B-", "C", "C-"}
    year, sem = int(acad_session[:4]), acad_session[5:]  # I, II, S, T1, T2, etc.
    if year > 2021:
        ec_grades = {"A", "A-", "B", "B-", "C", "C-"}
    elif year < 2021:
        pass_grades = {"A", "A-", "B", "B-", "C"}
    else: # Year 2021
        if sem == "I":
            pass_grades = {"A", "A-", "B", "B-", "C"}
            ec_grades = {"A", "A-", "B", "B-", "C", "C-"}
        elif sem in ["II", "S", "T1", "T2"]:
            ec_grades = {"A", "A-", "B", "B-", "C", "C-"}
        else:
            logging.warning(f"Unknown academic semester: '{sem}'")
    return ec_grades, pass_grades


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


def session_gpa(courses, degree):
    """SGPA, earned credits and CGPA points of one session's course rows."""
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
        if degree == "BTE":
            ec_grades = UG_EC_GRADES
        elif degree == "PHD":
            ec_grades, pass_grades = _phd_grade_sets(c["acad_session"])
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


def cumulative_gpa(sessions, degree):
    """For each session's course rows, in chronological order: its SGPA,
    earned and registered credits, and the cumulative earned credits (cec)
    and CGPA up to and including it."""
    ec, pts_cgpa, s_ec = 0, 0, 0
    results = []
    for courses in sessions:
        cg = session_gpa(courses, degree)
        pts_cgpa += cg["pts_cgpa"]
        s_ec += cg["s_ec"]
        ec += cg["ec"]
        results.append({"sgpa": cg["sgpa"], "ec": cg["ec"], "creg": cg["creg"],
                        "cec": ec,
                        "cgpa": round(pts_cgpa / (ec - s_ec), 2) if (ec - s_ec) > 0 else 0})
    return results
