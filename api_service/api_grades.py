import csv
import logging
import os
from pathlib import Path
import uuid
from quart import Blueprint, request
from quart.helpers import send_file
from io import BytesIO
from werkzeug.utils import secure_filename
from create_email import send_grades_submission_email

import policy as P
from api_auth import get_user_by_org_id
from api_course_enrolment import get_student_courses_perf_filtered, record_grade_change

import datetime
import shutil

import api_common as apiVC
import common as C
import models as DB
import settings as ST
import tasks_helper as TH
import validation_checks as VAL

# The report templates are sized for a canvas about 4/3 wider than the paper,
# so pages are laid out 4/3 larger than the paper and then zoomed out by 3/4.
_PDF_ZOOM = 0.75


def _html_to_pdf(html, target=None, size_mm=(210, 297), margin_mm=10):
    """Renders the HTML as a PDF on paper of ``size_mm`` (A4 by default):
    returns the bytes, or writes them to the file ``target``. Relative file
    paths in the HTML resolve against the working directory."""
    # Imported here so the app runs without WeasyPrint's system libraries
    # (Pango) when no PDF is rendered.
    from weasyprint import CSS, HTML

    width, height = (d / _PDF_ZOOM for d in size_mm)
    page_css = (f"@page {{ size: {width:.2f}mm {height:.2f}mm; "
                f"margin: {margin_mm / _PDF_ZOOM:.2f}mm }}")
    # presentational_hints: honour HTML layout attributes (width, align, ...)
    return HTML(string=html, base_url=os.getcwd()).write_pdf(
        target, stylesheets=[CSS(string=page_css)], zoom=_PDF_ZOOM,
        presentational_hints=True)


def _fill_report(template, data):
    """Renders a report template with the institute's name and place added to
    the data. A template of the same name in the report_templates folder of
    the upload folder is used in place of the one shipped with the app."""
    data = {"institute_name": ST.get("institute_name"),
            "institute_place": ST.get("institute_place"), **data}
    return C.fill_template("report_templates", template, data,
                           os.path.join(apiVC.get_upload_folder(), "report_templates"))


def init_routes(bp: Blueprint):
    bp.add_url_rule('/download_grade_distribution/<string:acad_session>/<string:degree>',
                       view_func=download_grade_distribution, methods=['GET'])
    bp.add_url_rule('/generate_semester_grade', view_func=generate_semester_grade, methods=['POST'])
    bp.add_url_rule('/download_sem_grade/<string:acad_session>/<string:entry_no>/<string:enrol_type>', 
                       view_func=download_sem_grade, methods=['GET'])
    bp.add_url_rule('/download_cgpa_sgpa/<string:acad_session>',
                       view_func=download_cgpa_sgpa, methods=['GET'])
    bp.add_url_rule(('/download_catwise_earned_credits/<string:acad_session>/'
                        '<string:degree>/<string:dept_name>/<string:course_type>/'
                        '<string:for_year>/<string:min_credits>/<string:max_credits>'),
                       view_func=download_catwise_earned_credits, methods=['GET'])
    bp.add_url_rule('/download_grade_status/<string:grades_st>/<string:acad_session>', 
                       view_func=download_grade_status, methods=['GET'])
    bp.add_url_rule('/bulk_download_sem_grade', view_func=bulk_download_sem_grade, 
                       methods=['POST'])
    bp.add_url_rule('/get_gradesheets/<string:job_key>', 
                       view_func=get_bulk_gradesheets, methods=['GET'])
    bp.add_url_rule(('/download_degree_certifcate/<string:entry_no>/<string:hi_name>'
                        '/<string:thesis_title>/<string:doc_sr_no>/<string:convocation_date>'),
                       view_func=download_degree_certifcate, methods=['GET'])
    bp.add_url_rule('/download_consolidated_grade_sheet/<string:entry_no>/<string:enrol_type>',
                       view_func=download_consolidated_grade_sheet, methods=['GET'])
    bp.add_url_rule('/grades_upload', view_func=grades_upload, methods=['POST'])
    bp.add_url_rule('/close_session', view_func=close_session, methods=['POST'])


@P.require("grades.reports")
async def download_grade_status(grades_st, acad_session):
    try:
        if grades_st == "GS":
            sql_id = "grades_status_submitted"
        else:
            sql_id = 'grades_status_pending'

        # Submitted: a grade of the grading schemes; pending: any other
        cursor = DB.db.execute_sql(C.sql_by_id(sql_id),
                                   [str(acad_session), apiVC.scheme_grades()])

        fp = apiVC.db_result_to_excel(cursor)
        return await send_file(fp,
                         attachment_filename="download_grade_status.csv",
                         as_attachment=True)
    except Exception as ex:
        msg = "Error when Downloading Grade Status as CSV."
        logging.exception(msg)
        return apiVC.error_json(msg)


@P.require("grades.reports")
async def download_consolidated_grade_sheet(entry_no,enrol_type):
        try:
            report_data = {}
            stu = get_user_by_org_id(entry_no)

            # if not stu:
            #     raise C.AcadStackException("Student {0} not found!".format(entry_no))
            if "roster.student" not in P.perms_of(stu.role):
                msg = "Only Student Gradesheet can be downloaded!"
                logging.error(msg)
                return apiVC.error_json(msg)
            # Fill the sudents personal info
            # report_data = _get_student_courses_perf(stu, True)
            report_data = get_student_courses_perf_filtered(stu, False, enrol_type)
            sem_courses = []
            for index,courses in report_data["enrollments"].items():
                sem_courses = courses

            s = 0
            acd_sess_to_remove = ""
            for acd,value in report_data["enrollments"].items():
                s = 0
                sem_courses = courses
                for cdata in value['courses']:
                    if cdata['enrol_status'] == 'ENRO':
                        s+= 1
                if s == 0:
                    acd_sess_to_remove = acd

            if acd_sess_to_remove != "":
                report_data["enrollments"].pop(acd_sess_to_remove)

            sem_courses['courses'] = list(filter(lambda i: i['enrol_status'] == "ENRO", sem_courses['courses']))

            report_data["name"] = "{0} {1}".format(stu.first_name, stu.last_name)
            report_data["entry_no"] = stu.person.org_id

            degree = stu.person.degree
            degreetypes = apiVC.static_data_item("Degrees")
            degree = apiVC.label_for_static_data_item(degree, degreetypes).upper()

            report_data["degree"] = degree
            report_data.update(apiVC.degree_print_fields(stu.person.degree, degree))

            dept_name = stu.person.dept_name
            depttypes = apiVC.static_data_item("Departments")
            dept_name = apiVC.label_for_static_data_item(dept_name, depttypes).upper()

            report_data["dept_name"] = dept_name

            date_issue = datetime.datetime.now()
            report_data["date_issue"] = date_issue.strftime("%d-%b-%Y")

            deg_type = stu.person.deg_type
            if deg_type:
                degtype = apiVC.static_data_item("DegreeType")
                deg_type = apiVC.label_for_static_data_item(deg_type, degtype).upper()
            else:
                deg_type = "NA"
            report_data["deg_type"] = deg_type

            static_file_dir = 'assets-degree'
            file_folder = os.path.join(apiVC.get_upload_folder(), static_file_dir)
            report_data["static_file_path"] = file_folder

            html = _fill_report("consolidatedGradeSheetnew.html", report_data)
            # US Legal paper with 0.1in margins
            pdf_str = _html_to_pdf(html, size_mm=(215.9, 355.6), margin_mm=2.54)
            fp = BytesIO()
            fp.write(pdf_str)
            fp.flush()
            fp.seek(0)
            return await send_file(fp, attachment_filename=f"grades_{entry_no}.pdf",
                            as_attachment=True)

        except C.AcadStackException as ae:
            return apiVC.error_json(str(ae))
        except Exception as ex:
            logging.error(ex)
            return apiVC.error_json("Error occurred when generating the degree "
                                 "certificate PDF file for download.")


def _get_semester_grade_data(entry_no, acad_session, enrol_type):
    acad_session = acad_session.strip()
    report_data = {}
    if acad_session and not apiVC.academic_session_valid(acad_session):
        raise C.AcadStackException("Unknown academic session.")

    stu = get_user_by_org_id(entry_no)
    if not stu:
        raise C.AcadStackException(f"Student {entry_no} not found!")
    # Fill the sudents personal info
    report_data["name"] = f"{stu.first_name} {stu.last_name}"
    report_data["entry_no"] = stu.person.org_id

    degree = stu.person.degree
    degreetypes = apiVC.static_data_item("Degrees")
    degree = apiVC.label_for_static_data_item(degree, degreetypes).upper()

    report_data["degree"] = degree
    report_data.update(apiVC.degree_print_fields(stu.person.degree, degree))

    dept_name = stu.person.dept_name
    depttypes = apiVC.static_data_item("Departments")
    dept_name = apiVC.label_for_static_data_item(dept_name, depttypes).upper()

    report_data["dept_name"] = dept_name
    date_issue = datetime.datetime.now()
    report_data["date_issue"] = date_issue.strftime("%d-%b-%Y")
    report_data["last_acad_session"] = acad_session


    deg_type_spec = stu.person.deg_type_spec
    degtypespec = apiVC.static_data_item("MinorConcSpecialization")
    if deg_type_spec is not None:
        deg_type_spec = apiVC.label_for_static_data_item(deg_type_spec, degtypespec).upper()
        report_data["deg_type_spec"] = deg_type_spec

   #TODo: check method calling with three parameters.
    all_data = get_student_courses_perf_filtered(stu, False, enrol_type)
    if not all_data["enrollments"]:
        raise C.AcadStackException("Records not found for this degree "
                                f"type for student {entry_no}")
    sem_courses = []
    for acd, courses in all_data["enrollments"].items():
        if acd == acad_session:
            sem_courses = courses
    if not sem_courses:
        #raise C.AcadStackException("Records not found for student {0}".format(entry_no))
        return False
    sem_courses['courses'] = list(filter(lambda i: i['enrol_status'] == "ENRO", sem_courses['courses']))
    report_data["courses"] = sem_courses['courses']
    report_data['sgpa'] =   sem_courses['sgpa']
    report_data['ec']  =  sem_courses['ec']
    report_data['creg']   = sem_courses['creg']
    report_data['cec'] = sem_courses['cec']
    report_data['cgpa'] = sem_courses['cgpa']
    return report_data


@P.require("grades.reports")
async def generate_semester_grade():
    try:
        fd = await request.get_json(force=True)
        entry_no = fd.get("entry_no")
        acad_session = fd.get("acad_session")
        enrol_type = fd.get("enrol_type")
        resp = _get_semester_grade_data(entry_no, acad_session, enrol_type)
        # TODO: Update the UI for this change
        if resp:
            return apiVC.ok_json(resp)
        else:
            raise C.AcadStackException(f"Records not found for student {entry_no}")
    except Exception as ex:
        msg = "Error occurred when process semester grade generation request."
        logging.exception(msg)
        return apiVC.error_json(str(ex) if isinstance(ex, C.AcadStackException) else msg)


@P.require("grades.reports")
async def download_sem_grade(acad_session, entry_no, enrol_type):
    try:
        data = _get_semester_grade_data(entry_no, acad_session, enrol_type)
        data['enrol_type'] = enrol_type
        # TODO: Check the HTML and the data's structure
        html = _fill_report("semester_grades.html", data)

        pdf_str = _html_to_pdf(html)
        fp = BytesIO()
        fp.write(pdf_str)
        fp.flush()
        fp.seek(0)
        return await send_file(fp,
                         attachment_filename=f"grades_{entry_no}_{acad_session}.pdf",
                         as_attachment=True)

    except C.AcadStackException as ae:
        return apiVC.error_json(str(ae))
    except Exception as ex:
        logging.error(ex)
        return apiVC.error_json("Error occurred when generating the grade "
                            "sheet PDF file for download.")


def _get_student_entry_no_data(degree,dept_name,year_of_entry):
    query = DB.User.select(DB.User.id, DB.Person.id, DB.Person.dept_name, 
            DB.Person.org_id, DB.User.role, DB.User.first_name, 
            DB.User.last_name).join(DB.Person, DB.ORM.JOIN.LEFT_OUTER)
    query = query.where(DB.User.is_deleted != True)
    query = query.where(DB.User.role.in_(P.roles_with("roster.student")) & 
                (DB.Person.degree.startswith(degree)) & 
                (DB.Person.dept_name.startswith(dept_name)) & 
                (DB.Person.year_of_entry.startswith(year_of_entry)))
    users = query.order_by(DB.Person.org_id)
    serialized = [r.person.org_id for r in users]
    return serialized


def _bulk_download_sem_grade(form_data, job_key):
    try:
        degree = form_data.get("degree")
        dept_name = form_data.get("dept_name")
        acad_session = form_data.get("acad_session")
        enrol_type = form_data.get("enrol_type")
        year_of_entry = str(form_data.get("for_year"))
        sub_dir = 'BULK_GS_PDF'
        missing_stu_enrol = []
        file_folder = os.path.join(apiVC.get_upload_folder(), sub_dir, job_key)
        zip_file = f"{os.path.join(apiVC.get_upload_folder(), sub_dir)}_{job_key}"
        Path(file_folder).mkdir(parents=True, exist_ok=True)
        resp = _get_student_entry_no_data(degree,dept_name,year_of_entry)
        if not resp:
            raise C.AcadStackException(f"No student record found in {dept_name} "
                                f"Department for Entry Year {year_of_entry}")
        for entry_no in resp:
            data = _get_semester_grade_data(entry_no, acad_session, enrol_type)
            if data:
                data['enrol_type'] = enrol_type
                html = _fill_report("semester_grades.html", data)
                out_pdf = f"{file_folder}/grades_{entry_no}_{acad_session}.pdf"
                _html_to_pdf(html, out_pdf)
            else:
                missing_stu_enrol.append(entry_no)
                continue
        # ZIP all the pdf files
        shutil.make_archive(zip_file, 'zip', file_folder)
    except Exception as ex:
        msg = "Error occurred when processing bulk semester grade generation request."
        logging.exception(msg)
        return apiVC.error_json(str(ex) if isinstance(ex, C.AcadStackException) else msg)
    logging.info("Missing Students Sem Grades Sheet, While Bulk "
                f"downloading: {missing_stu_enrol}")
    return zip_file


@P.require("grades.reports")
async def bulk_download_sem_grade():
    try:
        job_key = str(uuid.uuid4())
        form_data = await request.get_json(force=True)
        job_key = TH.create_task(_bulk_download_sem_grade, form_data, job_key, task_id=job_key)
        logging.info(f"Submitted background task (bulk grade download) with key {job_key}")
        return apiVC.ok_json({"job_key": job_key, "message": "Request successfully submitted."})
    except Exception as ex:
        msg = "Failed to generate the bulk grade sheets."
        logging.exception(msg)
        return apiVC.error_json(msg)


@P.require("grades.reports")
async def get_bulk_gradesheets(job_key):
    try:
        if not TH.get_own_task_info(job_key):
            return apiVC.error_json(f"Job info not found for {job_key}")
        zip_file = os.path.join(apiVC.get_upload_folder(), f"BULK_GS_PDF_{job_key}.zip")
        return await send_file(zip_file)

    except Exception as ex:
        msg = "Error when loading bulk grade sheets ZIP file."
        logging.exception(msg)
        return apiVC.error_json(msg)


@P.require("grades.distribution")
async def download_grade_distribution(acad_session, degree):
    try:
        if degree == "-":
            degree = ""
        if acad_session == "-":
            acad_session = ""

        cursor = DB.db.execute_sql(C.sql_by_id("generate_grade_distribution"),
                                [str(acad_session),
                                 str(degree)])
        fp = apiVC.db_result_to_excel(cursor)
        return await send_file(fp,
                         attachment_filename="download_grade_distribution.csv",
                         as_attachment=True)
    except Exception as ex:
        msg = "Error when loading enrolment data as CSV."
        logging.exception(msg)
        return apiVC.error_json(msg)


@P.require("credits.reports")
async def download_cgpa_sgpa(acad_session):
    try:
        if acad_session == "-":
            acad_session = ""

        cursor = DB.db.execute_sql(C.sql_by_id("generate_cgpa_sgpa"),
                                [str(acad_session)])
        fp = apiVC.db_result_to_excel(cursor)
        return await send_file(fp, attachment_filename="download_cgpa_sgpa.csv",
                         as_attachment=True)
    except Exception as ex:
        msg = "Error when loading enrolment data as CSV."
        logging.exception(msg)
        return apiVC.error_json(msg)


@P.require("grades.reports")
async def download_degree_certifcate(entry_no, hi_name, thesis_title, doc_sr_no,
                                     convocation_date):
        try:
            report_data = {}
            if convocation_date == "NA":
                report_data["convocation_date"] = ""
            else:
                try:
                    d = datetime.date.fromisoformat(convocation_date)
                    report_data["convocation_date"] = f"{d.day} {d:%B %Y}"
                except ValueError:
                    raise C.AcadStackException("The convocation date is not a valid date.")
            stu = get_user_by_org_id(entry_no)
            doc_sr_no = doc_sr_no.replace("-", "/")
            if not stu:
                raise C.AcadStackException(f"Student {entry_no} not found!")
            # Fill the sudents personal info
            report_data["name"] = f"{stu.first_name} {stu.last_name}"
            report_data["entry_no"] = stu.person.org_id
            report_data["hi_name"] = hi_name
            if thesis_title == "NA":
                thesis_title = ""

            report_data["thesis_title"] = thesis_title

            degree = stu.person.degree
            degreetypes = apiVC.static_data_item("Degrees")
            degree = apiVC.label_for_static_data_item(degree, degreetypes)

            report_data["degree"] = degree
            report_data.update(apiVC.degree_print_fields(stu.person.degree, degree))

            dept_name = stu.person.dept_name
            depttypes = apiVC.static_data_item("Departments")
            dept_name = apiVC.label_for_static_data_item(dept_name, depttypes)

            report_data["dept_name"] = dept_name
            report_data["doc_sr_no"] = doc_sr_no


            min_con_specialization = stu.person.deg_type_spec
            if min_con_specialization:
                minconspecialization = apiVC.static_data_item("MinorConcSpecialization")
                min_con_specialization = apiVC.label_for_static_data_item(min_con_specialization, 
                                            minconspecialization)

                report_data["min_con_specialization"] = min_con_specialization
            else:
                min_con_specialization = ''

            static_file_dir = 'assets-degree'
            file_folder = os.path.join(apiVC.get_upload_folder(), static_file_dir)
            report_data["static_file_path"] = file_folder

            html = _fill_report("degree.html", report_data)
            pdf_str = _html_to_pdf(html)
            fp = BytesIO()
            fp.write(pdf_str)
            fp.flush()
            fp.seek(0)
            return await send_file(fp, attachment_filename=f"grades_{entry_no}.pdf",
                            as_attachment=True)

        except C.AcadStackException as ae:
            return apiVC.error_json(str(ae))
        except Exception as ex:
            logging.error(ex)
            return apiVC.error_json("Error occurred when generating the degree "
                                "certificate PDF file for download.")


@P.require("credits.reports")
async def download_catwise_earned_credits(acad_session,degree,dept_name,course_type,
    for_year,min_credits,max_credits):
    try:
        if dept_name == "ALL" or dept_name == "-":
           dept_name = ""
        if degree == "-":
            degree = ""
        if for_year == "-":
            for_year = ""
        if acad_session == "-":
            acad_session = ""
        if course_type == "-":
            course_type = ""
        if min_credits == "-":
            min_credits = ""
        if max_credits == "-":
            max_credits = ""
        cursor = DB.db.execute_sql(C.sql_by_id("download_filtered_categorized_credits_enrolled"),
                            [str(for_year),str(for_year), str(for_year),
                            str(degree), str(degree),
                            str(dept_name), str(dept_name),
                            str(acad_session), str(acad_session),
                            *apiVC.graded_rows("earns_credit"),
                            str(course_type), str(course_type),
                            int(min_credits), int(max_credits)])

        fp = apiVC.db_result_to_excel(cursor)
        return await send_file(fp,
                         attachment_filename=f"course_enrolments_{for_year}.csv",
                         as_attachment=True)
    except Exception as ex:
        msg = "Error when download_filtered categorized credits enrolled CSV."
        logging.exception(msg)
        return apiVC.error_json(msg)

@P.require("grades.upload")
async def grades_upload():
    try:
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
        # Only the course instructor OR dean may upload the course grades            
        if not P.current_actor().allowed("grades.upload",
                                         own=lambda: VAL.validate_course_instructor(co_id)):
            return apiVC.error_json("Only the course coordinator can upload grades for the course!")

        # Raises exception when change not allowed
        VAL.validate_coff_status(co_id)

        grades_file = (await request.files)['grades_file']
        if grades_file.filename == '':
            return apiVC.error_json("No grades .csv file supplied!")
        filename = secure_filename(grades_file.filename)
        file_path = os.path.join(apiVC.get_upload_folder_for_user(), filename)
        await grades_file.save(file_path)

        # Convert all text to uppercase in the grades file
        with open(file_path, 'r') as inp:
            y = inp.read().upper().strip()
            lines = y.splitlines()
            if len(lines) < 2:
                return apiVC.error_json("No grades found in the CSV file you uploaded. Please upload a non-empty CSV file!")

            if not lines[0].replace(' ', '').startswith("FIRST_NAME,LAST_NAME,ROLL_NO,GRADE"):
                return apiVC.error_json("Invalid header row in CSV. Please make sure that the header row contains only: roll_no, grade")

            invalid_rows = []
            valid_grades = apiVC.valid_grades()
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
        # The grade rules of each program level in the offering's session
        level_rules = {}
        with DB.db.atomic() as txn:
            with open(file_path, newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    roll_no = row["ROLL_NO"].upper().strip()
                    grade = row["GRADE"].upper().strip()
                    stu = DB.User.select(DB.User, DB.Person).join(DB.Person)\
                        .where(DB.ORM.fn.UPPER(DB.Person.org_id) == roll_no)[0]
                    coe = DB.CourseEnrollment.select().where(
                        (DB.CourseEnrollment.course_offering == co_id) &
                        (DB.CourseEnrollment.student == stu.id)
                    )[0]

                    level = apiVC.degree_level(stu.person.degree) or "PG"
                    if level not in level_rules:
                        level_rules[level] = apiVC.grading_rules(
                            level, [co_obj.acad_session])[co_obj.acad_session]
                    allowed = apiVC.allowed_grades(level_rules[level], coe.enrol_type)
                    if grade not in allowed:
                        kind = "audited course" if coe.enrol_type == "A" else f"{level} student"
                        raise C.AcadStackException(f"Invalid grade {grade} assigned "
                                f"to {roll_no} ({kind}). Allowed grades are: {allowed}")

                    if coe.grade == grade:
                        logging.debug("Grade unchanged, skipping the update.")
                        continue

                    old_grade = coe.grade
                    coe.grade = grade
                    record_grade_change(coe, old_grade, P.current_actor())
                    apiVC.update_entity(DB.CourseEnrollment, coe)
                    upd_count += 1

            txn.commit()
        if not P.current_actor().has("roster.acad_section"):
            send_grades_submission_email(co_id, upd_count)
        return apiVC.ok_json(f"Grades processed successfully! Added/updated {
            upd_count} records.")

    except C.AcadStackException as ae:
        logging.exception(ae)
        return apiVC.error_json(str(ae))
    except Exception as ex:
        msg = "Error when handling grades upload request."
        logging.exception(msg)
        return apiVC.error_json(msg)


@P.require("sessions.close")
async def close_session():
    """Closes an academic session: copies each enrolment's credits onto the
    enrolment, so later changes to courses don't change transcripts. Grades
    of the session's (finished) offerings stay locked to offerings.edit_closed,
    and changing one needs a reason from then on."""
    try:
        fd = await request.get_json(force=True)
        acad_session = fd.get("acad_session")
        if not (acad_session and apiVC.academic_session_valid(acad_session)):
            return apiVC.error_json("Please supply a valid academic session!")
        if VAL.is_session_closed(acad_session):
            return apiVC.error_json(f"Session {acad_session} is already closed.")

        offerings = DB.CourseOffering.select(DB.CourseOffering, DB.Course)\
            .join(DB.Course).where(DB.CourseOffering.acad_session == acad_session)
        running = sorted({co.course.code for co in offerings if co.status in ("E", "R")})
        if running:
            return apiVC.error_json("These courses are still enrolling or running: "
                                    f"{', '.join(running)}")
        pending = DB.CourseEnrollment.select(DB.CourseEnrollment, DB.CourseOffering, DB.Course)\
            .join(DB.CourseOffering).join(DB.Course).where(
                (DB.CourseOffering.acad_session == acad_session) &
                (DB.CourseOffering.status.not_in(["C", "D"])) &
                (DB.CourseEnrollment.enrol_status == "ENRO") &
                (DB.CourseEnrollment.grade.not_in(apiVC.scheme_grades())))
        pending = sorted({ce.course_offering.course.code for ce in pending})
        if pending:
            return apiVC.error_json("Grades are pending in these courses: "
                                    f"{', '.join(pending)}")

        with DB.db.atomic():
            cursor = DB.db.execute_sql(C.sql_by_id("freeze_session_credits"), [acad_session])
            frozen = cursor.rowcount
            apiVC.save_entity(DB.AcademicCalendar(acad_session=acad_session,
                                                  event_code="SESSION_CLOSED",
                                                  event_value=C.current_dt_str()))
        return apiVC.ok_json(f"Closed session {acad_session}: froze the credits "
                             f"of {frozen} enrolments.")
    except C.AcadStackException as ae:
        return apiVC.error_json(str(ae))
    except Exception:
        msg = "Error when closing the session."
        logging.exception(msg)
        return apiVC.error_json(msg)
