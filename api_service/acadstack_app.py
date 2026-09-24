"""Main entry script for the flask web application.

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__version__ = "0.1"
__status__ = "Development"
"""

import os
from bg_tasks import BgTasks
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import api_auth as apiAU
import api_config as apiCFG
import api_course_enrolment as apiCE
import api_course_offering as apiCO
import api_course as apiCR
import api_dc as apiDC
import api_faces as apiFC
import api_feedback as apiVF
import api_grades as apiVG
import api_policy as apiPL
import api_reports as apiRP
import api_settings as apiST
import api_wflow as apiWF
import api_common as apiVC
import common as C
import models as M
from default_seed_data import run_seed_defaults
from domain import plugins
from schema_migrations import run_pending_migrations
from settings_store import validate_stored_settings

from quart import Quart


# Configure the logging first
rfh_info = RotatingFileHandler("server_acadstack.log", maxBytes=2000000, 
                               backupCount=10)
rfh_info.setLevel(logging.INFO)
rfh_error = RotatingFileHandler("server_acadstack_error.log", maxBytes=1000000, 
                                backupCount=10)
rfh_error.setLevel(logging.WARNING)
logging.basicConfig(level=logging.DEBUG, handlers=[rfh_info, rfh_error],
                    format='%(asctime)s %(levelname)s:: %(message)s',
                    datefmt='%d-%m-%Y@%I:%M:%S %p')


TS_FORMAT = "%Y%m%d_%H%M%S"

def _load_config_from_env():
    return {
        "host": os.environ.get('APP_HOST', "localhost"),
        "port": os.environ.get('APP_PORT'),
        "frec_port": os.environ.get('FREC_PORT'),
        "db_name": os.environ.get('POSTGRES_DB'),
        "db_args": {
            "user": os.environ.get('POSTGRES_USER'),
            "password": os.environ.get('POSTGRES_PASSWORD'),
            "host": os.environ.get('DB_HOST', "localhost"),
            "port": os.environ.get('DB_PORT', 5432),
        },
        "email": {
            "user": os.environ.get('EMAIL_USER'),
            "password": os.environ.get('EMAIL_PASSWORD'),
            "host": os.environ.get('EMAIL_HOST'),
            "port": os.environ.get('EMAIL_PORT'),
            "dryrun": os.environ.get('EMAIL_DRYRUN')
        },
        "oauth_client_id": os.environ.get('OAUTH_CLIENT_ID'),
        "oauth_domain": os.environ.get('OAUTH_DOMAIN'),
        "upload_folder": os.environ.get('UPLOAD_FOLDER', "./acadstack_upload")
    }


def setup_app_state(app):
    app.extensions['tasks'] = {}
    print("Added tasks holder to app extensions.")


def run_startup_db_tasks(cfg):
    """Brings an existing deployment's schema/default-data up to date on
    every app startup: ensures any brand-new tables exist (create-if-not
    -exists, same as demo_data.py), applies any pending versioned
    migrations under migrations/ (see schema_migrations.py), then inserts
    any missing default rows (see default_seed_data.py). All three steps
    are idempotent and never touch data an institution has already
    configured, so this is safe to run on every restart.

    Finally it checks the stored system settings against their declared
    schema (see settings_store.py) and logs anything invalid. That check
    only reports: a value that predates its declaration, or was edited
    directly in the DB, must be visible at boot rather than surfacing
    mid-request, but it is not a reason to refuse to start.
    """
    M.db.init(cfg['db_name'], **cfg['db_args'])
    M.db.connect()
    try:
        M.create_schema()
        applied = run_pending_migrations()
        if applied:
            logging.info(f"Applied {len(applied)} pending schema "
                         f"migration(s): {applied}")
        run_seed_defaults()
        problems = validate_stored_settings()
        if problems:
            logging.warning(f"{len(problems)} stored system setting(s) fail "
                            f"validation; their declared defaults will be "
                            f"used at read time.")
    finally:
        M.db.close()


def create_app(is_testing=False):
    myapp = Quart(__name__, static_folder="./app", static_url_path="/acadstack/")
    myapp.secret_key = C.get_rand_str(size=30)
    myapp.json_encoder = C.JSONEncoderWithDate
    myapp.active_users = {}

    cfg = _load_config_from_env()
    myapp.config.update(cfg)

    # Institution-specific domain overrides, if any are installed. Safe
    # to call when none are: it is a no-op. See domain/plugins.py.
    plugins.load_plugins()

    if not is_testing:
        run_startup_db_tasks(cfg)

    myapp.context_processor(C.add_user_to_session)
    myapp.before_request(C.init_db_connection)
    myapp.after_request(C.close_db_connection)
    myapp.before_request(apiVC.update_active_users)
    myapp.before_serving(lambda: setup_app_state(myapp))

    # Add custom filters
    myapp.add_template_filter(C.jinja2_filter_datefmt, "datefmt")

    logger = logging.getLogger('peewee')
    if "peewee_debug" in myapp.config and myapp.config["peewee_debug"]:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # Initialize uploads folder
    uploads = myapp.config['upload_folder']
    Path(uploads).mkdir(parents=True, exist_ok=True)

    apiVC.vbp.add_url_rule('/', view_func=apiVC.index, methods=['GET'])
    apiVC.vbp.add_url_rule('/auc', view_func=apiVC.get_active_users, methods=['GET'])
    apiVC.vbp.add_url_rule('/get_static_data', view_func=apiVC.get_static_data, methods=['GET'])

    # Attendance related
    apiVC.vbp.add_url_rule('/kface_bulk_add', view_func=apiFC.kface_bulk_add, methods=['POST'])
    apiVC.vbp.add_url_rule('/face_add', view_func=apiFC.kface_add, methods=['POST'])
    apiVC.vbp.add_url_rule('/get_class_photo/<string:file_name>/<int:user_id>',
                       view_func=apiFC.get_class_photo, methods=['GET'])

    # Initialize the routes defines in each module
    apiVF.init_routes(apiVC.vbp)
    apiAU.init_routes(apiVC.vbp)
    apiCE.init_routes(apiVC.vbp)
    apiCO.init_routes(apiVC.vbp)
    apiCR.init_routes(apiVC.vbp)
    apiDC.init_routes(apiVC.vbp)
    apiRP.init_routes(apiVC.vbp)
    apiVF.init_routes(apiVC.vbp)
    apiVG.init_routes(apiVC.vbp)
    apiWF.init_routes(apiVC.vbp)
    apiPL.init_routes(apiVC.vbp)
    apiST.init_routes(apiVC.vbp)
    apiCFG.init_routes(apiVC.vbp)

    # Register the blueprint for the application
    myapp.register_blueprint(apiVC.vbp, url_prefix='/acadstack')

    C.emailer.configure(myapp.config["email"])
    
    # Start the scheduler
    if not is_testing:
        bgt = BgTasks(myapp.config)
        # Courses status is updated every 6 hours
        bgt.add_job(apiCO.schedule_course_status,
            {"id": "CourseStatusUpdateTask",
            "trigger": "interval", "hours": 6
            })
        
        # Every 6hrs check for upcoming events and send alerts
        bgt.add_job(apiDC.schedule_event_alerts,
            {"id": "EventsAlertsTask",
            "trigger": "interval", "hours": 24
            })

        bgt.start()

    myapp.config['EXECUTOR_PROPAGATE_EXCEPTIONS'] = True
    return myapp


# create_app() registers routes on the module-level Blueprint in
# api_common.py, which Quart only allows once per process. The test suite
# needs to control its own single create_app(is_testing=True) call, so it
# sets ACADSTACK_SKIP_APP_INIT before importing this module to skip the
# instantiation below (see tests/conftest.py).
if not os.environ.get("ACADSTACK_SKIP_APP_INIT"):
    app = create_app()