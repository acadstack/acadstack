"""Minimal versioned schema-migration runner.

Why hand-rolled instead of peewee-migrate: this repo has no migration
history to bootstrap from (the schema is currently produced either by
models.py create_schema() or by scripts/initdb/schema_only.sql), and
peewee-migrate's value is mostly its auto-diff/CLI machinery, which we
don't need for what will mostly be a steady trickle of ALTER TABLE +
seed-data changes. A plain "run any *.sql file we haven't recorded yet,
in filename order, inside a transaction" runner is a fraction of the
code and has no new dependency to track.

Each file under migrations/ is applied at most once. Applied files are
recorded by filename in the schema_migrations table (see models.py), so
re-running this on a deployment that already has a change applied is a
no-op. Migration SQL should still be written defensively (IF NOT EXISTS /
IF EXISTS guards) so that a fresh install -- where create_schema() already
built the current schema from models.py -- can replay every migration
file without erroring; see migrations/README.md.

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__status__ = "Development"
"""

import logging
import re
from pathlib import Path

import models as M

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"

# Matches a SQL line comment, for detecting migration files that contain
# no executable statement (e.g. a comment-only baseline marker) -- psycopg2
# raises "can't execute an empty query" if asked to run one of those.
_LINE_COMMENT_RE = re.compile(r"--[^\n]*")


def _has_executable_sql(sql_text: str) -> bool:
    return bool(_LINE_COMMENT_RE.sub("", sql_text).strip())


def _execute_script(sql_text: str) -> None:
    """Runs a whole migration file as one script.

    Deliberately NOT M.db.execute_sql(): peewee passes `params or ()` down
    to the driver, and psycopg2 treats '%' as a placeholder introducer
    whenever a parameter sequence is present, even an empty one -- so a
    migration is free to contain a literal percent sign (a LIKE pattern,
    a to_char() format, a plpgsql RAISE ... % substitution) only if no
    parameter argument is passed at all. That is what this function does:
    it skips client-side interpolation entirely, which is what a DDL
    script wants.
    """
    cursor = M.db.cursor()
    cursor.execute(sql_text)


def run_pending_migrations(migrations_dir: Path = MIGRATIONS_DIR) -> list:
    """Applies every *.sql file under migrations_dir that is not yet
    recorded in schema_migrations, in filename order. Returns the list of
    filenames that were applied (empty if nothing was pending).

    Assumes the caller already has an open connection on models.db.
    """
    M.db.create_tables([M.SchemaMigration], safe=True)

    applied = {row.version for row in
               M.SchemaMigration.select(M.SchemaMigration.version)}

    pending = sorted(
        p for p in migrations_dir.glob("*.sql") if p.name not in applied
    )

    applied_now = []
    for path in pending:
        logging.info(f"Applying schema migration: {path.name}")
        sql_text = path.read_text()
        with M.db.atomic():
            if _has_executable_sql(sql_text):
                _execute_script(sql_text)
            M.SchemaMigration.create(version=path.name)
        logging.info(f"Applied schema migration: {path.name}")
        applied_now.append(path.name)

    if not applied_now:
        logging.info("No pending schema migrations.")

    return applied_now
