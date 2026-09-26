"""Tests for the settings seam (settings_store.py): the ``setting()``
accessor, the process cache and its invalidation on write, and write-time
validation.

These run against the real test database (the ``db`` fixture in
conftest.py), so a read after a write sees what Postgres actually stored.

Settings groups are declared per test through the ``settings`` fixture,
which isolates the module-level registry and cache. Production
declarations (the DECLARATIONS section at the bottom of
settings_store.py) are restored afterwards.
"""
import asyncio
import sys
import threading
from pathlib import Path

import peewee
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import models as DB  # noqa: E402
import vocab_defaults as VD  # noqa: E402
import settings_store as SS  # noqa: E402
from settings_store import (Spec, SettingValidationError, declare_group,  # noqa: E402
                            delete_setting, save_setting, save_settings,
                            setting, settings_in_group)


@pytest.fixture
def settings(db):
    """Isolates the declaration registry and the process-wide cache, so a
    test's groups can't leak into another test or into production
    declarations."""
    saved = dict(SS._REGISTRY)
    SS._REGISTRY.clear()
    SS._WARNED_UNDECLARED.clear()
    SS.invalidate_cache()
    yield SS
    SS._REGISTRY.clear()
    SS._REGISTRY.update(saved)
    SS._WARNED_UNDECLARED.clear()
    SS.invalidate_cache()


@pytest.fixture
def demo_group(settings):
    """A representative group: a flag, a threshold, a list of role codes
    and a JSON map."""
    declare_group("enrolment", [
        Spec("disable_fees_check", bool, default=False,
             doc="Skip the outstanding-fees check when enrolling."),
        Spec("max_credits", int, default=24, min_value=1, max_value=60),
        Spec("hide_stats_from", list, default=["STU"],
             choices=["ACA", "DEA", "HOD", "FAC", "STU", "RES", "SUP"]),
        Spec("grade_points", dict, default={"A": 10.0}),
        Spec("late_fee_note", str, default="", max_value=20),
    ], doc="Course enrolment policy.")
    return settings


def run_in_request(app, fn, path="/acadstack/"):
    """Calls fn() inside a Quart request context, the way a route handler
    would run, so the per-request snapshot pinned on `g` is exercised."""
    async def _run():
        async with app.test_request_context(path):
            return fn()
    return asyncio.run(_run())


class QueryCounter:
    """Counts every statement the process sends to Postgres. All peewee
    queries funnel through Database.execute_sql, including model
    selects/inserts."""

    def __init__(self, monkeypatch):
        self.count = 0
        original = DB.db.execute_sql

        def counting(*args, **kwargs):
            self.count += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(DB.db, "execute_sql", counting)

    def reset(self):
        self.count = 0


def save_from_another_thread(key, value):
    """Saves through the store from a thread with no request context, as
    a background job would: the process cache is invalidated, but not the
    calling request's pinned snapshot."""
    def run():
        try:
            save_setting(key, value)
        finally:
            DB.db.close()
    t = threading.Thread(target=run)
    t.start()
    t.join()


# ===================== Reading and precedence =====================

def test_declared_default_is_used_when_nothing_is_stored(demo_group):
    assert setting("enrolment.disable_fees_check") is False
    assert setting("enrolment.max_credits") == 24
    assert setting("enrolment.hide_stats_from") == ["STU"]


def test_callers_default_overrides_the_declared_default(demo_group):
    # A call site being migrated keeps its existing hard-coded fallback,
    # which must win until a value is actually seeded.
    assert setting("enrolment.max_credits", 99) == 99


def test_stored_value_wins_over_every_default(demo_group):
    save_setting("enrolment.max_credits", 30)
    assert setting("enrolment.max_credits") == 30
    assert setting("enrolment.max_credits", 99) == 30


def test_undeclared_key_falls_back_to_the_callers_default(settings):
    assert setting("nosuch.key", "fallback") == "fallback"
    assert setting("nosuch.key") is None


def test_values_come_back_typed_not_as_text(demo_group):
    save_settings({"enrolment.disable_fees_check": True,
                   "enrolment.max_credits": 18})
    assert setting("enrolment.disable_fees_check") is True
    assert setting("enrolment.max_credits") == 18


def test_json_settings_round_trip(demo_group):
    save_settings({"enrolment.grade_points": {"A": 10.0, "B": 8.0},
                   "enrolment.hide_stats_from": ["STU", "RES"]})
    assert setting("enrolment.grade_points") == {"A": 10.0, "B": 8.0}
    assert setting("enrolment.hide_stats_from") == ["STU", "RES"]


def test_caller_cannot_mutate_the_cached_json_value(demo_group):
    save_setting("enrolment.hide_stats_from", ["STU"])
    got = setting("enrolment.hide_stats_from")
    got.append("FAC")
    # The cache is shared by every request the process serves until the
    # next write, so a caller's mutation must not reach it.
    assert setting("enrolment.hide_stats_from") == ["STU"]
    assert settings_in_group("enrolment")["hide_stats_from"] == ["STU"]
    # The same applies to a value that is still the declared default.
    SS._REGISTRY["enrolment"].specs["grade_points"].default["X"] = 1.0
    default_map = setting("enrolment.grade_points")
    default_map["Z"] = 0.0
    assert "Z" not in setting("enrolment.grade_points")


def test_unusable_stored_value_falls_back_instead_of_raising(demo_group):
    """A hand-edited row or a restored dump must not blow up a read in the
    middle of, say, generating a transcript."""
    DB.SystemSetting.create(group="enrolment", name="max_credits",
                            value="not-a-number")
    SS.invalidate_cache()

    assert setting("enrolment.max_credits") == 24  # declared default
    assert SS.validate_stored_settings() == []  # coerced away before checking


def test_settings_in_group_merges_defaults_and_stored_values(demo_group):
    save_setting("enrolment.max_credits", 12)
    values = settings_in_group("enrolment")
    assert values["max_credits"] == 12
    assert values["disable_fees_check"] is False
    assert values["grade_points"] == {"A": 10.0}


def test_describe_settings_exposes_the_schema_for_an_admin_gui(demo_group):
    save_setting("enrolment.max_credits", 12)
    described = {d["key"]: d for d in SS.describe_settings()}
    entry = described["enrolment.max_credits"]
    assert entry["type"] == "int"
    assert entry["default"] == 24
    assert entry["value"] == 12
    assert entry["min_value"] == 1 and entry["max_value"] == 60


# ===================== Write-time validation =====================

def test_saving_an_undeclared_setting_is_rejected(settings):
    with pytest.raises(SettingValidationError) as ex:
        save_setting("mystery.flag", True)
    assert "no such setting is declared" in str(ex.value)
    assert DB.SystemSetting.select().count() == 0


def test_wrong_type_is_rejected_at_write_time(demo_group):
    with pytest.raises(SettingValidationError) as ex:
        save_setting("enrolment.max_credits", "twenty")
    assert "enrolment.max_credits" in str(ex.value)
    assert setting("enrolment.max_credits") == 24


def test_all_problems_are_reported_at_once(demo_group):
    with pytest.raises(SettingValidationError) as ex:
        save_settings({"enrolment.max_credits": 500,
                       "enrolment.hide_stats_from": ["NOPE"],
                       "enrolment.disable_fees_check": "maybe"})
    assert len(ex.value.errors) == 3


def test_numeric_bounds_are_enforced(demo_group):
    with pytest.raises(SettingValidationError):
        save_setting("enrolment.max_credits", 0)
    with pytest.raises(SettingValidationError):
        save_setting("enrolment.max_credits", 61)
    assert save_setting("enrolment.max_credits", 60) == 60


def test_bounds_measure_length_for_strings_and_collections(demo_group):
    with pytest.raises(SettingValidationError) as ex:
        save_setting("enrolment.late_fee_note", "x" * 21)
    assert "length 21" in str(ex.value)
    assert save_setting("enrolment.late_fee_note", "ok") == "ok"


def test_choices_constrain_the_items_of_a_list_setting(demo_group):
    with pytest.raises(SettingValidationError) as ex:
        save_setting("enrolment.hide_stats_from", ["STU", "WRONG"])
    assert "'WRONG' is not one of" in str(ex.value)
    assert save_setting("enrolment.hide_stats_from", ["STU", "RES"]) == \
        ["STU", "RES"]


def test_custom_validator_runs_on_save(settings):
    def even_only(value):
        if value % 2:
            raise ValueError("must be an even number of weeks")

    declare_group("calendar", [
        Spec("weeks", int, default=16, validator=even_only),
    ])
    with pytest.raises(SettingValidationError) as ex:
        save_setting("calendar.weeks", 15)
    assert "must be an even number of weeks" in str(ex.value)
    assert save_setting("calendar.weeks", 14) == 14


def test_a_rejected_save_writes_nothing_at_all(demo_group):
    save_setting("enrolment.max_credits", 20)

    with pytest.raises(SettingValidationError):
        save_settings({"enrolment.disable_fees_check": True,   # valid
                       "enrolment.max_credits": 999})          # invalid

    SS.invalidate_cache()
    assert setting("enrolment.disable_fees_check") is False
    assert setting("enrolment.max_credits") == 20


def test_form_style_string_input_is_coerced_before_validation(demo_group):
    # An admin GUI posts strings; the accessor's callers must still get
    # real types back.
    save_settings({"enrolment.disable_fees_check": "true",
                   "enrolment.max_credits": " 21 ",
                   "enrolment.hide_stats_from": '["STU", "FAC"]'})
    assert setting("enrolment.disable_fees_check") is True
    assert setting("enrolment.max_credits") == 21
    assert setting("enrolment.hide_stats_from") == ["STU", "FAC"]


def test_a_boolean_is_not_accepted_as_a_number(demo_group):
    with pytest.raises(SettingValidationError):
        save_setting("enrolment.max_credits", True)


def test_malformed_keys_are_rejected(settings):
    with pytest.raises(SettingValidationError):
        save_setting("nodot", True)


def test_declaring_an_invalid_default_fails_at_declaration_time(settings):
    with pytest.raises(ValueError) as ex:
        declare_group("bad", [Spec("weeks", int, default=99, max_value=52)])
    assert "Invalid declared default" in str(ex.value)
    assert "bad" not in SS.declared_groups()


def test_deleting_a_setting_reverts_it_to_the_declared_default(demo_group):
    save_setting("enrolment.max_credits", 30)
    assert setting("enrolment.max_credits") == 30

    assert delete_setting("enrolment.max_credits") is True
    assert setting("enrolment.max_credits") == 24
    assert delete_setting("enrolment.max_credits") is False


def test_a_key_is_stored_in_exactly_one_row(demo_group):
    save_setting("enrolment.hide_stats_from", ["STU"])
    save_setting("enrolment.hide_stats_from", ["FAC"])
    rows = list(DB.SystemSetting.select().where(
        (DB.SystemSetting.group == "enrolment") &
        (DB.SystemSetting.name == "hide_stats_from")))
    assert len(rows) == 1 and rows[0].value == ["FAC"]
    with pytest.raises(peewee.IntegrityError), DB.db.atomic():
        DB.SystemSetting.create(group="enrolment", name="hide_stats_from",
                                value=["STU"])


def test_validate_stored_settings_reports_rows_without_a_declaration(demo_group):
    DB.SystemSetting.create(group="orphan", name="leftover", value="x")
    SS.invalidate_cache()
    problems = SS.validate_stored_settings()
    assert problems == ["orphan.leftover: stored but not declared"]


# ===================== Caching =====================

def test_many_lookups_in_one_request_cost_one_query(app, demo_group,
                                                     monkeypatch):
    save_settings({"enrolment.max_credits": 20,
                   "enrolment.disable_fees_check": True})
    SS.invalidate_cache()
    counter = QueryCounter(monkeypatch)

    def read_a_lot():
        for _ in range(25):
            assert setting("enrolment.max_credits") == 20
            assert setting("enrolment.disable_fees_check") is True
            assert setting("enrolment.hide_stats_from") == ["STU"]
        return counter.count

    # One load of the table -- not one per lookup.
    assert run_in_request(app, read_a_lot) == 1


def test_a_later_request_costs_no_query(app, demo_group, monkeypatch):
    save_setting("enrolment.max_credits", 20)
    SS.invalidate_cache()
    counter = QueryCounter(monkeypatch)

    run_in_request(app, lambda: setting("enrolment.max_credits"))
    counter.reset()

    def read_again():
        for _ in range(10):
            assert setting("enrolment.max_credits") == 20
        return counter.count

    assert run_in_request(app, read_again) == 0


def test_a_save_is_visible_to_the_next_read(demo_group):
    assert setting("enrolment.max_credits") == 24  # warms the cache
    save_setting("enrolment.max_credits", 33)
    assert setting("enrolment.max_credits") == 33
    delete_setting("enrolment.max_credits")
    assert setting("enrolment.max_credits") == 24


def test_a_save_inside_a_request_is_visible_later_in_that_request(
        app, demo_group):
    def read_save_read():
        first = setting("enrolment.max_credits")
        save_setting("enrolment.max_credits", 40)
        return first, setting("enrolment.max_credits")

    assert run_in_request(app, read_save_read) == (24, 40)


def test_a_request_sees_one_consistent_snapshot_throughout(app, demo_group):
    save_settings({"enrolment.max_credits": 20,
                   "enrolment.disable_fees_check": False})
    SS.invalidate_cache()

    def read_write_read():
        first = setting("enrolment.max_credits")
        # A background job saves halfway through this request.
        save_from_another_thread("enrolment.max_credits", 40)
        return first, setting("enrolment.max_credits")

    first, second = run_in_request(app, read_write_read)
    assert (first, second) == (20, 20)

    # The next request picks the new value up.
    assert run_in_request(app, lambda: setting("enrolment.max_credits")) == 40


def test_a_warm_cache_serves_reads_without_a_query(demo_group, monkeypatch):
    save_setting("enrolment.max_credits", 20)
    setting("enrolment.max_credits")  # reloads after the save

    counter = QueryCounter(monkeypatch)
    for _ in range(5):
        assert setting("enrolment.max_credits") == 20
    assert counter.count == 0


def test_a_load_that_raced_a_write_is_not_cached(demo_group, monkeypatch):
    """A background job's thread loading the table while a write lands
    must not store its pre-write snapshot over the write's invalidation."""
    save_setting("enrolment.max_credits", 20)
    load = SS._load_values

    def load_then_write_lands():
        snapshot = load()
        SS.invalidate_cache()  # the write finishes mid-load
        return snapshot

    monkeypatch.setattr(SS, "_load_values", load_then_write_lands)
    setting("enrolment.max_credits")
    assert SS._cache is None


def test_a_database_failure_after_warming_serves_the_cached_values(
        demo_group, monkeypatch):
    save_setting("enrolment.max_credits", 20)
    assert setting("enrolment.max_credits") == 20  # primes the cache

    def boom(*args, **kwargs):
        raise RuntimeError("database is gone")

    monkeypatch.setattr(DB.db, "execute_sql", boom)
    assert setting("enrolment.max_credits") == 20


def test_with_no_cache_at_all_a_database_failure_yields_defaults(demo_group,
                                                                monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("database is gone")

    monkeypatch.setattr(DB.db, "execute_sql", boom)
    SS.invalidate_cache()
    # Never raises: call sites fall back to their declared/passed default.
    assert setting("enrolment.max_credits") == 24
    assert setting("enrolment.max_credits", 7) == 7


def test_none_is_rejected_as_a_missing_value(demo_group):
    with pytest.raises(SettingValidationError) as ex:
        save_setting("enrolment.max_credits", None)
    assert "is required" in str(ex.value)


def test_a_stored_value_of_the_wrong_type_falls_back_to_the_default(demo_group):
    """A hand-edited row holding a string where the Spec says list must
    degrade to the declared default, not hand a string to code expecting
    a list."""
    DB.SystemSetting.create(group="enrolment", name="hide_stats_from",
                            value="STU,RES")
    SS.invalidate_cache()

    assert setting("enrolment.hide_stats_from") == ["STU"]


# ===================== Vocabulary-backed choices =====================

def test_choices_vocab_reads_the_live_vocabulary(db):
    SS.declare_group("paint_demo", [Spec("roles", list, default=["STU"],
                                         choices_vocab="roles")])
    try:
        with pytest.raises(SettingValidationError, match="'LIB' is not one of"):
            save_setting("paint_demo.roles", ["LIB"])
        save_setting("vocab.roles", SS.vocab("roles") +
                     [{"code": "LIB", "label": "Librarian"}])
        assert save_setting("paint_demo.roles", ["LIB"]) == ["LIB"]
    finally:
        del SS._REGISTRY["paint_demo"]


def test_a_declared_default_is_checked_against_the_shipped_codes(settings):
    with pytest.raises(ValueError, match="'NOPE' is not one of"):
        declare_group("paint", [Spec("roles", list, default=["NOPE"],
                                     choices_vocab="roles")])


def test_a_spec_takes_choices_or_choices_vocab_not_both():
    with pytest.raises(ValueError, match="not both"):
        Spec("x", list, choices=["A"], choices_vocab="roles")


# ===================== Reserved vocabulary codes =====================

def _roles_without(code):
    return [it for it in SS.vocab("roles") if it["code"] != code]


def test_a_reserved_code_cannot_be_removed(db):
    with pytest.raises(SettingValidationError, match="'STU' is reserved"):
        save_setting("vocab.roles", _roles_without("STU"))


def test_a_reserved_code_can_be_relabelled(db):
    items = [dict(it, label="Learner") if it["code"] == "STU" else it
             for it in SS.vocab("roles")]
    save_setting("vocab.roles", items)
    assert {"code": "STU", "label": "Learner", "reserved": True} in \
        SS.vocab("roles")


def test_an_open_code_can_be_removed(db):
    assert "ADV" not in VD.reserved_codes("roles")
    save_setting("vocab.roles", _roles_without("ADV"))
    assert "ADV" not in SS.vocab_codes("roles")


def test_the_reserved_flag_cannot_be_cleared(db):
    items = [dict(it, reserved=False) if it["code"] == "STU" else it
             for it in SS.vocab("roles")]
    with pytest.raises(SettingValidationError, match="'reserved' must be True"):
        save_setting("vocab.roles", items)


def test_the_reserved_flag_cannot_be_set_on_an_open_code(db):
    items = SS.vocab("roles") + [{"code": "LIB", "label": "Librarian",
                                  "reserved": True}]
    with pytest.raises(SettingValidationError, match="'reserved' must be False"):
        save_setting("vocab.roles", items)


def test_describe_settings_names_the_reserved_codes(db):
    described = {d["key"]: d for d in SS.describe_settings()}
    assert "ENRO" in described["vocab.enrolment_statuses"]["reserved_codes"]
    assert described["app.page_size"]["reserved_codes"] is None


def test_milestone_items_need_a_sequence_and_a_degree(db):
    items = SS.vocab("milestones") + [{"code": "X", "label": "X",
                                       "sequence": "5"}]
    with pytest.raises(SettingValidationError) as ei:
        save_setting("vocab.milestones", items)
    assert "'sequence' must be a whole number" in str(ei.value)
    assert "'applies_to' must be a degree code" in str(ei.value)
