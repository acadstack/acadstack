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
from typing import Any, Dict, Type
from pathlib import Path
from io import BytesIO
from quart import current_app as APP
from quart import (jsonify, session)
from quart.blueprints import Blueprint
from datetime import datetime as DT
from playhouse.shortcuts import model_to_dict

# logger = logging.getLogger('peewee')
# logger.addHandler(logging.StreamHandler())
# logger.setLevel(logging.DEBUG)

# Query page size
PAGE_SIZE = 25
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
    """Entry years for students must be 20xx, e.g. 2010, 2018, etc.

    Args:
        years (str): Comma-separated list of strings representing years.
        E.g., "2021, 2022"

    Returns:
        bool: True if valid
    """
    years = "" if not years else years
    years = "".join(years.split())
    return re.match(r"^(20\d{2}[,]?)+$", years, re.IGNORECASE)


def course_code_for_pg(code:str)->bool:
    """Checks if the supplied course code represents a PG course. Any code
    number starting with a digit greater than 5 will be considered a
    PG course. E.g., CS504, EE677, etc. are PG courses.

    Args:
        code (str): Course code in the format CCddd.

    Returns:
        bool: True if yes.
    """
    code = "" if not code else code
    return re.match(r"^[A-Za-z]{2,3}[5,6,7,8,9]\d{2}$", code, re.IGNORECASE)


def current_login_id():
    if "user" in session:
        u = session['user']
        return u["login_id"]


def roll_number_valid(rollno:str)->bool:
    """Checks whether the roll number is in correct format.
    Args:
        rollno (str): Roll number string.
    Returns:
        bool: True if valid, else False
    """
    return re.match(r"^20\d{2}[A-Za-z]{2,4}\d{0,4}$", rollno, re.IGNORECASE)


def is_user_in_role(role):
    """Checks whether the currently logged in user has at least
    one of the given role(s).

    The supplied argument can be a single role code string, e.g., "STU",
    or it can be a list of such codes, e.g., ["HOD", "ACA"]
    or even a comma-separated list of role codes such as:
    "HOD,ACA,DEA".
    The role codes must be unique strings.
    
    Args:
        role (str or list of str): Role code or a list of role codes.

    Returns:
        bool: True if the user has any one of the role(s) supplied, else False
    """
    if "user" in session:
        u = session['user']
        return u["role"] in role
    else:
        return False


def logged_in_user():
    if "user" in session:
        u = session['user']
        return M.User.get(M.User.login_id == u["login_id"])


def get_current_user_and_nav():
    if "user" in session:
        u = session['user']
        nav = init_navbar_items(u["role"], u["degree"])
        return ok_json({"user": u, "nav": nav})
    else:
        return error_json("User not logged in.")


async def index():
    return await APP.send_static_file('default.html')


def static_data_dict():
    acs = __acad_sessions_nearby()
    with open(os.path.join(APP.root_path, "static_data.json"), "r") as str_json:
        sd = json.load(str_json)
        sd["AcademicSessions"] = acs if acs else []
        return sd


def academic_session_valid(ac_sess:str)->bool:
    return re.match(r"^20\d{2}-([S]|I{0,2}|T[1-4])$", ac_sess, re.IGNORECASE)


def static_data_item(item_key):
    sd = static_data_dict()
    return sd[item_key]


@C.rbac
async def get_static_data():
    try:
        return ok_json(static_data_dict())
    except Exception as ex:
        msg = "Error when loading static data."
        logging.exception(msg)
        return error_json(msg)


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
    curr_user = logged_in_user() if not outside_request else None
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
    if not outside_request:
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


@C.rbac
async def home():
    return ok_json("Welcome HOME!")


@C.rbac(roles=["ACA", "SUP", "DEA"])
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


def init_navbar_items(role_code:str, degree:str)->Dict[str, Any]:
    """Initializes the navigation bar menus/items for the given role code
    and degree (relevant for only student roles).

    Args:
        role_code (str): User's role
        degree (str): Degree code if student.

    Returns:
        Dict[str, Any]: JSON object containing the nav bar items.
    """
    try:
        with open(os.path.join(APP.root_path, "nav.json"), "r") as nd:
            nav = json.load(nd)
            links = []
            menus = {}
            for n in nav:
                r = n.pop("roles")
                if "-{}".format(role_code) in r:
                    continue

                if "*" in r or role_code in r:
                    m = n.pop("menu")
                    if m:
                        if role_code == "STU" and degree != "PHD" and \
                            m.upper() == "PHD":
                            continue
                        if m not in menus:
                            menus[m] = []
                        menus[m].append(n)
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


def __next_acad_session(cas):
    sm = {
            "S":"I","I":"II",
            "II":"S","T1":"T2",
            "T2":"T3","T3":"T4",
            "T4":"T1"
        }

    # I->II->S->I 
    cy = int(cas[:4])
    cs = cas[5:]
    
    ny =  cy+1 if cs in ["S","T4"] else cy
    ns = sm[cs]

    return "{0}-{1}".format(ny, ns)

def __acad_sessions_nearby():
    cas_list = __current_acad_sessions_with_dates()
    if cas_list:
        cas_row = cas_list[0]
        cas_str = "current session ({0} to {1})".format(cas_row[1], cas_row[2])
        cas = cas_row[0].strip().upper()
        ay = cas[:4]
        sem = cas[5:]
    
        cas = ay + "-" + sem

        n1 = __next_acad_session(cas)
        n1_v = "upcoming session"
        if n1.endswith("-S"):
            n1_v += " (summer)"
        else:
            n1_v += " (regular)"

        n2 = __next_acad_session(n1)
        n2_v = "next session"
        if n2.endswith("-S"):
            n2_v += " (summer)"
        else:
            n2_v += " (regular)"

        return [{"id": cas, "value": cas_str},
                {"id": n1, "value": n1_v},
                {"id": n2, "value": n2_v}]


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