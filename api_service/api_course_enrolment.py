from io import BytesIO
import logging
from quart import Blueprint, request
from quart import current_app as APP
from quart.helpers import send_file
from peewee import IntegrityError
from common import AcadStackException, sql_by_id
from create_email import send_enrolment_email
from playhouse.shortcuts import model_to_dict
import api_common as apiVC
import settings as ST
import validation_checks as VAL
import models as DB
import common as C
import policy as P
import transcript as TR
import workflows as WF


def __get_ce_ownership(eids, actor):
    """For each enrolment ID: (the actor is its course coordinator, the actor
    is its student's batch advisor)."""
    sql1 = sql_by_id("frag_pending_enrollments")
    sql2 = sql_by_id("frag_ba_and_instructor")
    sql = "{0} {1}".format(sql1, sql2)
    param = tuple(eids)
    cursor = DB.db.execute_sql(sql, [P.roles_with("roster.student")] + [param])

    ba_instr = apiVC.result_set_from_cursor(cursor)
    data = {}
    for obj in ba_instr:
        is_instr = obj["instructor_id"] == actor.id
        is_advisor = obj["batch_adv_id"] == actor.id
        data[obj["id"]] = (is_instr, is_advisor)
    return data


def record_grade_change(ce, old_grade, actor, reason=None):
    """Logs the change of the enrolment's grade to ``ce.grade``. Call it in
    the transaction that saves the grade. Once the session is closed, a
    change needs a reason."""
    if VAL.is_session_closed(ce.course_offering.acad_session) and not reason:
        raise AcadStackException("The session is closed. Please give a reason "
                                 "for changing the grade.")
    apiVC.save_entity(DB.GradeChange(enrolment=ce, old_grade=old_grade,
                                     new_grade=ce.grade, changed_by=actor.login_id,
                                     reason=reason))


def check_enrolment_grade(coe):
    """Raises AcadStackException unless the enrolment's grade is one that the
    grading scheme of its student allows for its enrolment type."""
    if coe.grade == C.NO_GRADE:
        return
    acs = coe.course_offering.acad_session
    level = apiVC.degree_level(coe.student.person.degree) or "PG"
    allowed = apiVC.allowed_grades(apiVC.grading_rules(level, [acs])[acs], coe.enrol_type)
    if coe.grade not in allowed:
        kind = "an audit" if coe.enrol_type == "A" else f"a {level} student's"
        raise AcadStackException(f"Grade {coe.grade} is not allowed for {kind} "
                                 f"enrolment. Allowed grades are: {allowed}")


def __get_existing_enrolment(co_id, student_id):
    qry = DB.CourseEnrollment.select().where(
        (DB.CourseEnrollment.course_offering == co_id) &
        (DB.CourseEnrollment.student == student_id) &
        (DB.CourseEnrollment.enrol_status != 'ENRO')
    )
    return qry[0] if qry.exists() else None


def __check_student_fees_status():
    # Applies to users who may enrol only themselves (students).
    if not P.current_actor().has("enrolments.enrol:any"):
        qry = DB.FeesTransaction.select() \
            .where(
            (DB.FeesTransaction.student == apiVC.logged_in_user().id) &
            # Trimester sessions count too, not just semesters.
            (DB.FeesTransaction.acad_session.in_(apiVC.current_acad_session_list(sem_only=False))) &
            (DB.FeesTransaction.is_deleted != True) &
            (DB.FeesTransaction.fees_txn_amt > 0)
        )
        if not qry.exists():
            raise AcadStackException(
                "Semester registration fees payment details/proof are "
                "required before submitting enrolment requests! Kindly "
                "submit the necessary details first.")


def slot_conflicts(new_timings, existing_timings):
    """The existing slot timings that overlap any of the new ones: same week
    day and time ranges that intersect (touching ranges don't)."""
    return [x for x in existing_timings
            if any(n.week_day == x.week_day and
                   n.start_time < x.end_time and x.start_time < n.end_time
                   for n in new_timings)]


def __get_slot_conflicts(co_id, student_id):
    stu = DB.User.get_or_none(int(student_id))
    if not stu:
        raise AcadStackException("User record not found for student.")
    co = DB.CourseOffering.get_or_none(int(co_id))
    if not co:
        return []

    # Only the student's other offerings in the same session can clash.
    slots = []
    for ce in stu.enrollments.join(DB.CourseOffering).where(
            DB.CourseEnrollment.enrol_status.in_(["IPEN", "APEN", "ENRO"]) &
            (DB.CourseOffering.acad_session == co.acad_session) &
            (DB.CourseOffering.id != co.id)):
        if ce.course_offering.slot:
            slots.append(ce.course_offering.slot)

    cst_list = list(DB.CourseSlotTiming.select().where(
        (DB.CourseSlotTiming.slot.in_(slots))
        & (DB.CourseSlotTiming.is_deleted != True)))

    course_slots = apiVC.static_data_item("CourseSlots")
    new_timings = list(DB.CourseSlotTiming.select().where(
        (DB.CourseSlotTiming.slot == co.slot)
        & (DB.CourseSlotTiming.is_deleted != True)))
    if not new_timings:
        slot_nm = apiVC.label_for_static_data_item(co.slot, course_slots)
        raise AcadStackException(
            f"Slot timing not setup for slot: '{slot_nm}'. "
            "Please contact the administrator.")
    conflicts = []
    for x in slot_conflicts(new_timings, cst_list):
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
               "credits": se.credits,
               "remarks": se.remarks}
        
        # Fetch the student's user/profile info
        stud = DB.User.select(DB.User, DB.Person).join(DB.Person, DB.ORM.JOIN.LEFT_OUTER)\
            .where(DB.User.id == se.student_id)

        if stud:
            st_year_of_entry = stud[0].person.year_of_entry
            st_dept_name = stud[0].person.dept_name
            st_degree = stud[0].person.degree
        else:
            raise AcadStackException("User not found for student. UserId="
                                f"{se.student_id}")

        # Fetch course categorization info applicable to the student; it is
        # chosen by entry year, so a student without one has none.
        cat_info = DB.CourseCategory.select(). \
            join(DB.CourseOffering).\
            where(
            (DB.CourseCategory.offering == se.course_offering.id) &
            (DB.CourseCategory.degree == st_degree)&
            (DB.CourseCategory.dept << (st_dept_name, 'ALL')) &
            (DB.CourseCategory.for_entry_years.contains(st_year_of_entry))) \
            if st_year_of_entry else []

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
    
    # Sort by academic session. Needed for cgpa calculations
    acad_sess_list = TR.sort_sessions(enrol_data.keys(), apiVC.session_start_dates(enrol_data.keys()))
    
    # We return the enrolment data per academic session, sorted in reverse
    # chronological order of academic sessions (2025-II, 2025-I, 2024-II ...).
    enrol_data_sorted = dict()
    for key in acad_sess_list:
        enrol_data_sorted[key] = enrol_data[key]

    logging.debug(f"Sorted acad sessions: {acad_sess_list}")
    return acad_sess_list, enrol_data_sorted


def __get_student_courses_perf(stu, include_attendance):
    level = apiVC.degree_level(stu.person.degree)
    # 'CC' -> Credit for concentration
    perf_conc = get_student_courses_perf_filtered(stu, include_attendance, "CC", level)

    # 'CM' -> Credit for minor
    perf_minor = get_student_courses_perf_filtered(stu, include_attendance, "CM", level)

    # 'C' -> Credit
    perf_regu = get_student_courses_perf_filtered(stu, include_attendance, "C", level)

    user = model_to_dict(stu, exclude=[DB.User.password_hashed])
    user["enrollments"] = {"CC": perf_conc, "CM": perf_minor, "C": perf_regu}

    return user


def __get_advisor_action_items():
    u = apiVC.logged_in_user()
    qry1 = sql_by_id("frag_pending_enrollments")
    qry2 = sql_by_id("frag_ba_pending_enrollments")
    qry = f"{qry1} {qry2}"
    cursor = DB.db.execute_sql(qry, [P.roles_with("roster.student")] + [u.id])
    # Add the data rows
    results = apiVC.result_set_from_cursor(cursor)
    return results

# =================== Public methods ==================

def init_routes(bp:Blueprint):
    bp.add_url_rule('/coe_view/<int:my_id>', view_func=course_enrollment_view, methods=['GET'])
    bp.add_url_rule('/coe_save', view_func=course_enrollment_save, methods=['POST'])
    bp.add_url_rule('/enroll_in_courses', view_func=enroll_in_courses, methods=['POST'])
    bp.add_url_rule('/change_enroll_status', view_func=change_enroll_status, methods=['POST'])
    bp.add_url_rule('/co_bulkenrol/<path:entry_no_pattern>/<int:co_id>', 
                        view_func=bulk_enrol_in_course, methods=['GET'])
    bp.add_url_rule('/get_course_enrollments/<int:my_id>', view_func=get_course_enrollments, methods=['GET'])
    bp.add_url_rule('/get_student_academics/<int:my_id>', view_func=get_student_academics, methods=['GET'])
    bp.add_url_rule('/get_passed_courses/<int:user_id>', view_func=get_passed_courses, methods=['GET'])
    bp.add_url_rule('/drop_withdraw_course/<int:my_id>/<string:status>',
                       view_func=drop_withdraw_course, methods=['POST'])
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
                                        filter_by_enrol_type=None, level=None):
    """level: the student's degree_level, when the caller already has it."""
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
    # acad_sessions is already in properly sorted chronology
    rules = apiVC.grading_rules(level or apiVC.degree_level(stu.person.degree),
                                acad_sessions)
    gpas = TR.cumulative_gpa([enrol_data[ad]["courses"] for ad in acad_sessions],
                             [rules[ad] for ad in acad_sessions])
    for ad, gpa in zip(acad_sessions, gpas):
        enrol_data[ad].update(gpa)

    return {"enrollments": enrol_data, "acad_sessions": acad_sessions}


@P.require("enrolments.change")
async def drop_withdraw_course(my_id, status):
    try:
        if status not in ("DROP", "WDRAW"):
            return apiVC.error_json(f"Invalid status {status}! Only drop/withdraw allowed!")

        # Raises AcadStackException
        actor = P.current_actor()
        VAL.validate_enrolment_change(my_id, status, actor)

        if actor.has("enrolments.edit:any"):
            status = "ASREJ"

        ce = DB.CourseEnrollment.get_by_id(my_id)
        ce.enrol_status = status
        apiVC.save_entity(ce)
        send_enrolment_email(my_id)
        return apiVC.ok_json("Course enrollment updated successfully")
    except AcadStackException as ex:
        msg = "Error when dropping/withdrawing the course"
        logging.exception(msg)
        return apiVC.error_json(str(ex))
    except Exception as ex:
        msg = "Error when dropping/withdrawing the course"
        logging.exception(msg)
        return apiVC.error_json(msg)


@P.require("enrolments.pending_instructor")
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
        logging.exception(msg)
        return apiVC.error_json(msg)


@P.require("enrolments.pending_advisor")
async def get_advisor_courses_enrol():
    try:
        qry = sql_by_id("pending_enrolments_advisor")
        if P.current_actor().has("enrolments.pending_advisor:dept"):
            qry = sql_by_id("pending_enrolments_hod")

        cursor = DB.db.execute_sql(qry, [apiVC.logged_in_user().id])
        results = apiVC.result_set_from_cursor(cursor)

        return apiVC.ok_json(results)

    except Exception as ex:
        msg = "Error when fetching DB.CourseEnrollment details."
        logging.exception(msg)
        return apiVC.error_json(msg)


@P.require("students.academics")
async def get_passed_courses(user_id):
    try:
        VAL.check_own_or_any("students.academics", "user_id", user_id, 
            "Student attempted to access passed courses data for someone else.")

        stu = DB.User.get_by_id(user_id)
        if stu:
            res = []
            enrols = list(stu.enrollments)
            rules = apiVC.grading_rules(apiVC.degree_level(stu.person.degree),
                                        {se.course_offering.acad_session for se in enrols})
            for se in enrols:
                # Passed: a grade counted in the CGPA, or credit without a GPA
                rule = rules[se.course_offering.acad_session].get(se.grade.strip().upper(), {})
                if rule.get("in_cgpa") or rule.get("credit_without_gpa"):
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


@P.require("enrolments.bulk_enrol")
async def bulk_enrol_in_course(entry_no_pattern, co_id):
    try:
        if not entry_no_pattern.strip():
            return apiVC.error_json("Entry number pattern is required!")

        query = DB.User.select(DB.User.id, DB.Person.org_id, 
                               DB.User.role).join(DB.Person)
        query = query.where(DB.User.role.in_(P.roles_with("roster.student")) & (DB.User.is_deleted != True) &
                            (DB.Person.current_status == 'REG') &
                            DB.Person.org_id.startswith(entry_no_pattern))

        co = DB.CourseOffering.get_by_id(co_id)
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


@P.require("enrolments.download")
async def download_course_enrollments(co_id, is_grades=False):
    try:
        sql_id = "enrolled_students"
        co = DB.CourseOffering.get_by_id(co_id)
        if is_grades:
            if P.current_actor().allowed("grades.upload", own=lambda:
                    VAL.validate_course_instructor(co_id, coordinator_only=False)):
                sql_id = "get_course_grades"
            else:
                sql_id = "enrolled_students_for_grades"

        # Columns for the scores of the requested evaluation components, with
        # the stored scores in the downloaded grades
        comps = []
        scores = {}
        if is_grades:
            codes = [c.strip().upper() for c in request.args.get("components", "").split(",")
                     if c.strip()]
            comps = [ec for ec in co.eval_components.order_by(DB.EvalComponent.id)
                     if ec.code in codes]
            if comps and sql_id == "get_course_grades":
                rows = DB.EvalScore.select(DB.EvalScore, DB.CourseEnrollment, DB.User, DB.Person)\
                    .join(DB.CourseEnrollment).join(DB.User).join(DB.Person)\
                    .where(DB.EvalScore.component.in_(comps))
                scores = {(es.enrolment.student.person.org_id.upper(), es.component_id):
                          f"{float(es.score):g}" for es in rows}

        qry = sql_by_id(sql_id)
        cursor = DB.db.execute_sql(qry, [int(co_id)])
        ncols = len(cursor.description)
        colnames = [cursor.description[i][0] for i in range(ncols)]
        result = []

        # Add the header row
        hdr_row = []
        for col_name in colnames:
            hdr_row.append(col_name)
        result.append(','.join(hdr_row + [ec.code for ec in comps]))

        # Add the data rows
        for row in cursor.fetchall():
            row_data = []
            for i in range(ncols):
                row_data.append(row[i])
            row_data += [scores.get((row[2], ec.id), "") for ec in comps]
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


@P.require("grades.upload")
async def download_enrollments_for_grades(co_id):
    return await download_course_enrollments(co_id, True)


@P.require("enrolments.download")
async def download_course_enrolments(dept_name, entry_year, acad_session):
    try:
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


@P.require("students.academics")
async def get_student_academics(my_id):
    try:
        VAL.check_own_or_any("students.academics", "user_id", my_id, 
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


@P.require("students.academics")
async def get_course_enrollments(my_id):
    try:
        res = DB.CourseEnrollment.select().where(
            DB.CourseEnrollment.course_offering == my_id)
        actor = P.current_actor()
        if not actor.has("students.academics:any"):
            res = res.where(DB.CourseEnrollment.student == actor.id)
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


@P.require("enrolments.enrol")
async def enroll_in_courses():
    try:
        fd = await request.get_json(force=True)
        std_id = int(fd["user_id"])
        VAL.check_own_or_any("enrolments.enrol", "user_id", std_id, 
            "Student attempted to enrol someone else in a course.")
        if ST.get("fees_check_enabled"):
            __check_student_fees_status()
        CREDIT_NA_ALLOWED_MSG = ""
        ALLOWED_COURSES = []
        saved_ids = []
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
                        # Leaving atomic() by return commits, so undo the
                        # courses already saved in this request.
                        txn.rollback()
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
                        saved_ids.append(coe.id)

                # VAL.check_enrolled_credits(std_id)
                txn.commit()
            for ce_id in saved_ids:
                send_enrolment_email(ce_id)
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

@P.require("enrolments.approve")
async def change_enroll_status():
    try:
        fd = await request.get_json(force=True)
        eids = fd.get("ids")
        status = fd.get("status")
        if len(eids) == 0:
            return apiVC.error_json("Select students to enrol first!")
        actor = P.current_actor()
        ce_ownership = __get_ce_ownership(eids, actor)
        changed_ids = []
        with DB.db.atomic() as txn:
            for eid in eids:
                ce = DB.CourseEnrollment.get_by_id(eid)
                is_instr, is_advisor = ce_ownership.get(eid, (False, False))
                new_status = WF.enrolment_next_status(actor, ce.enrol_status, status,
                                                      is_instr, is_advisor)
                VAL.validate_enrolment_change(ce, new_status, actor)

                ce.enrol_status = new_status
                if apiVC.update_entity(DB.CourseEnrollment, ce) == 1:
                    changed_ids.append(eid)
            txn.commit()
        for eid in changed_ids:
            send_enrolment_email(eid)

        logging.info("Enrolled students in courses: {}".format(fd))
        return apiVC.ok_json("Changed successfully!")

    except AcadStackException as ae:
        logging.exception(ae)
        return apiVC.error_json(str(ae))

    except Exception as ex:
        msg = "Error when changing course enrollment status."
        logging.exception(msg)
        return apiVC.error_json("{0}".format(msg))


@P.require("enrolments.change")
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


# Request fields that coe_save copies onto an enrolment. Users allowed only
# through enrolments.change:own (students) may only drop or withdraw their own
# enrolment; only holders of enrolments.edit:any may create one here.
COE_EDIT_FIELDS = ["enrol_type", "enrol_status", "grade", "current_score",
                   "remarks", "txn_no"]
COE_STUDENT_FIELDS = ["enrol_status", "txn_no"]
COE_STUDENT_STATUSES = ["DROP", "WDRAW"]


@P.require("enrolments.change")
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
                old_grade = coe.grade
                old_data = model_to_dict(coe)
                old_data["enrol_status"] = dict(DB.CourseEnrollment.ENROL_STATUSES)[old_data["enrol_status"]]
                # Raises AcadStackException
                VAL.validate_enrolment_change(coe, fd.get("enrol_status"), P.current_actor())

                access = VAL.is_enrollment_owner_valid(coe)
                if not access:
                    return apiVC.error_json("User not allowed to change enrollment!")

                if access == "own":
                    if fd.get("enrol_status") not in COE_STUDENT_STATUSES + [coe.enrol_status]:
                        return apiVC.error_json("Students can only drop or withdraw a course!")
                    allowed = COE_STUDENT_FIELDS
                else:
                    allowed = COE_EDIT_FIELDS
                C.update_model_skip_unknown(coe, {k: v for k, v in fd.items() if k in allowed})
                if coe.grade != old_grade or coe.enrol_type != old_data["enrol_type"]:
                    check_enrolment_grade(coe)
                if coe.grade != old_grade:
                    record_grade_change(coe, old_grade, P.current_actor(),
                                        fd.get("grade_change_reason"))
                if apiVC.update_entity(DB.CourseEnrollment, coe) != 1:  # if rc != 1:
                    return apiVC.error_json("Could not update. Please try again.")
                logging.debug(f"Updated DB.CourseEnrollment details: {coe}")
            else:
                if not P.current_actor().has("enrolments.edit:any"):
                    return apiVC.error_json("User not allowed to create enrollment!")
                allowed = COE_EDIT_FIELDS + ["course_offering", "student"]
                C.update_model_skip_unknown(coe, {k: v for k, v in fd.items() if k in allowed})
                check_enrolment_grade(coe)
                apiVC.save_entity(coe)
                logging.debug(f"Inserted DB.CourseEnrollment: {coe}")

            txn.commit()

        send_enrolment_email(coe.id, old_rec=old_data)
        return await course_enrollment_view(coe.id)
    except AcadStackException as ae:
        logging.exception(ae)
        return apiVC.error_json(str(ae))
    except Exception as ex:
        msg = "Error when saving course enrollment details."
        logging.exception(msg)
        return apiVC.error_json(msg)
