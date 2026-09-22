"""Transcript computation: a student's courses, SGPA, CGPA and credits.

This is the logic ``api_reports`` and ``api_grades`` were reaching into
``api_course_enrolment``'s privates to get at
(``__get_student_courses_perf``, ``get_student_courses_perf_filtered``).
It is now a module of its own that both import normally.

Behaviour is unchanged from the original, including the oddities
``tests/test_gpa_computation.py`` characterises. What did change is that
the grade vocabulary, credit rules and the 2021 PhD amendment are read
off a :class:`domain.policy.GradingPolicy` instead of being literals in
the loop, so a caller can compute a transcript under any ruleset. Phase
6/7 replaces the loaded default with an effective-dated lookup.
"""

import logging

from playhouse.shortcuts import model_to_dict

import common as C
import models as DB
from domain import academic_calendar as CAL
from domain import attendance as ATT
from domain import policy as POL
from domain.errors import DomainError


def compute_cgpa_sgpa_ec(courses, degree, policy=None):
    """SGPA, CGPA and credit totals for one academic session's courses.

    Args:
        courses: list of course dicts as built by
            :func:`fetch_student_enrollments_data` (keys: acad_session,
            ltp, enrol_type, enrol_status, grade, code).
        degree: the student's degree code, selecting the credit rules.
        policy (GradingPolicy): grade points and credit rules. Defaults
            to the configured policy.

    Returns:
        dict with sgpa, ec, s_ec, creg, cgpa, pts_cgpa.
    """
    pol = policy or POL.load_grading_policy()
    gpm = pol.grade_points
    pass_grades = pol.pass_grades

    # Temp variables used for calculations
    ec, s_ec, pts_sgpa, pts_cgpa, u_ec = 0, 0, 0, 0, 0
    creg, creg_wo_audit, sgpa, cgpa = 0, 0, 0, 0
    try:
        for c in courses:

            # Take only confirmed enrolments in finished courses
            if c["enrol_status"] != pol.counted_enrol_status:
                continue

            # The PhD grade sets in force for this course's session. Note
            # this is evaluated for every degree, not just PHD, exactly
            # as the original did -- so a malformed acad_session or an
            # unknown semester suffix still raises/warns for UG and PG.
            phd_ec_grades, phd_ec_pass_grades = POL.apply_phd_amendment(
                pol, c['acad_session'])

            # L-T-P-S-C
            ltp = c["ltp"].strip().split("-")
            if len(ltp) < 2 or not (ltp[0] and ltp[2]):
                raise DomainError(f"LTP data missing for course {c['code']}")
            if len(ltp) == 5:
                cc = round(C.parse_number(ltp[-1]), 2)
            else:
                raise DomainError(
                    f"LTP data not in L-T-P-S-C format for course {c['code']}")

            is_credit_course = c["enrol_type"] in pol.credit_enrol_types
            # Total registered credits
            creg += cc
            if is_credit_course:
                creg_wo_audit += cc

            # Grades that are counted towards earned credits
            ec_grades = pol.ec_grades_for(degree, phd_ec_grades)
            if degree == pol.phd_degree_code:
                pass_grades = phd_ec_pass_grades

            # Grade secured in this course
            grade = c["grade"]

            if grade == pol.satisfactory_grade:
                s_ec += cc
            if grade in pol.excluded_grades:
                u_ec += cc
            if grade in ec_grades and is_credit_course:
                ec += cc

            if grade in gpm and is_credit_course:
                pts_sgpa += gpm[grade] * cc
                if grade in pass_grades and is_credit_course:
                    pts_cgpa += gpm[grade] * cc
            else:
                logging.debug(f"Points not mapped for grade {grade}!")

        creg_sgpa = (creg_wo_audit - s_ec) - u_ec
        ec_cgpa = (ec - s_ec)
        sgpa = round(pts_sgpa / creg_sgpa, 2) if creg_sgpa > 0 else 0
        cgpa = round(pts_cgpa / ec_cgpa, 2) if ec_cgpa > 0 else 0

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

    # We use these suffixies for academic sessions. Change them as needed.
    # T1, T2 etc. are for trimesters, I, II and S are for regular semesters.
    suffixes = ['T1', 'T2', 'T3', 'T4', 'I', 'II', 'S']

    # Sort by academic session. Needed for cgpa calculations
    acad_sess_list = list(enrol_data.keys())
    acad_sess_list = sorted(
        acad_sess_list,
        key=lambda item: "{0}{1}".format(item[:4], suffixes.index(item[5:])))

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
        enrol_data[ad]["cgpa"] = round(pts_cgpa / (ec - s_ec), 2) \
            if (ec - s_ec) > 0 else 0

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
