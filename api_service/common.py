"""This module contains commonly used functions in this app.

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__version__ = "0.1"
__status__ = "Development"
"""

import logging, re, random, string, toml
from typing import Any, Callable, Optional
from datetime import datetime as DT
from datetime import date
from functools import wraps
from quart import current_app
from quart import (jsonify, session)

from jinja2 import Environment, FileSystemLoader
from playhouse.shortcuts import update_model_from_dict

from json import JSONEncoder

from models import db
from email_client import Emailer

class JSONEncoderWithDate(JSONEncoder):
    def default(self, obj):
        try:
            if isinstance(obj, date) or isinstance(obj, DT):
                return obj.isoformat()
            iterable = iter(obj)
        except TypeError:
            pass
        else:
            return list(iterable)
        return JSONEncoder.default(self, obj)

emailer = Emailer()

TS_FORMAT = "%Y%m%d_%H%M%S"
WEEK_DAY_NAMES = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']

VALID_GRADES = ['A','A-','B','B-','C','C-','D','E','F','I','W','NP', 'NF','S','NA', 'U']
VALID_AUDIT_GRADES = ["NP", "NF", "NA", "I", "W"]

ACAD_EVENT_CODES = ['ADD_DROP_E', 'ADD_DROP_S',
                    'CLASSES_E', 'CLASSES_S', 'COURSE_REG_E',
                    'COURSE_REG_S', 'FEEDBACK_E', 'FEEDBACK_S',
                    'GRADE_SUB_E', 'GRADE_SUB_S', 'MAJOR_EXAM_E',
                    'MAJOR_EXAM_S', 'MINOR_EXAM_E', 'MINOR_EXAM_S',
                    'SESSION_E', 'SESSION_S', 'WITHDRAW_E',
                    'WITHDRAW_S', 'FEEDBACK_MID_E', 'FEEDBACK_MID_S',
                    'SHOW_MIDSEM_FB_S', 'SHOW_ENDSEM_FB_S','RESULT_DECLARATION']

class AcadStackException(Exception):
    """
    This is application specific exception thrown to the clients.
    """
    pass


def current_dt_str():
    return DT.now().strftime("%Y-%m-%d")

def sql_by_id(sid):
    sql_map = toml.load("sql_statements.toml")
    return sql_map[sid]

def add_user_to_session():
    if "user" in session:
        logging.info("User is already in session: {0}".format(session["user"]))
        return dict(user=session["user"])
    else:
        logging.info("User not in session!")
        return dict()


def rbac(_func:Callable=None, *, roles=None):
    """Decorator that can be applied to a function to perform the role 
    based access checks for the current user if available in the session.
    If no authenticated user available in the session, the decorated 
    function wll not be called and an error JSON message will be returned.
    If the logged in user has at least one of the roles specified in the
    list, then the decorated function is called. If the roles list is not
    supplied then only the presence of the authenticated user in the session
    is checked before allowing the decorated function invocation.
    Args:
        _func (Callable, optional): The function being decorated. Defaults to None.
        roles (list[str], optional): Roles list allowed. Defaults to None.
    """
    def decor_auth(func):
        @wraps(func)
        async def wrapper_auth(*args, **kwargs):
            if "user" not in session:
                msg = "Login required to access this operation."
                logging.warning(msg)
                return jsonify({"status": "ERROR", "body": msg})

            user_role = session["user"]["role"]
            if roles and (user_role not in roles):
                msg = "You do not have required permissions to access."
                logging.warning(msg)
                return jsonify({"status": "ERROR", "body": msg})
            return await func(*args, **kwargs)

        return wrapper_auth

    if _func is None:
        return decor_auth
    else:
        return decor_auth(_func)


def jinja2_filter_datefmt(dt, fmt=None):
    if not fmt:
        fmt = TS_FORMAT
    if isinstance(dt, str):
        dt = DT.strptime(dt, fmt)
    nat_dt = dt.replace(tzinfo=None)
    to_fmt = '%d-%m-%Y@%I:%M:%S %p'
    return nat_dt.strftime(to_fmt)

def parse_number(sval):
    p = r"^[-+]?\d+[\./]?\d*$"
    sval = sval.strip()
    if re.search(p, sval):
        n = eval(sval)
        if isinstance(n, float):
            return round(n, 2)
        else:
            return n
    return None

def now_str():
    return DT.now().strftime(TS_FORMAT)

def get_rand_str(size=10):
    """Makes a random string from ASCII upper case letters and digits.
    Args:
        size (int, optional): Length desired. Defaults to 10.

    Returns:
        str: Random alphanumeric ASCII string.
    """
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=size))


def update_model_skip_unknown(mod, form_data):
    """[summary]

    Arguments:
        mod {Model} -- peewee Model class instance
        form_data {dict} -- dict from JSON object instance
    """
    update_model_from_dict(mod, form_data, ignore_unknown=True)


def init_db_connection():
    try:
        if db.is_closed():
            # DB connection params are configured in config.json
            db.init(current_app.config['db_name'], **current_app.config['db_args'])
            db.connect()
    except Exception as ex:
        logging.exception("Failed to connect to DB.")


def close_db_connection(http_resp):
    try:
        if not db.is_closed():
            db.close()
    except Exception as ex:
        logging.exception("Failed to close DB connection.")
    return http_resp


def fill_template(templ_dir:str, templ_name:str, data_dict:dict) -> str:
    """Loads a Jinja templare from local file system and renders the supplied
    data in the template.

    Args:
        templ_dir (str): Path of the templates folder.
        templ_name (str): Name of the template file.
        data_dict (dict): Data to use to populate the template.

    Returns:
        str: Populated template.
    """
    env = Environment(loader=FileSystemLoader(templ_dir))
    tpl = env.get_template(templ_name)
    return tpl.render(data_dict)


def this_user_name_login_id():
    if "user" in session:
        u = session['user']
        return f"{u["first_name"]} { u["last_name"]} ({u["login_id"]})"
    else:
        logging.warning("No authenticated user in session!")

def app_config(key: str, default_value: Optional[Any] = None) -> Any:
    return current_app.config.get(key, default_value)