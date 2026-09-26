"""View functions related to managing the courses.

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__version__ = "0.1"
__status__ = "Development"
"""


import os
import uuid
from quart import Blueprint, request, current_app as APP
from quart.helpers import send_file
from datetime import datetime as DT
from create_email import (send_access_violation_alert, 
                          send_events_alert_email)
import logging
import validation_checks as VAL
import api_common as apiVC
import models as DB
import common as C
import face_api_proxy as fapi
from domain import dc as DCD

def init_routes(bp: Blueprint):
    bp.add_url_rule('/download_degree_wise_students/<string:course_code>/<string:acad_session>',
                       view_func=download_degree_wise_students, methods=['GET'])    
    bp.add_url_rule('/get_advisor_detail/<int:my_id>', view_func=get_advisor_detail, methods=['GET'])
    bp.add_url_rule('/dc_save', view_func=dc_save, methods=['POST'])
    bp.add_url_rule('/dc_view/<int:dc_id>', view_func=dc_details, methods=['GET'])
    bp.add_url_rule('/dc_find', view_func=dc_search, methods=['POST'])
    bp.add_url_rule('/my_dc_students', view_func=get_dc_students, methods=['GET'])
    bp.add_url_rule('/ppr_save', view_func=save_progress_report, methods=['POST'])
    bp.add_url_rule('/ppr_get/<int:myid>', view_func=get_ppr, methods=['GET'])
    bp.add_url_rule('/student_pprs/<int:myid>', view_func=get_pprs_for_student, methods=['GET'])
    bp.add_url_rule('/isdcc/<int:uid>/<int:std_id>', view_func=is_dc_chair, methods=['GET'])
    bp.add_url_rule('/get_instructor_academics/<int:my_id>', 
                        view_func=get_instructor_academics, methods=['POST'])
    bp.add_url_rule('/att_find', view_func=attendance_find, methods=['POST'])
    bp.add_url_rule('/mark_attendance', view_func=mark_attendance, methods=['POST'])
    bp.add_url_rule('/get_student_att_details/<int:my_id>', view_func=get_student_attendance_details,
                       methods=['GET'])
    bp.add_url_rule('/daywise_att/<int:co_id>', view_func=get_daywise_attendance, methods=['GET'])
    bp.add_url_rule('/course_attd_on_date/<int:co_id>/<string:att_dt>', view_func=get_course_attd_on_date, methods=['GET'])
    bp.add_url_rule('/open_events', view_func=get_open_events, methods=['GET'])
    bp.add_url_rule('/download_dept_wise_avg/<string:form_type>/<string:acad_session>',
                       view_func=download_dept_wise_avg, methods=['GET'])
    bp.add_url_rule('/load_slots', view_func=load_course_slot_timings, methods=['GET'])


def _process_attendance_photos(ap_id):
    logging.info(f"Processing attendance photo ID={ap_id}")
    try:
        ap = DB.AttendancePhoto.get_by_id(ap_id)
        if ap.status == "DONE":
            logging.warning(f"Attendance record {ap_id} "
                            "already processed. Ignoring.")
            return
        
        face_encs, user_info = _get_face_enc_and_user_info(ap)
        file_path = os.path.join(apiVC.get_upload_folder("photos"), ap.file_name)
        tpl = fapi.find_persons_in_photo(file_path,
                                         (face_encs, user_info))

        names_found, names_missing, len_grp_faces, im_b64 = tpl
        logging.info(f"Total faces={len_grp_faces}, known={len(names_found)},"
                     f" missing={len(names_missing)}")
        all_faces = []
        all_faces.extend(names_found)
        all_faces.extend(names_missing)

        with DB.db.atomic() as txn:
            for user in all_faces:
                is_present = False
                if any(x for x in names_found if x["enrollment_id"] == user["enrollment_id"]):
                    # Mark user present
                    is_present = True

                sar = DB.StudentAttendance.select().where(
                    (DB.StudentAttendance.enrollment_id == user['enrollment_id']) &
                    (DB.StudentAttendance.attend_dt == ap.attend_dt)
                )
                if len(sar) == 0:
                    sar = DB.StudentAttendance()
                    sar.enrollment = user['enrollment_id']
                    sar.attend_dt = ap.attend_dt
                    sar.attend = "P" if is_present else "A"
                    apiVC.save_entity(sar)
                else:
                    # Retain an existing P when marking via class photo
                    if is_present or sar[0].attend == "P":
                        sar[0].attend = "P"
                    else:
                        sar[0].attend = "A"
                    apiVC.update_entity(DB.StudentAttendance, sar[0])
            
            ap.status = "DONE"
            apiVC.update_entity(DB.AttendancePhoto, ap)
            txn.commit()
        logging.info(f"Updated the attendance records for photo ID: {ap_id}")
    except Exception as ex:
        msg = "Error when processing attendance marking task."
        logging.exception(msg, ex)
        if ap:
            ap.status = "ERROR"
            apiVC.update_entity(DB.AttendancePhoto, ap)


def _get_face_enc_and_user_info(ap):
    face_encs = []
    user_info = []
        
    for ce in ap.offering.enrollments:
        kf = ce.student.known_faces
        if kf:
            face_encs.append(apiVC.json_to_np(kf[0].face_enc))
            obj = {"enrollment_id": ce.id,
                        "user_id": ce.student.id,
                        "login_id": ce.student.login_id,
                        "name": ce.student.get_full_name()}
            user_info.append(obj)
        else:
            logging.warning(f"No face encoding found for {ce.student.login_id}")
    if not face_encs:
        raise C.AcadStackException("None of the enrolled students have their "
                            "photos in the database!")
    return face_encs,user_info


@C.rbac(permissions=["dc.mark_attendance"])
async def mark_attendance():
    form = await request.form
    files = await request.files
    co = form.get('course_offering')
    photos = files.getlist("group_photos")
    if not photos:
        return apiVC.error_json("Please select at least one photo.")
    if not (apiVC.has_permission("dc.mark_attendance_any")
            or VAL.validate_course_instructor(co)):
        return apiVC.error_json("Insufficient privileges. Only the course coordinator can upload attendance.")

    # Raises exception when change not allowed
    VAL.validate_coff_status(int(co))
    ap_ids = []
    with DB.db.atomic() as txn:
        for ph in photos:
            f_nm = "ATTEND_{0}.jpg".format(uuid.uuid4())
            file_path = os.path.join(apiVC.get_upload_folder("photos"), f_nm)
            ph.save(file_path)
            ap = DB.AttendancePhoto(attend_dt = DT.now(), 
                    status = "PENDING", offering=int(co),
                    file_name=f_nm)
            if apiVC.save_entity(ap) != 1:
                raise C.AcadStackException("Could not save the attendance file record.")
            
            ap_ids.append(ap.id)

        txn.commit()

    for apid in ap_ids:
        APP.add_background_task(_process_attendance_photos, apid)

    return apiVC.ok_json(f"Saved {len(photos)} photos for processing.")


@C.rbac(permissions=["dc.view_instructor_academics"])
async def get_instructor_academics(my_id):
    VAL.is_current_user_in_role_and_id("FAC", "user_id", my_id, 
                                  ("Instructor attempted to access other's"
                                  " academic information."))

    fd = await request.get_json(force=True)
    pg_no = int(fd.get('pg_no', 1))
    subquery = DB.CourseEnrollment.select(DB.CourseEnrollment.course_offering_id,
                DB.ORM.fn.COUNT(DB.CourseEnrollment.student_id)\
                    .alias('classSize')).group_by(
                        DB.CourseEnrollment.course_offering_id)
    
    query = DB.CourseOffering.select(DB.CourseOffering.course_id, 
                                     DB.CourseOffering.acad_session,
                                  subquery.c.course_offering_id, 
                                  subquery.c.classSize, DB.Course.code, 
                                  DB.Course.ltp, DB.Course.title, 
                                  DB.CourseInstructor.instructor_id)\
                                    .join(DB.Course).switch(
                                    DB.CourseOffering).join(
                                        DB.CourseInstructor).join(
                                            subquery, on=(subquery.c.course_offering_id \
                                                          == DB.CourseOffering.id))\
                                .where(DB.CourseInstructor.instructor_id == my_id)

    courses = query.order_by(DB.CourseOffering.course_id).paginate(pg_no, apiVC.page_size())

    serialized = [{"id": r['course_offering_id'], "code": r['course'], 
                   "session": r['acad_session'], "classSize": r['classSize'], 
                   "name": r['code'] + ' ' + r['title'] + '(' + r['ltp'] + ')',
                   "insId": r['instructor'], "feedback": 'NA'}
                  for r in courses.dicts()]

    has_next = len(courses) >= apiVC.page_size()
    res = {"courses": serialized, "pg_no": pg_no, "pg_size": apiVC.page_size(),
           "has_next": has_next}

    return apiVC.ok_json(res)


@C.rbac
async def attendance_find():
    fd = await request.get_json(force=True)
    code, ltp, title = fd.get("code"), fd.get("ltp"), fd.get("title")
    pg_no = int(fd.get('pg_no', 1))
    query = DB.CourseOffering.select().join(DB.Course)
    if ltp:
        query = query.where(DB.CourseOffering.course.ltp == ltp)

    if code:
        query = query.where(DB.CourseOffering.course.code.contains(code))

    if title:
        query = query.where(DB.CourseOffering.course.title.contains(title))

    courses = query.order_by(-DB.Course.id).paginate(pg_no, apiVC.page_size())
    serialized = [apiVC.model_to_dict(r, exclude=[DB.CourseOffering.course.author]) 
                  for r in courses]

    has_next = len(courses) >= apiVC.page_size()
    res = {"courses": serialized, "pg_no": pg_no, "pg_size": apiVC.page_size(),
           "has_next": has_next}
    return apiVC.ok_json(res)


@C.rbac(permissions=["dc.view_advisor_detail"])
async def get_advisor_detail(my_id):
    res = DB.BatchAdvisors.select().where(
        DB.BatchAdvisors.user_id == my_id)
    if res:
        serialized = [{"year": r.year_of_entry, 
                       "dept": r.user.person.dept_name, 
                       "for_degree": r.for_degree} for r in res]
        return apiVC.ok_json(serialized)
    else:
        return apiVC.error_json(f"Record not found for advisor {my_id}")


def __get_attendance_photos(co, attend_dt):
    res = co.attendance_photos.where(
            (DB.AttendancePhoto.is_deleted != True) &
            (DB.AttendancePhoto.attend_dt == attend_dt))
    return [p.file_name for p in res]

@C.rbac
async def get_student_attendance_details(my_id):
    ce = DB.CourseEnrollment.select().where(DB.CourseEnrollment.id == my_id)
    if ce:
        roll_no = ce[0].student.person.org_id
        VAL.is_current_user_in_role_and_id("STU", "org_id", roll_no, 
                                  "Student attempted to view other's attendance records.")
        attendance = list(ce[0].attendance)  # A list of DB.StudentAttendance objects
        course_title = ce[0].course_offering.course.title
        acad_session = ce[0].course_offering.acad_session
        
        data = [{"lectureDate": attd.attend_dt,
                 "attendance": attd.attend,
                 "photos": __get_attendance_photos(
                            ce[0].course_offering, attd.attend_dt),
                 "remarks": attd.remarks}
                for attd in attendance]

        final_res = {"user_id": ce[0].student.id, 
                    "rollNo": roll_no, "course": course_title,
                    "session": acad_session, "records": data}

        return apiVC.ok_json(final_res)
    else:
        return apiVC.error_json(f"Attendance record not found for ID {my_id}")


@C.rbac(permissions=["course.manage_slot_timings"])
async def load_course_slot_timings():
    cst = DB.CourseSlotTiming.select().where(
        DB.CourseSlotTiming.is_deleted != True)
    data = [apiVC.model_to_dict(x) for x in cst]
    return apiVC.ok_json(data)


@C.rbac()
async def get_open_events():
    qry = C.sql_by_id("get_open_events")
    cursor = DB.db.execute_sql(qry)
    # Add the data rows
    result = []
    for row in cursor.fetchall():
        # Each item is a string "acad_session:event_code_prefix"
        # Example: 2020-W:COURSE_REG
        result.append(f"{row[0]}:{row[1]}")
    return apiVC.ok_json(result)


@C.rbac(permissions=["student.export_list"])
async def download_students_list(degree, year_of_entry, dept_name,acad_session):
    if degree == "-":
        degree = ""
    if year_of_entry == "-":
        year_of_entry = ""
    if dept_name == "-":
        dept_name = "" 
    if acad_session == "-":
        acad_session = ""   
    
    cursor = DB.db.execute_sql(C.sql_by_id("generate_student_list"),
                            [str(degree), 
                             str(year_of_entry),
                             str(dept_name),
                             str(acad_session)])

    fp = apiVC.db_result_to_excel(cursor)
    return await send_file(fp,
                     attachment_filename="download_student_list.csv",
                     as_attachment=True)


def schedule_event_alerts(config=None):
    try:
        DB.db.init(config['db_name'], **config['db_args'])
        DB.db.connect()

        cur = DB.db.execute_sql(C.sql_by_id("events_today"))
        events_today = apiVC.result_set_from_cursor(cur)
        cur = DB.db.execute_sql(C.sql_by_id("events_tomorrow"))
        events_tomorrow = apiVC.result_set_from_cursor(cur)
        if events_today or events_tomorrow:
            send_events_alert_email(events_today, events_tomorrow)
            logging.info("Sent the academic events alert email.")
        else:
            logging.info("No events alert information to send.")
    except Exception as ex:
        msg = "Error when fetching event alerts."
        logging.exception(msg, ex)
    finally:
        DB.db.close()

@C.rbac(permissions=["reports.generate"])
async def download_dept_wise_avg(form_type, acad_session):
    if form_type == "-":
        form_type = ""
    if acad_session == "-":
        acad_session = ""

    cursor = DB.db.execute_sql(C.sql_by_id("dept_wise_average"),
                            [str(form_type), str(acad_session)])

    fp = apiVC.db_result_to_excel(cursor)
    return await send_file(fp,
                     attachment_filename="download_dept_wise_avg.csv",
                     as_attachment=True)

@C.rbac(permissions=["dc.download_degree_wise_students"])
async def download_degree_wise_students(course_code, acad_session):
    if course_code == "-":
        course_code = ""
    if acad_session == "":
        acad_session = ""

    cursor = DB.db.execute_sql(C.sql_by_id("degree_wise_students"),
                            [str(course_code), str(course_code),str(acad_session)])

    fp = apiVC.db_result_to_excel(cursor)
    return await send_file(fp,
                     attachment_filename="download_degree_wise_students.csv",
                     as_attachment=True)


@C.rbac(permissions=["dc.save"])
async def dc_save():
    try:
        fd = await request.get_json(force=True)
        dc_id = DCD.save_dc(apiVC.current_actor(), fd,
                            C.update_model_skip_unknown)
        return await dc_details(dc_id)

    except C.AcadStackException as ae:
        logging.exception(ae)
        return apiVC.error_json(str(ae))
    except Exception as ex:
        msg = "Error when saving DC details."
        logging.exception(msg, ex)
        if "Duplicate entry " in str(ex):
            msg = "Duplicate record! Please check existing DC for the student."
        return apiVC.error_json(msg)

def __user_to_dcm(user):
    return {"user_id": user.id,
    "org_id": user.person.org_id,
    "first_name": user.first_name,
    "last_name": user.last_name,
    "dept_name": user.person.dept_name}


def __to_dc_dict(dc, excl_list=None):
    dc_dict = apiVC.model_to_dict(dc, exclude=excl_list)
    dc_dict["student"] = __user_to_dcm(dc.student)
    dcm_list = []
    for m in dc.dc_members.where(DB.DcMember.is_deleted != True):
        mdic = {}
        if not m.is_external:
            mdic = __user_to_dcm(m.member)
        
        mdic["ext_name"] = m.ext_name
        mdic["ext_contact"] = m.ext_contact
        mdic["is_external"] = m.is_external
        mdic["role"] = m.role
        mdic["dc_id"] = dc.id
        mdic["id"] = m.id
        mdic["txn_no"] = m.txn_no
        mdic["is_deleted"] = m.is_deleted
        dcm_list.append(mdic)
            
    dc_dict["members"] = dcm_list
    return dc_dict

@C.rbac()
async def dc_details(dc_id):
    dc_qry = DB.DcForStudent.select().where(DB.DcForStudent.id == int(dc_id))
    dcd = {}
    if dc_qry.exists():
        dcd = __to_dc_dict(dc_qry[0])
    return apiVC.ok_json(dcd)


@C.rbac
async def dc_search():
    fd = await request.get_json(force=True)
    stu_id = fd.get("student_id") or 0
    mem_id = fd.get("member_id") or 0
    mem_role = fd.get("member_role") or ""
    dept_name = fd.get("dept_name") or ""
    entry_year = fd.get("entry_year") or ""
    status = fd.get("status") or ""
    if not (stu_id or mem_id or mem_role or dept_name or \
            entry_year or status):
        return apiVC.error_json("At least one search criterion is required!")
    if (mem_role and not mem_id) or (not mem_role and mem_id):
        return apiVC.error_json("Member and role must be selected together!")
    

    dc_qry = DB.DcForStudent.select().join_from(DB.DcForStudent,
                DB.DcMember, DB.ORM.JOIN.LEFT_OUTER).join(DB.User, 
                on=(DB.DcForStudent.student == DB.User.id)).join(DB.Person)
    
    if stu_id:
        dc_qry = dc_qry.where(DB.DcForStudent.student == stu_id)
    if status:
        dc_qry = dc_qry.where(DB.DcForStudent.status == status)
    if mem_id:
        if mem_role == "S":
            dc_qry = dc_qry.where(DB.DcForStudent.supervisor == mem_id)
        else:
            dc_qry = dc_qry.where((DB.DcMember.member == mem_id) &
            (DB.DcMember.role == mem_role))
    if dept_name:
        dc_qry = dc_qry.where(DB.DcForStudent.student.person.
                              dept_name == dept_name)
    if entry_year:
        dc_qry = dc_qry.where(DB.DcForStudent.student.person.
                              year_of_entry == entry_year)
    
    dc_qry.order_by(-DB.DcForStudent.id).distinct()

    res = []
    added = []
    for dc in dc_qry:
        dcd = __to_dc_dict(dc)
        if dc.id not in added:
            added.append(dc.id)
            res.append(dcd)
    
    return apiVC.ok_json(res)


@C.rbac
async def get_dc_students():
    if not apiVC.has_permission("dc.view_dc_students"):
        return apiVC.error_json("You are not allowed to access this data.")
    uid = apiVC.logged_in_user().id
    cursor = DB.db.execute_sql(C.sql_by_id("get_dc_students"),[uid])
    data = []
    for row in cursor.fetchall():
        data.append({'user_id': row[0], 'first_name': row[1],
                    'last_name': row[2], 'email': row[3],
                    'dept_name': row[4], 'year_of_entry': row[5],
                    'org_id': row[6]})
    return apiVC.ok_json(data)


def __is_dc_member_or_admin(uid, student_id):
    if apiVC.has_permission("dc.manage_any"):
        return True
    q1 = DB.DcMember.select().join(DB.DcForStudent)
    q1 = q1.where(DB.DcMember.member==uid)
    q1 = q1.where(DB.DcForStudent.student==student_id)
    return q1.exists()


def __raise_on_invalid_ppr_status(old_st, new_st):
    if old_st == new_st or apiVC.has_permission("dc.manage_any"):
        return
    tran = "{0}>{1}".format(old_st, new_st)
    allowed = ["DRA>SUB", "SUB>APP"]
    if tran not in allowed:
        raise C.AcadStackException("Cannot change the report status!")


def __ppr_exists(stu_id, acad_sess, dcm_id):
    q1 = DB.PhDProgressReport.select()
    q1 = q1.where(DB.PhDProgressReport.student == stu_id)
    q1 = q1.where(DB.PhDProgressReport.acad_session == acad_sess)
    q1 = q1.where(DB.PhDProgressReport.dc_member == dcm_id)
    return q1.exists()


@C.rbac
async def save_progress_report():
    if not apiVC.has_permission("dc.manage_progress_report"):
        msg = (f"Student {apiVC.current_login_id()} attempted to "
                "submit progress report.")
        send_access_violation_alert(msg)
        return apiVC.error_json("You are not allowed to access this data.")
    uid = apiVC.logged_in_user().id
    fd = await request.get_json(force=True)
    pprid = fd.get("id") or 0
    ppr = DB.PhDProgressReport()
    if not __is_dc_member_or_admin(uid, fd.get("student")):
        raise C.AcadStackException("You must be a DC member!")
    rc = 0
    with DB.db.atomic() as txn:
        if pprid > 0:
            ppr = DB.PhDProgressReport.get_by_id(pprid)
            __raise_on_invalid_ppr_status(ppr.status, fd.get("status"))
            C.update_model_skip_unknown(ppr, fd)
            if ppr.status == "APP" and not is_dc_chair(uid, ppr.student.id):
                return apiVC.error_json("Only DC chair can approve the report!")
            
            rc = apiVC.update_entity(DB.PhDProgressReport, ppr)
        else:
            C.update_model_skip_unknown(ppr, fd)
            ppr.status = "DRA"
            dq = DB.DcMember.select().where(DB.DcMember.member==uid)
            if not dq.exists():
                return apiVC.error_json("You are not a DC member of the student!")
            ppr.dc_member = dq[0]
            if __ppr_exists(fd.get("student"), ppr.acad_session, 
                ppr.dc_member.id):
                return apiVC.error_json("DC member already submitted report "
                                     f"for {ppr.acad_session}.")
            
            rc = apiVC.save_entity(ppr)
        if rc != 1:
            raise C.AcadStackException("Could not save the reports data.")
    obj = apiVC.model_to_dict(ppr, recurse=False)
    return apiVC.ok_json(obj)


@C.rbac
async def get_ppr(myid):
    uid = apiVC.logged_in_user().id
    ppr = DB.PhDProgressReport.get_by_id(myid)
    if ppr.student.id != uid and apiVC.is_user_in_role("STU"):
        msg = (f"Student {apiVC.current_login_id()} attempted to access "
                "other's progress report.")
        send_access_violation_alert(msg)
        return apiVC.error_json("You are not allowed to access other's report.")
    
    if not __is_dc_member_or_admin(uid, ppr.student.id):
        raise C.AcadStackException("You must be a DC member!")
    obj = apiVC.model_to_dict(ppr, recurse=False)
    return apiVC.ok_json(obj)


@C.rbac
async def get_pprs_for_student(myid):
    uid = apiVC.logged_in_user().id        
    if myid != uid and apiVC.is_user_in_role("STU"):
        msg = (f"Student {apiVC.current_login_id()} attempted to access "
                "other's progress reports.")
        send_access_violation_alert(msg)
        return apiVC.error_json("You are not allowed to access other's reports.")

    if not __is_dc_member_or_admin(uid, myid):
        raise C.AcadStackException("You must be a DC member!")

    q1 = DB.PhDProgressReport.select().join(DB.User).where(
        DB.PhDProgressReport.student.id == myid)

    res = []
    for ppr in q1:
        obj = apiVC.model_to_dict(ppr, recurse=False)
        dm = ppr.dc_member
        obj["member"] = f"{dm.member.get_full_name()} ({dm.role})"
        res.append(obj)
    return apiVC.ok_json(res)


@C.rbac
async def is_dc_chair(uid, std_id):
    q1 = DB.DcMember.select().join(DB.DcForStudent)
    q1 = q1.where(DB.DcMember.member==uid)
    q1 = q1.where(DB.DcMember.role=="CP")
    q1 = q1.where(DB.DcForStudent.student==std_id)
    return apiVC.ok_json(q1.exists())


@C.rbac
async def get_daywise_attendance(co_id):
    if not (apiVC.has_permission("dc.view_daywise_attendance")
            or VAL.validate_course_instructor(co_id, coordinator_only=False)):
        return apiVC.error_json("You cannot access this attendance data!")
    sql = C.sql_by_id("daywise_attendance")
    cursor = DB.db.execute_sql(sql, [co_id])
    rs = apiVC.result_set_from_cursor(cursor)
    if not rs:
        return apiVC.error_json("No attendance records found for the course.")
    else:
        return apiVC.ok_json(rs)


@C.rbac
async def get_course_attd_on_date(co_id, att_dt):
    aq = DB.StudentAttendance.select().join(DB.CourseEnrollment)
    aq = aq.join(DB.User).join(DB.Person)
    aq = aq.where(DB.StudentAttendance.attend_dt == att_dt)
    aq = aq.where(DB.CourseEnrollment.course_offering == co_id)
    if aq.exists():
        data = [{"attend": x.attend, \
                "ce_id": x.enrollment.id,
                "name": x.enrollment.student.get_full_name(), \
                "roll_no": x.enrollment.student.person.org_id \
                } for x in aq]
        return apiVC.ok_json(data)
    else:
        return apiVC.error_json("No attendance record found!")
