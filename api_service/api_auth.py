"""View functions for managing the users and authentication tasks.

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__version__ = "0.1"
__status__ = "Development"
"""

import asyncio
import base64
import csv
import hmac
import logging
import os
import create_email as CM
import models as DB
import common as C
import api_common as apiVC
import settings as ST
import face_api_proxy as fapi
import policy as P

from datetime import datetime as DT, timedelta
from quart import Blueprint, request, current_app as APP
from quart.helpers import send_file
from google.auth.transport import requests
from google.oauth2 import id_token
from werkzeug.utils import secure_filename

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
    bp.add_url_rule('/get_image/<string:file_name>', view_func=get_image, methods=['GET'])
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


# A reset key is valid for PRK_TTL. After the lockout_limit setting's number
# of wrong keys the outstanding keys are discarded and resets for that login
# are refused for PRK_TTL. At most that many keys are issued per login within
# PRK_TTL.
PRK_TTL = timedelta(minutes=30)
PRK_SENT_MSG = ("If the login id and email match an account, a password "
                "reset key has been emailed to it.")
PRK_INVALID_MSG = "Invalid or expired reset key."

# Verified against when the login id is unknown, so that the response takes
# about as long as for a known login id.
_DUMMY_HASH = C.hash_password(C.get_rand_str(16))


def __prk_locked_out(login_id):
    count, since = APP.prk_failures.get(login_id, (0, None))
    if count < ST.get("lockout_limit"):
        return False
    if DT.now() - since < PRK_TTL:
        return True
    APP.prk_failures.pop(login_id, None)
    return False


def __record_wrong_prk(login_id):
    count, _ = APP.prk_failures.get(login_id, (0, None))
    APP.prk_failures[login_id] = (count + 1, DT.now())
    if count + 1 >= ST.get("lockout_limit"):
        logging.warning(f"Too many wrong reset keys for {login_id}; "
                        "password reset locked out.")
        __clear_prk_for_user(login_id)


async def gen_prk():
    try:
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
        elif u.is_locked or __prk_locked_out(login_id):
            logging.warning(f"Password reset key not issued to {login_id}: "
                            "account or password reset locked.")
        else:
            recent = DB.PasswordResetKey.select().where(
                (DB.PasswordResetKey.login_id == login_id) &
                (DB.PasswordResetKey.ins_ts > DT.now() - PRK_TTL)).count()
            if recent >= ST.get("lockout_limit"):
                logging.warning(f"Too many password reset key requests for {login_id}.")
            else:
                prk_str = C.get_rand_str(size=8)
                obj = DB.PasswordResetKey(login_id=login_id, prk=prk_str)
                apiVC.save_entity(obj)
                CM.send_password_reset_code(email, prk_str)
        return apiVC.ok_json(PRK_SENT_MSG)

    except Exception as ex:
        msg = "Error when generating password reset key."
        logging.exception(msg)
        return apiVC.error_json(msg)


async def reset_password():
    try:
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
            return apiVC.error_json(PRK_INVALID_MSG)
        if u.is_locked or __prk_locked_out(login_id):
            logging.warning(f"Password reset refused for locked user {login_id}.")
            return apiVC.error_json(PRK_INVALID_MSG)

        res = DB.PasswordResetKey.select().where(
            DB.PasswordResetKey.login_id == login_id).order_by(
            -DB.PasswordResetKey.id).limit(1)
        prk = res[0] if res else None
        if (prk and key_code and DT.now() - prk.ins_ts < PRK_TTL
                and hmac.compare_digest(prk.prk.encode(), str(key_code).encode())):
            u.password_hashed = C.hash_password(new_password)
            apiVC.save_entity(u)
            __clear_prk_for_user(login_id)
            APP.prk_failures.pop(login_id, None)
            CM.send_password_changed_alert(u.email, u.first_name)
            return apiVC.ok_json("Your password has been changed!")

        __record_wrong_prk(login_id)
        return apiVC.error_json(PRK_INVALID_MSG)

    except Exception as ex:
        msg = "Error when resetting password."
        logging.exception(msg)
        return apiVC.error_json(msg)


def __clear_prk_for_user(login_id):
    DB.PasswordResetKey.delete().where(
        DB.PasswordResetKey.login_id == login_id).execute()


@P.require("users.view")
async def get_my_photo():
    try:
        cu = apiVC.logged_in_user()
        if cu.known_faces.exists():
            photo = cu.known_faces.order_by(-DB.KnownFace.ins_ts)[0].photo
            return apiVC.ok_json(photo)
        else:
            return apiVC.error_json("Photo not found!")
    except Exception as ex:
        msg = "Error when authenticating."
        logging.exception(msg)
        return apiVC.error_json(msg)


async def login():
    try:
        lf = await request.get_json(force=True)
        login_id = lf.get("login_id")
        plain_pass = lf.get("password")
        logging.debug("Received login request for user {}".format(login_id))

        u = DB.User.get_or_none(DB.User.login_id == login_id)
        valid = False
        if u:
            logging.info("Got user: {0}, {1}".format(u.login_id, u.first_name))
            valid = C.verify_password(plain_pass, u.password_hashed)
            if valid and u.is_locked:
                return apiVC.error_json("DB.User is locked! Please contact admin.")
            if valid and C.password_needs_rehash(u.password_hashed):
                DB.User.update(password_hashed=C.hash_password(plain_pass)).where(
                    DB.User.id == u.id).execute()
        else:
            C.verify_password(str(plain_pass), _DUMMY_HASH)

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
            actor = P.current_actor()
            nav = apiVC.init_navbar_items(actor, u.person.degree)
            APP.active_users[C.this_user_name_login_id()] = DT.now()
            return apiVC.ok_json({"user": {**user_obj, "perms": sorted(actor.perms)},
                                  "nav": nav})
    except Exception as ex:
        msg = "Error when authenticating."
        logging.exception(msg)
        return apiVC.error_json(msg)


@P.require("users.find")
async def user_find():
    try:
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

        users = query.order_by(-DB.User.id).paginate(pg_no, ST.get("page_size"))
        serialized = []
        for r in users:
            uobj = apiVC.model_to_dict(r, exclude=[DB.User.password_hashed])
            uobj["photo"] = r.known_faces[0].photo if r.known_faces else ""
            serialized.append(uobj)

        has_next = len(users) >= ST.get("page_size")
        res = {"users": serialized, "pg_no": pg_no, "pg_size": ST.get("page_size"),
               "has_next": has_next}
        return apiVC.ok_json(res)

    except Exception as ex:
        msg = "Error when finding users."
        logging.exception(msg)
        return apiVC.error_json(msg)


@P.require("users.view")
async def user_view(my_id):
    try:
        actor = P.current_actor()
        if not actor.allowed("users.view", own=lambda: my_id == actor.id):
            return apiVC.error_json("You cannot access other users' information!")

        res = DB.User.select(DB.User, DB.Person).join(DB.Person, DB.ORM.JOIN.LEFT_OUTER).where(DB.User.id == my_id)
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
    except Exception as ex:
        msg = "Error when fetching User details."
        logging.exception(msg)
        return apiVC.error_json(msg)


# Request fields that user_save copies onto the user and person records.
# Users without users.edit:any may edit only their own names.
USER_ADMIN_FIELDS = ["login_id", "email", "first_name", "last_name", "role",
                     "is_locked", "txn_no"]
USER_SELF_FIELDS = ["first_name", "last_name", "txn_no"]
PERSON_EXCLUDED_FIELDS = ["id", "is_deleted", "ins_ts", "upd_ts", "txn_login_id"]


@P.require("users.edit")
async def user_save():
    try:
        fd = await request.get_json(force=True)

        logging.info("Saving user details: {}".format(
            {k: v for k, v in fd.items() if k != "photo_new"}))
        cid = int(fd.get("id") or 0)
        actor = P.current_actor()
        is_admin = actor.has("users.edit:any")
        if (not is_admin) and cid != actor.id:
            return apiVC.error_json("Insufficient privileges to perform the operation!")
        if not is_admin and "photo_new" in fd:
            return apiVC.error_json("Only the academic section can change the photo!")

        user_fd = {k: v for k, v in fd.items()
                   if k in (USER_ADMIN_FIELDS if is_admin else USER_SELF_FIELDS)}
        has_person = is_admin and "person" in fd
        person_fd = {k: v for k, v in (fd.get("person") or {}).items()
                     if k not in PERSON_EXCLUDED_FIELDS} if has_person else {}
        if "role" in user_fd and not DB.Role.get_or_none(DB.Role.code == user_fd["role"]):
            return apiVC.error_json("Invalid role!")

        user_mod = DB.User.get_by_id(cid) if cid else DB.User()
        # Only a permissions admin may edit one, or grant a role that makes one.
        if (not actor.has(P.ADMIN_PERM)
                and any(P.ADMIN_PERM in P.perms_of(r) for r in (user_mod.role, user_fd.get("role")) if r)):
            return apiVC.error_json("Only a permissions admin can edit a permissions admin or grant that role!")
        if (cid == actor.id and actor.has(P.ADMIN_PERM) and "role" in user_fd
                and P.ADMIN_PERM not in P.perms_of(user_fd["role"])):
            return apiVC.error_json(f"You cannot change your own role to one without {P.ADMIN_PERM}!")

        # Call the face service before opening the transaction, and off the
        # event loop.
        if "photo_new" in fd:
            img_data_b64 = fd["photo_new"]
            if not img_data_b64.startswith(apiVC.B64_HDR):
                raise C.AcadStackException("Expected JPEG images only!")
            face_enc = await asyncio.to_thread(__encode_face_to_json, img_data_b64)

        with DB.db.atomic() as txn:
            if cid:
                if user_mod.is_locked and not fd.get("is_locked"):
                    __clear_prk_for_user(user_mod.login_id)
                    APP.prk_failures.pop(user_mod.login_id, None)

                C.update_model_skip_unknown(user_mod, user_fd)
                if has_person and user_mod.person_id:
                    per = user_mod.person
                    C.update_model_skip_unknown(per, person_fd)
                    if 1 != apiVC.update_entity(DB.Person, per):
                        return apiVC.error_json("Could not update. Please try again.")
                elif has_person:
                    per = DB.Person()
                    C.update_model_skip_unknown(per, person_fd)
                    apiVC.save_entity(per)
                    user_mod.person = per
                if apiVC.update_entity(DB.User, user_mod) != 1:
                    return apiVC.error_json("Could not update. Please try again.")
                logging.debug("Updated DB.User details: {}".format(user_mod))
            else:
                per = DB.Person()
                C.update_model_skip_unknown(per, person_fd)
                apiVC.save_entity(per)
                logging.debug("Inserted Person: {}".format(per))
                user_mod.person = per
                user_mod.password_hashed = C.hash_password(C.get_rand_str())
                C.update_model_skip_unknown(user_mod, user_fd)
                apiVC.save_entity(user_mod)
                logging.debug("Inserted DB.User: {}".format(user_mod))

            # Save the photos
            if "photo_new" in fd:
                kf_mod = DB.KnownFace()
                img_data = base64.b64decode(img_data_b64[len(apiVC.B64_HDR):])
                # Save the image to disk
                kf_mod.photo = apiVC.save_file_to_uploads_folder("photos", img_data)
                kf_mod.user = user_mod
                kf_mod.face_enc = face_enc
                apiVC.save_entity(kf_mod)

                # Delete the old photo, if it belongs to this user
                if "known_faces" in fd and fd["known_faces"]:
                    kfid = fd["known_faces"][0]["id"]
                    DB.KnownFace.delete().where((DB.KnownFace.id == kfid) &
                        (DB.KnownFace.user == user_mod.id)).execute()

            txn.commit()
        if not cid:
            CM.send_user_creation_email(fd.get("email"), fd.get("login_id"))
        return await user_view(my_id=user_mod.id)

    except Exception as ex:
        msg = "Error when saving DB.User details."
        logging.exception(msg)
        return apiVC.error_json(str(ex) if isinstance(ex, C.AcadStackException) else msg)


@P.require("users.lookup")
async def instructor_lookup(query_str):
    try:
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

    except Exception as ex:
        msg = "Error when looking up instructors."
        logging.exception(msg)
        return apiVC.error_json(msg)


def __format_row(row):
    return "{0}, {1}, {2}".format(row["org_id"], row["login_id"], row["email"])


@P.require("users.bulk_add")
async def bulk_add_users():
    try:
        users_file = (await request.files)['users_file']
        if users_file.filename == '':
            return apiVC.error_json("No file supplied!")
        local_file_nm = C.get_rand_str(4) + "_" + secure_filename(users_file.filename)
        file_path = os.path.join(apiVC.get_upload_folder_for_user(), local_file_nm)
        await users_file.save(file_path)
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
                            u.password_hashed = C.hash_password(C.get_rand_str(8))
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
                        logging.error(f"Skipping to next. {ierr}")
                        dups.append(__format_row(row))

                txn.commit()

        os.remove(file_path)  # Cleanup
        return apiVC.ok_json("Created {0} new users. Updated {1} users: {2}. Failed {3} records due to integrity check: {4}"
                       .format(created, len(updated), str(updated), len(dups), str(dups)))

    except Exception as ex:
        msg = "Error when handling bulk user creation."
        logging.exception(msg)
        return apiVC.error_json(msg)


@P.require("users.view")
async def get_image(file_name):
    try:
        actor = P.current_actor()
        if not actor.allowed("users.view", own=lambda: DB.KnownFace.select().where(
                (DB.KnownFace.photo == file_name) &
                (DB.KnownFace.user == actor.id)).exists()):
            return apiVC.error_json("Access to the image not allowed!")
        fp = os.path.join(apiVC.get_upload_folder(),
                          "photos", secure_filename(file_name))
        return await send_file(fp)
    except Exception as ex:
        msg = "Error when loading image."
        logging.exception(msg)
        return apiVC.error_json(msg)


@P.require("users.lookup")
async def student_lookup(query_str):
    try:
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

    except Exception as ex:
        msg = "Error when looking up students."
        logging.exception(msg)
        return apiVC.error_json(msg)


def oauth_verify(token):
    """
    Validate the OAuth token with Google OAuth
    """
    try:
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

    except Exception as ex:
        # Invalid token
        msg = str(ex) if isinstance(ex, C.AcadStackException) else "Error when authrnticating."
        logging.exception(msg)
        return apiVC.error_json(msg)


@P.require("users.delete")
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


@P.require("students.find")
async def find_students():
    try:
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

    except Exception as ex:
        msg = "Error when finding students."
        logging.exception(msg)
        return apiVC.error_json(msg)


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


@P.require("advisors.view")
async def find_advisor():
    try:
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

    except Exception as ex:
        msg = "Error when finding advisor."
        logging.exception(msg)
        return apiVC.error_json(str(ex) if isinstance(ex, C.AcadStackException) else msg)


@P.require("advisors.assign")
async def assign_advisor():
    try:
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

    except Exception as ex:
        msg = "Error when assigning advisor."
        logging.exception(msg)
        return apiVC.error_json(str(ex) if isinstance(ex, C.AcadStackException) else msg)

def get_user_by_org_id(org_id):
    stu = DB.User.select().join(DB.Person, on=(DB.Person.id==DB.User.person)
            ).where(DB.Person.org_id == org_id)
    if stu.exists():
        return stu[0]
