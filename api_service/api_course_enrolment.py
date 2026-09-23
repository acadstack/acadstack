"""HTTP adapter for course enrolment.

Every handler here does the same four things and nothing else: read the
request, build the acting :class:`~domain.context.Actor`, call a
function in :mod:`domain.enrolment` (or :mod:`domain.transcript`), and
turn what comes back into the ``{"status": ..., "body": ...}`` envelope.
The business rules -- who may approve what, when a course may still be
added, how a transcript is computed -- live in the domain modules and
are callable without an HTTP request.

Coarse role gating stays here, on the @rbac decorators, because it is a
property of the endpoint. Resource-scoped checks ("is this *your*
enrolment") live in the domain, where the data is. See the service-layer
section of docs/architecture.md, and domain/__init__.py.
"""
from io import BytesIO
import logging
from quart import Blueprint, request
from quart.helpers import send_file
from peewee import IntegrityError
from common import AcadStackException, rbac
from playhouse.shortcuts import model_to_dict
import api_common as apiVC
import validation_checks as VAL
import models as DB
from domain import enrolment as ENR
from domain import transcript as TR

# tests/test_gpa_computation.py characterises the GPA computation via
# getattr(api_course_enrolment, "__compute_cgpa_sgpa_ec"). The function
# now lives in domain.transcript; this alias keeps that test (and any
# other caller of the old private name) working unchanged.
__compute_cgpa_sgpa_ec = TR.compute_cgpa_sgpa_ec


def init_routes(bp: Blueprint):
    bp.add_url_rule('/coe_view/<int:my_id>', view_func=course_enrollment_view, methods=['GET'])
    bp.add_url_rule('/coe_save', view_func=course_enrollment_save, methods=['POST'])
    bp.add_url_rule('/enroll_in_courses', view_func=enroll_in_courses, methods=['POST'])
    bp.add_url_rule('/change_enroll_status', view_func=change_enroll_status, methods=['POST'])
    bp.add_url_rule('/co_bulkenrol/<string:entry_no_pattern>/<int:co_id>', 
                        view_func=bulk_enrol_in_course, methods=['GET'])
    bp.add_url_rule('/get_course_enrollments/<int:my_id>', view_func=get_course_enrollments, methods=['GET'])
    bp.add_url_rule('/get_student_academics/<int:my_id>', view_func=get_student_academics, methods=['GET'])
    bp.add_url_rule('/get_passed_courses/<int:user_id>', view_func=get_passed_courses, methods=['GET'])
    bp.add_url_rule('/drop_withdraw_course/<int:my_id>/<string:status>',
                       view_func=drop_withdraw_course, methods=['GET'])
    bp.add_url_rule('/download_course_enrollments/<int:co_id>', 
                        view_func=download_course_enrollments,
                       methods=['GET'])
    bp.add_url_rule('/download_enrollments_for_grades/<int:co_id>', 
                        view_func=download_enrollments_for_grades, methods=['GET'])
    bp.add_url_rule('/get_instructor_courses_enrol', view_func=get_instructor_courses_enrol, methods=['GET'])
    bp.add_url_rule('/get_advisor_courses_enrol', view_func=get_advisor_courses_enrol, methods=['GET'])
    bp.add_url_rule('/download_course_enrolments/<string:dept_name>/<string:entry_year>/<string:acad_session>',
                       view_func=download_course_enrolments, methods=['GET'])


@rbac
async def drop_withdraw_course(my_id, status):
    try:
        if status not in "DROP,WDRAW":
            return apiVC.error_json(f"Invalid status {status}! Only drop/withdraw allowed!")

        ENR.drop_or_withdraw(apiVC.current_actor(), my_id, status)
        return apiVC.ok_json("Course enrollment updated successfully")
    except AcadStackException as ex:
        msg = "Error when dropping/withdrawing the course"
        logging.exception(msg, ex)
        return apiVC.error_json(str(ex))
    except Exception as ex:
        msg = "Error when dropping/withdrawing the course"
        logging.exception(msg, ex)
        return apiVC.error_json(msg)


@rbac(permissions=["enrolment.view_instructor_courses"])
async def get_instructor_courses_enrol():
    try:
        actor = apiVC.current_actor()
        return apiVC.ok_json({
            "instructor_enrol": ENR.instructor_pending_enrolments(actor),
            "advisor_enrol": ENR.advisor_action_items(actor)})
    except Exception as ex:
        msg = "Error when fetching DB.CourseEnrollment details."
        logging.exception(msg, ex)
        return apiVC.error_json(msg)


@rbac(permissions=["enrolment.view_advisor_courses"])
async def get_advisor_courses_enrol():
    try:
        results = ENR.pending_enrolments_for_approver(apiVC.current_actor())
        return apiVC.ok_json(results)
    except Exception as ex:
        msg = "Error when fetching DB.CourseEnrollment details."
        logging.exception(msg)
        return apiVC.error_json(msg)


@rbac
async def get_passed_courses(user_id):
    try:
        VAL.is_current_user_in_role_and_id("STU", "user_id", user_id, 
            "Student attempted to access passed courses data for someone else.")

        codes = ENR.passed_course_codes(user_id)
        if codes is None:
            return apiVC.error_json(f"Student not found for ID {user_id}")
        return apiVC.ok_json({"codes": codes})
    except AcadStackException as ae:
        return apiVC.error_json(str(ae))
    except Exception as ex:
        msg = "Error when fetching student academic details."
        logging.exception(msg)
        return apiVC.error_json(msg)


@rbac(permissions=["enrolment.bulk_enrol"])
async def bulk_enrol_in_course(entry_no_pattern, co_id):
    try:
        if not apiVC.roll_number_valid(entry_no_pattern):
            return apiVC.error_json("Invalid entry number pattern!")

        num, course_title = ENR.bulk_enrol(apiVC.current_actor(),
                                           entry_no_pattern, co_id)
        return apiVC.ok_json(f"Enrolled {num} students in {course_title} course.")

    except AcadStackException as ae:
        logging.exception(ae)
        return apiVC.error_json(str(ae))
    except Exception as ex:
        msg = "Error when bulk enrolling students."
        logging.exception(msg)
        return apiVC.error_json(msg)


@rbac
async def download_course_enrollments(co_id):
    return await _enrolments_csv_response(co_id, is_grades=False)


@rbac(permissions=["enrolment.download_for_grades"])
async def download_enrollments_for_grades(co_id):
    return await _enrolments_csv_response(co_id, is_grades=True)


async def _enrolments_csv_response(co_id, is_grades):
    """Shared body of the two enrolment CSV downloads.

    Both routes used to call the same decorated view function, and the
    grades one did so without awaiting it, so it returned a coroutine
    instead of a response and never produced a file. One plain helper
    that both handlers await removes the trap.
    """
    try:
        if not apiVC.has_permission("enrolment.download_csv"):
            return apiVC.error_json("Students cannot download!")
        co = DB.CourseOffering.get_by_id(co_id)
        colnames, rows = ENR.enrolment_export_rows(
            co_id, is_grades, actor=apiVC.current_actor())

        fp = _rows_to_csv_file(colnames, rows)
        return await send_file(fp, attachment_filename=f"{co.course.code}_students.csv",
                         as_attachment=True)

    except Exception as ex:
        msg = "Error when loading enrolment data as CSV."
        logging.exception(msg)
        return apiVC.error_json(msg)


@rbac
async def download_course_enrolments(dept_name, entry_year, acad_session):
    try:
        if not apiVC.has_permission("enrolment.download_csv"):
            return apiVC.error_json("Students cannot download!")
        if dept_name == "-":
            dept_name = ""
        if entry_year == "-":
            entry_year = ""

        colnames, rows = ENR.enrolments_by_dept_year_session(
            dept_name, entry_year, acad_session)
        fp = _rows_to_csv_file(colnames, rows)
        return await send_file(fp,
                         attachment_filename="generate_course_enrolments.csv",
                         as_attachment=True)
    except Exception as ex:
        msg = "Error when loading enrolment data as CSV."
        logging.exception(msg)
        return apiVC.error_json(msg)


@rbac
async def get_student_academics(my_id):
    try:
        VAL.is_current_user_in_role_and_id("STU", "user_id", my_id, 
            "Student attempted to access other's academics details.")

        stu = DB.User.get_or_none(my_id)
        if not stu:
            return apiVC.error_json(f"Student not found for ID {my_id}")
        return apiVC.ok_json(TR.courses_perf(stu, True))
    except AcadStackException as ae:
        return apiVC.error_json(str(ae))
    except Exception as ex:
        msg = "Error when fetching student academic details."
        logging.exception(msg)
        return apiVC.error_json(msg)


@rbac
async def get_course_enrollments(my_id):
    try:
        result = ENR.enrolments_for_offering(my_id)
        if result:
            return apiVC.ok_json(result)
        else:
            return apiVC.error_json("No enrolments found for course offering!")
    except Exception as ex:
        msg = "Error when fetching DB.CourseEnrollment details."
        logging.exception(msg)
        return apiVC.error_json(msg)


@rbac(permissions=["enrolment.request"])
async def enroll_in_courses():
    try:
        fd = await request.get_json(force=True)
        logging.debug("Enrolling student in courses: {}".format(fd))
        outcome = ENR.request_enrolment(
            apiVC.current_actor(), int(fd["user_id"]), fd["co_ids"],
            fd["enrol_type"],
            static_data=apiVC.static_data_item("CourseSlots"))

        if outcome.conflicts:
            return apiVC.error_json(outcome.conflicts)
        if outcome.message == "":
            return apiVC.ok_json("Enrollment requested successfully!")
        elif len(outcome.allowed_courses) != 0 and len(outcome.message):
            return apiVC.ok_json("Enrollment requested successfully for " + str(outcome.allowed_courses).replace('[','').replace(']','').replace('\'','') + ". " + outcome.message)
        else:
            return apiVC.ok_json(outcome.message)
    except IntegrityError as iex:
        msg = "Enrollment already exists for one of the selected courses."
        logging.exception(msg)
        return apiVC.error_json("ERROR: {0}".format(msg))
    except AcadStackException as ae:
        logging.exception(ae)
        return apiVC.error_json(str(ae))
    except Exception as ex:
        msg = "Error when saving course enrollment details."
        logging.exception(msg)
        return apiVC.error_json("{0}".format(msg))


@rbac(permissions=["enrolment.change_status"])
async def change_enroll_status():
    try:
        fd = await request.get_json(force=True)
        eids = fd.get("ids")
        status = fd.get("status")
        if len(eids) == 0:
            return apiVC.error_json("Select students to enrol first!")

        ENR.change_status(apiVC.current_actor(), eids, status)

        logging.info("Enrolled students in courses: {}".format(fd))
        return apiVC.ok_json("Changed successfully!")

    except AcadStackException as ae:
        logging.exception(ae)
        return apiVC.error_json(str(ae))

    except Exception as ex:
        msg = "Error when changing course enrollment status."
        logging.exception(msg)
        return apiVC.error_json("{0}".format(msg))


@rbac
async def course_enrollment_view(my_id):
    try:
        res = ENR.enrolment_for_view(apiVC.current_actor(), my_id)
        if not res:
            return apiVC.error_json(f"Enrollment record not found for ID {my_id}")
        obj = model_to_dict(res,
                            exclude=[DB.CourseEnrollment.course_offering.course.author,
                                     DB.CourseEnrollment.student.password_hashed])
        return apiVC.ok_json(obj)
    except AcadStackException as ae:
        return apiVC.error_json(str(ae))
    except Exception as ex:
        msg = "Error when fetching DB.CourseEnrollment details."
        logging.exception(msg)
        return apiVC.error_json(msg)


@rbac
async def course_enrollment_save():
    try:
        fd = await request.get_json(force=True)
        logging.debug(f"Saving course enrollment details: {fd}")
        outcome = ENR.save_enrolment(apiVC.current_actor(), fd)
        if outcome.error:
            return apiVC.error_json(outcome.error)
        return await course_enrollment_view(outcome.enrolment_id)
    except AcadStackException as ae:
        logging.exception(ae)
        return apiVC.error_json(str(ae))
    except Exception as ex:
        msg = "Error when saving course enrollment details."
        logging.exception(msg, ex)
        return apiVC.error_json(msg)


def _rows_to_csv_file(colnames, rows) -> BytesIO:
    result = [','.join(colnames)]
    for row in rows:
        result.append(','.join(map(str, row)))
    fp = BytesIO()
    fp.write('\n'.join(result).encode('utf-8'))
    fp.flush()
    fp.seek(0)
    return fp
