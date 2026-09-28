"""View functions for managing students' registration fee records.

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__version__ = "0.1"
__status__ = "Development"
"""

import logging
import os
import models as DB
import api_common as apiVC
import policy as P

from quart import Blueprint, request
from quart.helpers import send_file
from werkzeug.utils import secure_filename
from peewee import IntegrityError


def init_routes(bp:Blueprint):
    bp.add_url_rule('/get_fees_txn_file/<string:file_name>', view_func=get_fees_txn_image, methods=['GET'])
    bp.add_url_rule('/delete_fees_txn_data/<int:fee_id>', view_func=delete_student_reg_fees_data, methods=['POST'])
    bp.add_url_rule('/get_reg_fees_data/<int:stu_id>', view_func=get_student_reg_fees_data, methods=['GET'])
    bp.add_url_rule('/save_reg_fees_data', view_func=save_registration_fees_txn_info, methods=['POST'])


@P.require("fees.view")
async def get_fees_txn_image(file_name):
    try:
        fp = os.path.join(apiVC.get_upload_folder(),
                          "FEETXN", secure_filename(file_name))
        return await send_file(fp, attachment_filename="{}.jpg".format(file_name))
    except Exception as ex:
        msg = "Error when loading fees transaction proof image."
        logging.exception(ex)
        return apiVC.error_json(msg)


@P.require("fees.submit")
async def save_registration_fees_txn_info():
    try:
        form = await request.form
        stu_id = int(form['student_id'])
        actor = P.current_actor()
        if not actor.allowed("fees.submit", own=lambda: stu_id == actor.id):
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
    except Exception as ex:
        msg = "Error when handling registration fee details upload."
        logging.exception(ex)
        return apiVC.error_json(msg)


@P.require("fees.view")
async def get_student_reg_fees_data(stu_id):
    try:
        actor = P.current_actor()
        if not actor.allowed("fees.view", own=lambda: stu_id == actor.id):
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

    except Exception as ex:
        msg = "Error when fetching registration fee records."
        logging.exception(ex)
        return apiVC.error_json(msg)


@P.require("fees.delete")
async def delete_student_reg_fees_data(fee_id):
    try:
        ftxn = DB.FeesTransaction.get_or_none(int(fee_id))
        if not ftxn:
            return apiVC.error_json("Invalid transaction details!")

        actor = P.current_actor()
        if not actor.allowed("fees.delete", own=lambda: ftxn.student.id == actor.id):
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

    except Exception as ex:
        msg = "Error when deleting registration fee record."
        logging.exception(ex)
        return apiVC.error_json(msg)
