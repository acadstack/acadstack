"""Tests that policy referenced by a closed academic session cannot be
altered -- structurally, not by convention.

The guarantee is enforced at three levels and each is tested here
separately, because each catches something the others cannot:

* ``policy_store.supersede`` -- the curated write path, best message;
* ``models.PolicyVersion.save``/``delete_instance`` -- any ORM caller,
  including code that never heard of policy_store;
* Postgres triggers from migration 0003 -- raw ``db.execute_sql``, which
  this codebase does use, and peewee's bulk ``.update()``/``.delete()``
  queries, which never call ``Model.save()`` at all.

A test that only exercised the service layer would pass just as happily
against a design where immutability was a convention the UI is trusted
to follow, which is exactly what this must not be.
"""
import sys
from pathlib import Path

import peewee
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import acad_session as AS  # noqa: E402
import models as DB  # noqa: E402
import policy_store as PS  # noqa: E402
import settings_store as SS  # noqa: E402


@pytest.fixture
def policy(db):
    saved = dict(PS._REGISTRY)
    PS._REGISTRY.clear()
    PS.invalidate_cache()
    SS.invalidate_cache()
    PS.declare_policy_group("demo", doc="A demo ruleset.")
    yield PS
    PS._REGISTRY.clear()
    PS._REGISTRY.update(saved)
    PS.invalidate_cache()
    SS.invalidate_cache()


def _expect_db_error(match=None):
    """Runs the failing statement inside a transaction so the aborted
    transaction is rolled back and the connection stays usable."""
    return pytest.raises(peewee.DatabaseError, match=match)


# ===================== Session closure =====================

def test_close_session_records_the_seal_line(policy):
    assert policy.last_closed_session() is None
    assert policy.is_session_closed("2020-II") is False

    policy.close_session("2020-II", note="Results declared")

    assert policy.is_session_closed("2020-II") is True
    assert policy.last_closed_session() == "2020-II"
    assert policy.closed_sessions() == ["2020-II"]


def test_close_session_is_idempotent(policy):
    first = policy.close_session("2020-II")
    second = policy.close_session("2020-II")
    assert first.id == second.id
    assert DB.ClosedAcademicSession.select().count() == 1


def test_closed_sessions_are_reported_chronologically(policy):
    for sess in ("2021-I", "2020-S", "2021-T1"):
        policy.close_session(sess)
    # 2021-I and 2021-T1 both begin July 2021, so they tie on ordinal and
    # the suffix breaks the tie -- ordering by session_ord alone would be
    # whatever the DB happened to return.
    assert policy.closed_sessions() == ["2020-S", "2021-I", "2021-T1"]
    assert policy.last_closed_session() == "2021-T1"


def test_the_seal_line_names_every_session_closed_on_it(policy):
    """The seal is a point on the timeline, not one session: closing two
    concurrent sessions seals the same instant, and the message says so."""
    assert policy.seal_line() is None
    policy.close_session("2021-I")
    assert policy.seal_line() == "2021-I"
    policy.close_session("2021-T1")
    assert policy.seal_line() == "2021-I / 2021-T1"


def test_closing_a_session_does_not_close_its_concurrent_twin(policy):
    """is_session_closed is about THIS session, not its instant. Closing
    the semester must not report the quarter as closed -- they are
    different programmes' sessions and are closed separately."""
    policy.close_session("2021-I")
    assert policy.is_session_closed("2021-I") is True
    assert policy.is_session_closed("2021-T1") is False
    # Policy effective from that instant IS sealed, though, for both.
    assert policy.is_sealed("2021-I") is True
    assert policy.is_sealed("2021-T1") is True


def test_a_closed_session_cannot_be_reopened_through_the_orm(policy):
    row = policy.close_session("2020-II")
    with pytest.raises(DB.ImmutablePolicyError):
        row.delete_instance()
    row.note = "changed my mind"
    with pytest.raises(DB.ImmutablePolicyError):
        row.save()


def test_a_closed_session_cannot_be_reopened_through_raw_sql(policy):
    policy.close_session("2020-II")

    with _expect_db_error(match="append-only"):
        with DB.db.atomic():
            DB.db.execute_sql("DELETE FROM closedacademicsession")

    with _expect_db_error(match="append-only"):
        with DB.db.atomic():
            DB.db.execute_sql(
                "UPDATE closedacademicsession SET session_ord = 1")

    assert policy.is_session_closed("2020-II") is True


# ===================== Writes into sealed history =====================

def test_supersede_is_refused_for_a_closed_session(policy):
    policy.supersede("demo", "2019-I", {"v": 1})
    policy.close_session("2020-II")

    with pytest.raises(PS.PolicyImmutableError) as ei:
        policy.supersede("demo", "2020-II", {"v": 99})
    assert "2020-II" in str(ei.value)
    assert "still open" in str(ei.value)


def test_supersede_is_refused_before_a_closed_session(policy):
    policy.close_session("2020-II")
    with pytest.raises(PS.PolicyImmutableError):
        policy.supersede("demo", "2015-I", {"v": 99})
    assert DB.PolicyVersion.select().count() == 0


def test_supersede_is_allowed_after_the_seal_line(policy):
    policy.supersede("demo", "2019-I", {"v": 1})
    policy.close_session("2020-II")

    policy.supersede("demo", "2020-S", {"v": 2})

    assert policy.resolve("demo", "2020-II").payload["v"] == 1
    assert policy.resolve("demo", "2020-S").payload["v"] == 2


def test_policy_error_is_catchable_as_either_hierarchy(policy):
    """PolicyImmutableError subclasses both the storage-layer error and
    AcadStackException, so existing route handlers surface it and
    storage-level callers can catch it too."""
    policy.close_session("2020-II")
    with pytest.raises(DB.ImmutablePolicyError):
        policy.supersede("demo", "2019-I", {"v": 1})
    with pytest.raises(PS.AcadStackException):
        policy.supersede("demo", "2019-I", {"v": 1})


# ===================== Sealed rows are frozen =====================

def test_sealed_version_cannot_be_updated_through_the_orm(policy):
    policy.supersede("demo", "2019-I", {"v": 1})
    policy.close_session("2020-II")

    row = DB.PolicyVersion.get(DB.PolicyVersion.policy_group == "demo")
    assert row.is_sealed is True
    row.payload = {"v": 99}
    with pytest.raises(DB.ImmutablePolicyError) as ei:
        row.save()
    assert "Supersede it" in str(ei.value)


def test_sealed_version_cannot_be_deleted_or_soft_deleted(policy):
    policy.supersede("demo", "2019-I", {"v": 1})
    policy.close_session("2020-II")
    row = DB.PolicyVersion.get(DB.PolicyVersion.policy_group == "demo")

    with pytest.raises(DB.ImmutablePolicyError):
        row.delete_instance()

    row.is_deleted = True
    with pytest.raises(DB.ImmutablePolicyError):
        row.save()

    assert policy.resolve("demo", "2019-I").payload["v"] == 1


def test_sealed_version_cannot_be_updated_through_raw_sql(policy):
    """The guard that actually matters: this codebase runs hand-written
    SQL through db.execute_sql, which never goes near Model.save()."""
    policy.supersede("demo", "2019-I", {"v": 1})
    policy.close_session("2020-II")

    with _expect_db_error(match="sealed"):
        with DB.db.atomic():
            DB.db.execute_sql(
                "UPDATE policyversion SET payload = '{\"v\": 99}'::json")

    with _expect_db_error(match="sealed"):
        with DB.db.atomic():
            DB.db.execute_sql("DELETE FROM policyversion")

    assert policy.resolve("demo", "2019-I").payload["v"] == 1


def test_sealed_version_cannot_be_updated_through_a_bulk_orm_query(policy):
    """peewee's Model.update() builds an UPDATE directly -- Model.save()
    is never called, so only the trigger can stop this one."""
    policy.supersede("demo", "2019-I", {"v": 1})
    policy.close_session("2020-II")

    with _expect_db_error(match="sealed"):
        with DB.db.atomic():
            (DB.PolicyVersion
             .update(payload={"v": 99})
             .where(DB.PolicyVersion.policy_group == "demo").execute())

    with _expect_db_error(match="sealed"):
        with DB.db.atomic():
            DB.PolicyVersion.delete().execute()

    assert policy.resolve("demo", "2019-I").payload["v"] == 1


def test_backdated_insert_is_refused_by_the_orm(policy):
    """Bypassing supersede() and going straight to the model still cannot
    restate a closed session's rules."""
    policy.close_session("2020-II")

    with pytest.raises(DB.ImmutablePolicyError):
        DB.PolicyVersion.create(
            policy_group="demo", effective_from_session="2019-I",
            effective_from_ord=AS.ordinal("2019-I"), payload={"v": 9})


def test_backdated_insert_is_refused_by_the_database(policy):
    """...and bypassing the ORM as well, with a raw INSERT, still cannot.
    This is the trigger's own test: the statement below never touches
    Model.save(), so nothing in Python is in a position to stop it."""
    policy.close_session("2020-II")

    with _expect_db_error(match="already closed"):
        with DB.db.atomic():
            DB.db.execute_sql(
                "INSERT INTO policyversion (policy_group, "
                "effective_from_session, effective_from_ord, payload, "
                "is_deleted, txn_no, ins_ts, upd_ts) "
                "VALUES ('demo', '2019-I', %s, '{}'::json, false, 1, "
                "now(), now())", (AS.ordinal("2019-I"),))

    assert DB.PolicyVersion.select().count() == 0


# ===================== Unsealed policy stays workable =====================

def test_a_not_yet_effective_version_can_still_be_corrected(policy):
    """Sealing must not freeze the future: next year's ruleset has to
    remain fixable until a session it governs has closed."""
    policy.close_session("2020-II")
    policy.supersede("demo", "2026-I", {"v": "draft"})

    row = DB.PolicyVersion.get(DB.PolicyVersion.effective_from_session
                               == "2026-I")
    assert row.is_sealed is False
    row.payload = {"v": "corrected"}
    row.save()

    PS.invalidate_cache()
    SS.invalidate_cache()
    assert policy.resolve("demo", "2026-I").payload["v"] == "corrected"


def test_an_unsealed_version_cannot_be_dragged_back_into_sealed_history(
        policy):
    """Otherwise the seal would be trivially escapable: create a version
    in the open future, then move it back over closed sessions."""
    policy.close_session("2020-II")
    policy.supersede("demo", "2026-I", {"v": "draft"})

    row = DB.PolicyVersion.get(DB.PolicyVersion.effective_from_session
                               == "2026-I")
    row.effective_from_session = "2019-I"
    row.effective_from_ord = AS.ordinal("2019-I")
    with pytest.raises(DB.ImmutablePolicyError):
        row.save()

    with _expect_db_error(match="sealed"):
        with DB.db.atomic():
            (DB.PolicyVersion
             .update(effective_from_session="2019-I",
                     effective_from_ord=AS.ordinal("2019-I"))
             .where(DB.PolicyVersion.id == row.id).execute())


# ===================== Stored ordinals cannot lie =====================

def test_ordinal_column_must_match_its_session_string(policy):
    """Resolution and every guard above compare ordinals. A row whose
    ordinal disagreed with its session would be resolved into the wrong
    range and could sit under the seal line undetected."""
    with _expect_db_error(match="policyversion_ord_matches_session"):
        with DB.db.atomic():
            DB.PolicyVersion.create(
                policy_group="demo", effective_from_session="2019-I",
                effective_from_ord=AS.ordinal("2024-I"), payload={})

    with _expect_db_error(match="closedacadsession_ord_matches_session"):
        with DB.db.atomic():
            DB.ClosedAcademicSession.create(
                acad_session="2019-I", session_ord=AS.ordinal("2024-I"))


def test_malformed_session_string_is_refused_by_the_database(policy):
    with _expect_db_error(match="Malformed academic session"):
        with DB.db.atomic():
            DB.db.execute_sql(
                "INSERT INTO policyversion (policy_group, "
                "effective_from_session, effective_from_ord, payload, "
                "is_deleted, txn_no, ins_ts, upd_ts) "
                "VALUES ('demo', '2019-W', 1, '{}'::json, false, 1, "
                "now(), now())")


# ===================== The property all of this exists for =====================

def test_a_closed_sessions_ruleset_survives_later_policy_changes(policy):
    """The end-to-end guarantee: once results are out, nothing an admin
    can subsequently do changes what that session resolves to."""
    policy.supersede("demo", "2018-I", {"grade_points": {"A": 10, "B": 8}})
    before = policy.resolve("demo", "2019-II").payload_dict()

    policy.close_session("2019-II")

    # Every route an admin (or a careless script) could take.
    policy.supersede("demo", "2020-I", {"grade_points": {"A": 4, "B": 3}})
    for attempt in (
        lambda: policy.supersede("demo", "2018-I", {"grade_points": {}}),
        lambda: policy.supersede("demo", "2019-II", {"grade_points": {}}),
    ):
        with pytest.raises(PS.PolicyImmutableError):
            attempt()

    with _expect_db_error():
        with DB.db.atomic():
            DB.db.execute_sql(
                "UPDATE policyversion SET payload = '{}'::json "
                "WHERE effective_from_session = '2018-I'")

    assert policy.resolve("demo", "2019-II").payload_dict() == before
    # ...while the new ruleset does apply to the sessions after it.
    assert policy.resolve("demo", "2020-I").payload["grade_points"]["A"] == 4
