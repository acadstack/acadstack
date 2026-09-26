"""Functions used by other API modules.

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__version__ = "0.1"
__status__ = "Development"
"""

import csv, json, logging, os, re, uuid
import numpy as np
import acad_session as AS
import common as C
import models as M
import permissions as PERM
import settings_store as ST
import vocab_defaults as VD
from domain import academic_calendar as CAL
from domain import persistence
from domain.context import Actor
from typing import Any, Dict, Type
from pathlib import Path
from io import BytesIO, StringIO
from quart import current_app as APP
from quart import (jsonify, request, session)
from quart.blueprints import Blueprint
from datetime import datetime as DT
# Re-exported on purpose: several api_* modules call apiVC.model_to_dict().
from playhouse.shortcuts import model_to_dict  # noqa: F401

# logger = logging.getLogger('peewee')
# logger.addHandler(logging.StreamHandler())
# logger.setLevel(logging.DEBUG)

B64_HDR = "data:image/jpeg;base64,"


def page_size() -> int:
    """Default page size for paginated list endpoints. DB-backed via
    settings_store so it can be changed without a restart."""
    return ST.setting("app.page_size")

vbp = Blueprint('bp', __name__, template_folder='templates')


def init_routes(bp: Blueprint):
    bp.add_url_rule('/', view_func=index, methods=['GET'])
    bp.add_url_rule('/auc', view_func=get_active_users, methods=['GET'])
    bp.add_url_rule('/get_static_data', view_func=get_static_data, methods=['GET'])


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


def none_if_dash(v):
    """"-" is the frontend's "no filter selected" value for a dropdown;
    callers treat that the same as an empty filter."""
    return "" if v == "-" else v


async def json_body():
    """The request's JSON body, parsed the same way every route does."""
    return await request.get_json(force=True)


def entry_years_valid(years:str)->bool:
    """Entry years for students must be plausible 4-digit academic years
    (app.min_academic_year..app.max_academic_year), e.g. 2010, 2018.

    Args:
        years (str): Comma-separated list of strings representing years.
        E.g., "2021, 2022"

    Returns:
        bool: True if valid
    """
    years = "" if not years else years
    years = "".join(years.split())
    if not re.match(r"^(\d{4}[,]?)+$", years):
        return False
    lo, hi = ST.setting("app.min_academic_year"), ST.setting("app.max_academic_year")
    return all(lo <= int(y) <= hi for y in re.findall(r"\d{4}", years))


def current_login_id():
    return ST.current_login_id()


def roll_number_valid(rollno:str)->bool:
    """Checks whether the roll number is in correct format: a plausible
    4-digit entry year (app.min_academic_year..app.max_academic_year)
    followed by 2-4 letters and up to 4 digits.
    Args:
        rollno (str): Roll number string.
    Returns:
        bool: True if valid, else False
    """
    m = re.match(r"^(\d{4})[A-Za-z]{2,4}\d{0,4}$", rollno, re.IGNORECASE)
    if not m:
        return False
    lo, hi = ST.setting("app.min_academic_year"), ST.setting("app.max_academic_year")
    return lo <= int(m.group(1)) <= hi


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
        roles = role.split(",") if isinstance(role, str) else role
        return u["role"] in roles
    else:
        return False


def has_permission(name):
    """Checks whether the currently logged in user's role holds the named
    permission (see permissions.py). Session-only, like
    is_user_in_role() -- no DB query -- for adapter-layer checks that
    don't otherwise need an Actor.

    Args:
        name (str): Permission name, e.g. "course.save".

    Returns:
        bool: True if the current user's role holds the permission.
    """
    if "user" in session:
        return PERM.role_has_permission(session['user']["role"], name)
    else:
        return False


def logged_in_user():
    if "user" in session:
        u = session['user']
        return M.User.get(M.User.login_id == u["login_id"])


#: Stand-in for "nobody is logged in". Its role code is not a real role,
#: so has_role() never matches; routes behind @rbac never see it.
ANONYMOUS = Actor(login_id="", role="ANON")


def current_actor() -> Actor:
    """The acting user as a domain-layer :class:`Actor`.

    This is the ONE place the session is turned into something the
    domain can use. The role comes from the session (so role checks
    behave exactly as is_user_in_role() always has) while the ids come
    from the User row, at the cost of the same single query
    logged_in_user() already makes.
    """
    if "user" not in session:
        return ANONYMOUS
    su = session['user']
    u = M.User.get(M.User.login_id == su["login_id"])
    person = u.person
    return Actor(login_id=u.login_id,
                 role=su["role"],
                 user_id=u.id,
                 degree=person.degree if person else su.get("degree"),
                 dept_name=person.dept_name if person else su.get("dept"),
                 org_id=person.org_id if person else None)


async def get_current_user_and_nav():
    if "user" in session:
        u = session['user']
        nav = init_navbar_items(u["role"], u["degree"])
        return ok_json({"user": {**u, "permissions": PERM.permissions_for_role(u["role"])},
                         "nav": nav})
    else:
        return error_json("User not logged in.")


async def index():
    return await APP.send_static_file('default.html')


def static_data_dict():
    """Builds the dropdown/label data the frontend calls "static data",
    from the DB-effective controlled vocabularies (settings_store.vocab(),
    falling back to vocab_defaults.py) rather than a hand-maintained JSON
    file. Key names and shape (including which groups get a leading
    {"id": "", "value": "-Select-"} entry) are preserved exactly, so
    nothing on the frontend needs to change -- see
    vocab_defaults.STATIC_DATA_KEYS."""
    sd = {}
    for vocab_name, (json_key, with_blank) in VD.STATIC_DATA_KEYS.items():
        rows = [{"id": item["code"], "value": item["label"]}
                for item in ST.vocab(vocab_name)]
        if with_blank:
            rows = [{"id": "", "value": "-Select-"}] + rows
        sd[json_key] = rows
    acs = __acad_sessions_nearby()
    sd["AcademicSessions"] = acs if acs else []
    sd["MinAttendancePercentRequired"] = ST.setting("attendance.min_percent_required")
    return sd


def academic_session_valid(ac_sess:str)->bool:
    """Whether ac_sess is a well-formed "YYYY-<suffix>" academic session,
    per the canonical suffix table in acad_session.py (the single source
    for session ordering/validity -- see that module's docstring)."""
    return AS.is_valid(ac_sess)


def static_data_item(item_key):
    sd = static_data_dict()
    return sd[item_key]


@C.rbac
async def get_static_data():
    return ok_json(static_data_dict())


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
    actor = Actor(login_id=curr_user.login_id, role=curr_user.role,
                  user_id=curr_user.id) if curr_user else None
    return persistence.save(obj, actor)


def update_entity(entity:Type[M.BaseModel], obj:M.BaseModel, exclude=None,
                  outside_request=False)->int:
    """Updates the supplied model in the DB.

    Args:
        entity (Type[M.BaseModel]): Type of the model being updated.
        obj (M.BaseModel): Model instance to update.
        exclude (list, optional): List of props/columns to skip. Not
            mutated by this call.
        outside_request (bool): Whether invoked outside of HTTP request context.

    Returns:
        int: No. of rows affected in DB.
    """
    actor = None
    if not outside_request:
        u = logged_in_user()
        actor = Actor(login_id=u.login_id, role=u.role, user_id=u.id)
    return persistence.update(entity, obj, actor, exclude)


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


@C.rbac(permissions=["system.view_active_users"])
async def get_active_users():
    users = []
    active_window = ST.setting("app.active_user_window_secs")
    for k in list(APP.active_users.keys()):
        v = APP.active_users.get(k)
        sec_since_last_access = (DT.now() - v).total_seconds()
        if sec_since_last_access < active_window:
            users.append("{0}. | Last access {1:.2f} min ago".format(k, sec_since_last_access/60))
        else:
            APP.active_users.pop(k, None)
    
    return ok_json(users)


async def update_active_users():
    if "user" in session:
        APP.active_users[C.this_user_name_login_id()] = DT.now()


def end_user_session():
    APP.active_users.pop(C.this_user_name_login_id(), None)
    session.pop('user', None)


async def logout():
    end_user_session()
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
                # One permission name, or a list of which any one will do
                # (the same rule as @rbac(permissions=[...])).
                perm = n.pop("permission")
                perms = perm if isinstance(perm, list) else [perm]
                if not any(PERM.role_has_permission(role_code, p)
                           for p in perms):
                    continue

                restrict_degree = n.pop("restrictToDegree", None)
                if restrict_degree and role_code == "STU" and \
                        degree != restrict_degree:
                    continue

                m = n.pop("menu")
                if m:
                    if m not in menus:
                        menus[m] = []
                    menus[m].append(n)
                else:
                    links.append(n)

            return {"menus": menus, "links": links}

    except Exception as ex:
        logging.exception("Error occurred when loading nav data.")


# Implemented in domain.academic_calendar so the domain layer can read
# the calendar without importing this module; re-exported here because
# the api_* modules already import these names from api_common.
__current_acad_sessions_with_dates = CAL.current_acad_sessions_with_dates
current_acad_session_list = CAL.current_acad_session_list
current_acad_session = CAL.current_acad_session


def __next_acad_session(cas):
    """The session that follows `cas` within its own academic calendar
    (semester/quarter), wrapping to next year after the calendar's last
    suffix. Derived from acad_session.py's suffix ordering rather than a
    hand-maintained succession map, so it can never disagree with the
    ordinal comparisons policy_store.py relies on."""
    year, suffix = AS.parse(cas)
    own = AS.suffixes_for(AS.session_type(cas))
    idx = own.index(suffix)
    if idx + 1 < len(own):
        return "{0}-{1}".format(year, own[idx + 1])
    return "{0}-{1}".format(year + 1, own[0])

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


def cursor_to_csv(cursor):
    colnames = [d[0] for d in cursor.description]
    return rows_to_csv(colnames, cursor.fetchall())


def rows_to_csv(colnames, rows):
    """A CSV file object: a header row of ``colnames``, then ``rows``,
    properly quoted (a plain ','.join broke on any value containing a
    comma or newline)."""
    text_fp = StringIO()
    writer = csv.writer(text_fp)
    writer.writerow(colnames)
    writer.writerows(rows)
    fp = BytesIO(text_fp.getvalue().encode('utf-8'))
    fp.seek(0)
    return fp