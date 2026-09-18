"""Explicit, non-destructive schema-migration/seed command.

Applies pending schema migrations and inserts missing default rows
against an EXISTING database, without touching any data -- unlike
demo_data.py's setup_prod_db()/setup_db_with_demo_data(), which drop and
recreate the whole database. Use this to upgrade an existing deployment.

Usage (same calling convention as demo_data.py):

    python migrate.py config.json

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__status__ = "Development"
"""

import argparse
import json

import models as M
from default_seed_data import run_seed_defaults
from schema_migrations import run_pending_migrations


def migrate(config):
    M.db.init(config["db_name"], **config["db_args"])
    M.db.connect()
    try:
        M.create_schema()
        applied = run_pending_migrations()
        if applied:
            print(f"Applied {len(applied)} pending migration(s): {applied}")
        else:
            print("No pending schema migrations.")

        inserted = run_seed_defaults()
        if inserted:
            print(f"Inserted missing default rows: {inserted}")
        else:
            print("No missing default rows to insert.")
    finally:
        M.db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("cfg_file_path", type=str,
                        help="Configuration file path.")
    args = parser.parse_args()
    with open(args.cfg_file_path, "r") as cfg_file:
        cfg = json.load(cfg_file)
    migrate(cfg)
