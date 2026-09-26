import logging
import os
from pathlib import Path
import uuid
from quart import Blueprint, request
from quart.helpers import send_file
from quart.utils import run_sync
from io import BytesIO

from validation_checks import is_current_user_in_role_and_id
from api_auth import get_user_by_org_id
from domain import transcript as TR

import datetime
import shutil
import pdfkit

import api_common as apiVC
import common as C
import models as DB
import tasks_helper as TH

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
                        '/<string:thesis_title>/<string:doc_sr_no>'),
                       view_func=download_degree_certifcate, methods=['GET'])
    bp.add_url_rule('/download_consolidated_grade_sheet/<string:entry_no>/<string:enrol_type>',
                       view_func=download_consolidated_grade_sheet, methods=['GET'])


@C.rbac(permissions=["grades.export"])
async def download_grade_status(grades_st, acad_session):
    if grades_st == "GS":
        sql_id = "grades_status_submitted"
    else:
        sql_id = 'grades_status_pending'

    cursor = DB.db.execute_sql(C.sql_by_id(sql_id),
                            [str(acad_session)])

    fp = apiVC.db_result_to_excel(cursor)
    return await send_file(fp,
                     attachment_filename="download_grade_status.csv",
                     as_attachment=True)


@C.rbac(permissions=["grades.export"])
async def download_consolidated_grade_sheet(entry_no,enrol_type):
        report_data = {}
        stu = get_user_by_org_id(entry_no)

        # if not stu:
        #     raise C.AcadStackException("Student {0} not found!".format(entry_no))
        if stu.role != 'STU':
            msg = "Only Student Gradesheet can be downloaded!"
            logging.error(msg)
            return apiVC.error_json(msg)
        # Fill the sudents personal info
        # report_data = _get_student_courses_perf(stu, True)
        report_data = TR.courses_perf_filtered(stu, False, enrol_type)
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

        html = C.fill_template("report_templates", 
                "consolidatedGradeSheetnew.html", report_data)
        options = {
            'page-size': 'Legal',
            'orientation': 'Portrait',
            'encoding': "UTF-8",
            'margin-top': '0.1in',
            'margin-right': '0.1in',
            'margin-bottom': '0.1in',
            'margin-left': '0.1in',
            'custom-header': [
                ('Accept-Encoding', 'gzip')
            ],
            'no-outline': None,
            "enable-local-file-access": ""
        }
        pdf_str = await run_sync(pdfkit.from_string)(html, False, options=options)
        fp = BytesIO()
        fp.write(pdf_str)
        fp.flush()
        fp.seek(0)
        return await send_file(fp, attachment_filename=f"grades_{entry_no}.pdf",
                        as_attachment=True)


def _get_semester_grade_data(entry_no, acad_session, enrol_type, actor=None):
    acad_session = acad_session.strip().upper()
    report_data = {}
    if acad_session and not apiVC.academic_session_valid(acad_session):
        raise C.AcadStackException("Expected academic session in YYYY-S format.")

    is_current_user_in_role_and_id("STU", "org_id", entry_no, 
        "Student attempted to access someone else's grades sheet.",
        actor=actor)
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
    all_data = TR.courses_perf_filtered(stu, False, enrol_type)
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


@C.rbac(permissions=["grades.export"])
async def generate_semester_grade():
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


@C.rbac(permissions=["grades.export"])
async def download_sem_grade(acad_session, entry_no, enrol_type):
    data = _get_semester_grade_data(entry_no, acad_session, enrol_type)
    data['enrol_type'] = enrol_type
    # TODO: Check the HTML and the data's structure
    html = C.fill_template("report_templates", "semester_grades.html", data)

    pdf_str = await run_sync(pdfkit.from_string)(html, False, options={"enable-local-file-access": ""})
    fp = BytesIO()
    fp.write(pdf_str)
    fp.flush()
    fp.seek(0)
    return await send_file(fp,
                     attachment_filename=f"grades_{entry_no}_{acad_session}.pdf",
                     as_attachment=True)


def _get_student_entry_no_data(degree,dept_name,year_of_entry):
    query = DB.User.select(DB.User.id, DB.Person.id, DB.Person.dept_name, 
            DB.Person.org_id, DB.User.role, DB.User.first_name, 
            DB.User.last_name).join(DB.Person, DB.ORM.JOIN.LEFT_OUTER)
    query = query.where(DB.User.is_deleted != True)
    query = query.where((DB.User.role == "STU") & 
                (DB.Person.degree.startswith(degree)) & 
                (DB.Person.dept_name.startswith(dept_name)) & 
                (DB.Person.year_of_entry.startswith(year_of_entry)))
    users = query.order_by(DB.Person.org_id)
    serialized = [r.person.org_id for r in users]
    return serialized


def _bulk_download_sem_grade(form_data, job_key, upload_folder, actor):
    """Runs on an executor thread (TH.create_task), so the upload folder
    and acting user come in as arguments, not from the app/session."""
    degree = form_data.get("degree")
    dept_name = form_data.get("dept_name")
    acad_session = form_data.get("acad_session")
    enrol_type = form_data.get("enrol_type")
    year_of_entry = str(form_data.get("for_year"))
    sub_dir = 'BULK_GS_PDF'
    missing_stu_enrol = []
    file_folder = os.path.join(upload_folder, sub_dir, job_key)
    zip_file = f"{os.path.join(upload_folder, sub_dir)}_{job_key}"
    Path(file_folder).mkdir(parents=True, exist_ok=True)
    resp = _get_student_entry_no_data(degree,dept_name,year_of_entry)
    if not resp:
        raise C.AcadStackException(f"No student record found in {dept_name} "
                            f"Department for Entry Year {year_of_entry}")
    for entry_no in resp:
        data = _get_semester_grade_data(entry_no, acad_session, enrol_type,
                                        actor=actor)
        if data:
            data['enrol_type'] = enrol_type
            html = C.fill_template("report_templates", "semester_grades.html", data)
            out_pdf = f"{file_folder}/grades_{entry_no}_{acad_session}.pdf"
            pdfkit.from_string(html, out_pdf, \
                                options={"enable-local-file-access": ""})
        else:
            missing_stu_enrol.append(entry_no)
            continue
    # ZIP all the pdf files
    shutil.make_archive(zip_file, 'zip', file_folder)
    logging.info("Missing Students Sem Grades Sheet, While Bulk "
                f"downloading: {missing_stu_enrol}")
    return zip_file


@C.rbac(permissions=["grades.export"])
async def bulk_download_sem_grade():
    job_key = str(uuid.uuid4())
    form_data = await request.get_json(force=True)
    job_key = TH.create_task(_bulk_download_sem_grade, form_data, job_key,
                             apiVC.get_upload_folder(), apiVC.current_actor(),
                             task_id=job_key, owner=apiVC.current_login_id())
    logging.info(f"Submitted background task (bulk grade download) with key {job_key}")
    return apiVC.ok_json({"job_key": job_key, "message": "Request successfully submitted."})


@C.rbac(permissions=["grades.export"])
async def get_bulk_gradesheets(job_key):
    zip_file = os.path.join(apiVC.get_upload_folder(), f"BULK_GS_PDF_{job_key}.zip")
    return await send_file(zip_file)


@C.rbac(permissions=["grades.view_distribution"])
async def download_grade_distribution(acad_session, degree):
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


@C.rbac
async def download_cgpa_sgpa(acad_session):
    if not apiVC.has_permission("grades.download_reports"):
        return apiVC.error_json("Students cannot download!")

    if acad_session == "-":
        acad_session = ""

    cursor = DB.db.execute_sql(C.sql_by_id("generate_cgpa_sgpa"),
                            [str(acad_session)])
    fp = apiVC.db_result_to_excel(cursor)
    return await send_file(fp, attachment_filename="download_cgpa_sgpa.csv",
                     as_attachment=True)


@C.rbac(permissions=["grades.export"])
async def download_degree_certifcate(entry_no, hi_name, thesis_title, doc_sr_no):
        report_data = {}
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

        html = C.fill_template("report_templates", "degree.html", report_data)
        pdf_str = await run_sync(pdfkit.from_string)(html, False, options={"enable-local-file-access": ""})
        fp = BytesIO()
        fp.write(pdf_str)
        fp.flush()
        fp.seek(0)
        return await send_file(fp, attachment_filename=f"grades_{entry_no}.pdf",
                        as_attachment=True)


@C.rbac
async def download_catwise_earned_credits(acad_session,degree,dept_name,course_type,
    for_year,min_credits,max_credits):
    if not apiVC.has_permission("grades.download_reports"):
        return apiVC.error_json("Students cannot download!")

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
                        str(course_type), str(course_type),
                        int(min_credits), int(max_credits)])

    fp = apiVC.db_result_to_excel(cursor)
    return await send_file(fp,
                     attachment_filename=f"course_enrolments_{for_year}.csv",
                     as_attachment=True)
