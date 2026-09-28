"""This module contains commonly used functions in this app.

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__version__ = "0.1"
__status__ = "Development"
"""

import base64, hashlib, hmac, logging, re, secrets, string, toml
from typing import Any, Optional
from datetime import datetime as DT
from datetime import date
from quart import current_app
from quart import session

from jinja2 import Environment, FileSystemLoader
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
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
_password_hasher = PasswordHasher()

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
                    'SHOW_MIDSEM_FB_S', 'SHOW_ENDSEM_FB_S','RESULT_DECLARATION',
                    # Written only by closing the session (/close_session)
                    'SESSION_CLOSED']

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
        if "/" in sval:
            num, den = sval.split("/")
            n = int(num) / int(den)
        elif "." in sval:
            n = float(sval)
        else:
            n = int(sval)
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
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(size))


def hash_password(plain: str) -> str:
    return _password_hasher.hash(plain)


def _ab64_decode(data: str) -> bytes:
    # passlib's "adapted base64": '.' instead of '+', no padding.
    data = data.replace(".", "+")
    return base64.b64decode(data + "=" * (-len(data) % 4))


def verify_password(plain: str, hashed: str) -> bool:
    """Checks a password against an argon2 hash, or against a
    ``$pbkdf2-sha256$rounds$salt$checksum`` hash written by passlib."""
    if hashed.startswith("$pbkdf2-sha256$"):
        _, _, rounds, salt, checksum = hashed.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"),
                                 _ab64_decode(salt), int(rounds))
        return hmac.compare_digest(dk, _ab64_decode(checksum))
    try:
        return _password_hasher.verify(hashed, plain)
    except (VerificationError, InvalidHashError):
        return False


def password_needs_rehash(hashed: str) -> bool:
    return (not hashed.startswith("$argon2")
            or _password_hasher.check_needs_rehash(hashed))


def update_model_skip_unknown(mod, form_data):
    """[summary]

    Arguments:
        mod {Model} -- peewee Model class instance
        form_data {dict} -- dict from JSON object instance
    """
    update_model_from_dict(mod, form_data, ignore_unknown=True)


# These hooks are async so that they run on the event loop thread, the same
# thread as the views: peewee keeps one connection per thread, and a sync hook
# would open and close connections on executor threads instead, leaving the
# views' connection open (and dead after a DB restart) forever.
async def init_db_connection():
    try:
        db.connect(reuse_if_open=True)
    except Exception as ex:
        logging.exception("Failed to connect to DB.")


async def close_db_connection(exc=None):
    try:
        if not db.is_closed():
            db.close()
    except Exception as ex:
        logging.exception("Failed to close DB connection.")


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