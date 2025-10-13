"""View functions for managing the workflow specific tasks.

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__version__ = "0.1"
__status__ = "Development"
"""

import logging

from quart import Blueprint
from quart.views import request
import playhouse.shortcuts as PS

import models as M
import api_common as apiVC
import common as C

def init_routes(bp: Blueprint):
    bp.add_url_rule('/wfnote_find/<string:entity_name>/<int:entity_key>', 
                        view_func=wfnote_find, methods=['GET'])
    bp.add_url_rule('/wfnote_delete/<int:my_id>', 
                        view_func=wfnote_delete, methods=['GET'])
    bp.add_url_rule('/wfnote_save', view_func=wfnote_save, methods=['POST'])
    bp.add_url_rule('/dates_save', view_func=dates_save, methods=['POST'])
    bp.add_url_rule('/dates_search', view_func=dates_search, methods=['POST'])


@C.rbac
async def wfnote_save():
    """Save the workflow note. Expects the JSON request from
    client in an HTTP POST.

    Returns:
        [quart.Response]: quart.Response object containing the 
        JSONified data result of this operation.
    """
    try:
        if apiVC.is_user_in_role("STU"):
            return apiVC.error_json("Students not allowed to add workflow notes!")
        fd = await request.get_json(force=True)
        logging.debug(f"Saving workflow note details: {fd}")
        wfn = M.WorkflowNote()
        C.update_model_skip_unknown(wfn, fd)
        if wfn.entity_name and wfn.entity_key and wfn.note:
            apiVC.save_entity(wfn)
            logging.debug(f"Inserted workflow notes: {wfn}")
            return apiVC.ok_json(PS.model_to_dict(wfn))
        else:
            return apiVC.error_json("Please supply the required data!")

    except Exception as ex:
        msg = "Error when saving workflow note details."
        logging.exception(msg)
        return apiVC.error_json("{0}: {1}".format(msg, ex))


@C.rbac
async def wfnote_find(entity_name, entity_key):
    try:
        logging.info(f"Loading workflow note details for {entity_name}, "
                     f"Key: {entity_key}")
        query = M.WorkflowNote.select().where(
            (M.WorkflowNote.entity_name == entity_name) &
            (M.WorkflowNote.entity_key == entity_key)
        )
        res = query.order_by(-M.WorkflowNote.ins_ts).execute()
        return apiVC.ok_json([PS.model_to_dict(r) for r in res])

    except Exception as ex:
        msg = "Error when finding workflow note details."
        logging.exception(msg)
        return apiVC.error_json(f"{msg}: {ex}")


@C.rbac
async def wfnote_delete(my_id):
    try:
        if apiVC.is_user_in_role("STU"):
            return apiVC.error_json("Students not allowed to delete workflow notes!")
        note = M.WorkflowNote.get_or_none(int(my_id))
        if note and note.txn_login_id != apiVC.logged_in_user().login_id:
            return apiVC.error_json("Cannot delete notes of others!")

        rc = M.WorkflowNote.delete().where(M.WorkflowNote.id == my_id).execute()
        return apiVC.ok_json(f"Deleted {rc} records.")
    except Exception as ex:
        msg = "Error occurred when deleting Workflow Note."
        logging.exception(msg)
        return apiVC.error_json(msg)


@C.rbac(roles=["ACA", "DEA"])
async def dates_save():
    try:
        fd = await request.get_json(force=True)
        logging.info(f"Saving academic dates : {fd}")
        session = fd.get("session")
        eventdates = fd.get("eventDates")
        ac = M.AcademicCalendar()
        for x in eventdates:
            (ac.insert(acad_session=session, event_code=x, \
                       event_value=eventdates[x]) \
            .on_conflict(
                conflict_target=[M.AcademicCalendar.acad_session, M.AcademicCalendar.event_code],
                update={M.AcademicCalendar.event_value: eventdates[x]}
            ).execute())
            logging.debug(f"Inserted AcademicCalendar: {ac}")
        return apiVC.ok_json("inserted successfully")

    except Exception as ex:
        msg = "Error when saving academic dates."
        logging.exception(msg)
        return apiVC.error_json(f"{msg}: {ex}")


@C.rbac
async def dates_search():
    try:
        fd = await request.get_json(force=True)
        res = M.AcademicCalendar.select().where(M.AcademicCalendar.acad_session
                                                == fd.get("session")).execute()
        if res:
            obj = {"eventDates": {}}
            for r in res:
                obj["eventDates"][r.event_code] = r.event_value
            obj["session"] = res[0].acad_session
            return apiVC.ok_json(obj)
        else:
            return apiVC.error_json(f"No data for {fd.get("session")} session.")

    except Exception as ex:
        msg = "Error when saving academic dates."
        logging.exception(msg)
        return apiVC.error_json(f"{msg}: {ex}")
