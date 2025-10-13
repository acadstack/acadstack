from create_email import send_access_violation_alert
import logging

from common import AcadStackException, sql_by_id, current_dt_str
import models as DB
import api_common as apiVC


def validate_course_instructor(co_id, allowed_role="*", coordinator_only=True):
    if allowed_role != "*" and apiVC.is_user_in_role(allowed_role):
        return True
    ci = DB.CourseInstructor.select().where(
        (DB.CourseInstructor.offering == co_id)
        & (DB.CourseInstructor.instructor == apiVC.logged_in_user().id))
    
    if coordinator_only:
        ci = ci.where(DB.CourseInstructor.is_coordinator == True)

    if not ci.exists():
        msg = "Detected attempt by user {0} to edit/access (other's) course offering ID {1}.".format(apiVC.current_login_id(), co_id)
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


def is_course_status_valid_for_current_user(status_old):
    if status_old in "APP,RET" and not apiVC.is_user_in_role("DEA,ACA,RES"):
        return False
    else:
        return True


def validate_coff_status(co):
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
            not apiVC.is_user_in_role(["ACA", "DEA"]):
        raise AcadStackException("Cannot change data for a course that has ended/canceled!")


def check_enrollment_allowed(co):
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
 
    if apiVC.is_user_in_role(["STU"]) and co.status not in ["E", "R"]:
        msg = "User {0} forcibly attempted to enrol in course {1}.".format(
            apiVC.current_login_id(), co.course.code)
        logging.error(msg)
        send_access_violation_alert(msg)
        raise AcadStackException("You are not allowed to make this change. Incident has been reported!")
 

def is_course_add_drop_open(for_acad_session):
    return is_today_between_events("COURSE_REG_S", 
                "COURSE_REG_E", for_acad_session) or \
           is_today_between_events("ADD_DROP_S", 
                "ADD_DROP_E", for_acad_session)


def is_course_withdraw_open(for_acad_session):
    return is_today_between_events("WITHDRAW_S", 
            "WITHDRAW_E", for_acad_session)


def validate_enrolment_change(enrl, status):
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
    
    # Academic section and dean can make a change
    if apiVC.is_user_in_role(["ACA", "DEA"]):
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
        if (apiVC.is_user_in_role("STU") and ce.student.id != 
            apiVC.logged_in_user().id):
            
            logging.error(f"User {apiVC.current_login_id()} attempted changing"
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
        if (apiVC.is_user_in_role("STU") and ce.student.id != 
            apiVC.logged_in_user().id):
            logging.error(f"User {apiVC.current_login_id()} attempted to drop"
                          f" courses of user {ce.student.login_id}")
            raise AcadStackException("Cannot change others' enrolment. Your "
                                "attempt to do so has been reported.")


def is_today_between_events(event1, event2, for_acad_session=None):
    acad_session = for_acad_session or apiVC.current_acad_session()
    if not acad_session:
        return False

    res1 = DB.AcademicCalendar.select(DB.AcademicCalendar.event_value).where(
        (DB.AcademicCalendar.acad_session == acad_session) & 
        (DB.AcademicCalendar.event_code == event1))
    res2 = DB.AcademicCalendar.select(DB.AcademicCalendar.event_value).where(
        (DB.AcademicCalendar.acad_session == acad_session) & 
        (DB.AcademicCalendar.event_code == event2))

    now_str = current_dt_str()
    if res1.exists() and res2.exists():
        if res1[0].event_value <= now_str <= res2[0].event_value:
            return True
    return False


def get_event_date(event_code, for_acad_session=None):
    acad_session = for_acad_session or apiVC.current_acad_session()
    if not acad_session:
        raise AcadStackException("Current academic session not configured.")

    res1 = DB.AcademicCalendar.select(DB.AcademicCalendar.event_value).where(
        (DB.AcademicCalendar.acad_session == acad_session) & 
        (DB.AcademicCalendar.event_code == event_code))

    if res1.exists():
        return res1[0].event_value
    else:
        raise AcadStackException("Event {0} not configured in {1}."\
                            .format(event_code, acad_session))


def is_enrollment_owner_valid(coe):
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
    if apiVC.is_user_in_role("STU") and coe.student.id == apiVC.logged_in_user().id:
        valid = True
    elif apiVC.is_user_in_role("FAC") and validate_course_instructor(coe.course_offering):
        valid = True
    elif apiVC.is_user_in_role(["DEA", "ACA"]):
        valid = True
    elif apiVC.is_user_in_role("HOD"):
        valid = is_hod_for_course_offering(coe.course_offering, 
                                           apiVC.logged_in_user().id)
    else:
        valid = False
    
    if not valid:
        msg = "DB.User {0} attempted to access enrollment ID {1}." \
            .format(apiVC.current_login_id(), coe.id)
        logging.error(msg)
        send_access_violation_alert(msg)
    return valid


def is_feedback_open(acad_session, fb_form_type):
    """Checks whether the feedback submission is open for the given academic
    session.

    Args:
        acad_session (str): Academic session. E.g. 2025-II etc.
        fb_form_type (str): Type of feedback for. E.g. mid-semester or
        end-semester feedback.

    Raises:
        AcadStackException: When fb_form_type is not END_SEM_FB or MID_SEM_FB

    Returns:
        bool: True if the supplied feedback type is open for the
        given academic session.
    """
    if fb_form_type == "END_SEM_FB":
        return is_today_between_events("FEEDBACK_S", "FEEDBACK_E", 
                                       acad_session)
    elif fb_form_type == "MID_SEM_FB":
        return is_today_between_events("FEEDBACK_MID_S", "FEEDBACK_MID_E",
                                       acad_session)
    else:
        raise AcadStackException("Unsupported feedback form type: {}".format(
            fb_form_type))


def is_current_user_in_role_and_id(role, get_by, arg_for_get_by, error_msg):
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
    if not apiVC.is_user_in_role(role):
        return
    
    key = None
    if get_by == "user_id":
        key = apiVC.logged_in_user().id
    elif get_by == "login_id":
        key = apiVC.logged_in_user().login_id
    elif get_by == "org_id":
        key = apiVC.logged_in_user().person.org_id
    else:
        raise AcadStackException(f"Invalid query type {get_by} for check.")

    if key != arg_for_get_by:
        msg = "Illegal access! {0} Logged-in user {1}. Target user {2}." \
            .format(error_msg, apiVC.current_login_id(), arg_for_get_by)
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
    total_credits = res[0][0]
    if total_credits > 24:
        raise AcadStackException("Max. 24 credits allowed! Please remove course enrolments.")
