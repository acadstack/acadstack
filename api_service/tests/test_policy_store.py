"""Tests for policy_store.py: declaring policy groups, superseding, and
resolving the ruleset in force for an academic session.

Immutability is covered separately in test_policy_immutability.py; this
file is about the storage/resolution contract itself.

These run against the real test database, so a resolution after a write
sees what Postgres actually stored.
"""
import asyncio
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import acad_session as AS  # noqa: E402
import models as DB  # noqa: E402
import policy_store as PS  # noqa: E402
import settings_store as SS  # noqa: E402


# ===================== Fixtures =====================

@pytest.fixture
def policy(db):
    """Isolates the policy-group registry and both process caches, so one
    test's groups and cached snapshots cannot leak into another."""
    saved = dict(PS._REGISTRY)
    PS._REGISTRY.clear()
    PS.invalidate_cache()
    SS.invalidate_cache()
    yield PS
    PS._REGISTRY.clear()
    PS._REGISTRY.update(saved)
    PS.invalidate_cache()
    SS.invalidate_cache()


@pytest.fixture
def simple_group(policy):
    policy.declare_policy_group("demo", doc="A demo ruleset.")
    return "demo"


def _payload(**kw):
    base = {"limit": 5, "codes": ["A", "B"]}
    base.update(kw)
    return base


# ===================== Declaration & validation =====================

def test_supersede_requires_a_declared_group(policy):
    with pytest.raises(PS.PolicyValidationError) as ei:
        policy.supersede("nope", "2020-I", {"a": 1})
    assert "not declared" in str(ei.value)


def test_payload_must_be_a_json_object(policy, simple_group):
    for bad in ([1, 2], "text", 7, None):
        with pytest.raises(PS.PolicyValidationError):
            policy.supersede(simple_group, "2020-I", bad)


def test_builder_failure_rejects_the_write(policy):
    def builder(p):
        if "required" not in p:
            raise ValueError("needs 'required'")
        return p["required"]

    policy.declare_policy_group("built", builder=builder)

    with pytest.raises(PS.PolicyValidationError) as ei:
        policy.supersede("built", "2020-I", {"other": 1})
    assert "needs 'required'" in str(ei.value)
    assert DB.PolicyVersion.select().count() == 0

    policy.supersede("built", "2020-I", {"required": "ok"})
    assert policy.policy_for("built", "2020-I") == "ok"


def test_validator_errors_are_all_reported(policy):
    def two_problems(p):
        raise ValueError("first problem", "second problem")

    policy.declare_policy_group("checked", validator=two_problems)
    with pytest.raises(PS.PolicyValidationError) as ei:
        policy.supersede("checked", "2020-I", {"a": 1})
    assert ei.value.errors == ["checked: first problem",
                               "checked: second problem"]


def test_a_validator_that_returns_normally_accepts_the_payload(policy):
    policy.declare_policy_group("ok", validator=lambda p: None)
    policy.supersede("ok", "2020-I", {"a": 1})
    assert PS.resolve("ok", "2020-I").payload_dict() == {"a": 1}


def test_malformed_effective_session_is_reported_as_a_policy_error(
        policy, simple_group):
    # Write paths take a session string from a human, so it is reported
    # the way other rejected admin input is, not as a bare ValueError.
    with pytest.raises(PS.PolicyValidationError):
        policy.supersede(simple_group, "2020-W", _payload())
    with pytest.raises(PS.PolicyValidationError):
        policy.close_session("not-a-session")


# ===================== Resolution =====================

def test_resolve_returns_the_version_in_force(policy, simple_group):
    policy.supersede(simple_group, "2019-I", _payload(limit=1))
    policy.supersede(simple_group, "2021-I", _payload(limit=2))
    policy.supersede(simple_group, "2023-I", _payload(limit=3))

    assert policy.resolve(simple_group, "2019-I").payload["limit"] == 1
    assert policy.resolve(simple_group, "2020-S").payload["limit"] == 1
    assert policy.resolve(simple_group, "2021-I").payload["limit"] == 2
    assert policy.resolve(simple_group, "2022-T4").payload["limit"] == 2
    assert policy.resolve(simple_group, "2023-I").payload["limit"] == 3
    assert policy.resolve(simple_group, "2199-S").payload["limit"] == 3


def test_effective_from_is_inclusive_and_effective_to_exclusive(
        policy, simple_group):
    policy.supersede(simple_group, "2000-T1", _payload(limit=0))
    policy.supersede(simple_group, "2021-I", _payload(limit=1))
    policy.supersede(simple_group, "2021-II", _payload(limit=2))

    # The session immediately before a boundary still gets the old rules.
    # 2020-S is the last session of the previous academic year.
    assert policy.resolve(simple_group, "2020-S").payload["limit"] == 0
    assert policy.resolve(simple_group, "2021-I").payload["limit"] == 1
    assert policy.resolve(simple_group, "2021-II").payload["limit"] == 2
    # 2021-T4 starts in April, AFTER 2021-II starts in January, so it
    # takes 2021-II's ruleset. Under the pre-0004 rank scheme T4 sorted
    # before 2021-I and wrongly got the oldest ruleset instead.
    assert policy.resolve(simple_group, "2021-T4").payload["limit"] == 2


def test_concurrent_sessions_resolve_to_the_same_version(
        policy, simple_group):
    """A ruleset is in force for an instant, so two sessions that begin in
    the same month get the same one however different their calendars."""
    policy.supersede(simple_group, "2000-T1", _payload(limit=0))
    policy.supersede(simple_group, "2021-I", _payload(limit=1))

    assert policy.resolve(simple_group, "2021-T1").payload["limit"] == 1
    assert policy.resolve(simple_group, "2021-I").version_id == \
        policy.resolve(simple_group, "2021-T1").version_id


def test_effective_range_is_derived_from_the_neighbouring_versions(
        policy, simple_group):
    policy.supersede(simple_group, "2019-I", _payload())
    policy.supersede(simple_group, "2021-I", _payload())

    first, second = policy.versions(simple_group)
    assert (first.effective_from, first.effective_to) == ("2019-I", "2021-I")
    # The latest version's range is open-ended, not "until today".
    assert (second.effective_from, second.effective_to) == ("2021-I", None)
    assert first.covers("2020-S") and not first.covers("2021-I")
    assert second.covers("2021-I") and second.covers("2999-S")


def test_backfilling_a_version_between_two_others_re_derives_ranges(
        policy, simple_group):
    """Ranges are derived, never stored, so inserting a version in the
    middle changes its neighbours' effective ranges without any row being
    updated -- which is the whole reason effective_to is not a column."""
    policy.supersede(simple_group, "2019-I", _payload(limit=1))
    policy.supersede(simple_group, "2023-I", _payload(limit=3))
    assert policy.resolve(simple_group, "2021-I").payload["limit"] == 1

    policy.supersede(simple_group, "2021-I", _payload(limit=2))

    assert policy.resolve(simple_group, "2021-I").payload["limit"] == 2
    assert policy.versions(simple_group)[0].effective_to == "2021-I"
    assert [v.effective_from for v in policy.versions(simple_group)] == [
        "2019-I", "2021-I", "2023-I"]


def test_resolve_raises_before_the_first_version(policy, simple_group):
    policy.supersede(simple_group, "2021-I", _payload())
    with pytest.raises(PS.PolicyNotFoundError) as ei:
        policy.resolve(simple_group, "2020-S")
    assert "2021-I" in str(ei.value)


def test_resolve_raises_for_a_group_with_no_versions(policy, simple_group):
    with pytest.raises(PS.PolicyNotFoundError):
        policy.resolve(simple_group, "2021-I")


def test_resolve_rejects_a_malformed_session(policy, simple_group):
    policy.supersede(simple_group, "2021-I", _payload())
    for bad in ("2021-W", "2021", "twenty-I"):
        with pytest.raises(AS.InvalidAcadSession):
            policy.resolve(simple_group, bad)


def test_duplicate_effective_session_is_refused(policy, simple_group):
    policy.supersede(simple_group, "2021-I", _payload(limit=1))
    with pytest.raises(PS.PolicyImmutableError) as ei:
        policy.supersede(simple_group, "2021-I", _payload(limit=9))
    assert "already exists" in str(ei.value)
    assert policy.resolve(simple_group, "2021-I").payload["limit"] == 1


def test_groups_are_independent(policy):
    policy.declare_policy_group("a")
    policy.declare_policy_group("b")
    policy.supersede("a", "2019-I", {"v": "a19"})
    policy.supersede("b", "2022-I", {"v": "b22"})

    assert policy.resolve("a", "2023-I").payload["v"] == "a19"
    with pytest.raises(PS.PolicyNotFoundError):
        policy.resolve("b", "2021-I")


# ===================== Payload immutability in memory =====================

def test_resolved_payload_is_read_only(policy, simple_group):
    policy.supersede(simple_group, "2021-I", _payload())
    resolved = policy.resolve(simple_group, "2021-I")

    with pytest.raises(TypeError):
        resolved.payload["limit"] = 99
    # Nested structures are frozen too, so a caller cannot reach in.
    assert isinstance(resolved.payload["codes"], tuple)
    with pytest.raises(TypeError):
        resolved.payload["codes"][0] = "Z"


def test_payload_dict_gives_a_mutable_copy(policy, simple_group):
    policy.supersede(simple_group, "2021-I", _payload())
    editable = policy.resolve(simple_group, "2021-I").payload_dict()
    editable["limit"] = 99
    editable["codes"].append("C")

    assert policy.resolve(simple_group, "2021-I").payload["limit"] == 5
    # ...and it is in the shape supersede() accepts.
    policy.supersede(simple_group, "2022-I", editable)
    assert policy.resolve(simple_group, "2022-I").payload["limit"] == 99


# ===================== Cost of resolution =====================

def test_resolution_issues_no_queries_once_warm(policy, simple_group,
                                                monkeypatch):
    """Transcript building resolves per course, so resolution must not
    touch the database."""
    policy.supersede(simple_group, "2000-T1", _payload())
    policy.supersede(simple_group, "2021-I", _payload())
    policy.resolve(simple_group, "2020-I")  # warm the snapshot

    calls = []
    real = DB.db.execute_sql
    monkeypatch.setattr(DB.db, "execute_sql",
                        lambda *a, **k: (calls.append(a[0]), real(*a, **k))[1])

    for year in range(2019, 2025):
        for suffix in AS.SUFFIXES:
            policy.resolve(simple_group, f"{year}-{suffix}")

    assert calls == []


def test_builder_runs_once_per_version_not_once_per_resolution(policy):
    builds = []

    def builder(p):
        builds.append(p["limit"])
        return p["limit"] * 2

    policy.declare_policy_group("counted", builder=builder)
    policy.supersede("counted", "2019-I", _payload(limit=1))
    policy.supersede("counted", "2021-I", _payload(limit=2))

    # Each write already ran the builder once: that is write-time
    # validation, and it is why a payload that cannot be built never
    # reaches the table.
    assert sorted(builds) == [1, 2]
    builds.clear()

    for _ in range(25):
        assert policy.policy_for("counted", "2020-I") == 2
        assert policy.policy_for("counted", "2022-I") == 4

    # Reads build each version at most once per snapshot, however many
    # courses a transcript resolves.
    assert sorted(builds) == [1, 2]


def test_a_write_is_visible_to_the_next_resolution(policy, simple_group):
    policy.supersede(simple_group, "2019-I", _payload(limit=1))
    assert policy.resolve(simple_group, "2020-I").payload["limit"] == 1
    cached = PS._cache
    assert cached is not None

    # No manual invalidation: the write drops the cache itself.
    policy.supersede(simple_group, "2020-I", _payload(limit=7))
    assert policy.resolve(simple_group, "2020-I").payload["limit"] == 7
    assert PS._cache is not cached


def test_a_request_resolves_against_one_snapshot(app, policy, simple_group):
    policy.supersede(simple_group, "2019-I", _payload(limit=1))

    def other_thread_supersedes():
        try:
            policy.supersede(simple_group, "2020-I", _payload(limit=7))
        finally:
            DB.db.close()

    async def in_request():
        async with app.test_request_context("/acadstack/"):
            first = policy.resolve(simple_group, "2020-I").payload["limit"]
            t = threading.Thread(target=other_thread_supersedes)
            t.start()
            t.join()
            return first, policy.resolve(simple_group, "2020-I").payload["limit"]

    assert asyncio.run(in_request()) == (1, 1)
    assert policy.resolve(simple_group, "2020-I").payload["limit"] == 7


# ===================== Metadata =====================

def test_version_records_who_wrote_it_and_why(policy, simple_group):
    policy.supersede(simple_group, "2021-I", _payload(),
                     note="Senate resolution 2021/14", login_id="registrar")
    v = policy.resolve(simple_group, "2021-I")
    assert v.note == "Senate resolution 2021/14"
    assert v.recorded_by == "registrar"
    assert v.recorded_ts is not None


def test_str_shows_the_effective_range(policy, simple_group):
    policy.supersede(simple_group, "2021-I", _payload())
    policy.supersede(simple_group, "2022-I", _payload())
    first, second = policy.versions(simple_group)
    assert str(first) == "demo[2021-I -> 2022-I)"
    assert str(second) == "demo[2022-I -> (open))"
