import csv
import math
import os
from quart import request, Blueprint
from werkzeug.utils import secure_filename
from create_email import send_grades_submission_email, send_offering_updated_email
from datetime import datetime as DT
from peewee import IntegrityError
import api_common as apiVC
import validation_checks as VAL
import common as C
import models as DB
import settings_store as ST
import logging

def init_routes(bp:Blueprint):
    bp.add_url_rule('/co_save', view_func=course_offering_save, methods=['POST'])
    bp.add_url_rule('/co_view/<int:my_id>', view_func=course_offering_view, methods=['GET'])
    bp.add_url_rule('/co_find', view_func=course_offering_find, methods=['POST'])
    bp.add_url_rule('/co_lookup/<string:query_str>', view_func=course_offering_lookup, methods=['GET'])
    bp.add_url_rule('/co_lookup_all/<string:query_str>', view_func=course_offering_lookup_all, methods=['GET'])
    bp.add_url_rule('/offerings_of_course/<int:my_id>', view_func=offerings_of_course, methods=['GET'])
    bp.add_url_rule('/grades_upload', view_func=grades_upload, methods=['POST'])
    bp.add_url_rule('/fetch_stats/<int:my_id>', view_func=fetch_stats, methods=['GET'])
    bp.add_url_rule('/running_courses', view_func=get_running_courses, methods=['GET'])

def _save_co_instructors(instructors, co_id):
    for ins in instructors:
        ci = DB.CourseInstructor()
        ci.offering = co_id
        C.update_model_skip_unknown(ci, ins)
        if ci.id and ci.id > 0:
            rc = 0
            if ci.is_deleted:
                rc = DB.CourseInstructor.delete_by_id(ci.id)
            else:
                ci = DB.CourseInstructor.get_by_id(ci.id)
                C.update_model_skip_unknown(ci, ins)
                rc = apiVC.update_entity(DB.CourseInstructor, ci)

            if rc != 1:
                raise IntegrityError("Could not update DB. Please try reloading.")
        else:
            apiVC.save_entity(ci)


def _save_co_categorization(cats, co_id):
    all_deleted = True
    for c in cats:
        if not c.get("is_deleted"):
            all_deleted = False
            break
    if all_deleted:
        raise C.AcadStackException("Must add at least one valid categorization!")

    for cc in cats:
        cc_obj = DB.CourseCategory()
        cc_obj.offering = co_id
        C.update_model_skip_unknown(cc_obj, cc)
        if not apiVC.entry_years_valid(cc_obj.for_entry_years):
            raise C.AcadStackException("Entry years invalid! Must be a "
                                  "comma separated list of years "
                                  "(after 2000). E.g.,  2018, 2020")
        if cc_obj.id and cc_obj.id > 0:
            rc = 0
            if cc_obj.is_deleted:
                rc = DB.CourseCategory.delete_by_id(cc_obj.id)
            else:
                cc_obj = DB.CourseCategory.get_by_id(cc_obj.id)
                C.update_model_skip_unknown(cc_obj, cc)
                rc = apiVC.update_entity(DB.CourseCategory, cc_obj)

            if rc != 1:
                raise IntegrityError("Could not update DB. Please try reloading.")
        else:
            apiVC.save_entity(cc_obj)


@C.rbac
async def course_offering_view(my_id):

    co = DB.CourseOffering.get_or_none(my_id)
    if co:
        obj = apiVC.model_to_dict(co, recurse=False,
                exclude=[DB.CourseOffering.course.author])
        obj["course"] = {"id": co.course.id, "title": co.course.title,
                        "code": co.course.code, "ltp": co.course.ltp}
        obj["instructors"] = [{"id": ins.id, "user_id": ins.instructor.id,
                               "first_name": ins.instructor.first_name,
                               "last_name": ins.instructor.last_name,
                               "is_coordinator": ins.is_coordinator}
                              for ins in co.instructors]
        obj["course_categories"] = [{"id": cc.id,
                                     "degree": cc.degree,
                                     "dept": cc.dept,
                                     "category": cc.category,
                                     "for_entry_years": cc.for_entry_years,
                                     }
                                    for cc in co.course_categories]

        return apiVC.ok_json(obj)
    else:
        return apiVC.error_json(f"DB.Course offering not found for ID {my_id}")


def _is_course_approved(cour_dict):
    try:
        if not cour_dict or not cour_dict.get("id"):
            return False
        cid = cour_dict.get("id")
        cq = DB.Course.select().where((DB.Course.id == cid) & (DB.Course.status == "APP"))
        return cq.exists()
    except Exception as ex:
        logging.exception("Error when checking approved course.", ex)
        return False


@C.rbac(permissions=["course_offering.save"])
async def course_offering_save():
    fd = await request.get_json(force=True)
    logging.info("Saving course offering details: {}".format(fd))
    cid = int(fd.get("id") or 0)

    if cid:
        if apiVC.is_user_in_role("HOD") and \
                not VAL.is_hod_for_course_offering(cid, apiVC.logged_in_user().id):
            return apiVC.error_json("Only the HoD of the offering department can make changes to the course offering.")

        if not (apiVC.has_permission("course_offering.edit_any")
                or VAL.validate_course_instructor(cid)):
            return apiVC.error_json("Only the course cordinator can make changes.")

    acad_session = (fd.get("acad_session") or "").upper()
    fd["acad_session"] = acad_session

    if not apiVC.academic_session_valid(acad_session):
        return apiVC.error_json("Academic session invalid. Must be of the format 20NN-S. E.g., 2020-W")

    if not _is_course_approved(fd["course"]):
        return apiVC.error_json("The course being offered MUST be in approved state!")

    co = DB.CourseOffering()
    old_status = "P"
    with DB.db.atomic() as txn:
        if cid:
            co = DB.CourseOffering.get_by_id(cid)
            old_status = co.status
            VAL.validate_coff_status(co)
            C.update_model_skip_unknown(co, fd)
            if apiVC.update_entity(DB.CourseOffering, co) != 1:  # if rc != 1:
                return apiVC.error_json("Could not update. Please try again.")
            logging.debug("Updated DB.CourseOffering details: {}".format(co))
            _save_co_instructors(fd.get("instructors"), co.id)
            _save_co_categorization(fd.get("course_categories"), co.id)
        else:
            C.update_model_skip_unknown(co, fd)
            qry = C.sql_by_id("same_offering_exists")
            cursor = DB.db.execute_sql(qry, [co.acad_session, co.course.id,
                                    apiVC.current_login_id()])
            res_rows = cursor.fetchall()
            if res_rows:
                old_co_status = res_rows[0][0]
                cos_map = apiVC.static_data_item("OfferingStatuses")
                cos_label = apiVC.label_for_static_data_item(old_co_status, cos_map)
                return apiVC.error_json("An offering of the course already \
                    exists in status {0} for {1}. Please edit (or ask \
                    your HoD to do it) the existing record instead of \
                    creating a new one.".format(cos_label, co.acad_session))

            apiVC.save_entity(co)
            logging.debug(f"Inserted DB.CourseOffering: {co}")
            _save_co_instructors(fd.get("instructors"), co.id)
            _save_co_categorization(fd.get("course_categories"), co.id)

        send_offering_updated_email(co.id, old_status, co.status)
        txn.commit()

    return await course_offering_view(co.id)


@C.rbac(permissions=["grades.upload"])
async def grades_upload():
    form = await request.form
    co_id = form.get('course_offering')
    if not (co_id and co_id.isdigit()):
        return apiVC.error_json("It seems you have not selected the course for which you want to upload grades. Please retry after selecting the course.")
    co_id = int(co_id)
    co_obj = DB.CourseOffering.get_or_none(co_id)
    if not co_obj:
        return apiVC.error_json("DB.Course offering not found. Please make sure that you have selected a course when uploading grades.")

    if not VAL.is_today_between_events("GRADE_SUB_S", "GRADE_SUB_E",
            co_obj.acad_session):
        return apiVC.error_json("Grades upload is not open!")
    # Only the course instructor OR an academic-section/dean bypass may upload the course grades
    if not (apiVC.has_permission("grades.upload_any")
            or VAL.validate_course_instructor(co_id)):
        return apiVC.error_json("Only the course coordinator can upload grades for the course!")

    # Raises exception when change not allowed
    VAL.validate_coff_status(co_id)

    grades_file = (await request.files)['grades_file']
    if grades_file.filename == '':
        return apiVC.error_json("No grades .csv file supplied!")
    filename = secure_filename(grades_file.filename)
    file_path = os.path.join(apiVC.get_upload_folder_for_user(), filename)
    grades_file.save(file_path)

    # Convert all text to uppercase in the grades file
    with open(file_path, 'r') as inp:
        y = inp.read().upper().strip()
        lines = y.splitlines()
        if len(lines) < 2:
            return apiVC.error_json("No grades found in the CSV file you uploaded. Please upload a non-empty CSV file!")

        if not lines[0].replace(' ', '').startswith("FIRST_NAME,LAST_NAME,ROLL_NO,GRADE"):
            return apiVC.error_json("Invalid header row in CSV. Please make sure that the header row contains only: roll_no, grade")

        valid_grades = ST.valid_grade_codes()
        invalid_rows = []
        for ll in lines[1:]:
            if ll.split(',')[3].strip() not in valid_grades:
                invalid_rows.append(ll)

        if invalid_rows:
            return apiVC.error_json(f"Found invalid grades in rows: {invalid_rows}. "
                                 f"Allowed grades values are: {valid_grades}")


    with open(file_path, 'w') as out:
        out.write(y)

    # Check the uploaded roll numbers against what we have in the DB
    with open(file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        rolls = [row["ROLL_NO"].upper().strip() for row in reader]

    coe = DB.CourseEnrollment.select().where(
        (DB.CourseEnrollment.course_offering == co_id) &
        (DB.CourseEnrollment.enrol_status == "ENRO"))
    rolls_indb = [x.student.person.org_id.upper().strip() for x in coe]
    missing = set(rolls_indb) - set(rolls)
    if bool(missing):
        return apiVC.error_json(
            "Grades can be submitted only for enrolled students in "
            "this course. Following roll numbers are missing in the "
            f"uploaded .csv file: {missing}")
    extra = set(rolls) - set(rolls_indb)
    if bool(extra):
        return apiVC.error_json(
            "Grades can be submitted only for enrolled students in this "
            "course. Following roll numbers are supplied, but not "
            f"enrolled: {extra}")

    # If all is OK, then update the grades in DB
    upd_count = 0
    with DB.db.atomic() as txn:
        with open(file_path, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                roll_no = row["ROLL_NO"].upper().strip()
                grade = row["GRADE"].upper().strip()
                stu = DB.User.select(DB.User.id).join(DB.Person)\
                    .where(DB.Person.org_id == roll_no)[0]
                coe = DB.CourseEnrollment.select().where(
                    (DB.CourseEnrollment.course_offering == co_id) &
                    (DB.CourseEnrollment.student == stu.id)
                )[0]

                if coe.enrol_type == "A" and grade not in ST.valid_audit_grade_codes():
                    raise C.AcadStackException(f"Invalid grade {grade} assigned "
                            f"to {roll_no} for audited course. "
                            f"Allowed audit grades are: {ST.valid_audit_grade_codes()}")

                if coe.grade == grade:
                    logging.debug("Grade unchanged, skipping the update.")
                    continue

                coe.grade = grade
                apiVC.update_entity(DB.CourseEnrollment, coe)
                upd_count += 1

        txn.commit()
    if(apiVC.logged_in_user().role != "ACA"):
        send_grades_submission_email(co_id, upd_count)
    return apiVC.ok_json(f"Grades processed successfully! Added/updated {
        upd_count} records.")


def __fill_co_search_result(row, enrol_count):
    obj = apiVC.model_to_dict(row, recurse=False)
    obj["EnrollmentsCount"] = enrol_count or 0
    obj["course"] = apiVC.model_to_dict(row.course, recurse=False)
    obj["credits"] = row.course.credits
    obj["instructors"] = ", ".join([x.instructor.get_full_name()
                                    for x in row.instructors])
    obj["instructors_info"] = [{"id":x.instructor.id, "name": 
                                x.instructor.get_full_name()} 
                                for x in row.instructors]
    return obj


@C.rbac
async def course_offering_find():
    fd = await request.get_json(force=True)
    code, title, ltp, instructor, status, \
    instructor_id, dept, acad_session = \
        fd.get("code"), fd.get("title"), fd.get("ltp"), \
        fd.get("instructor"), fd.get("status"), \
        fd.get("instructor_id"), fd.get("dept"), \
        fd.get("acad_session")

    pg_no = int(fd.get('pg_no', 1))
    enroll_count = ((DB.CourseOffering.select(DB.CourseOffering.id,
                    DB.ORM.fn.Count(DB.CourseEnrollment.id)
                    .alias('EnrollmentsCount'))
                    .join(DB.CourseEnrollment, DB.ORM.JOIN.LEFT_OUTER))
                    .where(DB.CourseEnrollment.enrol_status == 'ENRO')
                    .group_by(DB.CourseOffering.id))

    pred = (DB.CourseOffering.id == enroll_count.c.id)

    query = DB.CourseOffering.select(DB.CourseOffering, enroll_count.c.EnrollmentsCount) \
        .join_from(DB.CourseOffering, enroll_count, DB.ORM.JOIN.LEFT_OUTER, on=pred) \
        .join_from(DB.CourseOffering, DB.Course) \
        .join_from(DB.CourseOffering, DB.CourseInstructor) \
        .join_from(DB.CourseInstructor, DB.User)

    if status:
        query = query.where(DB.CourseOffering.status == status)
    if code:
        query = query.where(DB.CourseOffering.course.code.contains(code))
    if ltp:
        query = query.where(DB.CourseOffering.course.ltp == ltp)
    if title:
        query = query.where(DB.CourseOffering.course.title.contains(title))
    if instructor:
        query = query.where(
            (DB.CourseInstructor.instructor.first_name.contains(instructor))
            | (DB.CourseInstructor.instructor.last_name.contains(instructor)))
    if instructor_id:
        query = query.where(DB.CourseInstructor.instructor.id == instructor_id)

    if dept:
        query = query.where(DB.CourseOffering.dept_name == dept)

    if acad_session:
        query = query.where(DB.CourseOffering.acad_session == acad_session)

    courses = query.order_by(-DB.CourseOffering.id).distinct() \
        .paginate(pg_no, apiVC.page_size())
    serialized = []
    for crs, co_dict in zip(courses, courses.dicts()):
        obj = __fill_co_search_result(crs, co_dict["EnrollmentsCount"])
        serialized.append(obj)

    has_next = len(courses) >= apiVC.page_size()
    res = {"courses": serialized, "pg_no": pg_no, "pg_size": apiVC.page_size(),
           "has_next": has_next}
    return apiVC.ok_json(res)


def _do_course_offering_lookup(query_str, all_statuses):
    query = DB.CourseOffering.select().join(
        DB.Course).where(
        (DB.CourseOffering.course.code.contains(query_str) |
         DB.CourseOffering.course.title.contains(query_str)))

    if not all_statuses:
        query  = query.where(DB.CourseOffering.status.in_(["R", "E"]))

    courses = query.order_by(-DB.CourseOffering.id).distinct().limit(15)
    serialized = [{"id": r.id, "acad_session": r.acad_session,
                    "course": {"code": r.course.code,
                                    "title": r.course.title,
                                    "section": r.section,
                                    "dept_name": r.dept_name}}
                  for r in courses]
    return apiVC.ok_json(serialized)


@C.rbac
async def course_offering_lookup(query_str):
    return _do_course_offering_lookup(query_str, False)


@C.rbac
async def course_offering_lookup_all(query_str):
    return _do_course_offering_lookup(query_str, True)


@C.rbac
async def offerings_of_course(my_id):
    c = DB.Course.get_by_id(my_id)
    serialized = [{"co_id": r.id,
                   "acad_session": r.acad_session,
                   "class_size": len(r.enrollments),
                   "coordinator": [x.instructor.login_id
                                   for x in r.instructors if x.is_coordinator]}
                  for r in c.offerings]
    return apiVC.ok_json(serialized)


@C.rbac
async def fetch_stats(my_id):
    res = {"data_att": [], "Weeks": [], "grades": [], "data": []}
    if apiVC.is_user_in_role(ST.setting("course_offering.hide_stats_from")):
        return apiVC.error_json("DB.Course stats are not visible for you!")

    cursor = DB.db.execute_sql(C.sql_by_id("course_grades"), [int(my_id)])
    grades = []
    data = []
    for row in sorted(cursor.fetchall()):
        grades.append(row[0])
        data.append(row[1])
    res["grades"] = grades
    res["data"] = data

    # Get attendance stats
    start_dt_rs = DB.db.execute_sql(
        C.sql_by_id("session_start_week"), [int(my_id)]).fetchall()

    if len(start_dt_rs) > 0:
        start_dt = DT.strptime(start_dt_rs[0][0], "%Y-%m-%d")
        session_start_week_number = start_dt.isocalendar()[1]
        cursor_att = DB.db.execute_sql(C.sql_by_id("course_attendance"),
                                    [int(my_id)])
        weeks_sorted = sorted(cursor_att.fetchall())
        if weeks_sorted:
            try:
                total_weeks = int(weeks_sorted[- 1][0] - session_start_week_number)
                data_att = total_weeks * [0]
                for row in weeks_sorted:
                    data_att[row[0] - session_start_week_number] = math.ceil(row[1])
                weeks = []
                for i in range(1, total_weeks + 1):
                    weeks.append('Week-' + str(i))

                res["data_att"] = data_att
                res["Weeks"] = weeks
            except Exception as ex2:
                logging.error(f"Error when populating attendance stats. {ex2}")
                res["data_att"] = []
                res["Weeks"] = []

    return apiVC.ok_json(res)


def schedule_course_status(config=None):
    try:
        DB.db.init(config['db_name'], **config['db_args'])
        DB.db.connect()
        cur = DB.db.execute_sql(C.sql_by_id("move_running_co_to_finish"), ['%Y-%m-%d'])
        rc = DB.db.rows_affected(cur)
        logging.info(f"Changed {rc} Running course offerings to Completed.")

        cur = DB.db.execute_sql(C.sql_by_id("move_enrolling_co_to_running"), ['%Y-%m-%d'])
        rc = DB.db.rows_affected(cur)
        logging.info(f"Changed {rc} Enrolling course offerings to Running.")

    except Exception as ex:
        msg = "Error when updating course status."
        logging.exception(msg, ex)
    finally:
        DB.db.close()


@C.rbac
async def get_running_courses():
    cu = apiVC.logged_in_user()
    coq = DB.CourseOffering.select().join(DB.CourseInstructor)
    coq = coq.where(DB.CourseOffering.status=="R")
    if not apiVC.has_permission("course_offering.view_all_running"):
        coq = coq.where(DB.CourseInstructor.instructor==cu.id)
    data = []
    for x in coq:
        c, item = x.course, {"id": x.id}
        item["value"] = "{0} ({1}). {2}. Dept. {3}".format(c.title,\
                    c.code, x.acad_session, x.dept_name)
        data.append(item)
    return apiVC.ok_json(data)
