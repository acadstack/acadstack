"""This module contains commonly used functions in this app.

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__version__ = "0.1"
__status__ = "Development"
"""

import logging, os, re, secrets, string, threading, toml
from typing import Any, Callable, Optional
from datetime import datetime as DT
from datetime import date
from functools import wraps
from pathlib import Path
from quart import current_app
from quart import (jsonify, session)

from jinja2 import Environment, FileSystemLoader
from playhouse.shortcuts import update_model_from_dict

from json import JSONEncoder

from models import db
from email_client import Emailer


def db_config_from_env(config=None):
    """DB connection config, preferring the POSTGRES_*/DB_HOST/DB_PORT env
    vars (the same ones the running server reads -- see
    acadstack_app.py's _load_config_from_env()) over a config.json file's
    db_name/db_args.

    config.json and the env vars are two separate config surfaces (see
    README.md) that must otherwise be hand-kept in sync; a stale db_args
    in a locally-edited config.json (e.g. "host": "localhost" instead of
    the Docker service name "db") is a recurring source of connection
    errors in demo_data.py/migrate.py. Env vars winning here means those
    scripts connect the same way the server does whenever the env is
    sourced (docker-compose's env_file, or `source app_env_vars.env`),
    with config.json's db_name/db_args only used as a fallback for
    whichever of these aren't set.

    Returns:
        (db_name, db_args) tuple, matching the shape of
        config["db_name"]/config["db_args"].
    """
    config = config or {}
    db_args = dict(config.get("db_args", {}))
    db_args["user"] = os.environ.get("POSTGRES_USER", db_args.get("user"))
    db_args["password"] = os.environ.get("POSTGRES_PASSWORD",
                                         db_args.get("password"))
    db_args["host"] = os.environ.get("DB_HOST", db_args.get("host",
                                                            "localhost"))
    db_args["port"] = os.environ.get("DB_PORT", db_args.get("port", 5432))
    db_name = os.environ.get("POSTGRES_DB", config.get("db_name"))
    return db_name, db_args


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
# Order is load-bearing: CourseSlotTiming.week_day stores the INDEX into
# this list, not a code, so it must stay a fixed, ordered code constant
# rather than move to an admin-editable vocab (which permits reordering).
WEEK_DAY_NAMES = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']

# The grade vocabulary (formerly VALID_GRADES/VALID_AUDIT_GRADES here) now
# lives in vocab_defaults.GRADES; read it via
# settings_store.valid_grade_codes()/valid_audit_grade_codes() rather than
# importing constants from this module. Not re-exported here to avoid a
# settings_store <-> common import cycle (settings_store already imports
# AcadStackException from this module).
#
# The academic-calendar event-code vocabulary (formerly ACAD_EVENT_CODES
# here, and never actually referenced anywhere) now lives in
# vocab_defaults.ACAD_EVENT_CODES for the same reason; read it via
# settings_store.vocab_codes("acad_event_codes").

class AcadStackException(Exception):
    """
    This is application specific exception thrown to the clients.
    """
    pass


def current_dt_str():
    return DT.now().strftime("%Y-%m-%d")

# sql_statements.toml is a ~1000-line static file read by nearly every
# query in the app. Parsing it per call was costing a full TOML parse on
# every DB access, so it is parsed once per process and held here. The
# path is resolved relative to this module rather than the working
# directory, which is what the rest of the app assumes but does not
# guarantee (background jobs, scripts).
_SQL_STATEMENTS_PATH = Path(__file__).resolve().parent / "sql_statements.toml"
_sql_statements = None
_sql_statements_lock = threading.Lock()


def sql_statements() -> dict:
    """Returns the parsed sql_statements.toml, loading it on first use."""
    global _sql_statements
    if _sql_statements is None:
        with _sql_statements_lock:
            # Re-checked under the lock: two threads can race the check
            # above, and the loser must not re-parse the file.
            if _sql_statements is None:
                _sql_statements = toml.load(_SQL_STATEMENTS_PATH)
                logging.info(f"Loaded {len(_sql_statements)} SQL statement(s) "
                             f"from {_SQL_STATEMENTS_PATH}")
    return _sql_statements


def reload_sql_statements() -> dict:
    """Forces a re-read of sql_statements.toml. For tests and for editing
    queries without restarting a dev server."""
    global _sql_statements
    with _sql_statements_lock:
        _sql_statements = None
    return sql_statements()


def sql_by_id(sid):
    return sql_statements()[sid]

def add_user_to_session():
    if "user" in session:
        logging.info("User is already in session: {0}".format(session["user"]))
        return dict(user=session["user"])
    else:
        logging.info("User not in session!")
        return dict()


def rbac(_func:Callable=None, *, permissions=None):
    """Decorator that can be applied to a function to perform the
    permission based access checks for the current user if available in
    the session.
    If no authenticated user available in the session, the decorated
    function wll not be called and an error JSON message will be returned.
    If the logged in user's role holds at least one of the permissions
    named in the list, then the decorated function is called. If the
    permissions list is not supplied then only the presence of the
    authenticated user in the session is checked before allowing the
    decorated function invocation.
    Args:
        _func (Callable, optional): The function being decorated. Defaults to None.
        permissions (list[str], optional): Named permissions, any one of
            which allows the call. See permissions.py. Defaults to None.
    """
    def decor_auth(func):
        @wraps(func)
        async def wrapper_auth(*args, **kwargs):
            if "user" not in session:
                msg = "Login required to access this operation."
                logging.warning(msg)
                return jsonify({"status": "ERROR", "body": msg})

            user_role = session["user"]["role"]
            if permissions:
                import permissions as PERM
                if not any(PERM.role_has_permission(user_role, p)
                           for p in permissions):
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
    """Parses an integer, decimal or 'a/b' fraction string. Returns an int
    for integers, a float rounded to 2 places otherwise, or None if
    ``sval`` is not one of those forms."""
    sval = sval.strip()
    if not re.fullmatch(r"[-+]?\d+[\./]?\d*", sval):
        return None
    try:
        if "/" in sval:
            num, den = sval.split("/")
            return round(int(num) / int(den), 2)
        if "." in sval:
            return round(float(sval), 2)
        return int(sval)
    except (ValueError, ZeroDivisionError):
        return None

def now_str():
    return DT.now().strftime(TS_FORMAT)


def compute_course_ltp(ltp_str):
    """(Re)computes a course's S (session/teaching hours) and C (credits)
    from the L/T/P components of an 'L-T-P[-S-C]' string, using this
    institution's credit formula: S = 2L - T + 0.5P, C = L + 0.5P.

    This is the ONLY place that formula is evaluated. Every call site that
    creates or edits a Course (the single-course save form, the CSV bulk
    importer, demo data) must route through this so Course.s_hours/credits
    are always server-computed from L/T/P, never trusted from the client
    or re-derived by parsing string positions elsewhere (SQL used to do
    both, which is the duplication this replaced).

    Returns (full_ltp_str, s, c), where full_ltp_str is 'L-T-P-S-C' with
    freshly computed S/C (replacing any S/C the input string already
    had). Returns None if L/T/P cannot be parsed as numbers, so the
    caller decides how to handle bad input.
    """
    if not ltp_str:
        return None
    parts = ltp_str.split("-")
    if len(parts) < 3:
        return None
    l, t, p = parse_number(parts[0]), parse_number(parts[1]), parse_number(parts[2])
    if l is None or t is None or p is None:
        return None
    s = round(2 * l - t + 0.5 * p, 2)
    c = round(l + 0.5 * p, 2)
    return f"{l}-{t}-{p}-{s}-{c}", s, c


def apply_computed_course_credits(course):
    """Sets course.ltp/s_hours/credits from course.ltp's current L/T/P via
    compute_course_ltp(). A no-op if ltp isn't at least 'L-T-P'."""
    result = compute_course_ltp(course.ltp)
    if result:
        course.ltp, course.s_hours, course.credits = result

def get_rand_str(size=10):
    """Makes a cryptographically secure random string from ASCII upper case
    letters and digits.
    Args:
        size (int, optional): Length desired. Defaults to 10.

    Returns:
        str: Random alphanumeric ASCII string.
    """
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(size))


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

# course_code_for_pg() moved to domain/course.py: it now reads the PG
# threshold digit from settings_store, which this module cannot import
# (settings_store already imports AcadStackException from here, so the
# reverse import would cycle).
