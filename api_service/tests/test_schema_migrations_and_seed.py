"""Tests for the Phase 1 migration runner (schema_migrations.py) and
default-data seeder (default_seed_data.py).

Both modules are pure DB-side tooling with no route/RBAC surface, so
these tests drive them directly against the real test database (via the
`db` fixture from conftest.py) rather than through HTTP.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import models as DB  # noqa: E402
from default_seed_data import run_seed_defaults  # noqa: E402
from schema_migrations import run_pending_migrations  # noqa: E402


# ===================== default_seed_data =====================

def test_seed_defaults_inserts_only_missing_rows(db):
    rows = [
        {"group": "test_grp", "name": "k1", "is_json": False, "value_text": "v1"},
        {"group": "test_grp", "name": "k2", "is_json": False, "value_text": "v2"},
    ]

    counts = run_seed_defaults([(DB.SystemSetting, rows)])
    assert counts == {"SystemSetting": 2}
    assert DB.SystemSetting.select().where(
        DB.SystemSetting.group == "test_grp").count() == 2

    # Re-running with an extra new row: only the new one should insert.
    rows2 = rows + [
        {"group": "test_grp", "name": "k3", "is_json": False, "value_text": "v3"},
    ]
    counts2 = run_seed_defaults([(DB.SystemSetting, rows2)])
    assert counts2 == {"SystemSetting": 1}
    assert DB.SystemSetting.select().where(
        DB.SystemSetting.group == "test_grp").count() == 3


def test_seed_defaults_never_overwrites_a_customized_value(db):
    DB.SystemSetting.create(group="test_grp", name="k1", is_json=False,
                             value_text="customized_by_institution")

    counts = run_seed_defaults([(DB.SystemSetting, [
        {"group": "test_grp", "name": "k1", "is_json": False,
         "value_text": "seeder_default"},
    ])])

    # Already present -> zero rows inserted, and left untouched.
    assert counts == {"SystemSetting": 0}
    row = DB.SystemSetting.get(DB.SystemSetting.group == "test_grp",
                                DB.SystemSetting.name == "k1")
    assert row.value_text == "customized_by_institution"


def test_seed_defaults_empty_specs_is_a_noop(db):
    assert run_seed_defaults([]) == {}


def test_seed_defaults_seeds_vocab_rows(db):
    # Phase 3 populates SEED_SPECS with one SystemSetting row per
    # controlled vocabulary (see vocab_defaults.ALL); a fresh DB should
    # get all of them on first run, and none again on a second run.
    import vocab_defaults as VD

    counts = run_seed_defaults()
    assert counts == {"SystemSetting": len(VD.ALL)}
    assert run_seed_defaults() == {"SystemSetting": 0}

    row = DB.SystemSetting.get(DB.SystemSetting.group == "vocab",
                                DB.SystemSetting.name == "degrees")
    assert row.is_json is True
    assert {d["code"] for d in row.value_json} == \
        {d["code"] for d in VD.DEGREES}


# ===================== schema_migrations =====================

def test_run_pending_migrations_applies_once_in_filename_order(db, tmp_path):
    (tmp_path / "0002_second.sql").write_text(
        "ALTER TABLE systemsetting ADD COLUMN IF NOT EXISTS mig_test_col TEXT;"
    )
    (tmp_path / "0001_first.sql").write_text(
        "-- comment-only file must not error (regression: psycopg2 raises\n"
        "-- 'can't execute an empty query' if the whole file is a comment)\n"
    )

    applied = run_pending_migrations(tmp_path)
    assert applied == ["0001_first.sql", "0002_second.sql"]

    versions = {r.version for r in DB.SchemaMigration.select()}
    assert versions == {"0001_first.sql", "0002_second.sql"}

    cols = [c.name for c in DB.db.get_columns("systemsetting")]
    assert "mig_test_col" in cols


def test_run_pending_migrations_skips_already_applied_files(db, tmp_path):
    mig = tmp_path / "0001_add_col.sql"
    mig.write_text(
        "ALTER TABLE systemsetting ADD COLUMN IF NOT EXISTS mig_test_col2 TEXT;"
    )

    first = run_pending_migrations(tmp_path)
    assert first == ["0001_add_col.sql"]

    # Second run against the same directory: nothing pending.
    second = run_pending_migrations(tmp_path)
    assert second == []
    assert DB.SchemaMigration.select().where(
        DB.SchemaMigration.version == "0001_add_col.sql").count() == 1


def test_migration_is_safe_to_replay_against_an_already_current_schema(db, tmp_path):
    """Simulates a fresh install: create_schema() already built the column
    from models.py, so a guarded (IF NOT EXISTS) migration replaying on
    top of it must no-op instead of erroring."""
    DB.db.execute_sql(
        "ALTER TABLE systemsetting ADD COLUMN IF NOT EXISTS mig_test_col3 TEXT;"
    )
    (tmp_path / "0001_add_col.sql").write_text(
        "ALTER TABLE systemsetting ADD COLUMN IF NOT EXISTS mig_test_col3 TEXT;"
    )

    applied = run_pending_migrations(tmp_path)
    assert applied == ["0001_add_col.sql"]  # recorded, did not error


def test_run_pending_migrations_with_no_files_is_a_noop(db, tmp_path):
    assert run_pending_migrations(tmp_path) == []


def test_migration_containing_a_percent_sign_is_applied_verbatim(db, tmp_path):
    """A migration may contain a literal percent sign -- a LIKE pattern,
    a to_char() format, a plpgsql RAISE ... % substitution -- without it
    being misread as a parameter placeholder (see _execute_script's
    docstring in schema_migrations.py). 0003 is such a migration."""
    (tmp_path / "0001_percent.sql").write_text(
        "CREATE OR REPLACE FUNCTION mig_pct_test(x text) RETURNS text\n"
        "LANGUAGE plpgsql IMMUTABLE AS $fn$\n"
        "BEGIN\n"
        "    IF x LIKE 'a%' THEN\n"
        "        RAISE EXCEPTION 'got %', x;\n"
        "    END IF;\n"
        "    RETURN x;\n"
        "END;\n"
        "$fn$;\n"
    )

    assert run_pending_migrations(tmp_path) == ["0001_percent.sql"]

    cur = DB.db.execute_sql("SELECT mig_pct_test(%s)", ("bee",))
    assert cur.fetchone()[0] == "bee"


def test_the_real_migrations_replay_cleanly(db):
    """migrations/README.md requires every file to be safe to run against
    a schema create_schema() already built in its current shape. The `db`
    fixture truncates schema_migrations, so this re-applies the whole real
    directory on top of the schema conftest already migrated -- which is
    exactly that scenario, and the only check that 0003's functions,
    CHECK constraints and triggers are genuinely idempotent."""
    from schema_migrations import MIGRATIONS_DIR

    expected = sorted(p.name for p in MIGRATIONS_DIR.glob("*.sql"))
    assert run_pending_migrations() == expected

    # And the immutability machinery still works afterwards.
    DB.db.execute_sql(
        "INSERT INTO closedacademicsession (acad_session, session_ord, "
        "closed_ts, is_deleted, txn_no, ins_ts, upd_ts) "
        "VALUES ('2020-II', 20205, now(), false, 1, now(), now())")
    with pytest.raises(Exception, match="append-only"):
        with DB.db.atomic():
            DB.db.execute_sql("DELETE FROM closedacademicsession")
