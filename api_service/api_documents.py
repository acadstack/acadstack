"""View functions for managing students' uploaded documents.

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__version__ = "0.1"
__status__ = "Development"
"""

import logging
import os
from pathlib import Path
import models as DB
import api_common as apiVC
import policy as P

from quart import Blueprint, request
from quart.helpers import send_file
from werkzeug.utils import secure_filename


def init_routes(bp:Blueprint):
    bp.add_url_rule('/get_student_docs/<int:stu_id>', view_func=get_student_docs, methods=['GET'])
    bp.add_url_rule('/upload_student_doc', view_func=upload_student_doc, methods=['POST'])
    bp.add_url_rule('/get_doc/<int:doc_id>', view_func=get_doc, methods=['GET'])
    bp.add_url_rule('/delete_doc/<int:doc_id>', view_func=delete_doc, methods=['POST'])


@P.require("student_docs.upload")
async def upload_student_doc():
    try:
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
    except Exception as ex:
        msg = "Error when handling document upload."
        logging.exception(msg)
        return apiVC.error_json(msg)


def __is_doc_access_allowed(stu_id):
    actor = P.current_actor()
    return actor.allowed("student_docs.access", own=lambda: int(stu_id) == actor.id)


@P.require("student_docs.access")
async def get_student_docs(stu_id):
    try:
        if __is_doc_access_allowed(stu_id):
            u = DB.UserDoc.select().where(DB.UserDoc.user == int(stu_id))
            serialized = [apiVC.model_to_dict(r, exclude=[DB.UserDoc.user]) for r in u]
            return apiVC.ok_json(serialized)
        else:
            return apiVC.error_json("Student documents cannot be displayed.")
    except Exception as ex:
        msg = "Error when fetching student documents."
        logging.exception(msg)
        return apiVC.error_json(msg)


@P.require("student_docs.access")
async def delete_doc(doc_id):
    try:
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
    except Exception as ex:
        msg = "Error when deleting the documents."
        logging.exception(msg)
        return apiVC.error_json(msg)


@P.require("student_docs.access")
async def get_doc(doc_id):
    try:
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
    except Exception as ex:
        msg = "Error when loading the documents."
        logging.exception(msg)
        return apiVC.error_json(msg)
