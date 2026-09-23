"""View functions related to various reports.

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__version__ = "0.1"
__status__ = "Development"
"""

import json
from quart import Blueprint, request
from create_email import send_credit_violation_email
from domain import transcript as TR

import logging
import api_common as apiVC
import common as C
import models as DB
import tasks_helper as TH

def init_routes(bp: Blueprint):
    bp.add_url_rule('/dept.wiseavg', view_func=generate_dept_wise_avg, methods=['POST'])
    bp.add_url_rule('/feedback.stats', view_func=generate_feedback_stats, methods=['POST'])
    bp.add_url_rule('/queswise.facscore', view_func=que_wise_facfeedbkp_score, methods=['POST'])
    bp.add_url_rule('/coursewise.facultyscore', view_func=course_wise_faculty_score, methods=['POST'])
    bp.add_url_rule('/grade_distribution', view_func=grade_distribution, methods=['POST'])
    bp.add_url_rule('/cgpa_sgpa', view_func=cgpa_sgpa, methods=['POST'])
    bp.add_url_rule('/credits_earned', view_func=credits_earned_report,
                       methods=['POST'])
    bp.add_url_rule('/grades.status', view_func=generate_grade_status, 
                        methods=['POST'])
    bp.add_url_rule('/course.enrolments', view_func=generate_course_enrolments, methods=['POST'])
    bp.add_url_rule('/course_lect_in_session/<string:acad_session>', 
                        view_func=course_lect_in_session, methods=['GET'])
    bp.add_url_rule('/earned_credit_check', view_func=earned_credit_check, methods=['POST'])
    bp.add_url_rule('/notify_credit_violation', view_func=notify_credit_violation, methods=['POST'])
    bp.add_url_rule('/fees_payment_report', view_func=get_fees_payment_transactions, methods=['POST'])
    bp.add_url_rule('/get_slotwise_courses/<string:acad_session>', view_func=get_slotwise_courses,
                       methods=['GET'])
    bp.add_url_rule('/gen_students_credits/<string:acad_session>', view_func=generate_students_credits_info,
                       methods=['GET'])
    bp.add_url_rule('/job_status/<string:job_key>', view_func=get_background_task_status,
                       methods=['GET'])
    bp.add_url_rule('/stu.strength', view_func=degree_wise_students, methods=['POST'])



def __get_total_credits_data(form_data):
    degree = form_data.get("degree")
    dept_name = form_data.get("dept_name")
    course_type = form_data.get("course_type")
    entry_year = form_data.get("entry_year")
    min_cr = form_data.get("min_credits") or 0
    max_cr = form_data.get("max_credits") or 9999
    acad_session = form_data.get("acad_session") or ""
    exclude_course = form_data.get("exclude_courses") or ""
    cursor = DB.db.execute_sql(C.sql_by_id("credits_earned_report"),
                            [
                                str(exclude_course),
                                str(entry_year), str(entry_year),
                                str(degree), str(degree),
                                str(dept_name), str(dept_name),
                                str(acad_session), int(min_cr),
                                int(max_cr)])
    data = []
    for row in cursor.fetchall():
        data.append({'first_name': row[0], 'last_name': row[1],
                     'email': row[2], 'acad_session': row[3],
                     'credits': row[4], 'user_id': row[5],
                     'entry_no': row[6]
                     })
    return data


@C.rbac
async def credits_earned_report():
    try:
        if not apiVC.has_permission("reports.view"):
            return apiVC.error_json("Students not allowed access!")
        fd = await request.get_json(force=True)
        acad_session = fd.get("acad_session")

        if not apiVC.academic_session_valid(acad_session):
            return apiVC.error_json("Expected academic session in YYYY-S format.")

        data = __get_total_credits_data(fd)
        res = {"data": data}
        return apiVC.ok_json(res)
    except Exception as ex:
        msg = "Error when fetching credit stats."
        logging.exception(msg)
        return apiVC.error_json(msg)


@C.rbac
async def course_lect_in_session(acad_session):
    try:
        if not apiVC.has_permission("reports.view"):
            return apiVC.error_json("Students not allowed access!")
        if not apiVC.academic_session_valid(acad_session):
            return apiVC.error_json("Expected academic session in YYYY-S format.")

        cursor = DB.db.execute_sql(C.sql_by_id("course_lectures_in_session"),
                                [str(acad_session)])
        data = []
        for row in cursor.fetchall():
            data.append({'lecture': row[0], 'acad_session': row[1], 
                         'code': row[2], 'title': row[3]})
        res = {"data": data}
        return apiVC.ok_json(res)
    except Exception as ex:
        msg = "Error when fetching lecture stats."
        logging.exception(msg)
        return apiVC.error_json(msg)

def __get_earned_credit_data(form_data):
    degree = form_data.get("degree")
    dept_name = form_data.get("dept_name")
    course_type = form_data.get("course_type")
    entry_year = form_data.get("for_year")
    min_cr = form_data.get("min_credits") or 0
    max_cr = form_data.get("max_credits") or 9999
    acad_session = form_data.get("acad_session") or ""

    if dept_name == "ALL" or dept_name == "-":
       dept_name = ""
    if degree == "-":
       degree = ""
    if entry_year == "-":
       entry_year = ""
    if acad_session == "-":
       acad_session = ""
    if course_type == "-":
       course_type = ""
    if min_cr == "-":
       min_cr = ""
    if max_cr == "-":
       max_cr = ""
       
    if not apiVC.has_permission("reports.view"):
        raise C.AcadStackException("Students not allowed access!")

    if acad_session and not apiVC.academic_session_valid(acad_session):
        raise C.AcadStackException("Expected academic session in YYYY-S format.")
    
    cursor = DB.db.execute_sql(C.sql_by_id("filtered_categorized_credits_enrolled"),
                            [str(entry_year), str(entry_year), str(entry_year),
                             str(degree), str(degree),
                             str(dept_name), str(dept_name),
                             str(acad_session), str(acad_session),
                             str(course_type), str(course_type),
                             int(min_cr), int(max_cr)])
    data = []
    ctypes = apiVC.static_data_item("CourseTypes")
    for row in cursor.fetchall():
        data.append({'credits': __replace_ct_with_labels(row[0], ctypes), 
                     'first_name': row[1], 'last_name': row[2],
                     'entry_no': row[3], 'acad_session': row[4], 
                     'email': row[5], 'user_id': row[6]})
    return data


def __replace_ct_with_labels(creds, ctypes):
    # TODO: Optimize the for loops
    # credits: 'PC=4.5, SC=3, UnCat=6, SE=3, PE=3'
    changed = creds
    for x in creds.split(","):
        ct = x.split("=")[0].strip()
        for y in ctypes:
            if ct == y["id"]:
                changed = changed.replace(ct, y["value"])
                break

    return changed


@C.rbac
async def earned_credit_check():
    try:
        fd = await request.get_json(force=True)
        data = __get_earned_credit_data(fd)
        res = {"data": data}
        return apiVC.ok_json(res)
    except C.AcadStackException as aex:
        return apiVC.error_json(str(aex))
    except Exception as ex:
        msg = "Error when fetching credit stats."
        logging.exception(msg)
        return apiVC.error_json(msg)


@C.rbac(permissions=["reports.notify_credit_violation"])
async def notify_credit_violation():
    try:
        fd = await request.get_json(force=True)
        rep_name = fd.get("report_name")
        data = []
        if rep_name == "EARNED_CREDITS":
            data = __get_total_credits_data(fd)

        elif rep_name == "CAT_CREDITS_CHECK":
            data = __get_earned_credit_data(fd)

        mt = fd.get("mark_type")
        marked_items = fd.get("marked_items")
        email_count = 0
        for row in data:
            user_id = row["user_id"]
            if ("exclude" == mt and user_id in marked_items) \
                    or ("include" == mt and user_id not in marked_items):
                continue

            send_credit_violation_email(row)
            email_count += 1

        return apiVC.ok_json(f"Emails sent to {email_count} students!")
    except C.AcadStackException as aex:
        return apiVC.error_json(str(aex))
    except Exception as ex:
        msg = "Error when notifying the credit violation to students."
        logging.exception(msg)
        return apiVC.error_json(msg)


@C.rbac(permissions=["reports.generate"])
async def get_fees_payment_transactions():
    try:
        form_data = await request.get_json(force=True)
        degree = form_data.get("degree")
        dept_name = form_data.get("dept_name")
        entry_year = form_data.get("entry_year")
        acad_session = form_data.get("acad_session") or ""

        if acad_session and not apiVC.academic_session_valid(acad_session):
            raise C.AcadStackException("Expected academic session in YYYY-S format.")

        cursor = DB.db.execute_sql(C.sql_by_id("fees_payment_report"),
                                [str(entry_year), str(entry_year),
                                 str(degree), str(degree),
                                 str(dept_name), str(dept_name),
                                 str(acad_session), str(acad_session)])
        data = []
        for row in cursor.fetchall():
            data.append({'acad_session': row[0], 'student_id': row[1],
                         'first_name': row[2], 'last_name': row[3], 'org_id': row[4],
                         'txn_info': json.loads("[{}]".format(row[5]))})

        res = {"data": data}
        return apiVC.ok_json(res)
    except C.AcadStackException as aex:
        return apiVC.error_json(str(aex))
    except Exception as ex:
        msg = "Error when fetching payment transactions data."
        logging.exception(msg)
        return apiVC.error_json(msg)


@C.rbac(permissions=["reports.generate"])
async def generate_course_enrolments():
    try:
        form_data = await request.get_json(force=True)

        dept_name = form_data.get("dept_name")
        entry_year = form_data.get("entry_year")
        acad_session = form_data.get("acad_session")
        if dept_name == "-":
            dept_name = ""
        if entry_year == "-":
            entry_year = ""
        if acad_session and not apiVC.academic_session_valid(acad_session):
            raise C.AcadStackException("Expected academic session in YYYY-S format.")

        cursor = DB.db.execute_sql(C.sql_by_id("generate_course_enrolments"),
                                [str(entry_year), str(entry_year),
                                 str(dept_name), str(dept_name),
                                 str(acad_session)])
        data = []
        for row in cursor.fetchall():
            data.append({'first_name': row[0], 'last_name': row[1],
                         'email': row[2], 'entry_no': row[3], 
                         'entry_year': row[4], 'dept_name': row[5],
                         'title': row[11], 'code': row[6], 'acad_session': row[7],
                         'enrol_type': row[8], 'user_id': row[10]})

        res = {"data": data}
        return apiVC.ok_json(res)
    except C.AcadStackException as aex:
        return apiVC.error_json(str(aex))
    except Exception as ex:
        msg = "Error in fetching Semester Course enrolments."
        logging.exception(msg)
        return apiVC.error_json(msg)


@C.rbac(permissions=["reports.generate"])
async def generate_feedback_stats():
    try:
        form_data = await request.get_json(force=True)
        form_type = form_data.get("form_type")
        acad_session = form_data.get("acad_session")
        if form_type == "-":
            form_type = ""
        if acad_session == "-":
            acad_session = ""
        if acad_session and not apiVC.academic_session_valid(acad_session):
            raise C.AcadStackException("Expected academic session in YYYY-S format.")

        cursor = DB.db.execute_sql(C.sql_by_id("generate_feedback_stats"),
                                [str(acad_session), str(acad_session), 
                                 str(form_type)])
        data = []
        for row in cursor.fetchall():
            data.append({'students_enrolled': row[0], 
                         'no_of_students_voted': row[1],
                         'pct_students_voted': float(row[2]), 
                         'code': row[3], 'title': row[4],
                         'ltp': row[5],'offering_department': row[6],
                         'acad_session': row[7],'first_name': row[8], 
                         'last_name': row[9]})

        res = {"data": data}
        return apiVC.ok_json(res)
    except C.AcadStackException as aex:
        return apiVC.error_json(str(aex))
    except Exception as ex:
        msg = "Error in fetching Semester Course enrolments."
        logging.exception(msg)
        return apiVC.error_json(msg)


@C.rbac
async def get_slotwise_courses(acad_session):
    try:
        if acad_session and not apiVC.academic_session_valid(acad_session):
            raise C.AcadStackException("Expected academic session in YYYY-S format.")

        cursor = DB.db.execute_sql(C.sql_by_id("slotwise_courses"),
                                [str(acad_session)])
        data = {}
        for row in cursor.fetchall():
            slot = row[0].strip() or "NA"
            if slot not in data:
                data[slot] = []
            data[slot].append({'co_id': row[1], 'code': row[2],
                               'title': row[3], 'ltp': row[4], 
                               'instructor': row[5]})

        return apiVC.ok_json(data)
    except C.AcadStackException as aex:
        return apiVC.error_json(str(aex))
    except Exception as ex:
        msg = "Error in fetching slotwise courses."
        logging.exception(msg)
        return apiVC.error_json(msg)

def __process_credits_gen_request(acad_session):
    try:
        DB.db.connect(reuse_if_open=True)
        cursor = DB.db.execute_sql(C.sql_by_id("get_students_having_enrolment"),
                                [acad_session])
        entry_nos = [(row[0], row[1]) for row in cursor.fetchall()]
        logging.info("Found {0} enroled students in acad session {1}".format(
            len(entry_nos), acad_session))
        
        if not entry_nos:
            return "No student enrolments found for {0}".format(acad_session)
        
        with DB.db.atomic() as txn:
            for (user_id, roll_no) in entry_nos:
                stu = DB.User.get_by_id(user_id)
                # Fetch the student's credits data                
                data = TR.courses_perf(stu, False)
                if not (data['enrollments']["CC"] or data['enrollments']["CM"] 
                        or data['enrollments']["C"]):
                    logging.error(f"Student record not found for entry no. {roll_no}")
                    continue
                # Save the credits data
                sc_qry = DB.StudentCredits.select().where(
                            (DB.StudentCredits.student == user_id) &
                            (DB.StudentCredits.acad_session == acad_session))
                sc_exists = sc_qry.exists()
                sc = DB.StudentCredits()
                if sc_exists:
                    sc = sc_qry[0]
                
                for enrol_type, _data in data['enrollments'].items():
                    if _data["enrollments"]:
                         if acad_session in _data["enrollments"].keys():
                            perf_data = _data["enrollments"][acad_session]
                            sc.acad_session = acad_session
                            sc.student = user_id
                            sc.cgpa = perf_data["cgpa"]
                            sc.sgpa = perf_data["sgpa"]
                            sc.cred_earned = perf_data["ec"]
                            sc.cred_earned_total = perf_data["cec"]
                            sc.cred_registered = perf_data["creg"]

                            if sc_exists:
                                apiVC.update_entity(DB.StudentCredits, sc, 
                                                    outside_request=True)
                            else:
                                apiVC.save_entity(sc, True)
        msg = f"Data generated successfully for {len(entry_nos)} students. "
        "Please contact the admin for customized report."
        logging.info(msg)
        return msg
    except Exception as ex:
        msg = "Failed to generate the students credits data."
        logging.exception(msg)
        return msg


@C.rbac(permissions=["reports.generate"])
async def generate_students_credits_info(acad_session):
    try:
        job_key = TH.create_task(__process_credits_gen_request, acad_session)
        logging.info(f"Submitted background job with key {job_key}")
        return apiVC.ok_json({"job_key": job_key, "message": 
                           "Request successfully submitted."})
    except Exception as ex:
        msg = "Failed to generate the students credits data."
        logging.exception(msg)
        return apiVC.error_json(msg)


@C.rbac(permissions=["reports.generate"])
async def get_background_task_status(job_key):
    try:
        task_result = TH.pop_task_info_if_done(job_key)
        if not task_result:
            logging.error(f"Background job with key {job_key} not found.")
            return apiVC.error_json(f"Job info not found for {job_key}")
        if task_result["status"] != "done":
            return apiVC.ok_json({"status": task_result["status"], "result": "Job not done yet."})
        
        return apiVC.ok_json(task_result)
    except Exception as ex:
        msg = f"Failed to get the background job status for {job_key}."
        logging.exception(msg)
        return apiVC.error_json(msg)


@C.rbac(permissions=["reports.generate"])
async def grade_distribution():
    try:
        form_data = await request.get_json(force=True)

        degree = form_data.get("degree")
        acad_session = form_data.get("acad_session")
        if degree == "-":
            degree = ""
        if acad_session == "-":
            acad_session = ""
        if acad_session and not apiVC.academic_session_valid(acad_session):
            raise C.AcadStackException("Expected academic session in YYYY-S format.")

        cursor = DB.db.execute_sql(C.sql_by_id("generate_grade_distribution"),
                                [str(acad_session), str(degree)])
        data = []
        for row in cursor.fetchall():
            data.append({'no_of_students': row[0], 'dept_name': row[1],
                         'grade': row[2], 'code': row[3]})

        res = {"data": data}
        return apiVC.ok_json(res)
    except C.AcadStackException as aex:
        return apiVC.error_json(str(aex))
    except Exception as ex:
        msg = "Error in fetching Generate rade Distribution."
        logging.exception(msg)
        return apiVC.error_json(msg)

@C.rbac(permissions=["reports.view_cgpa_sgpa"])
async def cgpa_sgpa():
    try:
        form_data = await request.get_json(force=True)
        acad_session = form_data.get("acad_session")
       
        if acad_session == "-":
            acad_session = ""
        if acad_session and not apiVC.academic_session_valid(acad_session):
            raise C.AcadStackException("Expected academic session in YYYY-S format.")

        cursor = DB.db.execute_sql(C.sql_by_id("generate_cgpa_sgpa"),
                                [str(acad_session)])
        data = []
        for row in cursor.fetchall():
            data.append({'roll_no': row[0], 'first_name': row[1],
                         'last_name': row[2],'dept_name': row[3],
                         'cgpa': row[4], 'sgpa': row[5], 
                         'cred_earned': row[6], 'cred_registered': row[7],
                         'cred_earned_total': row[8]})

        res = {"data": data}
        return apiVC.ok_json(res)
    except C.AcadStackException as aex:
        return apiVC.error_json(str(aex))
    except Exception as ex:
        msg = "Error in fetching Generate CGPA SGPA Report."
        logging.exception(msg)
        return apiVC.error_json(msg)

@C.rbac(permissions=["reports.generate"])
async def generate_dept_wise_avg():
    try:
        form_data = await request.get_json(force=True)
        form_type = form_data.get("form_type")
        acad_session = form_data.get("acad_session")
        if form_type == "-":
            form_type = ""
        if acad_session == "-":
            acad_session = ""
        if acad_session and not apiVC.academic_session_valid(acad_session):
            raise C.AcadStackException("Expected academic session in YYYY-S format.")

        cursor = DB.db.execute_sql(C.sql_by_id("dept_wise_average"),
                                [ str(form_type), str(acad_session)])
        data = []
        for row in cursor.fetchall():
            data.append({'dept_name': row[0], 'acad_session': row[1],
                         'question': row[2], 'avg_score': float(row[3])})

        res = {"data": data}
        return apiVC.ok_json(res)
    except C.AcadStackException as aex:
        return apiVC.error_json(str(aex))
    except Exception as ex:
        msg = "Error in fetching deptartment wise avgerage:."
        logging.exception(msg)
        return apiVC.error_json(msg)


@C.rbac(permissions=["reports.generate"])
async def course_wise_faculty_score():
    try:
        form_data = await request.get_json(force=True)
        form_type = form_data.get("form_type")
        acad_session = form_data.get("acad_session")
        if form_type == "-":
            form_type = ""
        if acad_session == "-":
            acad_session = ""
        if acad_session and not apiVC.academic_session_valid(acad_session):
            raise C.AcadStackException("Expected academic session in YYYY-S format.")

        cursor = DB.db.execute_sql(C.sql_by_id("course_wise_faculty_score"),
                                [ str(form_type), str(acad_session)])
        data = []
        for row in cursor.fetchall():
            data.append({'first_name': row[0], 'last_name': row[1],
                         'acad_session': row[2],'course_code': row[3],
                         'dept_name': row[4], 'faculty_score': float(row[5]),
                         'total_votes': float(row[6])})
            
        res = {"data": data}
        return apiVC.ok_json(res)
    except C.AcadStackException as aex:
        return apiVC.error_json(str(aex))
    except Exception as ex:
        msg = "Error in fetching Course Wise Faculty Score."
        logging.exception(msg)
        return apiVC.error_json(msg)


@C.rbac(permissions=["reports.generate"])
async def que_wise_facfeedbkp_score():
    try:
        form_data = await request.get_json(force=True)
        form_type = form_data.get("form_type")
        acad_session = form_data.get("acad_session")
        if form_type == "-":
            form_type = ""
        if acad_session == "-":
            acad_session = ""
        if acad_session and not apiVC.academic_session_valid(acad_session):
            raise C.AcadStackException("Expected academic session in YYYY-S format.")

        cursor = DB.db.execute_sql(C.sql_by_id("que_wise_facfeedbk_score"),
                                [ str(form_type), str(acad_session)])
        data = []
        for row in cursor.fetchall():
            data.append({'first_name': row[0], 'last_name': row[1],  
                         'course_code': row[2],'dept_name': row[3],
                         'acad_session': row[4], 'question': row[5],
                         'q_score': float(row[6]), 'total_votes': float(row[7])})
            
        res = {"data": data}
        return apiVC.ok_json(res)
    except C.AcadStackException as aex:
        return apiVC.error_json(str(aex))
    except Exception as ex:
        msg = "Error in fetching Questions Wise Faculty Feedback."
        logging.exception(msg)
        return apiVC.error_json(msg)

@C.rbac(permissions=["reports.generate"])
async def degree_wise_students():
    try:
        form_data = await request.get_json(force=True)
        course_code = form_data.get("course_code")
        acad_session = form_data.get("acad_session")
        if course_code == "-":
            course_code = ""
        if acad_session == "-":
            acad_session = ""
        if acad_session and not apiVC.academic_session_valid(acad_session):
            raise C.AcadStackException("Expected academic session in YYYY-S format.")

        cursor = DB.db.execute_sql(C.sql_by_id("degree_wise_students"),
                                [str(course_code), str(course_code),
                                 str(acad_session)])
        data = []
        for row in cursor.fetchall():
            data.append({'code': row[0], 'title': row[1],  'ltp': row[2],
                         'offering_department': row[3],'acad_session': row[4],
                         'degree': row[5], 'no_of_students': row[6]})
            
        res = {"data": data}
        return apiVC.ok_json(res)
    except C.AcadStackException as aex:
        return apiVC.error_json(str(aex))
    except Exception as ex:
        msg = "Error in Fetching Degree Wise Students."
        logging.exception(msg)
        return apiVC.error_json(msg)


@C.rbac(permissions=["grades.export"])
async def generate_grade_status():
    try:
        form_data = await request.get_json(force=True)
        grades_st = form_data.get("selected")
        acad_session = form_data.get("acad_session")

        if acad_session == "-":
            acad_session = ""
        if acad_session and not apiVC.academic_session_valid(acad_session):
            raise C.AcadStackException("Expected academic session in YYYY-S format.")

        if grades_st == "GS":
            sql_id = "grades_status_submitted"
        else:
            sql_id = 'grades_status_pending'

        cursor = DB.db.execute_sql(C.sql_by_id(sql_id), [str(acad_session)])
        data = []
        for row in cursor.fetchall():
            data.append({'code': row[0], 'acad_session': row[1], 
                         'title': row[2], 'first_name': row[3], 
                         'last_name': row[4], 'dept_name' : row[5]})

        res = {"data": data}
        return apiVC.ok_json(res)
    except C.AcadStackException as aex:
        return apiVC.error_json(str(aex))
    except Exception as ex:
        msg = "Error in Generate Grade Status."
        logging.exception(msg)
        return apiVC.error_json(msg)