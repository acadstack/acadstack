import csv
import logging
import os
from quart import Blueprint, request
from werkzeug.utils import secure_filename
from peewee import IntegrityError
from create_email import send_course_updated_email
from validation_checks import is_course_status_valid_for_current_user
import api_common as apiVC
import models as DB
import common as C

def init_routes(bp: Blueprint):
    bp.add_url_rule('/cour/<int:my_id>', view_func=course_view, methods=['GET'])
    bp.add_url_rule('/cour_save', view_func=course_save, methods=['POST'])
    bp.add_url_rule('/cour_find', view_func=course_find, methods=['POST'])
    bp.add_url_rule('/cour_add', view_func=bulk_add_courses, methods=['POST'])
    bp.add_url_rule('/course_lookup/<string:query_str>', view_func=course_lookup, methods=['GET'])
    bp.add_url_rule('/save_slot', view_func=save_course_slot_timings, methods=['POST'])


@C.rbac
async def course_view(my_id):
    try:
        cour = DB.Course.get_by_id(my_id)
        if cour:
            obj = apiVC.model_to_dict(cour, exclude=[DB.Course.author.password_hashed])
            return apiVC.ok_json(obj)
        else:
            return apiVC.error_json(f"Record not found for the course# {my_id}")
    except Exception as ex:
        msg = "Error when fetching course details."
        logging.exception(msg)
        return apiVC.error_json(msg)


@C.rbac(roles=["ACA", "FAC", "DEA", "HOD", "RES"])
async def course_save():
    try:
        fd = await request.get_json(force=True)

        logging.debug("Saving course details: {}".format(fd))
        crs_id = int(fd.get("id") or 0)
        crs = DB.Course()

        if crs_id > 0:
            # Edit case
            if fd["author"]["id"] != apiVC.logged_in_user().id and \
                    not apiVC.is_user_in_role(["HOD", "ACA", "DEA", "RES"]):
                return apiVC.error_json("Cannot save course authored by another faculty!")
        else:
            # Assign the currently logged in user as the author
            if "author" not in fd:
                fd["author"] = {}
            fd["author"]["id"] = apiVC.logged_in_user().id

        if crs_id:
            crs = DB.Course.get_by_id(crs_id)
            old_status = crs.status
            if not is_course_status_valid_for_current_user(old_status):
                return apiVC.error_json("This course is already in "
                    f"{DB.Course.get_status_label(old_status)} state. "
                    "Please contact the academic section to edit it.")

            # Research section user can edit only PG/PhD courses
            if apiVC.is_user_in_role("RES") and not apiVC.course_code_for_pg(crs.code):
                return apiVC.error_json("You can edit only PG/PhD courses!")

            C.update_model_skip_unknown(crs, fd)

            if apiVC.update_entity(DB.Course, crs) != 1:  # if rc != 1:
                return apiVC.error_json("Could not update. Please try again.")
            logging.debug("Updated course details: {}".format(crs))
            send_course_updated_email(crs_id, old_status)
        else:
            C.update_model_skip_unknown(crs, fd)
            apiVC.save_entity(crs)
            logging.debug("Inserted course details: {}".format(crs))

        return apiVC.ok_json(apiVC.model_to_dict(crs, exclude=[DB.Course.author.password_hashed]))

    except Exception as ex:
        msg = "Error when saving course details."
        logging.exception(msg)
        return apiVC.error_json(f"{msg}: {ex}")


@C.rbac
async def course_find():
    try:
        fd = await request.get_json(force=True)
        status, code = fd.get("status"), fd.get("code")
        ltp, title = fd.get("ltp"), fd.get("title")
        author_id, dept = fd.get("author"), fd.get("dept")
        if type(status) == str:
            status = [status]
        elif status is None:
            status = []
        pg_no = int(fd.get('pg_no', 1))
        query = DB.Course.select(DB.Course.id, DB.Course.status,
                              DB.Course.code, DB.Course.title
                              , DB.Course.ltp).join(DB.User).join(DB.Person)
        if len(status) > 0:
            query = query.where(DB.Course.status << status)
        if code:
            query = query.where(DB.Course.code.contains(code))
        if ltp:
            query = query.where(DB.Course.ltp.contains(ltp))
        if title:
            query = query.where(DB.Course.title.contains(title))
        if author_id:
            query = query.where(DB.Course.author_id == author_id)
        if dept:
            query = query.where(DB.Person.dept_name == dept)

        courses = query.order_by(-DB.Course.id).paginate(pg_no, apiVC.page_size())
        serialized = [apiVC.model_to_dict(r, exclude=[DB.Course.author]) for r in courses]

        has_next = len(courses) >= apiVC.page_size()
        res = {"courses": serialized, "pg_no": pg_no, "pg_size": apiVC.page_size(),
               "has_next": has_next}
        return apiVC.ok_json(res)

    except Exception as ex:
        msg = "Error when finding courses."
        logging.exception(msg)
        return apiVC.error_json(msg)


@C.rbac
async def course_lookup(query_str):
    try:
        query = DB.Course.select(DB.Course.id, DB.Course.code, 
            DB.Course.title, DB.Course.ltp).where(
            ((DB.Course.title.contains(query_str)) | 
            (DB.Course.code.contains(query_str) )
            ) & (DB.Course.status=="APP")
        )

        courses = query.order_by(-DB.Course.id).limit(15)
        serialized = [{"id": r.id, "title": r.title, "code": r.code, 
                        "ltp": r.ltp} for r in courses]
        return apiVC.ok_json(serialized)

    except Exception as ex:
        msg = "Error in course lookup."
        logging.exception(msg)
        return apiVC.error_json(msg)


def __do_courses_exist(file_path):
    codes = []
    with open(file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            codes.append(row["code"])

    qry = DB.Course.select().where(DB.Course.code << codes)
    return [x.code for x in qry]


@C.rbac(roles=["ACA", "DEA"])
async def bulk_add_courses():
    try:
        courses_file = (await request.files)['courses_file']
        if courses_file.filename == '':
            return apiVC.error_json("Please supply a .csv containing the "
            "course information!")
        local_file_nm = C.get_rand_str(4) + "_" + \
            secure_filename(courses_file.filename)
        file_path = os.path.join(apiVC.get_upload_folder_for_user(), 
                                local_file_nm)
        courses_file.save(file_path)

        existing = __do_courses_exist(file_path)
        if existing:
            return apiVC.error_json("There are courses that already exist \
                in the system. Please remove them from the .csv file \
                that you are uploading.\
                Following courses already exists: " + str(existing))

        with open(file_path, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            with DB.db.atomic() as txn:
                for row in reader:
                    l, t, p, *x = row["ltp"].split("-")
                    l, t, p = C.parse_number(l), C.parse_number(t), \
                                C.parse_number(p)
                    s = round(2 * l - t + 0.5 * p, 2)
                    c = round(l + 0.5 * p, 2)
                    ltpsc = f"{l}-{t}-{p}-{s}-{c}"
                    cou = DB.Course(code=row["code"], title=row["title"],
                                 ltp=ltpsc, status="APP", 
                                 author=apiVC.logged_in_user())
                    cou.save()
                txn.commit()

        os.remove(file_path)  # Cleanup
        return apiVC.ok_json("Created new courses successfully!")

    except Exception as ex:
        msg = "Error when handling bulk course creation."
        logging.exception(msg)
        return apiVC.error_json(msg)


@C.rbac(roles="ACA,DEA")
async def save_course_slot_timings():
    try:
        fd = await request.get_json(force=True)
        cst = DB.CourseSlotTiming()
        C.update_model_skip_unknown(cst, fd)
        if cst.id and cst.id > 0:
            apiVC.update_entity(DB.CourseSlotTiming, cst)
        else:
            apiVC.save_entity(cst)
        res = apiVC.model_to_dict(cst)
        return apiVC.ok_json(res)
    except IntegrityError as iex:
        logging.error(iex)
        return apiVC.error_json("Cannot save duplicate record. "
        "Please make sure the slot data is unique.")
    except Exception as ex:
        logging.error(ex)
        return apiVC.error_json("Error occurred when saving "
        "course slot timings.")


