"""Transcript computation: a student's courses, SGPA, CGPA and credits.

This is the logic ``api_reports`` and ``api_grades`` were reaching into
``api_course_enrolment``'s privates to get at
(``__get_student_courses_perf``, ``get_student_courses_perf_filtered``).
It is now a module of its own that both import normally.

Behaviour is unchanged from the original, including the oddities
``tests/test_gpa_computation.py`` characterises. What did change is that
every rule the computation used to carry as a literal -- the grade point
map, the earned-credit and CGPA grade sets, the degree classification, the
credit-bearing enrolment types, the LTP format and the rounding -- is now
read off an effective-dated :class:`domain.policy.GradingPolicy` resolved
for the session being computed. There is no branch on a year and no
hardcoded degree code left in this module.
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


def _course_credits(course, ltp):
    """The credit value out of a course's LTP string.

    The order of the two checks is deliberate and load-bearing. The
    "missing data" check runs first and indexes ``required_indices``
    without a bounds check, so a string with too few fields raises a raw
    IndexError rather than a DomainError. That is the original behaviour
    and ``tests/test_gpa_computation.py`` pins it; a caller catching
    AcadStackException for bad data does not catch it. Guarding the index
    here would be a behaviour change, so it is left as it is and named
    instead.
    """
    parts = course["ltp"].strip().split(ltp.separator)
    if len(parts) < 2 or not all(parts[i] for i in ltp.required_indices):
        raise DomainError(f"LTP data missing for course {course['code']}")
    if len(parts) != ltp.field_count:
        raise DomainError(f"LTP data not in {ltp.format_label} format for "
                          f"course {course['code']}")
    return round(C.parse_number(parts[ltp.credits_index]), 2)


def sgpa_denominator(registered_credits, satisfactory_credits,
                     excluded_credits):
    """Credits SGPA is averaged over.

    Satisfactory grades carry no points, so they are netted out rather
    than dragging the average to zero; excluded grades (I/W/U) come out
    entirely, as though the course had never been registered for.

    This stays in code rather than becoming a policy field, and so does
    :func:`cgpa_denominator`. Every term is an accumulator this module
    defines, and what each one MEANS is already configurable -- which
    grades are satisfactory, which are excluded, which earn credit, which
    count towards CGPA all come off the ruleset. Making the formula itself
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


def _gpa(points, denominator, policy):
    """A grade average, rounded as the ruleset says, or 0 when there is
    nothing to average over."""
    return policy.round_gpa(points / denominator) if denominator > 0 else 0


def compute_cgpa_sgpa_ec(courses, degree, policy=None):
    """SGPA, CGPA and credit totals for one academic session's courses.

    Args:
        courses: list of course dicts as built by
            :func:`fetch_student_enrollments_data` (keys: acad_session,
            ltp, enrol_type, enrol_status, grade, code).
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
    # Carries the last ruleset resolved, which is what the final rounding
    # uses. Courses reaching here belong to one session, so this is that
    # session's ruleset; the initial value only matters for an empty list.
    pol = policy or POL.load_grading_policy()
    try:
        for c in courses:
            # The ruleset in force for THIS course's session. An explicit
            # policy always wins, so an injected ruleset is never
            # second-guessed by a store lookup.
            pol = policy or POL.load_grading_policy(c["acad_session"])

            # Take only confirmed enrolments in finished courses
            if c["enrol_status"] != pol.counted_enrol_status:
                continue

            rules = pol.rules_for(degree)
            cc = _course_credits(c, pol.ltp)
            is_credit_course = pol.is_credit_enrol_type(c["enrol_type"])

            # Total registered credits
            creg += cc
            if is_credit_course:
                creg_wo_audit += cc

            # Grade secured in this course
            grade = c["grade"]

            if grade == pol.satisfactory_grade:
                s_ec += cc
            if grade in pol.excluded_grades:
                u_ec += cc
            if grade in rules.earned_credit_grades and is_credit_course:
                ec += cc

            if grade in rules.grade_points and is_credit_course:
                pts_sgpa += rules.grade_points[grade] * cc
                if grade in rules.cgpa_grades:
                    pts_cgpa += rules.grade_points[grade] * cc
            else:
                logging.debug(f"Points not mapped for grade {grade}!")

        sgpa = _gpa(pts_sgpa,
                    sgpa_denominator(creg_wo_audit, s_ec, u_ec), pol)
        cgpa = _gpa(pts_cgpa, cgpa_denominator(ec, s_ec), pol)

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
        # Ignore canceled and declined course offerings
        if se.course_offering.status in ["C", "D"]:
            continue

        my_course = {"id": se.id, "co_id": se.course_offering.id,
                     "code": se.course_offering.course.code,
                     "title": se.course_offering.course.title,
                     "ltp": se.course_offering.course.ltp,
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

        if cat_info:
            for cat in cat_info:
                my_course["cc_category"] = cat.category
                if cat.dept == st_dept_name:
                    my_course["cc_category"] = cat.category
                    break
        else:
            logging.warning("Course categorization not found. CO id="
                            f"{se.course_offering.id}")

        # Release the grade only after result declaration date
        try:
            result_dec_dt = CAL.event_date("RESULT_DECLARATION",
                                           se.course_offering.acad_session)
        except Exception:
            pass
        else:
            if result_dec_dt > C.current_dt_str():
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
        enrol_data[ad]["cgpa"] = _gpa(pts_cgpa,
                                      cgpa_denominator(ec, s_ec), pol)

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
