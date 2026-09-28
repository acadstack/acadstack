import pytest

import migrate
import models as M

# The versions of the real migration files, all applied by the test setup.
APPLIED = sorted(migrate._migration_files())
NEXT = APPLIED[-1] + 1


def _versions():
    return [r[0] for r in M.db.execute_sql("SELECT version FROM public.schema_migrations ORDER BY 1")]


def test_every_model_column_exists_in_migrated_schema(db):
    """Catches a model change that shipped without a migration."""
    rows = db.execute_sql("SELECT table_name, column_name FROM information_schema.columns "
                          "WHERE table_schema = 'public'")
    columns = {(t, c) for t, c in rows}
    missing = [(m._meta.table_name, f.column_name)
               for m in M.BaseModel.__subclasses__() for f in m._meta.sorted_fields
               if (m._meta.table_name, f.column_name) not in columns]
    assert missing == []


def test_rerun_applies_nothing(db):
    assert migrate.migrate() == []
    assert _versions() == APPLIED


async def test_empty_database_gets_superuser_who_can_log_in(client, auth, capsys):
    migrate.migrate()
    admin = M.User.get(M.User.login_id == migrate.ADMIN_LOGIN)
    assert admin.role == "SUP"
    password = capsys.readouterr().out.split("Password: ")[1].split()[0]

    res = await auth.login(migrate.ADMIN_LOGIN, password)
    assert (await res.get_json())["status"] == "OK"


def test_superuser_not_seeded_when_users_exist(db):
    migrate.migrate()
    migrate.migrate()
    assert M.User.select().count() == 1


@pytest.fixture
def migrations_dir(db, tmp_path, monkeypatch):
    monkeypatch.setattr(migrate, "MIGRATIONS_DIR", tmp_path)
    yield tmp_path
    db.execute_sql(f"DELETE FROM public.schema_migrations WHERE version > {APPLIED[-1]}")
    db.execute_sql("DROP TABLE IF EXISTS public.mig_probe")


def test_pending_files_applied_in_order_and_failed_file_rolled_back(migrations_dir):
    (migrations_dir / "0001_baseline.sql").write_text("SELECT 1/0;")  # already applied
    (migrations_dir / f"{NEXT:04d}_probe.sql").write_text("CREATE TABLE public.mig_probe (n int);")
    (migrations_dir / f"{NEXT + 1:04d}_insert.sql").write_text("INSERT INTO public.mig_probe VALUES (3);")
    (migrations_dir / f"{NEXT + 2:04d}_broken.sql").write_text(
        "INSERT INTO public.mig_probe VALUES (4); SELECT * FROM no_such_table;")

    with pytest.raises(Exception, match="no_such_table"):
        migrate.migrate()

    assert _versions() == APPLIED + [NEXT, NEXT + 1]
    assert [r[0] for r in M.db.execute_sql("SELECT n FROM public.mig_probe")] == [3]


@pytest.mark.parametrize("names, error", [
    (["0002_a.sql", "2_b.sql"], "Two migration files numbered 2"),
    (["probe.sql"], "must start with a number"),
])
def test_bad_file_names_rejected(migrations_dir, names, error):
    for name in names:
        (migrations_dir / name).write_text("SELECT 1;")
    with pytest.raises(ValueError, match=error):
        migrate.migrate()
    assert _versions() == APPLIED
