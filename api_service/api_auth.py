"""View functions for managing the users and authentication tasks.

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__version__ = "0.1"
__status__ = "Development"
"""

import base64
import csv
import logging
import os
from pathlib import Path
import create_email as CM
import models as DB
import common as C
import api_common as apiVC
import face_api_proxy as fapi
import permissions as PERM
import settings_store as ST

from datetime import datetime as DT
from quart import Blueprint, request, current_app as APP
from quart.helpers import send_file
from google.auth.transport import requests
from google.oauth2 import id_token
from passlib.handlers.pbkdf2 import pbkdf2_sha256
from werkzeug.utils import secure_filename
from peewee import IntegrityError

def init_routes(bp:Blueprint):
    bp.add_url_rule('/oauth/<string:token>', view_func=oauth_verify, methods=['GET'])
    bp.add_url_rule('/login', view_func=login, methods=['POST'])
    bp.add_url_rule('/logout', view_func=apiVC.logout, methods=['GET', 'POST'])
    bp.add_url_rule('/current_user', view_func=apiVC.get_current_user_and_nav, methods=['GET'])
    bp.add_url_rule('/reset_password', view_func=reset_password, methods=['POST'])
    bp.add_url_rule('/gen_prk', view_func=gen_prk, methods=['POST'])
    bp.add_url_rule('/add_users', view_func=bulk_add_users, methods=['POST'])
    bp.add_url_rule('/user_find', view_func=user_find, methods=['POST'])
    bp.add_url_rule('/user/<int:my_id>', view_func=user_view, methods=['GET'])
    bp.add_url_rule('/user_save', view_func=user_save, methods=['POST'])
    bp.add_url_rule('/user_delete', view_func=user_delete, methods=['POST'])
    bp.add_url_rule('/instructor_lookup/<string:query_str>', view_func=instructor_lookup, methods=['GET'])
    bp.add_url_rule('/student_lookup/<string:query_str>', view_func=student_lookup, methods=['GET'])
    bp.add_url_rule('/students_find', view_func=find_students, methods=['POST'])
    bp.add_url_rule('/my_photo', view_func=get_my_photo, methods=['GET'])

    bp.add_url_rule('/get_student_docs/<int:stu_id>', view_func=get_student_docs, methods=['GET'])
    bp.add_url_rule('/upload_student_doc', view_func=upload_student_doc, methods=['POST'])
    bp.add_url_rule('/get_doc/<int:doc_id>', view_func=get_doc, methods=['GET'])
    bp.add_url_rule('/delete_doc/<int:doc_id>', view_func=delete_doc, methods=['GET'])
    bp.add_url_rule('/get_image/<string:file_name>', view_func=get_image, methods=['GET'])
    bp.add_url_rule('/get_fees_txn_file/<string:file_name>', view_func=get_fees_txn_image, methods=['GET'])
    bp.add_url_rule('/delete_fees_txn_data/<int:fee_id>', view_func=delete_student_reg_fees_data, methods=['GET'])
    bp.add_url_rule('/get_reg_fees_data/<int:stu_id>', view_func=get_student_reg_fees_data, methods=['GET'])
    bp.add_url_rule('/save_reg_fees_data', view_func=save_registration_fees_txn_info, methods=['POST'])
    bp.add_url_rule('/find_advisor', view_func=find_advisor, methods=['POST'])
    bp.add_url_rule('/assign_advisor', view_func=assign_advisor, methods=['POST'])


def __encode_face_to_json(photo_str):
    if photo_str.startswith(apiVC.B64_HDR):
        photo_b64 = photo_str[len(apiVC.B64_HDR):]
        face_enc = fapi.get_face_encoding_b64(photo_b64)
        return apiVC.np_to_json(face_enc)
    else:
        raise Exception(
            "Please supply a JPG format image. Mere renaming to .jpg won't work!")


async def gen_prk():
    lf = await request.get_json(force=True)
    login_id = lf.get("login_id")
    email = lf.get("email")
    logging.debug(
        "Received password reset key request for user {}".format(login_id))

    u = DB.User.get_or_none((DB.User.login_id == login_id)
                         & (DB.User.email == email))

    if not u:
        logging.warning(
            "Attempted to initiate password reset for non-existent user {}".format(login_id))
        return apiVC.error_json("Invalid user/email.")
    else:
        attempts = DB.PasswordResetKey.select().where(
            DB.PasswordResetKey.login_id == login_id).count()
        max_attempts = ST.setting("auth.password_reset_lockout_attempts")
        if attempts > max_attempts:
            u.is_locked = True
            apiVC.save_entity(u)
            return apiVC.error_json(
                f"Too many attempts (more than {max_attempts})! "
                f"Your account has been locked.")
        prk_str = C.get_rand_str(size=8)
        CM.send_password_reset_code(email, prk_str)
        obj = DB.PasswordResetKey(login_id=login_id, prk=prk_str)
        apiVC.save_entity(obj)
        logging.debug("PRK: {}".format(prk_str))
        return apiVC.ok_json("A password reset key code has been emailed to you.")


async def reset_password():
    lf = await request.get_json(force=True)
    login_id = lf.get("login_id")
    email = lf.get("email")
    new_password = lf.get("new_password")
    key_code = lf.get("key_code")

    logging.debug("Password reset key for user {}".format(login_id))

    u = DB.User.get_or_none((DB.User.login_id == login_id)
                         & (DB.User.email == email))

    if not u:
        logging.warning(
            "Attempted to reset password for non-existent user {}".format(login_id))
        return apiVC.error_json("Invalid user/email.")
    elif u.is_locked:
        return apiVC.error_json("DB.User is locked. Please contact the admin.")
    else:
        res = DB.PasswordResetKey.select(DB.PasswordResetKey.prk).where(
            DB.PasswordResetKey.login_id == login_id).order_by(
            -DB.PasswordResetKey.id).execute()

        if res and res[0].prk == key_code:
            u.password_hashed = pbkdf2_sha256.hash(new_password)
            apiVC.save_entity(u)
            DB.PasswordResetKey.delete().where(DB.PasswordResetKey.login_id == login_id).execute()
            CM.send_password_changed_alert(u.email, u.first_name)
            return apiVC.ok_json("Your password has been changed!")
        else:
            return apiVC.error_json("Invalid reset key!")


def __clear_prk_for_user(login_id):
    DB.PasswordResetKey.delete().where(
        DB.PasswordResetKey.login_id == login_id).execute()


@C.rbac
async def get_my_photo():
    cu = apiVC.logged_in_user()
    if cu.known_faces.exists():
        photo = cu.known_faces.order_by(-DB.KnownFace.ins_ts)[0].photo
        return apiVC.ok_json(photo)
    else:
        return apiVC.error_json("Photo not found!")


async def login():
    lf = await request.get_json(force=True)
    login_id = lf.get("login_id")
    plain_pass = lf.get("password")
    logging.debug("Received login request for user {}".format(login_id))

    u = DB.User.get_or_none(DB.User.login_id == login_id)
    valid = False
    if u and plain_pass:
        if u.is_locked:
            return apiVC.error_json("DB.User is locked! Please contact admin.")
        logging.info("Got user: {0}, {1}".format(u.login_id, u.first_name))
        valid = pbkdf2_sha256.verify(plain_pass, u.password_hashed)

    if not valid:
        return apiVC.error_json("Invalid user/password.")
    else:
        user_obj = {"id": u.id, "login_id": login_id,
                    "first_name": u.first_name, "last_name": u.last_name,
                    "category": u.person.category, "degree": u.person.degree,
                    "deg_type": u.person.deg_type, "role_name": u.get_role_label(),
                    "role": u.role, "dept": u.person.dept_name,
                    "deg_type_spec": u.person.deg_type_spec, 
                    "current_status": u.person.current_status}
        apiVC.session['user'] = user_obj
        nav = apiVC.init_navbar_items(u.role, u.person.degree)
        APP.active_users[C.this_user_name_login_id()] = DT.now()
        return apiVC.ok_json({"user": {**user_obj,
                                        "permissions": PERM.permissions_for_role(u.role)},
                               "nav": nav})


@C.rbac
async def user_find():
    if not apiVC.has_permission("user.search"):
        return apiVC.error_json("DB.User search not allowed!")

    fd = await request.get_json(force=True)
    dept_name, org_id, fname, lname, role = fd.get("dept_name"), \
                                            fd.get("org_id"), fd.get("first_name"), fd.get("last_name"), \
                                            fd.get("role")

    pg_no = int(fd.get('pg_no', 1))
    query = DB.User.select(DB.User.id, DB.Person.id, DB.Person.dept_name,
                           DB.Person.org_id, DB.User.role, 
                           DB.User.first_name, DB.User.last_name
                        ).join(DB.Person, DB.ORM.JOIN.LEFT_OUTER)
    # TODO: Fetch faces
    query = query.where(DB.User.is_deleted != True)
    if dept_name:
        query = query.where(DB.Person.dept_name.contains(dept_name))
    if org_id:
        query = query.where(DB.Person.org_id.contains(org_id))
    if role:
        query = query.where(DB.User.role == role)
    if fname:
        query = query.where(DB.User.first_name.contains(fname))
    if lname:
        query = query.where(DB.User.last_name.contains(lname))

    users = query.order_by(-DB.User.id).paginate(pg_no, apiVC.page_size())
    serialized = []
    for r in users:
        uobj = apiVC.model_to_dict(r, exclude=[DB.User.password_hashed])
        uobj["photo"] = r.known_faces[0].photo if r.known_faces else ""
        serialized.append(uobj)

    has_next = len(users) >= apiVC.page_size()
    res = {"users": serialized, "pg_no": pg_no, "pg_size": apiVC.page_size(),
           "has_next": has_next}
    return apiVC.ok_json(res)


@C.rbac
async def user_view(my_id):
    cu = apiVC.logged_in_user()
    if (not apiVC.has_permission("user.view_others")) and my_id != cu.id:
        return apiVC.error_json("You cannot access other users' information!")

    res = DB.User.select().join(DB.Person, DB.ORM.JOIN.LEFT_OUTER).where(DB.User.id == my_id)
    if res:
        user = res[0]
        res1 = DB.BatchAdvisors.select().where(DB.BatchAdvisors.user == my_id)
        obj = apiVC.model_to_dict(user, exclude=[DB.User.password_hashed])
        if res1:
            advisor = apiVC.model_to_dict(res1[0])
            obj["batch"] = advisor["year_of_entry"]
            obj["for_degree"] = advisor["for_degree"]
        obj["known_faces"] = [apiVC.model_to_dict(kf) for kf in user.known_faces]
        return apiVC.ok_json(obj)
    else:
        return apiVC.error_json("Record not found for ID {}".format(my_id))


@C.rbac
async def user_save():
    fd = await request.get_json(force=True)
    role = fd.get("role")

    logging.info("Saving user details: {}".format(fd))
    cid = int(fd.get("id") or 0)
    cu = apiVC.logged_in_user()
    if (not apiVC.has_permission("user.edit_any")) and cid != cu.id:
        return apiVC.error_json("Insufficient privileges to perform the operation!")
    user_mod = DB.User()
    with DB.db.atomic() as txn:
        if cid:
            user_mod = DB.User.get_by_id(cid)
            if user_mod.is_locked and not fd.get("is_locked"):
                __clear_prk_for_user(user_mod.login_id)

            C.update_model_skip_unknown(user_mod, fd)
            if user_mod.person:
                if user_mod.person.id:
                    if 1 != apiVC.update_entity(DB.Person, user_mod.person):
                        return apiVC.error_json("Could not update. Please try again.")
                else:
                    per = DB.Person()
                    C.update_model_skip_unknown(per, fd["person"])
                    apiVC.save_entity(per)
                    user_mod.person = per
            if apiVC.update_entity(DB.User, user_mod) != 1:
                return apiVC.error_json("Could not update. Please try again.")
            logging.debug("Updated DB.User details: {}".format(user_mod))
        else:
            per = DB.Person()
            C.update_model_skip_unknown(per, fd["person"])
            apiVC.save_entity(per)
            logging.debug("Inserted Person: {}".format(per))
            user_mod.person = per
            user_mod.password_hashed = pbkdf2_sha256.hash(C.get_rand_str())
            C.update_model_skip_unknown(user_mod, fd)
            CM.send_user_creation_email(fd.get("email"), fd.get("login_id"))
            apiVC.save_entity(user_mod)
            logging.debug("Inserted DB.User: {}".format(user_mod))

        # Save the photos
        if "photo_new" in fd:
            kf_mod = DB.KnownFace()
            img_data_b64 = fd["photo_new"]
            if not img_data_b64.startswith(apiVC.B64_HDR):
                raise C.AcadStackException("Expected JPEG images only!")
            img_data = base64.b64decode(img_data_b64[len(apiVC.B64_HDR):])
            # Save the image to disk
            kf_mod.photo = apiVC.save_file_to_uploads_folder("photos", img_data)
            kf_mod.user = user_mod
            kf_mod.face_enc = __encode_face_to_json(img_data_b64)
            apiVC.save_entity(kf_mod)

            # Delete the old photo
            if "known_faces" in fd and fd["known_faces"]:
                kfid = fd["known_faces"][0]["id"]
                DB.KnownFace.delete_by_id(kfid)

        txn.commit()
    return await user_view(my_id=user_mod.id)


@C.rbac
async def instructor_lookup(query_str):
    query = DB.User.select(DB.User.id, DB.Person.id, DB.Person.dept_name,
                           DB.Person.org_id, DB.User.role,
                           DB.User.first_name, DB.User.last_name
                        ).join(DB.Person, DB.ORM.JOIN.LEFT_OUTER)
    query = query.where(DB.User.is_deleted != True)
    query = query.where((DB.User.role == "FAC") & 
                        (DB.User.first_name.contains(query_str)
                         | DB.User.last_name.contains(query_str)))
    users = query.order_by(-DB.User.id).limit(15)
    serialized = [{"user_id": r.id, "first_name": r.first_name,
                   "last_name": r.last_name,
                   "dept_name": r.person.dept_name, 
                   "org_id": r.person.org_id} for r in users]

    return apiVC.ok_json(serialized)


def __format_row(row):
    return "{0}, {1}, {2}".format(row["org_id"], row["login_id"], row["email"])


@C.rbac(permissions=["user.bulk_create"])
async def bulk_add_users():
    if not apiVC.has_permission("user.bulk_create"):
        return apiVC.error_json("Operation not allowed due to insufficient privileges!")
    users_file = (await request.files)['users_file']
    if users_file.filename == '':
        return apiVC.error_json("No file supplied!")
    local_file_nm = C.get_rand_str(4) + "_" + secure_filename(users_file.filename)
    file_path = os.path.join(apiVC.get_upload_folder_for_user(), local_file_nm)
    users_file.save(file_path)
    updated = []
    dups = []
    created = 0
    with open(file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        with DB.db.atomic() as txn:
            for row in reader:
                try:
                    p = DB.Person()
                    u = DB.User()
                    creating = False
                    person_qry = DB.Person.select().where(
                        DB.Person.org_id == row["org_id"])
                    if person_qry.exists():
                        p = person_qry.execute()[0]
                        updated.append(__format_row(row))

                    user_qry = DB.User.select().where(
                        DB.User.login_id == row["login_id"])
                    if user_qry.exists():
                        u = user_qry.execute()[0]
                    else:
                        # Generate random password, user will reset it later
                        u.password_hashed = pbkdf2_sha256.hash(C.get_rand_str(8))
                        creating = True

                    p.org_id = row["org_id"]
                    p.dept_name = row["department"]
                    p.year_of_entry = row["year_of_entry"]
                    p.degree = row["degree"]
                    p.save()

                    u.login_id = row["login_id"]
                    u.first_name = row["first_name"]
                    u.last_name = row["last_name"]
                    u.email = row["email"]
                    u.role = row["role"]
                    u.person = p.id
                    u.save()
                    if creating:
                        created += 1
                except DB.IntegrityError as ierr:
                    logging.error("Skipping to next.", ierr)
                    dups.append(__format_row(row))

            txn.commit()

    os.remove(file_path)  # Cleanup
    return apiVC.ok_json("Created {0} new users. Updated {1} users: {2}. Failed {3} records due to integrity check: {4}"
                   .format(created, len(updated), str(updated), len(dups), str(dups)))


@C.rbac
async def upload_student_doc():
    if not apiVC.has_permission("user.upload_document"):
        return apiVC.error_json("Students not allowed to upload here!")
    form = await request.form
    stu_id = form['student_id']
    doc_desc = form['description']
    files = await request.files
    docf = files['doc_file']
    if docf.filename == '':
        return apiVC.error_json("No file supplied!")

    u = DB.User.get_by_id(int(stu_id))
    if not u:
        return apiVC.error_json("Student record not found!")

    filename = secure_filename(docf.filename)
    ud = DB.UserDoc(description=doc_desc, category="STU",
                 user=u, file_name=filename)
    ud.doc = apiVC.save_file_to_uploads_folder("docs", docf.stream.read())

    apiVC.save_entity(ud)
    return apiVC.ok_json(apiVC.model_to_dict(ud, exclude=[DB.UserDoc.doc, DB.UserDoc.user]))


def __is_doc_access_allowed(stu_id):
    return apiVC.has_permission("user.view_document") or \
           int(stu_id) == apiVC.logged_in_user().id


@C.rbac
async def get_student_docs(stu_id):
    if __is_doc_access_allowed(stu_id):
        u = DB.UserDoc.select().where(DB.UserDoc.user == int(stu_id))
        serialized = [apiVC.model_to_dict(r, exclude=[DB.UserDoc.user]) for r in u]
        return apiVC.ok_json(serialized)
    else:
        return apiVC.error_json("Student documents cannot be displayed.")


@C.rbac
async def delete_doc(doc_id):
    doc = DB.UserDoc.get_by_id(int(doc_id))
    if __is_doc_access_allowed(doc.user.id):
        DB.UserDoc.delete_by_id(doc.id)
        # Remove file from disk
        if doc.doc:
            fp = os.path.join(apiVC.get_upload_folder(), "docs", doc.doc)
            p = Path(fp)
            p.unlink(missing_ok=True)
        return apiVC.ok_json("Deleted")
    else:
        return apiVC.error_json("Access to documents not allowed!")


@C.rbac
async def get_doc(doc_id):
    u_doc = DB.UserDoc.get_or_none(DB.UserDoc.id == int(doc_id))
    if u_doc.category == 'FEETXN':
        docs_folder="FEETXN"
    else:
        docs_folder="docs"
    
    if u_doc and u_doc.doc:
        if __is_doc_access_allowed(u_doc.user.id):
            fp = os.path.join(apiVC.get_upload_folder(),
                              docs_folder, secure_filename(u_doc.doc))
            return await send_file(fp,
                             attachment_filename=u_doc.file_name,
                             as_attachment=True)
        else:
            return apiVC.error_json("Access to documents not allowed!")
    else:
        return apiVC.error_json("Document not found!")


@C.rbac
async def get_fees_txn_image(file_name):
    fp = os.path.join(apiVC.get_upload_folder(),
                      "FEETXN", secure_filename(file_name))
    return await send_file(fp, attachment_filename="{}.jpg".format(file_name))


@C.rbac
async def get_image(file_name):
    fp = os.path.join(apiVC.get_upload_folder(),
                      "photos", secure_filename(file_name))
    return await send_file(fp)


@C.rbac
async def student_lookup(query_str):
    if not apiVC.roll_number_valid(query_str):
        return apiVC.error_json("Invalid entry number pattern!")

    query = DB.User.select(DB.User.id, DB.Person.id, DB.Person.dept_name,
                           DB.Person.org_id, DB.User.role,
                           DB.User.first_name, DB.User.last_name
                        ).join(DB.Person, DB.ORM.JOIN.LEFT_OUTER)

    query = query.where(DB.User.is_deleted != True)
    query = query.where((DB.User.role == "STU") & 
                        (DB.Person.org_id.startswith(query_str) &
                         (DB.Person.current_status == 'REG')))
    users = query.order_by(DB.Person.org_id)
    serialized = [{"user_id": r.id,"first_name": r.first_name,
                   "last_name": r.last_name,
                   "dept_name": r.person.dept_name, "org_id": r.person.org_id} for r in users]

    return apiVC.ok_json(serialized)


def oauth_verify(token):
    """
    Validate the OAuth token with Google OAuth
    """
        # Specify the CLIENT_ID of the app that accesses the backend
    CLIENT_ID = C.app_config("oauth_client_id")
    oauth_domain = C.app_config("oauth_domain")
    idinfo = id_token.verify_oauth2_token(token,
                                          requests.Request(), CLIENT_ID)

    # If auth request is from a G Suite domain:
    if idinfo['hd'] != oauth_domain:
        raise C.AcadStackException(f'Login allowed with only {oauth_domain} accounts!')

    # ID token is valid. Get the user's Google Account ID from the decoded token.
    email_id = idinfo['email']
    u = DB.User.get_or_none(DB.User.email == email_id)
    if u:
        if u.is_locked:
            return apiVC.error_json("DB.User is locked! Please contact admin.")
    else:
        return apiVC.error_json(f"The user with email {email_id} not found!")

    logging.info(f"Got user: {u.login_id}, {u.first_name}")
    user_obj = {"id": u.id, "login_id": u.login_id,
                "first_name": u.first_name, "last_name": u.last_name,
                "role_name": u.get_role_label(), "role": u.role,
                "category": u.person.category,"degree": u.person.degree,
                "deg_type": u.person.deg_type,"dept": u.person.dept_name,
                "deg_type_spec": u.person.deg_type_spec, 
                "current_status": u.person.current_status,"is_oauth": True}
        
    C.session['user'] = user_obj
    return apiVC.ok_json("Loging successful.")


@C.rbac(permissions=["user.delete"])
async def user_delete():
    fd = await request.get_json(force=True)
    user_ids = fd.get("ids")
    if user_ids:
        q = (DB.User.update({DB.User.is_deleted: True})
             .where(DB.User.id.in_(user_ids)))
        rc = q.execute()
        return apiVC.ok_json("Deleted {0} users!".format(rc))
    else:
        return apiVC.error_json("No user specified! Nothing to delete.")


@C.rbac
async def save_registration_fees_txn_info():
    try:
        form = await request.form
        stu_id = int(form['student_id'])
        if (not apiVC.has_permission("fees.manage_others_txn")) and stu_id != apiVC.logged_in_user().id:
            logging.error(
                "DB.User {0} attempted to submit fees transaction data for user {1}.".format(apiVC.current_login_id(), stu_id))
            return apiVC.error_json("You are not allowed to submit data for others! This incident has been reported.")

        acadSession = form['acadSession']
        feesTxnAmt = form['feesTxnAmt']
        feesTxnNo = form['feesTxnNo']
        feesTxnDt = form['feesTxnDt']
        feesTxnBank = form['feesTxnBank']
        files = await request.files 
        docf = files['doc_file']

        if not (apiVC.academic_session_valid(acadSession)
                and feesTxnNo and feesTxnDt and feesTxnBank
                and docf.filename and feesTxnAmt):
            return apiVC.error_json("Please supply valid academic session and other inputs!")

        u = DB.User.get_by_id(int(stu_id))
        if not u:
            return apiVC.error_json("Student record not found!")

        filename = secure_filename(docf.filename)
        ud = DB.UserDoc(description="{0}/{1}/{2}/{3}".format(
            acadSession, feesTxnNo, feesTxnDt, feesTxnBank),
            category="FEETXN", user=u, file_name=filename)
        ud.doc = apiVC.save_file_to_uploads_folder(ud.category, docf.stream.read())

        fee_txn = DB.FeesTransaction()
        fee_txn.student = u
        fee_txn.acad_session = acadSession
        fee_txn.fees_txn_amt = feesTxnAmt
        fee_txn.fees_txn_no = feesTxnNo
        fee_txn.fees_txn_dt = feesTxnDt
        fee_txn.fees_txn_bank = feesTxnBank
        fee_txn.doc_file_name = ud.doc

        with DB.db.atomic() as txn:
            apiVC.save_entity(ud)
            apiVC.save_entity(fee_txn)

        return apiVC.ok_json(apiVC.model_to_dict(fee_txn,
                                     exclude=[DB.FeesTransaction.student]))
    except IntegrityError as ie:
        logging.exception(ie)
        return apiVC.error_json("An old record with same transaction information exists!")


@C.rbac
async def get_student_reg_fees_data(stu_id):
    if (not apiVC.has_permission("fees.manage_others_txn")) and stu_id != apiVC.logged_in_user().id:
        logging.error(
            "DB.User {0} attempted to fetch fees transaction data for user {1}.".format(apiVC.current_login_id(), stu_id))
        return apiVC.error_json("You are not allowed to access others' data! This incident has been reported.")

    qry = DB.FeesTransaction.select().where(
        (DB.FeesTransaction.student == stu_id) &
        (DB.FeesTransaction.is_deleted != True))
    data = [apiVC.model_to_dict(x,
                          exclude=[DB.FeesTransaction.student])
            for x in qry]
    return apiVC.ok_json(data)


@C.rbac
async def delete_student_reg_fees_data(fee_id):
    try:
        ftxn = DB.FeesTransaction.get_or_none(int(fee_id))
        if not ftxn:
            return apiVC.error_json("Invalid transaction details!")

        if (not apiVC.has_permission("fees.manage_others_txn")) and ftxn.student.id != apiVC.logged_in_user().id:
            logging.error("DB.User {0} attempted to delete fees transaction data for user {1}."
                          .format(apiVC.current_login_id(), ftxn.student.login_id))
            return apiVC.error_json("You are not allowed to delete others' data! "+
                                 "This incident has been reported.")

        ftxn.is_deleted = True
        rc = apiVC.update_entity(DB.FeesTransaction, ftxn)
        if rc == 1:
            return apiVC.ok_json("Fees record deleted!")
        else:
            return apiVC.error_json("Fees record could not be deleted! "+
                                 "Please try again, or contact the admin.")

    except IntegrityError as ie:
        logging.exception(ie)
        return apiVC.error_json("An old deleted record with same transaction "+
                             "details for a student exists!")


@C.rbac
async def find_students():
    if not apiVC.has_permission("user.search"):
        return apiVC.error_json("Operation not allowed!")

    fd = await request.get_json(force=True)
    fname, lname, email = fd.get("first_name"), \
        fd.get("last_name"),  fd.get("email")
    org_id, degree, year_of_entry, dept_name = fd.get("org_id"), \
        fd.get("degree"), fd.get("year_of_entry"), fd.get("dept_name")

    query = DB.User.select(DB.User.id, DB.Person.dept_name,
                           DB.Person.year_of_entry, DB.Person.dept_name, 
                           DB.Person.org_id, DB.Person.degree, DB.User.email,
                           DB.User.first_name, DB.User.last_name
                        ).join(DB.Person, DB.ORM.JOIN.LEFT_OUTER)
    query = query.where(DB.User.is_deleted != True)
    query = query.where(DB.User.role == "STU")
    if email:
        query = query.where(DB.User.email.contains(email))
    if org_id:
        query = query.where(DB.Person.org_id.contains(org_id))
    if fname:
        query = query.where(DB.User.first_name.contains(fname))
    if lname:
        query = query.where(DB.User.last_name.contains(lname))
    if degree:
        query = query.where(DB.Person.degree == degree)
    if year_of_entry:
        query = query.where(DB.Person.year_of_entry == year_of_entry)
    if dept_name:
        query = query.where(DB.Person.dept_name == dept_name)

    students = query.order_by(-DB.User.id)
    data = []
    for r in students:
        obj = {"id": r.id, "org_id": r.person.org_id,
                "first_name": r.first_name,
                "last_name": r.last_name,
                "degree": r.person.degree, 
                "dept_name": r.person.dept_name,
                "year_of_entry": r.person.year_of_entry,
                "dept_name": r.person.dept_name}
        data.append(obj)
    
    return apiVC.ok_json(data)


def __get_advisor(for_degree, fey, dept_name):
    qry = DB.BatchAdvisors.select().join(DB.User).join(DB.Person)
    qry = qry.where(DB.BatchAdvisors.for_degree == for_degree)
    qry = qry.where(DB.BatchAdvisors.year_of_entry == fey)
    qry = qry.where(DB.Person.dept_name == dept_name)
    qry = qry.where(DB.User.is_deleted != True)

    if len(qry) == 1:
        return qry[0]
    elif len(qry) > 1:
        raise C.AcadStackException("More than one advisors assigned for {0} {1} {2}".format(
            for_degree, dept_name, fey
        ))
    else:
        return None


@C.rbac
async def find_advisor():
    fd = await request.get_json(force=True)
    for_degree, fey, dept_name = fd.get("for_degree"), \
                            fd.get("for_entry_year"), \
                            fd.get("dept_name")
    obj = __get_advisor(for_degree, fey, dept_name)
    
    if obj:
        return apiVC.ok_json({"user_id": obj.user.id, 
                "first_name": obj.user.first_name,
                "last_name": obj.user.last_name,
                "dept_name": dept_name
                })
    else:
        msg = "No advisor found for {0} {1} {2}".format(
            for_degree, dept_name, fey)
        return apiVC.ok_json({"user_id": -1, "message": msg})


@C.rbac(permissions=["user.assign_advisor"])
async def assign_advisor():
    fd = await request.get_json(force=True)
    for_degree, fey, dept_name = fd.get("for_degree"), \
                                    fd.get("for_entry_year"), \
                                    fd.get("dept_name")
    user_id = fd.get("user_id")

    obj = __get_advisor(for_degree, fey, dept_name)
    if obj:
        obj.user = DB.User.get_by_id(user_id)
        apiVC.update_entity(DB.BatchAdvisors, obj)
    else:
        obj = DB.BatchAdvisors()
        obj.user = user_id
        obj.for_degree = for_degree
        obj.year_of_entry = fey
        apiVC.save_entity(obj)

    return apiVC.ok_json("Assigned {0} as batch advisor for {1} {2} {3}".format(
        obj.user.get_full_name(), fey, for_degree, dept_name))


def get_user_by_org_id(org_id):
    stu = DB.User.select().join(DB.Person, on=(DB.Person.id==DB.User.person)
            ).where(DB.Person.org_id == org_id)
    if stu.exists():
        return stu[0]
