"""Shared validation and access checks.

These are called from both the HTTP adapters and the domain layer, so
every function that needs to know who is acting takes an optional
``actor`` (a :class:`domain.context.Actor`). When it is not supplied the
actor is resolved from the Quart session, exactly as before -- that is
what keeps the modules that have not been through the service-layer
extraction yet working untouched.

This module is scheduled to move under ``domain/`` once the extraction
has propagated past course enrolment; it is shared by nearly every
api_* module, so moving it early would have dragged all of them into
one change. See the service-layer section of docs/architecture.md.
"""
from create_email import send_access_violation_alert
import logging

from common import AcadStackException, sql_by_id
import models as DB
import api_common as apiVC
import settings_store as ST
from domain import academic_calendar as CAL


def validate_course_instructor(co_id, allowed_role="*", coordinator_only=True,
                               actor=None):
    actor = apiVC.actor_or_current(actor)
    if allowed_role != "*" and actor.has_role(allowed_role):
        return True
    ci = DB.CourseInstructor.select().where(
        (DB.CourseInstructor.offering == co_id)
        & (DB.CourseInstructor.instructor == actor.user_id))
    
    if coordinator_only:
        ci = ci.where(DB.CourseInstructor.is_coordinator == True)

    if not ci.exists():
        msg = "Detected attempt by user {0} to edit/access (other's) course offering ID {1}.".format(actor.login_id, co_id)
        logging.error(msg)
        send_access_violation_alert(msg)
        return False
    else:
        return True


def is_hod_for_course_offering(co_id, user_id):
    sql_qry = sql_by_id("is_hod_for_course_offering")
    cursor = DB.db.execute_sql(sql_qry, [co_id, user_id])
    res = cursor.fetchall()
    return res[0][0]


def validate_coff_status(co, actor=None):
    """Checks the status of supplied course offering by considering the role
    of current user and the status of the supplied offering.

    Args:
        co (`DB.CourseOffering` or int): Instance of CourseOffering model or
        its Id (PK).

    Raises:
        AcadStackException: If the course is finished or canceled and user is not
        having ACA or DEA role, we raise an exception.
    """
    if type(co) is int:
        co = DB.CourseOffering.get_by_id(co)
 
    if co.status in ["F", "C"] and \
            not apiVC.actor_or_current(actor).can("course_offering.edit_after_close"):
        raise AcadStackException("Cannot change data for a course that has ended/canceled!")


def check_enrollment_allowed(co, actor=None):
    """Checks if currentl user is allowed to enrol in the supplied course
    offering by considering the role of current user and the status of 
    the supplied offering.

    If the enrollment is not allowed then an email alert is sent and
    exception is raised with suitable message.

    Args:
        co (`DB.CourseOffering` or int): CourseOffering model instance
        of its Id (PK).

    Raises:
        AcadStackException: When the enrollment is not allowed.
    """
    if type(co) is int:
        co = DB.CourseOffering.get_by_id(co)
 
    actor = apiVC.actor_or_current(actor)
    if actor.has_role(["STU"]) and co.status not in ["E", "R"]:
        msg = "User {0} forcibly attempted to enrol in course {1}.".format(
            actor.login_id, co.course.code)
        logging.error(msg)
        send_access_violation_alert(msg)
        raise AcadStackException("You are not allowed to make this change. Incident has been reported!")
 

# The academic-calendar reads below live in domain.academic_calendar now
# (the domain layer needs them and must not import api_common). These
# remain as the names the api_* modules already import.
is_course_add_drop_open = CAL.is_course_add_drop_open
is_course_withdraw_open = CAL.is_course_withdraw_open
is_today_between_events = CAL.is_today_between_events
get_event_date = CAL.event_date
is_feedback_open = CAL.is_feedback_open


def validate_enrolment_change(enrl, status, actor=None):
    """Checks if the supplied status can be assigned to the given enrollment
    record. The checks take into consideration the role of the current user,
    the status of the course offerring (i.e., whether the course has finished
    etc.), type of enrollment (credit/audit etc.), the current date and the
    relevant academic calendar dates.

    The change is always allowed to a user having roles DEA and ACA.

    Args:
        enrl (`DB.CourseEnrollment`): Model object for CourseEnrollment.
        status (str): New status to be assigned.

    Raises:
        AcadStackException: When the assignment is not possible/allowed.

    Returns:
        bool: True is the change of status is allowed, else False.
    """
    if not any(s[0] == status for s in DB.CourseEnrollment.ENROL_STATUSES):
        raise AcadStackException("Unknown enrolment status: "+status)
    
    actor = apiVC.actor_or_current(actor)
    # Academic section and dean can make a change
    if actor.can("enrolment.override"):
        return True

    if isinstance(enrl, int):
        ce = DB.CourseEnrollment.get_by_id(enrl)
    else:
        ce = enrl
    
    # Enrollment change allowed only for running
    # or enrolling offerings
    if ce.course_offering.status not in ["E", "R"]:
        raise AcadStackException("Enrollment in only running/enrolling courses can be changed!")

    acad_sess = ce.course_offering.acad_session
    if ce.enrol_type == 'A': # Course is being audited only
        if not is_course_withdraw_open(acad_sess):
            raise AcadStackException(f"Course withdrawals not open for {acad_sess}.")
        # Student can drop/withdraw only their own enrollment
        if actor.has_role("STU") and ce.student.id != actor.user_id:
            logging.error(f"User {actor.login_id} attempted changing"
                          f" enrolment of user {ce.student.login_id}.")
            raise AcadStackException("Cannot change others' enrolment. Your attempt to do so has been reported.")

    else: # Everything other than an audited course
        if "WDRAW" == status and not is_course_withdraw_open(acad_sess):
            raise AcadStackException(f"Course withdrawals not open for {acad_sess}")
        elif "DROP" == status and not is_course_add_drop_open(acad_sess):
            raise AcadStackException(f"Course add/drop not open for {acad_sess}")
        elif "WDRAW" != status and not is_course_add_drop_open(acad_sess):
            raise AcadStackException(f"Course add/drop not open for {acad_sess}")
        # Student can drop/withdraw only their own enrollment
        if actor.has_role("STU") and ce.student.id != actor.user_id:
            logging.error(f"User {actor.login_id} attempted to drop"
                          f" courses of user {ce.student.login_id}")
            raise AcadStackException("Cannot change others' enrolment. Your "
                                "attempt to do so has been reported.")


def is_enrollment_owner_valid(coe, actor=None):
    """Checks whther currently logged in user is the owner of the supplied
    enrollment. If the current user has a role such as DEA or ACA then we
    always return True.
    An alert email is triggered if the check fails (i.e., when we return False).

    Args:
        coe (DB.CourseEnrollment): Enrollment object respresenting the
        corresponding row in database table.

    Returns:
        bool: True when the current user can be considered the owner of the
        supplied enrollment, else False.
    """
    actor = apiVC.actor_or_current(actor)
    if actor.has_role("STU") and coe.student.id == actor.user_id:
        valid = True
    elif actor.has_role("FAC") and validate_course_instructor(
            coe.course_offering, actor=actor):
        valid = True
    elif actor.can("enrolment.override"):
        valid = True
    elif actor.has_role("HOD"):
        valid = is_hod_for_course_offering(coe.course_offering, actor.user_id)
    else:
        valid = False
    
    if not valid:
        msg = "DB.User {0} attempted to access enrollment ID {1}." \
            .format(actor.login_id, coe.id)
        logging.error(msg)
        send_access_violation_alert(msg)
    return valid


def is_current_user_in_role_and_id(role, get_by, arg_for_get_by, error_msg,
                                   actor=None):
    """Checks whether the currently logged in user has the given role and
    the supplied identity matches the corresponding identity of the current
    user.

    Args:
        role (str): Role code to check.
        get_by (str): Identity type. Can be: user_id, login_id or org_id.
        arg_for_get_by (any): Value of identity to check.
        error_msg (str): Error message to throw when validation fails

    Raises:
        AcadStackException: When the currently logged in user does not have
        supplied role and identity.
    """
    actor = apiVC.actor_or_current(actor)
    if not actor.has_role(role):
        return
    
    key = None
    if get_by == "user_id":
        key = actor.user_id
    elif get_by == "login_id":
        key = actor.login_id
    elif get_by == "org_id":
        key = actor.org_id
    else:
        raise AcadStackException(f"Invalid query type {get_by} for check.")

    if key != arg_for_get_by:
        msg = "Illegal access! {0} Logged-in user {1}. Target user {2}." \
            .format(error_msg, actor.login_id, arg_for_get_by)
        logging.error(msg)
        send_access_violation_alert(msg)
        raise AcadStackException(msg)


def validate_course_categorization(co,stu_id):
        user = DB.User.get_by_id(stu_id)
        stu = DB.Person.get_by_id(user.person_id)
        course = DB.Course.get_by_id(co.course_id)
        status = False
        msg = ""
        allowed_courses = []
        depttypes = apiVC.static_data_item("Departments")
        degreetypes = apiVC.static_data_item("Degrees")
        cc = DB.CourseCategory.select().where(
            DB.CourseCategory.offering == int(co.id))
        for ccrow in cc:
            if (stu.dept_name == ccrow.dept or ccrow.dept == "ALL") \
                and stu.degree == ccrow.degree \
                and stu.year_of_entry in ccrow.for_entry_years:
                
                allowed_courses.append(course.code)
                status = True
        if status == False:
            msg = f"Course {course.code} is not offered for "\
                f"{apiVC.label_for_static_data_item(stu.degree, degreetypes)}-"\
                f"{stu.year_of_entry}, "\
                f"{apiVC.label_for_static_data_item(stu.dept_name, depttypes)}. "\
                f"Kindly check the Crediting Categorization of the {course.code}."
            
        return allowed_courses, msg
        

def check_enrolled_credits(user_id,acad_session):
    sql_qry = sql_by_id("credits_enrolled_by_student")
    cursor = DB.db.execute_sql(sql_qry, [user_id,acad_session])
    res = cursor.fetchall()
    # SUM() over no matching rows is NULL, which this then compared to an
    # int. It happens whenever the student has no credit-bearing
    # enrolment in the session -- notably when the enrolment being
    # checked is an audit ('A'), which the query excludes -- and the
    # TypeError surfaced to the student as "Error when saving course
    # enrollment details", with their enrolment rolled back.
    total_credits = res[0][0] or 0
    max_credits = ST.setting("enrolment.max_credits_per_session")
    if total_credits > max_credits:
        raise AcadStackException(
            f"Max. {max_credits} credits allowed! Please remove course enrolments.")
