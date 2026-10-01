"""View functions related to managing the courses.

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__version__ = "0.1"
__status__ = "Development"
"""


from quart import Blueprint, request
from quart.helpers import send_file
from create_email import send_events_alert_email
import logging
import validation_checks as VAL
import api_common as apiVC
import settings as ST
import models as DB
import common as C
import policy as P
import workflows as WF

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
    bp.add_url_rule('/open_events', view_func=get_open_events, methods=['GET'])
    bp.add_url_rule('/download_dept_wise_avg/<string:form_type>/<string:acad_session>',
                       view_func=download_dept_wise_avg, methods=['GET'])
    bp.add_url_rule('/load_slots', view_func=load_course_slot_timings, methods=['GET'])


@P.require("instructors.view")
async def get_instructor_academics(my_id):
    try:
        VAL.check_own_or_any("instructors.view", "user_id", my_id, 
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

        courses = query.order_by(DB.CourseOffering.course_id).paginate(pg_no, ST.get("page_size"))

        serialized = [{"id": r['course_offering_id'], "code": r['course'], 
                       "session": r['acad_session'], "classSize": r['classSize'], 
                       "name": r['code'] + ' ' + r['title'] + '(' + r['ltp'] + ')',
                       "insId": r['instructor'], "feedback": 'NA'}
                      for r in courses.dicts()]

        has_next = len(courses) >= ST.get("page_size")
        res = {"courses": serialized, "pg_no": pg_no, "pg_size": ST.get("page_size"),
               "has_next": has_next}

        return apiVC.ok_json(res)
    except C.AcadStackException as ae:
        return apiVC.error_json(str(ae))
    except Exception as ex:
        msg = "Error in Instructor Academics."
        logging.exception(msg)
        return apiVC.error_json(msg)


@P.require("instructors.view")
async def get_advisor_detail(my_id):
    try:
        res = DB.BatchAdvisors.select().where(
            DB.BatchAdvisors.user_id == my_id)
        if res:
            serialized = [{"year": r.year_of_entry, 
                           "dept": r.user.person.dept_name, 
                           "for_degree": r.for_degree} for r in res]
            return apiVC.ok_json(serialized)
        else:
            return apiVC.error_json(f"Record not found for advisor {my_id}")
    except Exception as ex:
        msg = "Error when fetching advisor year details."
        logging.exception(msg)
        return apiVC.error_json(msg)


@P.require("slots.manage")
async def load_course_slot_timings():
    try:
        cst = DB.CourseSlotTiming.select().where(
            DB.CourseSlotTiming.is_deleted != True)
        data = [apiVC.model_to_dict(x) for x in cst]
        return apiVC.ok_json(data)
    except Exception as ex:
        logging.error(ex)
        return apiVC.error_json("Error occurred when loading course slot timings.")


@P.require("calendar.view")
async def get_open_events():
    try:
        qry = C.sql_by_id("get_open_events")
        cursor = DB.db.execute_sql(qry)
        # Add the data rows
        result = []
        for row in cursor.fetchall():
            # Each item is a string "acad_session:event_code_prefix"
            # Example: 2020-W:COURSE_REG
            result.append(f"{row[0]}:{row[1]}")
        return apiVC.ok_json(result)
    except Exception as ex:
        logging.error(ex)
        return apiVC.error_json("Failed to fetch open events.")


@P.require("reports.students_list")
async def download_students_list(degree, year_of_entry, dept_name,acad_session):
    try:
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
    except Exception as ex:
        msg = "Error when loading enrolment data as CSV."
        logging.exception(msg)
        return apiVC.error_json(msg)


def schedule_event_alerts(config=None):
    try:
        # Runs on a scheduler thread, with its own connection to the DB
        # that the app initialised.
        with DB.db.connection_context():
            cur = DB.db.execute_sql(C.sql_by_id("events_today"))
            events_today = apiVC.result_set_from_cursor(cur)
            cur = DB.db.execute_sql(C.sql_by_id("events_tomorrow"))
            events_tomorrow = apiVC.result_set_from_cursor(cur)
            labels = apiVC.calendar_event_labels()
        for e in events_today + events_tomorrow:
            e["label"] = apiVC.calendar_entry_label(e["event_code"], labels)
        if events_today or events_tomorrow:
            send_events_alert_email(events_today, events_tomorrow)
            logging.info("Sent the academic events alert email.")
        else:
            logging.info("No events alert information to send.")
    except Exception as ex:
        msg = "Error when fetching event alerts."
        logging.exception(msg)

@P.require("feedback.reports")
async def download_dept_wise_avg(form_type, acad_session):
    try:
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
    except Exception as ex:
        msg = "Error when Downloading department wise feedback as CSV."
        logging.exception(msg)
        return apiVC.error_json(msg)

@P.require("reports.student_strength_download")
async def download_degree_wise_students(course_code, acad_session):
    try:
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
    except Exception as ex:
        msg = "Error when Downloading Degree Wise Students CSV."
        logging.exception(msg)
        return apiVC.error_json(msg)


def _save_dcm(dcm, dc_id):
    for mem in dcm:
        is_del = mem.get("is_deleted") or False
        m_id = mem.get("id") or 0
        if is_del and m_id < 1:
            continue
        mod = DB.DcMember()
        mod.is_deleted = is_del
        mod.role = mem["role"]
        mod.is_external = mem.get("is_external") or False
        if mod.is_external:
            mod.ext_name = mem["ext_name"]
            mod.ext_contact = mem["ext_contact"]
        else:
            mod.member = int(mem["user_id"])
        mod.dc = dc_id
        mem_id_name = mem.get("org_id") or mem.get("ext_name")
        if m_id > 0:
            mod.id = int(m_id)
            mod.txn_no = int(mem["txn_no"])
            rc = apiVC.update_entity(DB.DcMember, mod)
            if rc != 1:
                raise C.AcadStackException(f"Could not update the DC member {mem_id_name}")
        else:
            apiVC.save_entity(mod)
            if mod.id < 1:
                raise C.AcadStackException(f"Could not add the DC member {mem_id_name}")
        


def _raise_on_invalid_dc_change(actor, sup_id, stu_id, old_status, new_status):
    WF.dc_next_status(actor, old_status, new_status)

    if not (sup_id and stu_id):
        raise C.AcadStackException("Please select student AND supervisor!")
    
    sup = DB.User.get_by_id(sup_id)
    stu = DB.User.get_by_id(stu_id)

    if sup.role != "FAC":
        raise C.AcadStackException("Only a faculty can be the supervisor!")
    stu_per = stu.person
    if sup.person.dept_name != stu_per.dept_name:
        raise C.AcadStackException("Supervisor and student must be from same department!")
    
    if not actor.allowed("dc.edit", own=lambda: sup_id == actor.id,
                         dept=lambda: actor.dept == stu_per.dept_name):
        if actor.has("dc.edit:dept"):
            raise C.AcadStackException("Only HOD of student's own dept. can make changes!")
        raise C.AcadStackException("You must be the supervisor/HoD/Dean to make changes to ")
    

def _raise_on_invalid_dc_dates(dc_id, stu_id, from_dt, to_dt):
    qry = DB.DcForStudent.select().where((DB.DcForStudent.id != dc_id) & \
        (DB.DcForStudent.student == stu_id))
    if to_dt and to_dt != '0000-00-00':
        qry = qry.where(DB.DcForStudent.effective_from <= to_dt)
    qry = qry.where(DB.DcForStudent.effective_to >= from_dt)
    
    if qry.exists():
        raise C.AcadStackException("DC dates overlap with an existing DC of the same student!")


@P.require("dc.edit")
async def dc_save():
    try:
        fd = await request.get_json(force=True)
        stu = fd.get("student") or {}
        dcm = fd.get("members") or []
        stu_id = stu.get("user_id")
        dcid = int(fd.get("id") or 0)
        dc = DB.DcForStudent.get_by_id(dcid) if dcid > 0 else DB.DcForStudent()
        old_dc_status = dc.status
        sups = [m for m in dcm if m.get("role") == "SU" and \
                    not m.get("is_deleted")]
        has_sup = len(sups) == 1
        has_cp = len([m for m in dcm if m.get("role") == "CP" and \
                        not m.get("is_deleted")]) == 1
        has_mem = len([m for m in dcm if m.get("role") == "ME" and \
                        not m.get("is_deleted")]) > 0
        if not(has_mem and has_cp and has_sup):
            return apiVC.error_json("At least one DC member, supervisor and "
                                 "the DC chairperson is required!")
        
        sup_id = sups[0].get("user_id")
        _raise_on_invalid_dc_change(P.current_actor(), sup_id, stu_id, old_dc_status,
                                    fd.get("status", old_dc_status))

        from_dt = fd.get("effective_from")
        to_dt = fd.get("effective_to")
        _raise_on_invalid_dc_dates(dcid, stu_id, from_dt, to_dt)
        
        logging.info("Saving DC details: {}".format(fd))
        C.update_model_skip_unknown(dc, fd)
        dcid = int(fd.get("id") or 0)
        dc.student = int(stu_id)

        with DB.db.atomic() as txn:
            rc = 0
            expected_rc = 0
            if dcid:
                rc += apiVC.update_entity(DB.DcForStudent, dc)
                expected_rc += 1
                if dc.status == "APP" and old_dc_status != "APP":
                    amo = DB.AcademicMilestone(dc=dc.id, student=stu_id,
                                            milestone="DC Approved")
                    rc += apiVC.save_entity(amo)
                    expected_rc += 1
            else:
                rc += apiVC.save_entity(dc)
                expected_rc += 1
                amo = DB.AcademicMilestone(dc=dc.id, student=stu_id,
                                            milestone="DC Proposed")
                rc += apiVC.save_entity(amo)
                expected_rc += 1
            
            if rc == expected_rc:
                _save_dcm(dcm, dc.id)
                txn.commit()
            else:
                txn.rollback()
                return apiVC.error_json("Failed to save details. "
                                     "Please refresh and try again.")

        return await dc_details(dc.id)

    except C.AcadStackException as ae:
        logging.exception(ae)
        return apiVC.error_json(str(ae))
    except Exception as ex:
        msg = "Error when saving DC details."
        logging.exception(msg)
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

@P.require("dc.view")
async def dc_details(dc_id):
    try:
        dc_qry = DB.DcForStudent.select().where(DB.DcForStudent.id == int(dc_id))
        actor = P.current_actor()
        if not actor.has("dc.view:any"):
            dc_qry = dc_qry.where(DB.DcForStudent.student == actor.id)
        dcd = {}
        if dc_qry.exists():
            dcd = __to_dc_dict(dc_qry[0])
        return apiVC.ok_json(dcd)

    except C.AcadStackException as ae:
        logging.exception(ae)
        return apiVC.error_json(str(ae))

    except Exception as ex:
        msg = "Error when loading Dc details."
        logging.exception(msg)
        return apiVC.error_json(msg)


@P.require("dc.view")
async def dc_search():
    try:
        fd = await request.get_json(force=True)
        stu_id = fd.get("student_id") or 0
        actor = P.current_actor()
        if not actor.has("dc.view:any"):
            stu_id = actor.id
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
    except Exception as ex:
        msg = "Error when searching dc details."
        logging.exception(msg)
        return apiVC.error_json(msg)


@P.require("ppr.edit")
async def get_dc_students():
    try:
        uid = apiVC.logged_in_user().id
        cursor = DB.db.execute_sql(C.sql_by_id("get_dc_students"),[uid])
        data = []
        for row in cursor.fetchall():
            data.append({'user_id': row[0], 'first_name': row[1],
                        'last_name': row[2], 'email': row[3],
                        'dept_name': row[4], 'year_of_entry': row[5],
                        'org_id': row[6]})
        return apiVC.ok_json(data)
    except Exception as ex:
        logging.error(ex)
        return apiVC.error_json("Failed to fetch DC students.")


def __is_dc_member(uid, student_id):
    q1 = DB.DcMember.select().join(DB.DcForStudent)
    q1 = q1.where(DB.DcMember.member==uid)
    q1 = q1.where(DB.DcForStudent.student==student_id)
    return q1.exists()


def __ppr_exists(stu_id, acad_sess, dcm_id):
    q1 = DB.PhDProgressReport.select()
    q1 = q1.where(DB.PhDProgressReport.student == stu_id)
    q1 = q1.where(DB.PhDProgressReport.acad_session == acad_sess)
    q1 = q1.where(DB.PhDProgressReport.dc_member == dcm_id)
    return q1.exists()


@P.require("ppr.edit", alert=True)
async def save_progress_report():
    try:
        actor = P.current_actor()
        uid = actor.id
        fd = await request.get_json(force=True)
        pprid = fd.get("id") or 0
        ppr = DB.PhDProgressReport()
        if not actor.allowed("ppr.edit", own=lambda: __is_dc_member(uid, fd.get("student"))):
            raise C.AcadStackException("You must be a DC member!")
        rc = 0
        with DB.db.atomic() as txn:
            if pprid > 0:
                ppr = DB.PhDProgressReport.get_by_id(pprid)
                WF.ppr_next_status(actor, ppr.status, fd.get("status", ppr.status),
                                   __is_dc_chair(uid, ppr.student.id))
                C.update_model_skip_unknown(ppr, fd)
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
    except C.AcadStackException as ae:
        return apiVC.error_json(str(ae))
    except Exception as ex:
        logging.error(ex)
        return apiVC.error_json("Error occurred when saving progress report.")


@P.require("ppr.view", alert=True)
async def get_ppr(myid):
    try:
        actor = P.current_actor()
        uid = actor.id
        ppr = DB.PhDProgressReport.get_by_id(myid)
        if not actor.allowed("ppr.view", own=lambda: __is_dc_member(uid, ppr.student.id)):
            raise C.AcadStackException("You must be a DC member!")
        obj = apiVC.model_to_dict(ppr, recurse=False)
        return apiVC.ok_json(obj)
    except C.AcadStackException as ae:
        return apiVC.error_json(str(ae))
    except Exception as ex:
        logging.error(ex)
        return apiVC.error_json("Error occurred when fetching progress report.")


@P.require("ppr.view", alert=True)
async def get_pprs_for_student(myid):
    try:
        actor = P.current_actor()
        uid = actor.id
        if not actor.allowed("ppr.view", own=lambda: __is_dc_member(uid, myid)):
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
    except C.AcadStackException as ae:
        return apiVC.error_json(str(ae))
    except Exception as ex:
        logging.error(ex)
        return apiVC.error_json("Error occurred when fetching progress reports.")


def __is_dc_chair(uid, std_id):
    q1 = DB.DcMember.select().join(DB.DcForStudent)
    q1 = q1.where(DB.DcMember.member==uid)
    q1 = q1.where(DB.DcMember.role=="CP")
    q1 = q1.where(DB.DcForStudent.student==std_id)
    return q1.exists()


@P.require("ppr.view")
async def is_dc_chair(uid, std_id):
    try:
        actor = P.current_actor()
        if not actor.allowed("ppr.view", own=lambda: uid == actor.id):
            return apiVC.error_json("You can check only your own DC role!")
        return apiVC.ok_json(__is_dc_chair(uid, std_id))
    except Exception as ex:
        msg = "Error occurred when checking DC chair."
        logging.exception(msg)
        return apiVC.error_json(msg)


