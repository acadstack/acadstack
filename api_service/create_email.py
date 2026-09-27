"""functions related to sending mail.

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__version__ = "0.1"
__status__ = "Development"
"""

import logging
from jinja2 import Environment, FileSystemLoader
from common import emailer, sql_by_id
import api_common as apiVC
import models as DB


def __make_email_body(template_name, data_dict):
    env = Environment(loader=FileSystemLoader('email_templates'))
    tpl = env.get_template(template_name)
    return tpl.render(data_dict)


def send_grades_submission_email(co_id, upd_count):
    try:
        res = DB.CourseInstructor.select(
            DB.Course.code, DB.Course.title, DB.User.email) \
            .join(DB.CourseOffering).join(DB.Course).switch(
            DB.CourseInstructor).join(DB.User).where(
            DB.CourseOffering.id == co_id)
        to = []
        for r in res:
            to.append(r.instructor.email)
        res1 = DB.User.select().where(DB.User.role == "ACA")
        for r in res1:
            to.append(r.email)
        to = ', '.join(to)

        data = {"title": res.dicts()[0]["title"],
                "code": res.dicts()[0]["code"], 
                "upd_count": upd_count}

        subject = "Grades submitted for {0}".format(data["title"])
        body = __make_email_body("grades_upload_confirmation.txt", data)

        emailer.send_mail(to, subject, body)
    except Exception as ex:
        msg = "Error when creating template."
        logging.exception(msg)


def send_enrolment_email(enrol_id, old_rec=None):
    try:
        cursor = DB.db.execute_sql(sql_by_id("enrolment_info"), [int(enrol_id)])
        enrol_info = cursor.fetchall()[0]
        data = {}
        if enrol_info:
            data["course"] = enrol_info[0]
            data["instructor"] = enrol_info[1]
            data["instructor_email"] = enrol_info[2]
            data["student"] = enrol_info[3]
            data["student_email"] = enrol_info[4]
            data["enrol_status"] = dict(DB.CourseEnrollment.ENROL_STATUSES)[enrol_info[5]]
            data["acad_session"] = enrol_info[6]
            data["grade"] = enrol_info[7]
            data["enrol_type"] = enrol_info[8]
            data["remarks"] = enrol_info[9]
            if old_rec:
                data["old_rec"] = old_rec

        body = __make_email_body("enrolment_status_changed.txt", data)
        to = "{0},{1}".format(data["instructor_email"],
                              data["student_email"])
        subject = "Changed enrollment status"
        emailer.send_mail(to, subject, body)
    except Exception as ex:
        msg = "Error when creating template."
        logging.exception(msg)


def send_password_reset_code(email, code):
    try:
        body = __make_email_body("password_reset_key.txt",
                                {"key": code})
        subject = "Password reset Key"
        emailer.send_mail(email, subject, body)
    except Exception as ex:
        msg = "Error when sending PRK."
        logging.exception(msg)


def send_password_changed_alert(email, name):
    try:
        body = __make_email_body("password_reset_notification.txt",
                                {"name": name})
        subject = "Your AcadStack password has been changed"
        emailer.send_mail(email, subject, body)
    except Exception as ex:
        msg = "Error when sending password change alert."
        logging.exception(msg)


def send_user_creation_email(email, login_id):
    try:
        body = __make_email_body("new_user.txt", {"login_id": login_id})
        subject = "DB.User Account created"
        emailer.send_mail(email, subject, body)

    except Exception as ex:
        msg = "Error when sending user creation alert."
        logging.exception(msg)


def send_offering_updated_email(co_id, old_status, new_status):
    try:
        cursor = DB.db.execute_sql(sql_by_id("course_offering_info"),
                                   [int(co_id)])
        co_info = cursor.fetchall()[0]
        data = {}
        if co_info:
            data["course"] = co_info[0]
            data["instructor"] = co_info[1]
            data["instructor_email"] = co_info[2]
            data["hod_email"] = co_info[4]
            data["old_status"] = dict(DB.CourseOffering.CO_STATUSES)[old_status]
            data["new_status"] = dict(DB.CourseOffering.CO_STATUSES)[new_status]
            data["acad_session"] = co_info[5]
            data["dept_name"] = co_info[6]
        body = __make_email_body("offering_status_changed.txt", data)
        to = "{0},{1}".format(data["instructor_email"], data["hod_email"])
        subject = "Changed course offering status"
        emailer.send_mail(to, subject, body)
    except Exception as ex:
        msg = "Error when sending CO status email."
        logging.exception(msg)


def send_course_updated_email(crs_id, old_status):
    try:
        cursor = DB.db.execute_sql(sql_by_id("course_info"), [int(crs_id)])
        co_info = cursor.fetchall()[0]
        data = {}
        if co_info:
            data["course"] = co_info[0]
            data["author"] = co_info[1]
            data["author_email"] = co_info[2]
            data["status"] = dict(DB.Course.COURSE_STATUSES)[co_info[3]]

        body = __make_email_body("course_status_changed.txt", data)
        to = data["author_email"]
        subject = "Changed course status"
        emailer.send_mail(to, subject, body)
    except Exception as ex:
        msg = "Error when sending course details change email."
        logging.exception(msg)


def send_credit_violation_email(student_data):
    try:
        body = __make_email_body("send_credit_violation_email.txt",
                                 student_data)
        to = student_data["email"]
        subject = "DB.Course credits violation"
        emailer.send_mail(to, subject, body)
    except Exception as ex:
        msg = "Error when creating template."
        logging.exception(msg)


def send_access_violation_alert(message_txt):
    try:
        to_list=[]
        if apiVC.is_user_in_role("STU"):
            u = apiVC.logged_in_user()
            u.is_locked = True
            apiVC.save_entity(u)
            to_list.append(u.email)
            message_txt += " DB.User's AcadStack account has been locked."
            apiVC.logout(send_response=False)
        body = __make_email_body("access_violation.txt",
                                {"message": message_txt})
        subject = "AcadStack access violation alert"
        to_list.append("acadstack_help@iitrpr.ac.in")
        to = ', '.join(to_list)
        emailer.send_mail(to, subject, body)
    except Exception as ex:
        msg = "Error when sending access violation alert."
        logging.exception(msg)


def send_events_alert_email(events_today, events_tomorrow):
    try:
        data = {"events_today": events_today, 
                "events_tomorrow": events_tomorrow}
        body = __make_email_body("upcoming_events.txt", data)
        # Send to both students and faculty
        # TODO: Get the email ids from some config
        to = "students@iitrpr.ac.in,faculty-broadcast@iitrpr.ac.in"
        subject = "Academic calendar event(s) alert"
        emailer.send_mail(to, subject, body)
    except Exception as ex:
        msg = "Error when creating template."
        logging.exception(msg)


