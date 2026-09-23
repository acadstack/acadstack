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
from domain import course as CRS
from domain import dc as DCD
from domain import enrolment as ENR
from domain import milestones as MS
from domain import workflow as WF

# Per workflow: the domain function listing the moves the acting user may
# make on one record (id 0 = a record not yet created).
_ACTIONS = {
    ENR.ENROLMENT: ENR.enrolment_actions,
    DCD.DC: DCD.dc_actions,
    CRS.COURSE: CRS.course_actions,
}

def init_routes(bp: Blueprint):
    bp.add_url_rule('/wfnote_find/<string:entity_name>/<int:entity_key>', 
                        view_func=wfnote_find, methods=['GET'])
    bp.add_url_rule('/wfnote_delete/<int:my_id>', 
                        view_func=wfnote_delete, methods=['GET'])
    bp.add_url_rule('/wfnote_save', view_func=wfnote_save, methods=['POST'])
    bp.add_url_rule('/dates_save', view_func=dates_save, methods=['POST'])
    bp.add_url_rule('/dates_search', view_func=dates_search, methods=['POST'])
    bp.add_url_rule('/workflow_actions/<string:name>/<int:record_id>',
                        view_func=workflow_actions, methods=['GET'])
    bp.add_url_rule('/workflow/<string:name>', view_func=workflow_view,
                        methods=['GET'])
    bp.add_url_rule('/workflow_save', view_func=workflow_save, methods=['POST'])
    bp.add_url_rule('/milestones', view_func=milestones_view, methods=['GET'])
    bp.add_url_rule('/milestones_save', view_func=milestones_save,
                        methods=['POST'])


@C.rbac
async def wfnote_save():
    """Save the workflow note. Expects the JSON request from
    client in an HTTP POST.

    Returns:
        [quart.Response]: quart.Response object containing the 
        JSONified data result of this operation.
    """
    try:
        if not apiVC.has_permission("workflow_notes.manage"):
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
        if not apiVC.has_permission("workflow_notes.manage"):
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


@C.rbac(permissions=["academic_calendar.manage_dates"])
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


@C.rbac
async def workflow_actions(name, record_id):
    """The approval actions the current user may take on a record, which
    the frontend renders as its action buttons."""
    try:
        if name not in _ACTIONS:
            return apiVC.error_json(f"Unknown workflow: {name}")
        return apiVC.ok_json(_ACTIONS[name](apiVC.current_actor(), record_id))
    except C.AcadStackException as ae:
        return apiVC.error_json(str(ae))
    except Exception as ex:
        msg = "Error when loading workflow actions."
        logging.exception(msg)
        return apiVC.error_json(msg)


@C.rbac(permissions=["system.manage_workflows"])
async def workflow_view(name):
    """A workflow's transition table, plus the guard/check/effect names a
    row may refer to."""
    try:
        return apiVC.ok_json({"workflow": WF.load(name).to_json(),
                              "registered": WF.registered_steps()})
    except C.AcadStackException as ae:
        return apiVC.error_json(str(ae))
    except Exception as ex:
        msg = "Error when loading the workflow."
        logging.exception(msg)
        return apiVC.error_json(msg)


@C.rbac(permissions=["system.manage_workflows"])
async def workflow_save():
    """Replaces a workflow's transition table (the whole definition, as
    returned by workflow_view's "workflow")."""
    try:
        fd = await request.get_json(force=True)
        wf = WF.save_workflow(apiVC.current_actor(), fd)
        return apiVC.ok_json(wf.to_json())
    except C.AcadStackException as ae:
        return apiVC.error_json(str(ae))
    except Exception as ex:
        msg = "Error when saving the workflow."
        logging.exception(msg)
        return apiVC.error_json(msg)


@C.rbac
async def milestones_view():
    try:
        return apiVC.ok_json(MS.definitions())
    except Exception as ex:
        msg = "Error when loading academic milestones."
        logging.exception(msg)
        return apiVC.error_json(msg)


@C.rbac(permissions=["system.manage_workflows"])
async def milestones_save():
    """Replaces the academic milestone sequence."""
    try:
        fd = await request.get_json(force=True)
        return apiVC.ok_json(
            MS.save_definitions(apiVC.current_actor(), fd.get("milestones") or []))
    except C.AcadStackException as ae:
        return apiVC.error_json(str(ae))
    except Exception as ex:
        msg = "Error when saving academic milestones."
        logging.exception(msg)
        return apiVC.error_json(msg)
