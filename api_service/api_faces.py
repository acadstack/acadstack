"""View functions for managing the face recognition tasks.

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__version__ = "0.1"
__status__ = "Development"
"""

import logging
import os
from zipfile import ZipFile

from quart import request, send_file, current_app as APP
from werkzeug.utils import secure_filename

import api_common as apiVC
import models as DB
import common as C
import face_api_proxy as fapi
from validation_checks import is_current_user_in_role_and_id

def process_photos_zip(zip_file):
    recs = 0
    try:
        with ZipFile(zip_file) as myzip:
            zitems = [x for x in myzip.namelist()
                      if x.lower().endswith(".jpg") and "MACOSX" not in x]
            logging.info("ZIP file {0} contains {1} items.".format(
                zip_file, len(zitems)))
            for zn in zitems:
                try:
                    logging.debug("Extracting JPG from ZIP entry: " + str(zn))
                    with myzip.open(zn) as zf:
                        logging.debug("Processing ZIP entry: {}".format(zn))
                        photo = zf.read()
                        if not photo:
                            logging.warning(
                                "Photo not found in ZIP entry: {}".format(zn))
                            continue
                        # [LoginId].jpg
                        name_w_ext = zn.split("/")[-1]
                        name = name_w_ext[:name_w_ext.rindex(".")]
                        login_ = str(name)
                        logging.debug("Login ID in file name: {}".format(login_))
                        uq = DB.User.select().where(DB.User.login_id == login_)
                        if not uq.exists():
                            logging.error("User {} not found. Skipping photo.".format(login_))
                            continue

                        user_id = uq[0].id
                        __encode_and_save_face(photo, user_id)
                        recs += 1
                except Exception as ex:
                    logging.exception("Error when processing photo: {}.".format(zn))

    except Exception as ex:
        logging.exception("Error when processing ZIP file.")
    logging.info("Added {0} face photos.".format(recs))
    return recs


def __encode_and_save_face(photo_buff, user_id):
    kfq = DB.KnownFace.select().where(DB.KnownFace.user == user_id)
    kf = kfq[0] if kfq.exists() else DB.KnownFace()
    kf.user = user_id
    fenc = fapi.get_face_encoding(photo_buff)
    kf.face_enc = apiVC.np_to_json(fenc)
                        # Save the image to disk
    kf.photo = apiVC.save_file_to_uploads_folder("photos", photo_buff)
    if kfq.exists():
        apiVC.update_entity(DB.KnownFace, kf)
    else:
        apiVC.save_entity(kf)


@C.rbac(permissions=["user.bulk_upload_faces"])
async def kface_bulk_add():
    try:
        zipf = (await request.files)['zip_file']
        if zipf.filename == '':
            return apiVC.error_json("No file supplied!")
        filename = secure_filename(zipf.filename)
        file_path = os.path.join(apiVC.get_upload_folder_for_user(), filename)
        zipf.save(file_path)
        APP.add_background_task(process_photos_zip, file_path)
        return apiVC.ok_json("Submitted the photos for processing.")
    except Exception as ex:
        msg = "Error when handling ZIP file."
        logging.exception(msg)
        return apiVC.error_json(msg)


@C.rbac()
async def kface_add():
    try:
        ph_file = (await request.files)['photo_file']
        if ph_file.filename == '':
            return apiVC.error_json("No file supplied!")
        photo = ph_file.read()
        cu = apiVC.logged_in_user()
        __encode_and_save_face(photo, cu.id)
        return apiVC.ok_json("Photos processed.")
    except Exception as ex:
        msg = "Error when processing face photo."
        logging.exception(msg)
        return apiVC.error_json(msg)


@C.rbac
async def get_class_photo(file_name, user_id):
    try:
        is_current_user_in_role_and_id("STU", "user_id", user_id,
            "Cannot access other's data! Your attempt has been reported.")
        qry = DB.KnownFace.select().where(DB.KnownFace.user == user_id)
        gp = os.path.join(apiVC.get_upload_folder("photos"),
                                secure_filename(file_name))
        for kf in qry:
            fp = os.path.join(apiVC.get_upload_folder("photos"),
                                secure_filename(kf.photo))
            marked = fapi.mark_person_in_photo(fp, gp)
            if not marked:
                continue
            return await send_file(marked,
                     attachment_filename='marked_pic.jpg',
                     mimetype='image/jpg')
        
        img = fapi.write_text_on_image(gp, "User not found in photo.", (10, 50))
        return await send_file(img,
                     attachment_filename='marked_pic.jpg',
                     mimetype='image/jpg')
        # return "Person not found in photo."
    except C.AcadStackException as ae:
        logging.exception(ae)
        return apiVC.error_json(str(ae))
    except Exception as ex:
        msg = "Error when marking the person in photo."
        logging.exception(msg)
        return apiVC.error_json(msg)
