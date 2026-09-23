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
    # controlled vocabulary (see vocab_defaults.ALL); Phase 8 adds one more
    # per named permission (see permissions.py). A fresh DB should get all
    # of them on first run, and none again on a second run.
    import permissions as PERM
    import settings_store as ST
    import vocab_defaults as VD

    expected_rows = len(VD.ALL) + len(ST.declared_groups()[PERM.GROUP].specs)

    from domain import milestones as MS
    from domain import workflow as WF

    counts = run_seed_defaults()
    # Plus the one baseline grading ruleset, which makes the versioned
    # policy store the runtime source of truth instead of the in-code
    # fallback (see default_seed_data.seed_grading_policy); the milestone
    # sequence; and one baseline table per approval workflow.
    assert counts == {"SystemSetting": expected_rows, "PolicyVersion": 1,
                      "MilestoneDefinition": len(MS.BASELINE),
                      "WorkflowDefinition": len(WF.names())}
    assert run_seed_defaults() == {"SystemSetting": 0,
                                   "MilestoneDefinition": 0}

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
    # The ordinal comes from acad_session, not a literal: migration 0004
    # renumbered the scale, and a hardcoded value here would only be
    # testing that someone remembered to update this line.
    import acad_session as AS
    DB.db.execute_sql(
        "INSERT INTO closedacademicsession (acad_session, session_ord, "
        "closed_ts, is_deleted, txn_no, ins_ts, upd_ts) "
        "VALUES ('2020-II', %s, now(), false, 1, now(), now())",
        (AS.ordinal("2020-II"),))
    with pytest.raises(Exception, match="append-only"):
        with DB.db.atomic():
            DB.db.execute_sql("DELETE FROM closedacademicsession")


# ===================== 0004: renumbering existing ordinals =====================

OLD_SCHEME_ORDINAL_FN = """
CREATE OR REPLACE FUNCTION acadstack_session_ordinal(sess text)
RETURNS integer LANGUAGE plpgsql IMMUTABLE STRICT AS $fn$
BEGIN
    IF sess !~ '^[0-9]{4}-(T[1-4]|II|I|S)$' THEN
        RAISE EXCEPTION 'Malformed academic session %', sess
            USING ERRCODE = '22023';
    END IF;
    RETURN substring(sess from 1 for 4)::integer * 10
         + CASE substring(sess from 6)
               WHEN 'T1' THEN 0 WHEN 'T2' THEN 1 WHEN 'T3' THEN 2
               WHEN 'T4' THEN 3 WHEN 'I' THEN 4 WHEN 'II' THEN 5
               WHEN 'S' THEN 6 END;
END;
$fn$;
"""


def _revert_to_pre_0004_state():
    """Puts the schema back the way migration 0003 left it: the rank-based
    ordinal function, and no CHECK constraints tying columns to it."""
    from schema_migrations import _execute_script
    _execute_script("""
        ALTER TABLE policyversion
            DROP CONSTRAINT IF EXISTS policyversion_ord_matches_session;
        ALTER TABLE closedacademicsession
            DROP CONSTRAINT IF EXISTS closedacadsession_ord_matches_session;
    """ + OLD_SCHEME_ORDINAL_FN)


def _apply_0004():
    from schema_migrations import MIGRATIONS_DIR, _execute_script
    path = MIGRATIONS_DIR / "0004_session_type_month_ordinals.sql"
    _execute_script(path.read_text())


def test_0004_renumbers_rows_written_under_the_old_rank_scheme(db):
    """The renumbering is the whole point of 0004, and nothing else
    exercises it: replaying the migrations on an already-current schema
    finds nothing to change.

    Simulates a real upgrade -- policy rows and a CLOSED session stored
    with rank-based ordinals -- and checks 0004 moves them onto the month
    scale. The closed row matters most: 0003's triggers exist to forbid
    exactly the UPDATE that has to happen here.
    """
    import acad_session as AS

    _revert_to_pre_0004_state()

    # Policy versions first: 0003's insert guard rightly refuses to add a
    # version effective from a session that is already closed, so an
    # upgrade scenario has to be built in the order it really happened.
    for sess, old_ord in (("2000-T1", 20000), ("2021-I", 20214),
                          ("2021-II", 20215)):
        DB.db.execute_sql(
            "INSERT INTO policyversion (policy_group, effective_from_session, "
            "effective_from_ord, payload, is_deleted, txn_no, ins_ts, upd_ts) "
            "VALUES ('grading', %s, %s, '{}', false, 1, now(), now())",
            (sess, old_ord))
    DB.db.execute_sql(
        "INSERT INTO closedacademicsession (acad_session, session_ord, "
        "closed_ts, is_deleted, txn_no, ins_ts, upd_ts) "
        "VALUES ('2020-II', 20205, now(), false, 1, now(), now())")

    # Every policy row is now sealed (2020-II closed at rank ordinal 20205
    # is at or after all three), so the triggers are genuinely in the way
    # of the UPDATE the migration has to perform.
    cur = DB.db.execute_sql(
        "SELECT effective_from_ord FROM policyversion "
        "WHERE effective_from_session = '2000-T1'")
    assert cur.fetchone()[0] == 20000
    with pytest.raises(Exception, match="closed"):
        with DB.db.atomic():
            DB.db.execute_sql("UPDATE policyversion SET effective_from_ord = 7")

    _apply_0004()

    cur = DB.db.execute_sql(
        "SELECT effective_from_session, effective_from_ord FROM policyversion "
        "ORDER BY effective_from_ord")
    assert cur.fetchall() == [
        ("2000-T1", AS.ordinal("2000-T1")),
        ("2021-I", AS.ordinal("2021-I")),
        ("2021-II", AS.ordinal("2021-II")),
    ]

    cur = DB.db.execute_sql(
        "SELECT acad_session, session_ord FROM closedacademicsession")
    assert cur.fetchall() == [("2020-II", AS.ordinal("2020-II"))]


def test_0004_leaves_the_immutability_guards_armed_afterwards(db):
    """The triggers are suspended mid-migration; a migration that forgot to
    re-enable them would leave sealed history writable forever."""
    _revert_to_pre_0004_state()
    DB.db.execute_sql(
        "INSERT INTO closedacademicsession (acad_session, session_ord, "
        "closed_ts, is_deleted, txn_no, ins_ts, upd_ts) "
        "VALUES ('2020-II', 20205, now(), false, 1, now(), now())")

    _apply_0004()

    # The append-only trigger is armed again.
    with pytest.raises(Exception, match="append-only"):
        with DB.db.atomic():
            DB.db.execute_sql("DELETE FROM closedacademicsession")

    # And both CHECK constraints exist again. Asserted against the catalog
    # rather than by provoking a violation, because on these two tables a
    # trigger would fire first and mask which guard actually caught it.
    cur = DB.db.execute_sql(
        "SELECT conname FROM pg_constraint WHERE conname IN "
        "('policyversion_ord_matches_session', "
        " 'closedacadsession_ord_matches_session') ORDER BY conname")
    assert [r[0] for r in cur.fetchall()] == [
        "closedacadsession_ord_matches_session",
        "policyversion_ord_matches_session",
    ]

    # The constraint really does police the column: a fresh row whose
    # ordinal disagrees with its session string is rejected. The bogus
    # ordinal has to sit ABOVE the seal line, or the insert guard fires
    # first and we would be asserting the wrong guard caught it.
    with pytest.raises(Exception, match="check constraint"):
        with DB.db.atomic():
            DB.db.execute_sql(
                "INSERT INTO policyversion (policy_group, "
                "effective_from_session, effective_from_ord, payload, "
                "is_deleted, txn_no, ins_ts, upd_ts) VALUES "
                "('grading', '2030-I', 99999, '{}', false, 1, now(), now())")


def test_0004_refuses_to_renumber_when_two_versions_would_collide(db):
    """Concurrent sessions share an instant on the new scale, so two
    versions of one group at 2021-I and 2021-T1 cannot both survive. There
    is no defensible automatic answer, so the migration stops."""
    _revert_to_pre_0004_state()
    for sess, old_ord in (("2021-I", 20214), ("2021-T1", 20210)):
        DB.db.execute_sql(
            "INSERT INTO policyversion (policy_group, effective_from_session, "
            "effective_from_ord, payload, is_deleted, txn_no, ins_ts, upd_ts) "
            "VALUES ('grading', %s, %s, '{}', false, 1, now(), now())",
            (sess, old_ord))

    with pytest.raises(Exception, match="run concurrently"):
        with DB.db.atomic():
            _apply_0004()
