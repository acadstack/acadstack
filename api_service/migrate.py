"""Brings the database schema up to date and seeds the first user.

The numbered SQL files in ``migrations/`` are applied in order, once each; the
applied ones are recorded in the ``schema_migrations`` table. To change the
schema, add a new file with the next number; never edit an applied one.

When the database has no users, a superuser is created and its credentials are
printed, so that one can log in and configure the application.

The app runs this when it starts. To run it by hand, from ``api_service/``:
    python migrate.py config.json
"""

import argparse
import json
import re
import secrets
from pathlib import Path

import common as C
import models as M

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
ADMIN_LOGIN = "admin"

# Postgres advisory lock key, so that two runs never apply the same file.
_LOCK_KEY = 530001


def _migration_files() -> dict[int, Path]:
    files = {}
    for f in MIGRATIONS_DIR.glob("*.sql"):
        m = re.match(r"(\d+)_", f.name)
        if not m:
            raise ValueError(f"Migration file name must start with a number: {f.name}")
        version = int(m.group(1))
        if version in files:
            raise ValueError(f"Two migration files numbered {version}: {files[version].name}, {f.name}")
        files[version] = f
    return dict(sorted(files.items()))


def _apply_migrations() -> list[str]:
    M.db.execute_sql("""CREATE TABLE IF NOT EXISTS public.schema_migrations (
                            version integer PRIMARY KEY,
                            name text NOT NULL,
                            applied_at timestamptz NOT NULL DEFAULT now())""")
    done = {row[0] for row in M.db.execute_sql("SELECT version FROM public.schema_migrations")}
    applied = []
    for version, f in _migration_files().items():
        if version in done:
            continue
        # The file and its record commit together, or not at all.
        with M.db.atomic():
            M.db.cursor().execute(f.read_text())
            M.db.execute_sql("INSERT INTO public.schema_migrations (version, name) VALUES (%s, %s)",
                             (version, f.name))
        applied.append(f.name)
    return applied


def _seed_superuser() -> str | None:
    """Creates the first user, a superuser, if there are no users yet.
    Returns its password, or None if nothing was created."""
    if M.User.select().exists():
        return None
    password = secrets.token_urlsafe(12)
    with M.db.atomic():
        person = M.Person.create(org_id=ADMIN_LOGIN, dept_name="ACA")
        M.User.create(login_id=ADMIN_LOGIN, role="SUP", email="admin@localhost",
                      first_name="System", last_name="Administrator",
                      password_hashed=C.hash_password(password), person=person)
    print("=" * 60)
    print(f"Created the superuser.  Login: {ADMIN_LOGIN}  Password: {password}")
    print("Log in, change this password and set the email address.")
    print("=" * 60, flush=True)
    return password


def migrate() -> list[str]:
    """Applies the pending migrations, then seeds the first user.
    ``M.db`` must be initialised. Returns the names of the applied files."""
    with M.db.connection_context():
        M.db.execute_sql("SELECT pg_advisory_lock(%s)", (_LOCK_KEY,))
        try:
            applied = _apply_migrations()
            _seed_superuser()
        finally:
            M.db.execute_sql("SELECT pg_advisory_unlock(%s)", (_LOCK_KEY,))
    return applied


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("cfg_file_path", type=str, help="Configuration file path.")
    args = parser.parse_args()
    with open(args.cfg_file_path, "r") as cfg_file:
        cfg = json.load(cfg_file)
    M.db.init(cfg["db_name"], **cfg["db_args"])
    applied = migrate()
    print(f"Applied {len(applied)} migration(s): {', '.join(applied) or 'none pending'}")
