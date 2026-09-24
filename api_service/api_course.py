import csv
import logging
import os
from quart import Blueprint, request
from werkzeug.utils import secure_filename
from peewee import IntegrityError
import api_common as apiVC
import models as DB
import common as C
from common import AcadStackException
from domain import course as CRS

def init_routes(bp: Blueprint):
    bp.add_url_rule('/cour/<int:my_id>', view_func=course_view, methods=['GET'])
    bp.add_url_rule('/cour_save', view_func=course_save, methods=['POST'])
    bp.add_url_rule('/cour_find', view_func=course_find, methods=['POST'])
    bp.add_url_rule('/cour_add', view_func=bulk_add_courses, methods=['POST'])
    bp.add_url_rule('/course_lookup/<string:query_str>', view_func=course_lookup, methods=['GET'])
    bp.add_url_rule('/save_slot', view_func=save_course_slot_timings, methods=['POST'])


@C.rbac
async def course_view(my_id):
    cour = DB.Course.get_by_id(my_id)
    if cour:
        obj = apiVC.model_to_dict(cour, exclude=[DB.Course.author.password_hashed])
        return apiVC.ok_json(obj)
    else:
        return apiVC.error_json(f"Record not found for the course# {my_id}")


@C.rbac(permissions=["course.save"])
async def course_save():
    fd = await request.get_json(force=True)
    logging.debug("Saving course details: {}".format(fd))
    crs = CRS.save_course(apiVC.current_actor(), fd,
                          C.update_model_skip_unknown)
    return apiVC.ok_json(apiVC.model_to_dict(crs, exclude=[DB.Course.author.password_hashed]))


@C.rbac
async def course_find():
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


@C.rbac
async def course_lookup(query_str):
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


def __do_courses_exist(file_path):
    codes = []
    with open(file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            codes.append(row["code"])

    qry = DB.Course.select().where(DB.Course.code << codes)
    return [x.code for x in qry]


@C.rbac(permissions=["course.bulk_create"])
async def bulk_add_courses():
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
                computed = C.compute_course_ltp(row["ltp"])
                if not computed:
                    raise AcadStackException(
                        f"Course {row['code']}: could not parse L-T-P "
                        f"from ltp {row['ltp']!r}.")
                ltpsc, s, c = computed
                cou = DB.Course(code=row["code"], title=row["title"],
                             ltp=ltpsc, s_hours=s, credits=c, status="APP",
                             author=apiVC.logged_in_user())
                cou.save()
            txn.commit()

    os.remove(file_path)  # Cleanup
    return apiVC.ok_json("Created new courses successfully!")


@C.rbac(permissions=["course.manage_slot_timings"])
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


