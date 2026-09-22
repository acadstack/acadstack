from io import BytesIO
import logging
from quart import Blueprint, request
from quart.helpers import send_file
from peewee import IntegrityError
from common import AcadStackException, rbac, sql_by_id
from create_email import send_enrolment_email
from playhouse.shortcuts import model_to_dict
import api_common as apiVC
import validation_checks as VAL
import models as DB
import common as C
import settings_store as ST


def __get_ce_ownership(eids):
    sql1 = sql_by_id("frag_pending_enrollments")
    sql2 = sql_by_id("frag_ba_and_instructor")
    sql = "{0} {1}".format(sql1, sql2)
    param = tuple(eids)
    cursor = DB.db.execute_sql(sql, [param])

    ba_instr = apiVC.result_set_from_cursor(cursor)
    cuid = apiVC.logged_in_user().id
    data = {}
    for obj in ba_instr:
        is_instr = obj["instructor_id"] == cuid
        is_advisor = obj["batch_adv_id"] == cuid
        data[obj["id"]] = [is_instr, is_advisor]
    return data


def __get_existing_enrolment(co_id, student_id):
    qry = DB.CourseEnrollment.select().where(
        (DB.CourseEnrollment.course_offering == co_id) &
        (DB.CourseEnrollment.student == student_id) &
        (DB.CourseEnrollment.enrol_status != 'ENRO')
    )
    return qry[0] if qry.exists() else None


def __check_student_fees_status():
    if apiVC.is_user_in_role("STU"):
        qry = DB.FeesTransaction.select() \
            .where(
            (DB.FeesTransaction.student == apiVC.logged_in_user().id) &
            (DB.FeesTransaction.acad_session.in_(apiVC.current_acad_session_list())) &
            (DB.FeesTransaction.is_deleted != True) &
            (DB.FeesTransaction.fees_txn_amt > 0)
        )
        if not qry.exists():
            raise AcadStackException(
                "Semester registration fees payment details/proof are "
                "required before submitting enrolment requests! Kindly "
                "submit the necessary details first.")


def __get_slot_conflicts(co_id, student_id):
    stu = DB.User.get_or_none(int(student_id))
    if not stu:
        raise AcadStackException("User record not found for student.")
    slots = []
    for ce in stu.enrollments.where(DB.CourseEnrollment.
                                    enrol_status.in_(["IPEN", "APEN", "ENRO"])):
        if ce.course_offering.slot:
            slots.append(ce.course_offering.slot)

    cst_list = list(DB.CourseSlotTiming.select().where(
        (DB.CourseSlotTiming.slot.in_(slots))
        & (DB.CourseSlotTiming.is_deleted != True)))

    co = DB.CourseOffering.get_or_none(int(co_id))
    conflicts = []
    if co:
        course_slots = apiVC.static_data_item("CourseSlots")
        cst_qry = DB.CourseSlotTiming.select().where(
            DB.CourseSlotTiming.slot == co.slot)
        if not cst_qry.exists():
            course_slots = apiVC.static_data_item("CourseSlots")
            slot_nm = apiVC.label_for_static_data_item(co.slot, course_slots)
            raise AcadStackException(
                f"Slot timing not setup for slot: '{slot_nm}'. "
                "Please contact the administrator.")
        for x in cst_list:
            if cst_qry[0].week_day == x.week_day and \
                    ((x.start_time < cst_qry[0].start_time < x.end_time) or
                     (x.start_time < cst_qry[0].end_time < x.end_time)):
                slot = apiVC.label_for_static_data_item(x.slot, course_slots)
                msg = (f"{slot} : {C.WEEK_DAY_NAMES[x.week_day]} "
                        f"{x.start_time}-{x.end_time}")
                conflicts.append(msg)

    return conflicts


def __calculate_attendance(obj, se):
    present_count = 0
    total = 0
    att = se.attendance
    for row in att:
        if row.attend == 'P':
            present_count = present_count + 1
        total = total + 1
    if total == 0:
        obj["attendance"] = 0
    else:
        percent = float(present_count) / float(total)
        percent = '%.2f' % round(percent * 100, 2)
        obj["attendance"] = percent


def __fetch_student_enrollments_data(enrols, include_attendance):
    
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
            raise AcadStackException("User not found for student. UserId="
                                f"{se.student_id}")

        # Fetch course categorization info applicable to the student
        cat_info = DB.CourseCategory.select(). \
            join(DB.CourseOffering).\
            where(
            (DB.CourseCategory.offering == se.course_offering.id) &
            (DB.CourseCategory.degree == st_degree)&
            (DB.CourseCategory.dept << (st_dept_name, 'ALL')) &
            (DB.CourseCategory.for_entry_years.contains(st_year_of_entry)))

        if cat_info:
           for cat in cat_info:
               my_course["cc_category"] = cat.category
               if cat.dept == st_dept_name :
                  my_course["cc_category"] = cat.category
                  break
        else:
            logging.warning("Course categorization not found. CO id="
                            f"{se.course_offering.id}")

        # Release the grade only after result declaration date
        try:
            result_dec_dt  = VAL.get_event_date("RESULT_DECLARATION", 
                                                se.course_offering.acad_session)
        except:
            pass
        else:
            result_dec_dt = VAL.get_event_date("RESULT_DECLARATION", 
                                               se.course_offering.acad_session)
            if result_dec_dt > C.current_dt_str():
                my_course["grade"] = "NA"

        if include_attendance:
            __calculate_attendance(my_course, se)

        acad_sess_key = my_course["acad_session"]
        if acad_sess_key not in enrol_data:
            enrol_data[acad_sess_key] = {"courses": [], "sgpa": 0, "ec": 0}

        enrol_data[acad_sess_key]["courses"].append(my_course)
    
    # We use these suffixies for academic sessions. Change them as needed.
    # T1, T2 etc. are for trimesters, I, II and S are for regular semesters.
    suffixes = ['T1', 'T2', 'T3', 'T4', 'I', 'II', 'S']

    # Sort by academic session. Needed for cgpa calculations
    acad_sess_list = list(enrol_data.keys())
    acad_sess_list = sorted(acad_sess_list,
        key=lambda item: "{0}{1}".format(item[:4], suffixes.index(item[5:])))
    
    # We return the enrolment data per academic session, sorted in reverse
    # chronological order of academic sessions (2025-II, 2025-I, 2024-II ...).
    enrol_data_sorted = dict()
    for key in acad_sess_list:
        enrol_data_sorted[key] = enrol_data[key]

    logging.debug(f"Sorted acad sessions: {acad_sess_list}")
    return acad_sess_list, enrol_data_sorted


def __compute_cgpa_sgpa_ec(courses, degree):

    # Mapping of grade letter to points
    gpm = {"A": 10, "A-": 9, "B": 8, "B-": 7, "C": 6, "C-": 5, 
           "D": 4, "E": 2, "F": 0}

    # Grades counted for earned credits for UG students
    ug_ec_grades = "A,A-,B,B-,C,C-,D,S,NP"

    # Grades counted for earned credits for PG students
    pg_ec_grades = "A,A-,B,B-,C,C-,D,S"

    # Passing grades (UG+PG) used in CGPA calculation
    pass_grades = "A,A-,B,B-,C,C-,D"


    # Temp variables used for calculations
    ec, s_ec, pts_sgpa, pts_cgpa,u_ec = 0, 0, 0, 0, 0
    creg, creg_wo_audit, sgpa, cgpa = 0, 0, 0, 0
    try:
        for c in courses:

            # Take only confirmed enrolments in finished courses
            if c["enrol_status"] != "ENRO":
                continue

            # Default grades counted for earned credits for PhD students
            phd_ec_pass_grades = "A,A-,B,B-,C,C-"
            phd_ec_grades = "A,A-,B,B-,C"

            academic_session = c['acad_session']
            academic_session_year = int(academic_session[:4])
            academic_session_sem = academic_session[5:] # I, II, S, T1, T2, etc.

            # Adjustment for PhD passing grades introduced in 2021
            if academic_session_year > 2021:
                phd_ec_grades = "A,A-,B,B-,C,C-"
            elif academic_session_year < 2021:
                phd_ec_pass_grades = "A,A-,B,B-,C"
            else: # Year 2021
                if academic_session_sem == "I":
                    phd_ec_pass_grades = "A,A-,B,B-,C"
                    phd_ec_grades = "A,A-,B,B-,C,C-"
                elif academic_session_sem in ["II", "S", "T1", "T2"]:
                    phd_ec_grades = "A,A-,B,B-,C,C-"
                else:
                    logging.warning(
                        f"Unknown academic semester: '{academic_session_sem}'")

            # L-T-P-S-C
            ltp = c["ltp"].strip().split("-")
            if len(ltp) < 2 or not (ltp[0] and ltp[2]):
                raise AcadStackException(f"LTP data missing for course {c["code"]}")
            if len(ltp) == 5:
                cc = round(C.parse_number(ltp[-1]), 2)
            else:
                raise AcadStackException(
                    f"LTP data not in L-T-P-S-C format for course {c["code"]}")

            is_credit_course = c["enrol_type"] in "C,CM,CC"
            # Total registered credits
            creg += cc
            if is_credit_course:
                creg_wo_audit += cc

            # Grades that are counted towards earned credits
            if degree == "BTE":
                 ec_grades = ug_ec_grades
            elif degree == "PHD":
                 ec_grades = phd_ec_grades
                 pass_grades = phd_ec_pass_grades
            else:
                 ec_grades = pg_ec_grades


            # Grade secured in this course
            grade = c["grade"]

            if grade == "S":
                s_ec += cc
            if grade == "U" or grade == "I" or grade == "W":
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


def __get_student_courses_perf(stu, include_attendance):
    # 'CC' -> Credit for concentration
    perf_conc = get_student_courses_perf_filtered(stu, include_attendance, "CC")

    # 'CM' -> Credit for minor
    perf_minor = get_student_courses_perf_filtered(stu, include_attendance, "CM")

    # 'C' -> Credit
    perf_regu = get_student_courses_perf_filtered(stu, include_attendance, "C")

    user = model_to_dict(stu, exclude=[DB.User.password_hashed])
    user["enrollments"] = {"CC": perf_conc, "CM": perf_minor, "C": perf_regu}

    return user


def __get_advisor_action_items():
    u = apiVC.logged_in_user()
    qry1 = sql_by_id("frag_pending_enrollments")
    qry2 = sql_by_id("frag_ba_pending_enrollments")
    qry = f"{qry1} {qry2}"
    cursor = DB.db.execute_sql(qry, [u.id])
    # Add the data rows
    results = apiVC.result_set_from_cursor(cursor)
    return results

# =================== Public methods ==================

def init_routes(bp:Blueprint):
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


def get_student_courses_perf_filtered(stu, include_attendance, 
                                        filter_by_enrol_type=None):
    if filter_by_enrol_type == "C": # 'C' -> Credit, 'A' -> Audit, etc.
        enrols = stu.enrollments.where(DB.CourseEnrollment.enrol_type 
                                       << (filter_by_enrol_type, 'A'))
    elif filter_by_enrol_type:
        enrols = stu.enrollments.where(DB.CourseEnrollment.enrol_type 
                                       == filter_by_enrol_type)
    else:
        enrols = stu.enrollments
    
    acad_sessions, enrol_data = __fetch_student_enrollments_data(
        enrols, include_attendance)
    ec, pts_cgpa, s_ec = 0, 0, 0
    
    # acad_sessions is already in properly sorted chronology
    for ad in acad_sessions:
        cg_data = __compute_cgpa_sgpa_ec(enrol_data[ad]["courses"], 
                                         stu.person.degree)
        enrol_data[ad]["sgpa"] = cg_data["sgpa"]
        enrol_data[ad]["ec"] = cg_data["ec"]
        enrol_data[ad]["creg"] = cg_data["creg"]
        pts_cgpa += cg_data["pts_cgpa"]
        s_ec += cg_data["s_ec"]
        ec += cg_data["ec"]

        enrol_data[ad]["cec"] = ec
        enrol_data[ad]["cgpa"] =round(pts_cgpa /(ec - s_ec), 2) if (ec - s_ec) > 0 else 0

    return {"enrollments": enrol_data, "acad_sessions": acad_sessions}


@rbac
async def drop_withdraw_course(my_id, status):
    try:
        if status not in "DROP,WDRAW":
            return apiVC.error_json(f"Invalid status {status}! Only drop/withdraw allowed!")

        # Raises AcadStackException
        VAL.validate_enrolment_change(my_id, status)

        if apiVC.is_user_in_role("ACA,DEA"):
            status = "ASREJ"

        ce = DB.CourseEnrollment.get_by_id(my_id)
        ce.enrol_status = status
        apiVC.save_entity(ce)
        send_enrolment_email(my_id)
        return apiVC.ok_json("Course enrollment updated successfully")
    except AcadStackException as ex:
        msg = "Error when dropping/withdrawing the course"
        logging.exception(msg, ex)
        return apiVC.error_json(str(ex))
    except Exception as ex:
        msg = "Error when dropping/withdrawing the course"
        logging.exception(msg, ex)
        return apiVC.error_json(msg)


@rbac(roles=["FAC", "ACA", "DEA"])
async def get_instructor_courses_enrol():
    try:
        res = DB.CourseEnrollment.select(). \
            join(DB.CourseOffering).join(DB.CourseInstructor). \
            where(
            (DB.CourseInstructor.instructor_id == apiVC.logged_in_user().id) &
            (DB.CourseEnrollment.enrol_status == 'IPEN')
        )
        result_adv = __get_advisor_action_items()
        result_ins = []
        if res:
            for coe in res:
                obj = {}
                obj["id"] = coe.id
                obj["user_id"] = coe.student.id
                obj["student"] = coe.student.get_full_name()
                obj["org_id"] = coe.student.person.org_id
                obj["enrol_type"] = coe.enrol_type
                obj["enrol_status"] = coe.enrol_status
                obj["acad_session"] = coe.course_offering.acad_session
                obj["year"] = coe.student.person.year_of_entry
                obj["dep"] = coe.student.person.dept_name
                obj["degree"] = coe.student.person.degree
                obj["course"] = coe.course_offering.course.code + ' ' + coe.course_offering.course.title
                obj["for_instructor"] = True
                __calculate_attendance(obj, coe)
                result_ins.append(obj)

        return apiVC.ok_json({"instructor_enrol": result_ins,
                        "advisor_enrol": result_adv})
    except Exception as ex:
        msg = "Error when fetching DB.CourseEnrollment details."
        logging.exception(msg, ex)
        return apiVC.error_json(msg)


@rbac(roles=["ADV", "ACA", "DEA", "HOD"])
async def get_advisor_courses_enrol():
    try:
        qry = sql_by_id("pending_enrolments_advisor")
        if apiVC.is_user_in_role("HOD"):
            qry = sql_by_id("pending_enrolments_hod")

        cursor = DB.db.execute_sql(qry, [apiVC.logged_in_user().id])
        results = apiVC.result_set_from_cursor(cursor)

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

        stu = DB.User.get_by_id(user_id)
        if stu:
            res = []
            enrols = stu.enrollments
            pass_grades = "A,A-,B,B-,C,C-,D,S"
            for se in enrols:
                if se.grade in pass_grades:
                    res.append(se.course_offering.course.code)

            records = {}
            records["codes"] = res
            return apiVC.ok_json(records)
        else:
            return apiVC.error_json(f"Student not found for ID {user_id}")
    except AcadStackException as ae:
        return apiVC.error_json(str(ae))
    except Exception as ex:
        msg = "Error when fetching student academic details."
        logging.exception(msg)
        return apiVC.error_json(msg)


@rbac(roles=["ACA", "DEA"])
async def bulk_enrol_in_course(entry_no_pattern, co_id):
    try:
        if not apiVC.roll_number_valid(entry_no_pattern):
            return apiVC.error_json("Invalid entry number pattern!")

        query = DB.User.select(DB.User.id, DB.Person.org_id, 
                               DB.User.role).join(DB.Person)
        query = query.where((DB.User.role == "STU") & (
            DB.Person.org_id.startswith(entry_no_pattern)))

        co = DB.CourseOffering.get_by_id(co_id)
        VAL.check_enrollment_allowed(co)
        num = 0
        with DB.db.atomic() as txn:
            for stu in query:
                coe = DB.CourseEnrollment()
                coe.course_offering = co
                coe.student = stu.id
                coe.enrol_type = "C"
                coe.enrol_status = "ENRO"
                apiVC.save_entity(coe)
                num += 1
            txn.commit()

        return apiVC.ok_json(f"Enrolled {num} students in {co.course.title} course.")

    except AcadStackException as ae:
        logging.exception(ae)
        return apiVC.error_json(str(ae))
    except Exception as ex:
        msg = "Error when bulk enrolling students."
        logging.exception(msg)
        return apiVC.error_json(msg)


@rbac
async def download_course_enrollments(co_id, is_grades=False):
    try:
        if apiVC.is_user_in_role("STU"):
            return apiVC.error_json("Students cannot download!")
        sql_id = "enrolled_students"
        co = DB.CourseOffering.get_by_id(co_id)
        if is_grades:
            if VAL.validate_course_instructor(co_id,
                    allowed_role=["ACA", "DEA", "HOD"],
                    coordinator_only=False):
                sql_id = "get_course_grades"
            else:
                sql_id = "enrolled_students_for_grades"

        qry = sql_by_id(sql_id)
        cursor = DB.db.execute_sql(qry, [int(co_id)])
        ncols = len(cursor.description)
        colnames = [cursor.description[i][0] for i in range(ncols)]
        result = []

        # Add the header row
        hdr_row = []
        for col_name in colnames:
            hdr_row.append(col_name)
        result.append(','.join(hdr_row))

        # Add the data rows
        for row in cursor.fetchall():
            row_data = []
            for i in range(ncols):
                row_data.append(row[i])
            result.append(','.join(row_data))
        fp = BytesIO()
        fp.write('\n'.join(result).encode('utf-8'))
        fp.flush()
        fp.seek(0)
        return await send_file(fp, attachment_filename=f"{co.course.code}_students.csv",
                         as_attachment=True)

    except Exception as ex:
        msg = "Error when loading enrolment data as CSV."
        logging.exception(msg)
        return apiVC.error_json(msg)


@rbac(roles=["FAC", "ACA", "DEA"])
async def download_enrollments_for_grades(co_id):
    return download_course_enrollments(co_id, True)


@rbac
async def download_course_enrolments(dept_name, entry_year, acad_session):
    try:
        if apiVC.is_user_in_role("STU"):
            return apiVC.error_json("Students cannot download!")
        if dept_name == "-":
            dept_name = ""
        if entry_year == "-":
            entry_year = ""

        cursor = DB.db.execute_sql(sql_by_id("generate_course_enrolments"),
                                [str(entry_year), str(entry_year),
                                 str(dept_name), str(dept_name),
                                 str(acad_session)])
        fp = apiVC.db_result_to_excel(cursor)
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

        stu = DB.User.get_by_id(my_id)
        if stu:
            user = __get_student_courses_perf(stu, True)
            return apiVC.ok_json(user)
        else:
            return apiVC.error_json(f"Student not found for ID {my_id}")
    except AcadStackException as ae:
        return apiVC.error_json(str(ae))
    except Exception as ex:
        msg = "Error when fetching student academic details."
        logging.exception(msg)
        return apiVC.error_json(msg)


@rbac
async def get_course_enrollments(my_id):
    try:
        res = DB.CourseEnrollment.select().where(
            DB.CourseEnrollment.course_offering == my_id)
        if res:
            result = []
            for coe in res:
                obj = {"id": coe.id, "user_id": coe.student.id,
                        "student": coe.student.get_full_name(),
                       "org_id": coe.student.person.org_id,
                       "enrol_type": coe.enrol_type,
                       "enrol_status": coe.enrol_status,
                       "year": coe.student.person.year_of_entry,
                       "dep": coe.student.person.dept_name,
                       "degree": coe.student.person.degree,
                       "course": (coe.course_offering.course.code + ' ' + 
                                  coe.course_offering.course.title)}
                __calculate_attendance(obj, coe)
                result.append(obj)

            return apiVC.ok_json(result)
        else:
            return apiVC.error_json("No enrolments found for course offering!")
    except Exception as ex:
        msg = "Error when fetching DB.CourseEnrollment details."
        logging.exception(msg)
        return apiVC.error_json(msg)


@rbac(roles=["ACA", "STU"])
async def enroll_in_courses():
    try:
        fd = await request.get_json(force=True)
        std_id = int(fd["user_id"])
        VAL.is_current_user_in_role_and_id("STU", "user_id", std_id, 
            "Student attempted to enrol someone else in a course.")
        if not ST.setting("enrolment.disable_fees_check"):
            __check_student_fees_status()
        CREDIT_NA_ALLOWED_MSG = ""
        ALLOWED_COURSES = []
        logging.debug("Enrolling student in courses: {}".format(fd))
        if fd["co_ids"]:
            with DB.db.atomic() as txn:
                for co_id in fd["co_ids"]:
                    co = DB.CourseOffering.get_by_id(co_id)
                    if fd["enrol_type"] == 'A':
                        if not VAL.is_course_withdraw_open(co.acad_session):
                            raise AcadStackException("Course enrolment/Audit not open for "
                                + str(co.acad_session))
                    else:
                        if not VAL.is_course_add_drop_open(co.acad_session):
                            raise AcadStackException("Course enrolment/add not open for "
                                + str(co.acad_session))
                    VAL.check_enrollment_allowed(co)
                    ccode, msg = VAL.validate_course_categorization(co, std_id)
                    CREDIT_NA_ALLOWED_MSG += msg
                    if ccode:
                        ALLOWED_COURSES.append(ccode)
                    conflicts = __get_slot_conflicts(co_id, std_id)
                    if len(conflicts) > 0:
                        return apiVC.error_json(conflicts)

                    coe = DB.CourseEnrollment()
                    existing_ce = __get_existing_enrolment(co_id, std_id)
                    if existing_ce:
                        coe = existing_ce
                    if ccode:
                        coe.enrol_status = "IPEN"
                        coe.enrol_type = fd["enrol_type"]
                        coe.course_offering = co_id
                        coe.student = std_id
                        if existing_ce:
                            apiVC.update_entity(DB.CourseEnrollment, coe)
                        else:
                            apiVC.save_entity(coe)
                        logging.debug("Saved: {}".format(coe))
                        VAL.check_enrolled_credits(std_id,co.acad_session)
                        send_enrolment_email(coe.id)

                # VAL.check_enrolled_credits(std_id)
                txn.commit()
            if CREDIT_NA_ALLOWED_MSG == "":
                return apiVC.ok_json("Enrollment requested successfully!")
            elif (len(ALLOWED_COURSES) != 0 and len(CREDIT_NA_ALLOWED_MSG)):
                return apiVC.ok_json("Enrollment requested successfully for " + str(ALLOWED_COURSES).replace('[','').replace(']','').replace('\'','') + ". " + CREDIT_NA_ALLOWED_MSG)
            else:
                return apiVC.ok_json(CREDIT_NA_ALLOWED_MSG)
        else:
            return apiVC.error_json("Please select a course to enrol!")
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

@rbac(roles=["ACA", "DEA", "FAC", "HOD"])
async def change_enroll_status():
    try:
        fd = await request.get_json(force=True)
        eids = fd.get("ids")
        status = fd.get("status")
        if len(eids) == 0:
            return apiVC.error_json("Select students to enrol first!")
        # if VC.is_user_in_role("FAC") and not validate_ce_approver(fd.get("ids")):
        #     return VC.error_json("You do not have privileges to approve one or more of the selected enrolments!")

        ce_ownership = __get_ce_ownership(eids)
        with DB.db.atomic() as txn:
            for eid in eids:
                ce = DB.CourseEnrollment.get_by_id(eid)
                enrol_status = ce.enrol_status
                new_status = ""
                if apiVC.is_user_in_role(["ACA", "DEA"]):
                    new_status = "ENRO" if status == "approve" else "ASREJ"
                elif apiVC.is_user_in_role(["FAC", "HOD"]):
                    ceos = ce_ownership[eid]
                    # User is course instructor
                    if ceos[0] and not(ceos[1]):
                        new_status = "APEN" if status == "approve" else "IREJ"
                    # User is batch advisor
                    elif ceos[1] and not(ceos[0]):
                        new_status = "ENRO" if status == "approve" else "AREJ"
                    # User is both instrcutor and batch advisor
                    elif ceos[0] and ceos[1] and enrol_status =="IPEN":
                        new_status = "APEN" if status == "approve" else "AREJ"
                    elif ceos[0] and ceos[1] and enrol_status =="APEN":
                        new_status = "ENRO" if status == "approve" else "AREJ"
                    elif apiVC.is_user_in_role("HOD") and enrol_status =="APEN":
                        new_status = "ENRO" if status == "approve" else "AREJ"
                    else:
                        raise AcadStackException("You do not have privileges to change one or more enrollments!")
                else:
                    raise AcadStackException("Unexpected user role: "+apiVC.logged_in_user().role)

                VAL.validate_enrolment_change(ce, new_status)

                ce.enrol_status = new_status
                if apiVC.update_entity(DB.CourseEnrollment, ce) == 1:
                    send_enrolment_email(eid)
            txn.commit()

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
        res = DB.CourseEnrollment.get_by_id(my_id)
        if res:
            if not VAL.is_enrollment_owner_valid(res):
                return apiVC.error_json("You are not allowed to view this enrolment!")
            obj = model_to_dict(res,
                                exclude=[DB.CourseEnrollment.course_offering.course.author,
                                         DB.CourseEnrollment.student.password_hashed])
            return apiVC.ok_json(obj)
        else:
            return apiVC.error_json(f"Enrollment record not found for ID {my_id}")
    except Exception as ex:
        msg = "Error when fetching DB.CourseEnrollment details."
        logging.exception(msg)
        return apiVC.error_json(msg)


@rbac
async def course_enrollment_save():
    try:
        fd = await request.get_json(force=True)
        logging.debug(f"Saving course enrollment details: {fd}")
        cid = int(fd.get("id") or 0)
        coe = DB.CourseEnrollment()
        with DB.db.atomic() as txn:
            old_data = {}
            if cid:
                coe = DB.CourseEnrollment.get_by_id(cid)
                old_data = model_to_dict(coe)
                old_data["enrol_status"] = dict(DB.CourseEnrollment.ENROL_STATUSES)[old_data["enrol_status"]]
                # Raises AcadStackException
                VAL.validate_enrolment_change(coe, fd.get("enrol_status"))

                if not VAL.is_enrollment_owner_valid(coe):
                    return apiVC.error_json("User not allowed to change enrollment!")

                C.update_model_skip_unknown(coe, fd)
                if apiVC.update_entity(DB.CourseEnrollment, coe) != 1:  # if rc != 1:
                    return apiVC.error_json("Could not update. Please try again.")
                logging.debug(f"Updated DB.CourseEnrollment details: {coe}")
            else:
                C.update_model_skip_unknown(coe, fd)
                apiVC.save_entity(coe)
                logging.debug(f"Inserted DB.CourseEnrollment: {coe}")

            send_enrolment_email(coe.id, old_rec=old_data)
            txn.commit()

        return await course_enrollment_view(coe.id)
    except AcadStackException as ae:
        logging.exception(ae)
        return apiVC.error_json(str(ae))
    except Exception as ex:
        msg = "Error when saving course enrollment details."
        logging.exception(msg, ex)
        return apiVC.error_json(msg)
