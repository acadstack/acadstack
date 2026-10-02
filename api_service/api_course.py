import csv
import logging
import os
import re
from quart import Blueprint, request
from werkzeug.utils import secure_filename
from peewee import IntegrityError
from create_email import send_course_updated_email
from validation_checks import is_course_status_valid_for_current_user
import api_common as apiVC
import settings as ST
import models as DB
import common as C
import policy as P

def init_routes(bp: Blueprint):
    bp.add_url_rule('/cour/<int:my_id>', view_func=course_view, methods=['GET'])
    bp.add_url_rule('/cour_save', view_func=course_save, methods=['POST'])
    bp.add_url_rule('/cour_find', view_func=course_find, methods=['POST'])
    bp.add_url_rule('/cour_add', view_func=bulk_add_courses, methods=['POST'])
    bp.add_url_rule('/course_lookup/<string:query_str>', view_func=course_lookup, methods=['GET'])
    bp.add_url_rule('/save_slot', view_func=save_course_slot_timings, methods=['POST'])


@P.require("courses.view")
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


def _course_levels():
    return [cl["id"] for cl in C.static_data_json()["CourseLevels"]]


def _ltpsc_valid(ltpsc):
    """The credits are given as L-T-P-S-C, five numbers such as 3-0-2-6-4."""
    parts = (ltpsc or "").split("-")
    return len(parts) == 5 and all(re.fullmatch(r"[0-9]+(\.[0-9]+)?", x) for x in parts)


@P.require("courses.edit")
async def course_save():
    try:
        fd = await request.get_json(force=True)

        logging.debug("Saving course details: {}".format(fd))
        crs_id = int(fd.get("id") or 0)
        crs = DB.Course()
        levels = _course_levels()
        if "level" in fd and fd["level"] not in levels:
            return apiVC.error_json(f"Course level must be one of {', '.join(levels)}.")
        if (crs_id <= 0 or "ltp" in fd) and not _ltpsc_valid(fd.get("ltp")):
            return apiVC.error_json("The credits must be in the L-T-P-S-C format, e.g. 3-0-2-6-4.")

        if crs_id > 0:
            # Edit case: the author stays as stored
            fd.pop("author", None)
            actor = P.current_actor()
            old = DB.Course.get_by_id(crs_id)
            if not actor.allowed("courses.edit", own=lambda: old.author_id == actor.id,
                                 pg=lambda: old.level in ("PG", "ALL")):
                if actor.has("courses.edit:pg"):
                    return apiVC.error_json("You can edit only PG or all-level courses!")
                return apiVC.error_json("Cannot save course authored by another faculty!")
        else:
            # Assign the currently logged in user as the author
            if "author" not in fd:
                fd["author"] = {}
            fd["author"]["id"] = apiVC.logged_in_user().id

        # The pg scope covers PG and all-level courses only, also as the level saved
        actor = P.current_actor()
        author_id = old.author_id if crs_id > 0 else actor.id
        level = fd.get("level") or (old.level if crs_id > 0 else DB.Course.level.default)
        if level not in ("PG", "ALL") and \
                not actor.allowed("courses.edit", own=lambda: author_id == actor.id):
            return apiVC.error_json("You can create or edit only PG or all-level courses!")

        if crs_id:
            crs = DB.Course.get_by_id(crs_id)
            old_status = crs.status
            if not is_course_status_valid_for_current_user(old_status):
                return apiVC.error_json("This course is already in "
                    f"{DB.Course.get_status_label(old_status)} state. "
                    "Please contact the academic section to edit it.")

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
        return apiVC.error_json(msg)


@P.require("courses.view")
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

        courses = query.order_by(-DB.Course.id).paginate(pg_no, ST.get("page_size"))
        serialized = [apiVC.model_to_dict(r, exclude=[DB.Course.author]) for r in courses]

        has_next = len(courses) >= ST.get("page_size")
        res = {"courses": serialized, "pg_no": pg_no, "pg_size": ST.get("page_size"),
               "has_next": has_next}
        return apiVC.ok_json(res)

    except Exception as ex:
        msg = "Error when finding courses."
        logging.exception(msg)
        return apiVC.error_json(msg)


@P.require("courses.view")
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


@P.require("courses.bulk_add")
async def bulk_add_courses():
    file_path = None
    try:
        courses_file = (await request.files)['courses_file']
        if courses_file.filename == '':
            return apiVC.error_json("Please supply a .csv containing the "
            "course information!")
        local_file_nm = C.get_rand_str(4) + "_" + \
            secure_filename(courses_file.filename)
        file_path = os.path.join(apiVC.get_upload_folder_for_user(), 
                                local_file_nm)
        await courses_file.save(file_path)

        existing = __do_courses_exist(file_path)
        if existing:
            return apiVC.error_json("There are courses that already exist \
                in the system. Please remove them from the .csv file \
                that you are uploading.\
                Following courses already exists: " + str(existing))

        with open(file_path, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            levels = _course_levels()
            with DB.db.atomic() as txn:
                for row in reader:
                    level = (row.get("level") or "").strip().upper()
                    if level not in levels:
                        raise C.AcadStackException(
                            f"Course {row.get('code')}: level must be one of "
                            f"{', '.join(levels)}.")
                    ltpsc = (row["ltp"] or "").strip()
                    if not _ltpsc_valid(ltpsc):
                        raise C.AcadStackException(
                            f"Course {row.get('code')}: ltp must be in the "
                            "L-T-P-S-C format, e.g. 3-0-2-6-4.")
                    cou = DB.Course(code=row["code"], title=row["title"],
                                 ltp=ltpsc, level=level, status="APP", 
                                 author=apiVC.logged_in_user())
                    cou.save()
                txn.commit()

        return apiVC.ok_json("Created new courses successfully!")

    except C.AcadStackException as ex:
        return apiVC.error_json(str(ex))
    except Exception as ex:
        msg = "Error when handling bulk course creation."
        logging.exception(msg)
        return apiVC.error_json(msg)
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)  # Cleanup


@P.require("slots.manage")
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


