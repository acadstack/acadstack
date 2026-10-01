"""Functions used by other API modules.

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__version__ = "0.1"
__status__ = "Development"
"""

import json, logging, os, re, uuid
import numpy as np
import common as C
import models as M
import settings as ST
import policy as P
from typing import Any, Dict, Type
from pathlib import Path
from io import BytesIO
from quart import current_app as APP
from quart import (has_request_context, jsonify, request, session)
from quart.blueprints import Blueprint
from datetime import datetime as DT
from playhouse.shortcuts import model_to_dict

# logger = logging.getLogger('peewee')
# logger.addHandler(logging.StreamHandler())
# logger.setLevel(logging.DEBUG)

B64_HDR = "data:image/jpeg;base64,"

vbp = Blueprint('bp', __name__, template_folder='templates')

# Face encodings are serialized using this encoder 
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)


def json_to_np(json_str):
    jobj = json.loads(json_str)
    return np.asarray(jobj["obj"])


def np_to_json(obj):
    return json.dumps({'obj': obj}, cls=NumpyEncoder)


def entry_years_valid(years:str)->bool:
    """Entry years for students are 4-digit years, e.g. 2010, 2018, etc.

    Args:
        years (str): Comma-separated list of strings representing years.
        E.g., "2021, 2022"

    Returns:
        bool: True if valid
    """
    years = "" if not years else years
    years = "".join(years.split())
    return re.match(r"^(\d{4}[,]?)+$", years, re.IGNORECASE)


def current_login_id():
    if "user" in session:
        u = session['user']
        return u["login_id"]


def logged_in_user():
    if "user" in session:
        u = session['user']
        return M.User.get(M.User.login_id == u["login_id"])


def get_current_user_and_nav():
    if "user" in session:
        u = session['user']
        actor = P.current_actor()
        nav = init_navbar_items(actor, u.get("degree_level"))
        return ok_json({"user": {**u, "perms": sorted(actor.perms)}, "nav": nav})
    else:
        return error_json("User not logged in.")


async def index():
    return await APP.send_static_file('default.html')


# Lists that differ between universities. They are stored in the VocabItem
# table; the lists that code depends on stay in static_data.json.
DB_VOCABS = ("Departments", "Degrees", "CourseSlots", "CourseTypes",
             "MinorConcSpecialization", "PersonCategories", "DegreeType",
             "CourseFreqs", "CalendarEvents")

# The columns that store a list's codes; a code must fit the shortest one.
VOCAB_CODE_COLUMNS = {
    "Departments": (M.Person.dept_name, M.CourseOffering.dept_name, M.CourseCategory.dept),
    "Degrees": (M.Person.degree, M.CourseCategory.degree, M.BatchAdvisors.for_degree),
    "CourseSlots": (M.CourseOffering.slot, M.CourseSlotTiming.slot),
    "CourseTypes": (M.CourseCategory.category,),
    "MinorConcSpecialization": (M.Person.deg_type_spec,),
    "PersonCategories": (M.Person.category,),
    "DegreeType": (M.Person.deg_type,),
    "CourseFreqs": (M.Course.freq,),
    "CalendarEvents": (),
}

# The attrs an item of a list may have: name -> allowed values, or None for
# any text.
VOCAB_ATTRS = {
    "Degrees": {"level": ["UG", "PG", "PHD"], "printed_name": None,
                "specialisation": None},
    "CourseTypes": {"group": ["CORE", "ELECTIVE"]},
}


def degree_level(code):
    """The level (UG, PG or PHD) of the program with this code, or None."""
    row = M.VocabItem.get_or_none((M.VocabItem.vocab == "Degrees") &
                                  (M.VocabItem.code == code))
    return row.attrs.get("level") if row else None


def _workflow_lists():
    """The lists of static_data.json, with the label_overrides setting applied."""
    sd = C.static_data_json()
    for lst, labels in ST.get("label_overrides").items():
        for e in sd.get(lst, []):
            e["value"] = labels.get(e["id"], e["value"])
    return sd


def static_data_dict():
    acs = __acad_sessions_nearby()
    sd = _workflow_lists()
    hidden = ST.get("hidden_enrol_types")
    sd["EnrolTypes"] = [e for e in sd["EnrolTypes"] if e["id"] not in hidden]
    sd["AcademicSessions"] = acs
    for v in DB_VOCABS:
        sd[v] = [{"id": "", "value": "-Select-"}]
    rows = M.VocabItem.select().where(M.VocabItem.is_deleted == False) \
        .order_by(M.VocabItem.vocab, M.VocabItem.sort_order, M.VocabItem.id)
    for r in rows:
        if r.vocab in DB_VOCABS:
            sd[r.vocab].append({"id": r.code, "value": r.label})
    # roster: the kinds of person a role's users count as, e.g. ["student"].
    sd["UserRoles"] = [{"id": "", "value": "-Select-", "roster": []}] + [
        {"id": r.code, "value": r.label,
         "roster": sorted(p.split(".", 1)[1] for p in P.perms_of(r.code) if p.startswith("roster."))}
        for r in M.Role.select().order_by(M.Role.id)]
    return sd


def calendar_event_labels():
    """Label of every calendar event: the workflow events, then the university's
    CalendarEvents, hidden ones included because their dates are kept."""
    labels = {e["id"]: e["value"] for e in _workflow_lists()["WorkflowEvents"]}
    for r in M.VocabItem.select().where(M.VocabItem.vocab == "CalendarEvents"):
        labels.setdefault(r.code, r.label)
    return labels


def calendar_entry_label(event_code, labels):
    """Label of an academiccalendar row: an event's own code, or the code with
    _S or _E for the event's start or end date."""
    if event_code in labels:
        return labels[event_code]
    base, _, end = event_code.rpartition("_")
    if base in labels and end in ("S", "E"):
        return f"{labels[base]} {'starts' if end == 'S' else 'ends'}"
    return event_code


def academic_session_valid(ac_sess:str)->bool:
    return M.AcademicSession.select().where(M.AcademicSession.code == ac_sess).exists()


def session_start_dates(acad_sessions):
    """The SESSION_S date of each of the given academic sessions that has one."""
    rows = M.AcademicCalendar.select().where(
        (M.AcademicCalendar.event_code == "SESSION_S")
        & (M.AcademicCalendar.acad_session << list(acad_sessions)))
    return {r.acad_session: r.event_value for r in rows}


def static_data_item(item_key):
    sd = static_data_dict()
    return sd[item_key]


@P.require("app.access")
async def get_static_data():
    try:
        return ok_json(static_data_dict())
    except Exception as ex:
        msg = "Error when loading static data."
        logging.exception(msg)
        return error_json(msg)


@P.require("settings.manage")
async def get_settings():
    return ok_json(ST.all_settings())


@P.require("settings.manage")
async def save_setting():
    fd = await request.get_json(force=True)
    try:
        ST.save(fd.get("key"), fd.get("value"))
    except ValueError as ex:
        return error_json(str(ex))
    return ok_json(ST.all_settings())


def all_vocab():
    items = {v: [] for v in DB_VOCABS}
    for r in M.VocabItem.select().where(M.VocabItem.vocab << DB_VOCABS) \
            .order_by(M.VocabItem.sort_order, M.VocabItem.id):
        items[r.vocab].append({"id": r.id, "code": r.code, "label": r.label,
                               "sort_order": r.sort_order, "attrs": r.attrs,
                               "is_deleted": r.is_deleted})
    return {"items": items, "attrs": VOCAB_ATTRS}


def _vocab_item_error(row, fd):
    """Why the list item can't be saved with the values in fd, or None."""
    code, label = row.code, fd.get("label")
    sort_order, attrs = fd.get("sort_order", row.sort_order), fd.get("attrs", row.attrs)
    declared = VOCAB_ATTRS.get(row.vocab, {})
    if row.id is None:
        max_len = min(f.max_length for f in (M.VocabItem.code, *VOCAB_CODE_COLUMNS[row.vocab]))
        if type(code) is not str or not 0 < len(code) <= max_len:
            return f"A {row.vocab} code must be 1 to {max_len} characters."
        if M.VocabItem.get_or_none((M.VocabItem.vocab == row.vocab) & (M.VocabItem.code == code)):
            return f"{row.vocab} already has the code {code}."
        if row.vocab == "CalendarEvents":
            # An event's dates are stored under its code and <code>_S/_E, so
            # these must not be the date codes of another event.
            dates = lambda c: {c, f"{c}_S", f"{c}_E"}
            taken = [c for c in calendar_event_labels() if dates(c) & dates(code)]
            if taken:
                return f"{code} clashes with the dates of the event {taken[0]}."
    elif fd.get("code") != row.code or fd.get("vocab") != row.vocab:
        return "The list and code of a saved item can't change."
    if type(label) is not str or not 0 < len(label.strip()) <= 200:
        return "The label must be 1 to 200 characters."
    if type(sort_order) is not int:
        return "The sort order must be a whole number."
    if type(attrs) is not dict:
        return "The attributes must be an object."
    for name, value in attrs.items():
        if name not in declared:
            return f"Unknown attribute {name} for {row.vocab}."
        allowed = declared[name]
        if type(value) is not str or (allowed and value not in allowed):
            return f"Invalid value for {name}: {value!r}."
    if row.vocab == "Departments" and row.code == "ALL" and fd.get("is_deleted"):
        return "The ALL department can't be hidden."


@P.require("settings.manage")
async def get_vocab():
    return ok_json(all_vocab())


@P.require("settings.manage")
async def save_vocab():
    """Adds a list item, or changes the label, sort order, attrs or hiding of
    the item with the given id."""
    try:
        fd = await request.get_json(force=True)
        if type(fd) is not dict:
            return error_json("Expected the list item as an object.")
        if fd.get("id"):
            row = M.VocabItem.get_or_none(M.VocabItem.id == int(fd["id"]))
            if row is None:
                return error_json("No such list item.")
        elif fd.get("vocab") in DB_VOCABS:
            code = fd.get("code")
            row = M.VocabItem(vocab=fd["vocab"], code=code.strip() if type(code) is str else code)
        else:
            return error_json(f"Unknown list: {fd.get('vocab')}")
        error = _vocab_item_error(row, fd)
        if error:
            return error_json(error)
        row.label = fd["label"].strip()
        row.sort_order = fd.get("sort_order", row.sort_order)
        row.attrs = fd.get("attrs", row.attrs)
        row.is_deleted = bool(fd.get("is_deleted", row.is_deleted))
        save_entity(row)
        return ok_json(all_vocab())
    except Exception as ex:
        msg = "Error when saving the list item."
        logging.exception(msg)
        return error_json(msg)


@P.require(P.ADMIN_PERM)
async def get_permissions():
    return ok_json(P.all_grants())


@P.require(P.ADMIN_PERM)
async def save_role_permissions():
    fd = await request.get_json(force=True)
    try:
        P.save(fd.get("role"), fd.get("label"), fd.get("permissions"), P.current_actor())
    except ValueError as ex:
        return error_json(str(ex))
    return ok_json(P.all_grants())


def label_for_static_data_item(item_code, items_map):
    long_label = item_code
    for y in items_map:
        ct = item_code
        if ct == y["id"]:
            long_label = y["value"]
            break

    return long_label


def save_entity(obj: M.BaseModel, outside_request=False):
    """Persists the model instance in the DB.
    Args:
        obj (M.BaseModel): Model instance to persist.

    Returns:
        Any: PK of the record inserted in DB.
    """
    in_request = has_request_context() and not outside_request
    curr_user = logged_in_user() if in_request else None
    obj.txn_login_id = curr_user.login_id if curr_user else "None"
    obj.upd_ts = DT.now()
    obj.ins_ts = DT.now()
    return obj.save()


def update_entity(entity:Type[M.BaseModel], obj:M.BaseModel, exclude=[],
                  outside_request=False)->int:
    """Updates the supplied model in the DB.

    Args:
        entity (Type[M.BaseModel]): Type of the model being updated.
        obj (M.BaseModel): Model instance to update.
        exclude (list, optional): List of props/columns to skip. Defaults to [].
        outside_request (bool): Whether invoked outside of HTTP request context.

    Returns:
        int: No. of rows affected in DB.
    """
    txn_no = int(obj.txn_no)
    obj.txn_no = 1 + txn_no # For optimistic locking
    obj.upd_ts = DT.now()
    # Background tasks run without a request, so without a logged-in user.
    if has_request_context() and not outside_request:
        obj.txn_login_id = logged_in_user().login_id
    else:
        obj.txn_login_id = "Out of request"
    # We exclude the insert timestamp from the update
    exclude.append(getattr(entity, "ins_ts"))
    mdict = model_to_dict(obj, recurse=False, exclude=exclude)
    return entity.update(mdict).where(
        (entity.txn_no == obj.txn_no - 1) & # Optimistic locking check
        (entity.id == obj.id)).execute()


def ok_json(obj):
    return jsonify({"status": "OK", "body": obj})


def error_json(obj):
    return jsonify({"status": "ERROR", "body": obj})


def get_upload_folder(sub_dir=None):
    # Ensure that the uploads folder for this user exists
    uf = APP.config['upload_folder']
    if sub_dir:
        uf = os.path.join(uf, sub_dir)
    Path(uf).mkdir(parents=True, exist_ok=True)
    return uf


def get_upload_folder_for_user():
    # Ensure that the uploads folder for this user exists
    uf = os.path.join(APP.config['upload_folder'], session["user"]["login_id"])
    Path(uf).mkdir(parents=True, exist_ok=True)
    return uf


@P.require("app.access")
async def home():
    return ok_json("Welcome HOME!")


@P.require("users.view_active")
async def get_active_users():
    try:
        users = []
        for k in list(APP.active_users.keys()):
            v = APP.active_users.get(k)
            # Older than 30 minutes are inactive
            sec_since_last_access = (DT.now() - v).total_seconds()
            if sec_since_last_access < 1800:
                users.append("{0}. | Last access {1:.2f} min ago".format(k, sec_since_last_access/60))
            else:
                APP.active_users.pop(k, None)
        
        return ok_json(users)
    except Exception as ex:
        msg = "Failed to get active users."
        logging.exception(msg)
        return error_json(msg)


def update_active_users():
    if "user" in session:
        APP.active_users[C.this_user_name_login_id()] = DT.now()


def logout(send_response=True):
    APP.active_users.pop(C.this_user_name_login_id(), None)
    session.pop('user', None)
    if send_response:
        return ok_json("Logged out.")


def init_navbar_items(actor:P.Actor, degree_level:str)->Dict[str, Any]:
    """Builds the navigation menus for the given user. Each nav.json entry
    names the permission of the endpoint its page opens: a scoped code such
    as "fees.view:own" must be held exactly, a plain one at any scope.

    Args:
        actor (P.Actor): The logged-in user.
        degree_level (str): The level of the user's program; the PhD menu is
            shown to users who act only on their own records (students) only
            if it is PHD.

    Returns:
        Dict[str, Any]: JSON object containing the nav bar items.
    """
    try:
        with open(os.path.join(APP.root_path, "nav.json"), "r") as nd:
            nav = json.load(nd)
        links = []
        menus = {}
        for n in nav:
            perm = n.pop("perm")
            if not (actor.has(perm) if ":" in perm else actor.can(perm)):
                continue
            m = n.pop("menu")
            if m:
                if m.upper() == "PHD" and actor.own_records_only and degree_level != "PHD":
                    continue
                menus.setdefault(m, []).append(n)
            else:
                links.append(n)

        return {"menus": menus, "links": links}

    except Exception as ex:
        logging.exception("Error occurred when loading nav data.")


def __current_acad_sessions_with_dates(sem_only=True):
    sql_qry = C.sql_by_id("current_acad_sessions")
    cursor = C.db.execute_sql(sql_qry, [sem_only])
    cas = []
    for row in cursor.fetchall():
        # Row has: (acad_session, start_dt, end_dt)
        cas.append((row[0], row[1], row[2]))
    return cas


def current_acad_session_list(sem_only=True):
    casd = __current_acad_sessions_with_dates(sem_only)
    # Return the earliest starting acad session
    return [x[0] for x in casd]


def current_acad_session():
    casd = __current_acad_sessions_with_dates()
    # Return the earliest starting acad session
    return casd[0][0]


def __acad_sessions_nearby():
    """The current session and the next two sessions starting after today."""
    sessions = []
    cas_list = __current_acad_sessions_with_dates()
    if cas_list:
        cas, start_dt, end_dt = cas_list[0]
        sessions.append({"id": cas, "value": f"current session ({start_dt} to {end_dt})"})
    cursor = C.db.execute_sql(C.sql_by_id("upcoming_sessions"))
    for (code, is_additional), label in zip(cursor.fetchall(),
                                            ["upcoming session", "next session"]):
        if is_additional:
            label += " (additional)"
        sessions.append({"id": code, "value": label})
    return sessions


def save_file_to_uploads_folder(file_category, data_bytes):
    file_folder = os.path.join(get_upload_folder(), file_category)
    Path(file_folder).mkdir(parents=True, exist_ok=True)
    file_name = str(uuid.uuid4()).replace("-", "")
    file_path = os.path.join(file_folder, file_name)
    with open(file_path, 'wb') as df:
        df.write(data_bytes)
    return file_name


def result_set_from_cursor(cursor):
    ncols = len(cursor.description)
    colnames = [cursor.description[i][0] for i in range(ncols)]
    results = []

    for row in cursor.fetchall():
        res = {}
        for i in range(ncols):
            res[colnames[i]] = row[i]
        results.append(res)
    
    return results


def db_result_to_excel(cursor):
    ncols = len(cursor.description)
    colnames = [cursor.description[i][0] for i in range(ncols)]
    result = []

    # Add the header row
    hdr_row = []
    for col_name in colnames:
        hdr_row.append(col_name)
    result.append(','.join(hdr_row))

    # Add the data rows
    for row in cursor.fetchall():
        row_data = []
        for i in range(ncols):
            row_data.append(row[i])
        result.append(','.join(map(str, row_data)))
    fp = BytesIO()
    fp.write('\n'.join(result).encode('utf-8'))
    fp.flush()
    fp.seek(0)
    return fp