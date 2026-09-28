"""View functions related to student attendance.

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__version__ = "0.1"
__status__ = "Development"
"""


import os
import uuid
from quart import Blueprint, request, current_app as APP
from datetime import datetime as DT
import logging
import validation_checks as VAL
import api_common as apiVC
import settings as ST
import models as DB
import common as C
import face_api_proxy as fapi
import policy as P


def init_routes(bp: Blueprint):
    bp.add_url_rule('/att_find', view_func=attendance_find, methods=['POST'])
    bp.add_url_rule('/mark_attendance', view_func=mark_attendance, methods=['POST'])
    bp.add_url_rule('/get_student_att_details/<int:my_id>', view_func=get_student_attendance_details,
                       methods=['GET'])
    bp.add_url_rule('/daywise_att/<int:co_id>', view_func=get_daywise_attendance, methods=['GET'])
    bp.add_url_rule('/course_attd_on_date/<int:co_id>/<string:att_dt>', view_func=get_course_attd_on_date, methods=['GET'])


def _process_attendance_photos(ap_id):
    # Runs as a background task on a worker thread, which needs its own
    # DB connection.
    with DB.db.connection_context():
        __process_attendance_photo(ap_id)


def __process_attendance_photo(ap_id):
    logging.info(f"Processing attendance photo ID={ap_id}")
    ap = None
    try:
        ap = DB.AttendancePhoto.get_by_id(ap_id)
        if ap.status == "DONE":
            logging.warning(f"Attendance record {ap_id} "
                            "already processed. Ignoring.")
            return
        
        face_encs, user_info = _get_face_enc_and_user_info(ap)
        file_path = os.path.join(apiVC.get_upload_folder("photos"), ap.file_name)
        tpl = fapi.find_persons_in_photo(file_path,
                                         (face_encs, user_info),
                                         ST.get("face_match_tolerance"))

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
        logging.exception(msg)
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


@P.require("attendance.mark")
async def mark_attendance():
    try:
        form = await request.form
        files = await request.files
        co = form.get('course_offering')
        photos = files.getlist("group_photos")
        if not photos:
            return apiVC.error_json("Please select at least one photo.")
        if not P.current_actor().allowed("attendance.mark",
                                         own=lambda: VAL.validate_course_instructor(co)):
            return apiVC.error_json("Insufficient privileges. Only the course coordinator can upload attendance.")

        # Raises exception when change not allowed
        VAL.validate_coff_status(int(co))
        ap_ids = []
        with DB.db.atomic() as txn:
            for ph in photos:
                f_nm = "ATTEND_{0}.jpg".format(uuid.uuid4())
                file_path = os.path.join(apiVC.get_upload_folder("photos"), f_nm)
                await ph.save(file_path)
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
    except Exception as ex:
        msg = "Error when saving attendance photos."
        logging.exception(msg)
        return apiVC.error_json(msg)


@P.require("offerings.view")
async def attendance_find():
    try:
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

        courses = query.order_by(-DB.Course.id).paginate(pg_no, ST.get("page_size"))
        serialized = [apiVC.model_to_dict(r, exclude=[DB.CourseOffering.course.author]) 
                      for r in courses]

        has_next = len(courses) >= ST.get("page_size")
        res = {"courses": serialized, "pg_no": pg_no, "pg_size": ST.get("page_size"),
               "has_next": has_next}
        return apiVC.ok_json(res)

    except Exception as ex:
        msg = "Error when finding courses."
        logging.exception(msg)
        return apiVC.error_json(msg)


def __get_attendance_photos(co, attend_dt):
    res = co.attendance_photos.where(
            (DB.AttendancePhoto.is_deleted != True) &
            (DB.AttendancePhoto.attend_dt == attend_dt))
    return [p.file_name for p in res]


@P.require("students.academics")
async def get_student_attendance_details(my_id):
    try:
        ce = DB.CourseEnrollment.select().where(DB.CourseEnrollment.id == my_id)
        if ce:
            roll_no = ce[0].student.person.org_id
            VAL.check_own_or_any("students.academics", "org_id", roll_no, 
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
    except C.AcadStackException as ae:
        return apiVC.error_json(str(ae))
    except Exception as ex:
        msg = "Error when fetching attendance details."
        logging.exception(msg)
        return apiVC.error_json(msg)


@P.require("attendance.view")
async def get_daywise_attendance(co_id):
    try:
        if not P.current_actor().allowed("attendance.view", own=lambda:
                VAL.validate_course_instructor(co_id, coordinator_only=False)):
            return apiVC.error_json("You cannot access this attendance data!")
        sql = C.sql_by_id("daywise_attendance")
        cursor = DB.db.execute_sql(sql, [co_id])
        rs = apiVC.result_set_from_cursor(cursor)
        if not rs:
            return apiVC.error_json("No attendance records found for the course.")
        else:
            return apiVC.ok_json(rs)
    except Exception as ex:
        msg = "Error occurred when fetching daywise attendance for course."
        logging.exception(msg)
        return apiVC.error_json(msg)


@P.require("attendance.view")
async def get_course_attd_on_date(co_id, att_dt):
    try:
        if not P.current_actor().allowed("attendance.view", own=lambda:
                VAL.validate_course_instructor(co_id, coordinator_only=False)):
            return apiVC.error_json("You cannot access this attendance data!")
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
    except Exception as ex:
        msg = "Error occurred when fetching attendance for given date."
        logging.exception(msg)
        return apiVC.error_json(msg)
