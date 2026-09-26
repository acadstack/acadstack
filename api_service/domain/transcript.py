"""Transcript computation: a student's courses, SGPA, CGPA and credits.

This is the logic ``api_reports`` and ``api_grades`` were reaching into
``api_course_enrolment``'s privates to get at
(``__get_student_courses_perf``, ``get_student_courses_perf_filtered``).
It is now a module of its own that both import normally.

Every rule an institution can amend -- the grade point map, the
earned-credit and CGPA grade sets, the degree classification, the
credit-bearing enrolment types, the excluded and passing grades -- is read
off an effective-dated :class:`domain.policy.GradingPolicy` resolved for
the session being computed. There is no branch on a year and no hardcoded
degree code left in this module. What stays here as constants is not
policy: fixed vocabulary codes and the rounding.
"""

import logging

from playhouse.shortcuts import model_to_dict

import acad_session as AS
import common as C
import models as DB
from domain import academic_calendar as CAL
from domain import attendance as ATT
from domain import policy as POL
from domain.errors import DomainError


#: Only enrolments in this status are counted.
COUNTED_ENROL_STATUS = "ENRO"

#: Satisfactory grade: earns credit (where the programme's earned-credit
#: grades include it), carries no points, and is netted out of both GPA
#: denominators.
SATISFACTORY_GRADE = "S"

#: Decimal places SGPA and CGPA are rounded to.
GPA_DECIMAL_PLACES = 2

#: Offering statuses left off a transcript: cancelled and declined.
EXCLUDED_OFFERING_STATUSES = ("C", "D")


def grade_released(acad_session):
    """Whether a session's grades may be shown: true unless a result
    declaration date is configured and still in the future. Until then a
    grade reads as "NA"."""
    try:
        declared = CAL.event_date("RESULT_DECLARATION", acad_session)
    except Exception:
        return True
    return declared <= C.current_dt_str()


def category_for(categories, dept_name):
    """The category of one offering for a student, given the
    ``(category, dept)`` pairs of the CourseCategory rows that apply to
    the student's degree, entry year and department (or "ALL"): the
    department's own row wins over "ALL". None when there are none."""
    chosen = None
    for category, dept in categories:
        chosen = category
        if dept == dept_name:
            break
    return chosen


def _course_credits(course):
    """The course's stored credit value (``Course.credits``, computed from
    its L/T/P by ``common.compute_course_ltp`` when the course is saved).
    """
    if course.get("credits") is None:
        raise DomainError(f"Credits missing for course {course['code']}: "
                          f"its LTP has no valid L-T-P values")
    return course["credits"]


def sgpa_denominator(registered_credits, satisfactory_credits,
                     excluded_credits):
    """Credits SGPA is averaged over.

    Satisfactory grades carry no points, so they are netted out rather
    than dragging the average to zero; excluded grades (I/W/U) come out
    entirely, as though the course had never been registered for.

    This stays in code rather than becoming a policy field, and so does
    :func:`cgpa_denominator`. Every term is an accumulator this module
    defines, and what each one MEANS is already configurable -- which
    grades are excluded, which earn credit, which count towards CGPA all
    come off the ruleset. Making the formula itself
    configurable would take either an expression language evaluated
    against grade data, or a row of booleans enumerating the combinations
    someone happened to imagine. Changing this arithmetic changes what
    SGPA means at an institution; that deserves a code review and a test,
    not a row an admin can edit. It is a function so that the one
    definition is shared -- the CGPA formula used to be restated in
    courses_perf_filtered.
    """
    return (registered_credits - satisfactory_credits) - excluded_credits


def cgpa_denominator(earned_credits, satisfactory_credits):
    """Credits CGPA is averaged over. See :func:`sgpa_denominator`."""
    return earned_credits - satisfactory_credits


def earns_credit(grade, enrol_type, degree, policy):
    """Whether an enrolment's grade earns credit under ``policy``: a
    credit-bearing enrolment type and one of the degree's earned-credit
    grades. Transcripts and the credit reports both count by this."""
    return (enrol_type in policy.credit_enrol_types
            and grade in policy.rules_for(degree).earned_credit_grades)


def _gpa(points, denominator):
    """A grade average, rounded, or 0 when there is nothing to average
    over."""
    return round(points / denominator, GPA_DECIMAL_PLACES) \
        if denominator > 0 else 0


def compute_cgpa_sgpa_ec(courses, degree, policy=None):
    """SGPA, CGPA and credit totals for one academic session's courses.

    Args:
        courses: list of course dicts as built by
            :func:`fetch_student_enrollments_data` (keys: acad_session,
            credits, enrol_type, enrol_status, grade, code).
        degree: the student's degree code. The ruleset maps it to a
            programme class, which selects the grade rules.
        policy (GradingPolicy): the ruleset to compute under. When None,
            the ruleset in force for each course's own academic session is
            resolved -- which is what makes a historical transcript compute
            under the rules of its time.

    Returns:
        dict with sgpa, ec, s_ec, creg, cgpa, pts_cgpa.
    """
    # Temp variables used for calculations
    ec, s_ec, pts_sgpa, pts_cgpa, u_ec = 0, 0, 0, 0, 0
    creg, creg_wo_audit = 0, 0
    try:
        for c in courses:
            # The ruleset in force for THIS course's session. An explicit
            # policy always wins, so an injected ruleset is never
            # second-guessed by a store lookup.
            pol = policy or POL.load_grading_policy(c["acad_session"])

            # Take only confirmed enrolments in finished courses
            if c["enrol_status"] != COUNTED_ENROL_STATUS:
                continue

            rules = pol.rules_for(degree)
            cc = _course_credits(c)
            is_credit_course = c["enrol_type"] in pol.credit_enrol_types

            # Total registered credits
            creg += cc
            if is_credit_course:
                creg_wo_audit += cc

            # Grade secured in this course
            grade = c["grade"]

            if grade == SATISFACTORY_GRADE:
                s_ec += cc
            if grade in pol.excluded_grades:
                u_ec += cc
            if earns_credit(grade, c["enrol_type"], degree, pol):
                ec += cc

            if grade in rules.grade_points and is_credit_course:
                pts_sgpa += rules.grade_points[grade] * cc
                if grade in rules.cgpa_grades:
                    pts_cgpa += rules.grade_points[grade] * cc
            else:
                logging.debug(f"Points not mapped for grade {grade}!")

        sgpa = _gpa(pts_sgpa, sgpa_denominator(creg_wo_audit, s_ec, u_ec))
        cgpa = _gpa(pts_cgpa, cgpa_denominator(ec, s_ec))

    except Exception as ex:
        logging.error(ex)
        raise ex

    return {"sgpa": sgpa, "ec": ec, "s_ec": s_ec,
            "creg": creg, "cgpa": cgpa, "pts_cgpa": pts_cgpa}


def fetch_student_enrollments_data(enrols, include_attendance):
    """Groups a student's enrolments by academic session.

    Returns ``(acad_sessions, enrol_data)`` where ``acad_sessions`` is
    the session list in chronological order and ``enrol_data`` maps each
    session to ``{"courses": [...], "sgpa": 0, "ec": 0}``.
    """
    # Dict's key is acad_session and value will be an object containing
    # information about courses, CGPA, SGPA, earned credits etc.
    enrol_data = {}

    for se in enrols:
        if se.course_offering.status in EXCLUDED_OFFERING_STATUSES:
            continue

        my_course = {"id": se.id, "co_id": se.course_offering.id,
                     "code": se.course_offering.course.code,
                     "title": se.course_offering.course.title,
                     "ltp": se.course_offering.course.ltp,
                     "credits": se.course_offering.course.credits,
                     "acad_session": se.course_offering.acad_session,
                     "status": se.course_offering.status.strip().upper(),
                     "enrol_type": se.enrol_type.strip().upper(),
                     "enrol_status": se.enrol_status.strip().upper(),
                     "grade": se.grade.strip().upper(),
                     "remarks": se.remarks}

        # Fetch the student's user/profile info
        stud = DB.User.select().join(DB.Person, DB.ORM.JOIN.LEFT_OUTER)\
            .where(DB.User.id == se.student_id)

        if stud:
            st_year_of_entry = stud[0].person.year_of_entry
            st_dept_name = stud[0].person.dept_name
            st_degree = stud[0].person.degree
        else:
            raise DomainError("User not found for student. UserId="
                              f"{se.student_id}")

        # Fetch course categorization info applicable to the student
        cat_info = DB.CourseCategory.select(). \
            join(DB.CourseOffering).\
            where(
            (DB.CourseCategory.offering == se.course_offering.id) &
            (DB.CourseCategory.degree == st_degree) &
            (DB.CourseCategory.dept << (st_dept_name, 'ALL')) &
            (DB.CourseCategory.for_entry_years.contains(st_year_of_entry)))

        category = category_for([(c.category, c.dept) for c in cat_info],
                                st_dept_name)
        if category is not None:
            my_course["cc_category"] = category
        else:
            logging.warning("Course categorization not found. CO id="
                            f"{se.course_offering.id}")

        if not grade_released(se.course_offering.acad_session):
            my_course["grade"] = "NA"

        if include_attendance:
            my_course["attendance"] = ATT.percent_for_enrolment(se)

        acad_sess_key = my_course["acad_session"]
        if acad_sess_key not in enrol_data:
            enrol_data[acad_sess_key] = {"courses": [], "sgpa": 0, "ec": 0}

        enrol_data[acad_sess_key]["courses"].append(my_course)

    # Sort by academic session. Needed for cgpa calculations, which
    # accumulate forward in time. Session chronology is acad_session.py's
    # job -- it is the same order effective-dated policy resolves on, and
    # keeping one definition means a transcript cannot accumulate in one
    # order while policy resolves in another.
    acad_sess_list = AS.sorted_sessions(enrol_data.keys())

    # We return the enrolment data per academic session, sorted in reverse
    # chronological order of academic sessions (2025-II, 2025-I, 2024-II ...).
    enrol_data_sorted = dict()
    for key in acad_sess_list:
        enrol_data_sorted[key] = enrol_data[key]

    logging.debug(f"Sorted acad sessions: {acad_sess_list}")
    return acad_sess_list, enrol_data_sorted


def courses_perf_filtered(stu, include_attendance,
                          filter_by_enrol_type=None, policy=None):
    """Per-session performance for one student, optionally restricted to
    an enrolment type ('C', 'CM', 'CC').

    'C' deliberately also pulls in audited ('A') enrolments, since audits
    show on the regular transcript.
    """
    if filter_by_enrol_type == "C":  # 'C' -> Credit, 'A' -> Audit, etc.
        enrols = stu.enrollments.where(DB.CourseEnrollment.enrol_type
                                       << (filter_by_enrol_type, 'A'))
    elif filter_by_enrol_type:
        enrols = stu.enrollments.where(DB.CourseEnrollment.enrol_type
                                       == filter_by_enrol_type)
    else:
        enrols = stu.enrollments

    acad_sessions, enrol_data = fetch_student_enrollments_data(
        enrols, include_attendance)
    ec, pts_cgpa, s_ec = 0, 0, 0

    # acad_sessions is already in properly sorted chronology
    for ad in acad_sessions:
        pol = policy or POL.load_grading_policy(ad)
        cg_data = compute_cgpa_sgpa_ec(enrol_data[ad]["courses"],
                                       stu.person.degree, policy=pol)
        enrol_data[ad]["sgpa"] = cg_data["sgpa"]
        enrol_data[ad]["ec"] = cg_data["ec"]
        enrol_data[ad]["creg"] = cg_data["creg"]
        pts_cgpa += cg_data["pts_cgpa"]
        s_ec += cg_data["s_ec"]
        ec += cg_data["ec"]

        enrol_data[ad]["cec"] = ec
        # Cumulative CGPA over every session up to this one, by the same
        # formula and the same rounding as the per-session figure.
        enrol_data[ad]["cgpa"] = _gpa(pts_cgpa, cgpa_denominator(ec, s_ec))

    return {"enrollments": enrol_data, "acad_sessions": acad_sessions}


def courses_perf(stu, include_attendance, policy=None):
    """The student's profile plus their performance split by enrolment
    type: concentration credit (CC), minor credit (CM) and regular
    credit (C, which includes audits)."""
    # 'CC' -> Credit for concentration
    perf_conc = courses_perf_filtered(stu, include_attendance, "CC", policy)

    # 'CM' -> Credit for minor
    perf_minor = courses_perf_filtered(stu, include_attendance, "CM", policy)

    # 'C' -> Credit
    perf_regu = courses_perf_filtered(stu, include_attendance, "C", policy)

    user = model_to_dict(stu, exclude=[DB.User.password_hashed])
    user["enrollments"] = {"CC": perf_conc, "CM": perf_minor, "C": perf_regu}

    return user
