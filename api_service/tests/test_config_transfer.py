"""Tests for config_transfer.py: exporting the full configuration as one
document and importing it back.

Policy-group tests isolate policy_store's registry (mirroring
test_policy_store.py's `policy` fixture) so they exercise a simple,
builder-less group rather than the real "grading" group's complex
payload shape -- export_config()/import_config() only need
PS.declared_groups()/versions()/supersede(), which behave identically for
any declared group.
"""
import dataclasses
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conftest import create_user  # noqa: E402

import config_transfer as CT  # noqa: E402
import models as DB  # noqa: E402
import permissions as PERM  # noqa: E402
import policy_store as PS  # noqa: E402
import settings_store as ST  # noqa: E402
from common import AcadStackException  # noqa: E402
from domain import milestones as MS  # noqa: E402
from domain import workflow as WF  # noqa: E402
from domain.context import Actor  # noqa: E402


@pytest.fixture
def policy(db):
    saved = dict(PS._REGISTRY)
    PS._REGISTRY.clear()
    PS.invalidate_cache()
    ST.invalidate_cache()
    yield PS
    PS._REGISTRY.clear()
    PS._REGISTRY.update(saved)
    PS.invalidate_cache()
    ST.invalidate_cache()


@pytest.fixture
def demo_group(policy):
    policy.declare_policy_group("demo", doc="A demo ruleset for tests.")
    return "demo"


SUP = Actor(login_id="admin1", role="SUP", user_id=1)


# ===================== export_config =====================

def test_export_has_the_document_envelope(db):
    doc = CT.export_config()
    assert doc["acadstack_config_version"] == CT.DOCUMENT_VERSION
    assert "exported_at" in doc
    assert "settings" in doc and "policy" in doc


def test_export_includes_a_known_settings_group_and_value(db):
    ST.save_settings({"enrolment.max_credits_per_session": 30})
    doc = CT.export_config()
    assert doc["settings"]["enrolment"]["max_credits_per_session"] == 30


def test_export_includes_permissions_by_default(db):
    doc = CT.export_config()
    assert PERM.GROUP in doc["settings"]
    assert "system.manage_permissions" in doc["settings"][PERM.GROUP]


def test_export_can_exclude_permissions(db):
    doc = CT.export_config(include_permissions=False)
    assert PERM.GROUP not in doc["settings"]


def test_export_can_exclude_policy_history(db, demo_group):
    PS.supersede(demo_group, "2020-I", {"limit": 1})
    doc = CT.export_config(include_policy_history=False)
    assert doc["policy"] == {}


def test_export_includes_recorded_policy_versions(db, demo_group):
    PS.supersede(demo_group, "2020-I", {"limit": 1}, note="baseline")
    PS.supersede(demo_group, "2022-I", {"limit": 2}, note="raised")
    doc = CT.export_config()
    versions = doc["policy"][demo_group]
    assert [v["effective_from_session"] for v in versions] == \
        ["2020-I", "2022-I"]
    assert versions[0]["payload"] == {"limit": 1}
    assert versions[0]["note"] == "baseline"


# ===================== import_config: document shape =====================

def test_import_rejects_unsupported_document_version(db):
    with pytest.raises(CT.ConfigImportError) as ei:
        CT.import_config({"acadstack_config_version": 999})
    assert "version" in str(ei.value)


def test_import_rejects_undeclared_settings_group(db):
    doc = {"acadstack_config_version": CT.DOCUMENT_VERSION,
           "settings": {"nope_not_a_group": {"x": 1}}}
    with pytest.raises(CT.ConfigImportError) as ei:
        CT.import_config(doc)
    assert "no such setting is declared" in str(ei.value)


def test_import_is_all_or_nothing_across_settings_keys(db):
    """One bad key in the document must not let the good key next to it
    get written."""
    doc = {"acadstack_config_version": CT.DOCUMENT_VERSION,
           "settings": {
               "enrolment": {"max_credits_per_session": 40},
               "nope_not_a_group": {"x": 1},
           }}
    with pytest.raises(CT.ConfigImportError):
        CT.import_config(doc)
    assert ST.setting("enrolment.max_credits_per_session") == \
        ST.spec_for("enrolment.max_credits_per_session").default


def test_import_rejects_a_value_that_fails_its_spec(db):
    doc = {"acadstack_config_version": CT.DOCUMENT_VERSION,
           "settings": {"enrolment": {"max_credits_per_session": -5}}}
    with pytest.raises(CT.ConfigImportError):
        CT.import_config(doc)


# ===================== import_config: settings round-trip =====================

def test_export_then_import_restores_a_settings_value(db):
    ST.save_settings({"enrolment.max_credits_per_session": 33})
    doc = CT.export_config(include_permissions=False)
    ST.save_settings({"enrolment.max_credits_per_session": 12})
    assert ST.setting("enrolment.max_credits_per_session") == 12

    report = CT.import_config(doc)
    assert ST.setting("enrolment.max_credits_per_session") == 33
    assert "enrolment.max_credits_per_session" in report["settings_applied"]


# ===================== import_config: permission group =====================

def test_import_of_permission_group_requires_an_actor(db):
    doc = CT.export_config()  # includes "permission" by default
    with pytest.raises(CT.ConfigImportError) as ei:
        CT.import_config(doc)
    assert "permission" in str(ei.value)


def test_import_of_permission_group_respects_the_lockout_guard(db):
    doc = {"acadstack_config_version": CT.DOCUMENT_VERSION,
           "settings": {PERM.GROUP: {"system.manage_permissions": ["ACA"]}}}
    with pytest.raises(CT.ConfigImportError) as ei:
        CT.import_config(doc, actor=SUP)
    assert "lock" in str(ei.value).lower()
    # Rejected -- nothing written.
    assert "SUP" in PERM.roles_for_permission("system.manage_permissions")


def test_import_of_permission_group_applies_with_a_valid_actor(db):
    doc = {"acadstack_config_version": CT.DOCUMENT_VERSION,
           "settings": {PERM.GROUP: {"user.delete": ["SUP", "DEA"]}}}
    CT.import_config(doc, actor=SUP)
    assert PERM.roles_for_permission("user.delete") == ["SUP", "DEA"]


# ===================== import_config: policy =====================

def test_import_rejects_a_payload_that_fails_the_builder(db, policy):
    def builder(p):
        if "required" not in p:
            raise ValueError("needs 'required'")
        return p
    policy.declare_policy_group("built", builder=builder)
    doc = {"acadstack_config_version": CT.DOCUMENT_VERSION,
           "policy": {"built": [
               {"effective_from_session": "2020-I", "payload": {}}]}}
    with pytest.raises(CT.ConfigImportError):
        CT.import_config(doc)


def test_import_applies_a_new_policy_version(db, demo_group):
    doc = {"acadstack_config_version": CT.DOCUMENT_VERSION,
           "policy": {demo_group: [
               {"effective_from_session": "2020-I",
                "payload": {"limit": 1}, "note": "seed"}]}}
    report = CT.import_config(doc)
    assert report["policy"][demo_group] == \
        [{"effective_from_session": "2020-I", "status": "applied"}]
    assert PS.resolve(demo_group, "2020-I").payload_dict() == {"limit": 1}


def test_import_skips_a_version_that_clashes_with_an_existing_one(db, demo_group):
    PS.supersede(demo_group, "2020-I", {"limit": 1})
    doc = {"acadstack_config_version": CT.DOCUMENT_VERSION,
           "policy": {demo_group: [
               {"effective_from_session": "2020-I", "payload": {"limit": 9}}]}}
    report = CT.import_config(doc)
    entry = report["policy"][demo_group][0]
    assert entry["status"] == "skipped"
    # The pre-existing version must be untouched.
    assert PS.resolve(demo_group, "2020-I").payload_dict() == {"limit": 1}


def test_import_skips_a_version_at_or_before_the_seal_line(db, demo_group):
    PS.supersede(demo_group, "2020-I", {"limit": 1})
    PS.close_session("2020-I")
    doc = {"acadstack_config_version": CT.DOCUMENT_VERSION,
           "policy": {demo_group: [
               {"effective_from_session": "2019-I", "payload": {"limit": 0}}]}}
    report = CT.import_config(doc)
    assert report["policy"][demo_group][0]["status"] == "skipped"


def test_import_applies_some_versions_and_skips_others_in_one_group(db, demo_group):
    PS.supersede(demo_group, "2020-I", {"limit": 1})
    doc = {"acadstack_config_version": CT.DOCUMENT_VERSION,
           "policy": {demo_group: [
               {"effective_from_session": "2020-I", "payload": {"limit": 9}},
               {"effective_from_session": "2024-I", "payload": {"limit": 5}},
           ]}}
    report = CT.import_config(doc)
    statuses = {e["effective_from_session"]: e["status"]
                for e in report["policy"][demo_group]}
    assert statuses == {"2020-I": "skipped", "2024-I": "applied"}


# ===================== import_config: referential integrity =====================

def test_import_blocks_a_vocab_change_that_orphans_a_referenced_code(db):
    items = ST.vocab("degrees") + [{"code": "ZDEG", "label": "Z Degree"}]
    ST.save_settings({"vocab.degrees": items})
    create_user("STU", "stu1", degree="ZDEG")

    without_it = [it for it in items if it["code"] != "ZDEG"]
    doc = {"acadstack_config_version": CT.DOCUMENT_VERSION,
           "settings": {"vocab": {"degrees": without_it}}}
    with pytest.raises(CT.ConfigImportError) as ei:
        CT.import_config(doc)
    assert "ZDEG" in str(ei.value)
    assert "ZDEG" in ST.vocab_codes("degrees")


def test_a_failure_in_a_later_write_path_rolls_back_the_earlier_ones(db):
    """The permission mapping is written before the vocab check fails; the
    whole import must still leave nothing behind, including in the
    process cache."""
    items = ST.vocab("degrees") + [{"code": "ZDEG", "label": "Z Degree"}]
    ST.save_settings({"vocab.degrees": items})
    create_user("STU", "stu1", degree="ZDEG")

    doc = {"acadstack_config_version": CT.DOCUMENT_VERSION,
           "settings": {
               PERM.GROUP: {"user.delete": ["SUP", "DEA"]},
               "vocab": {"degrees": [it for it in items
                                     if it["code"] != "ZDEG"]}}}
    with pytest.raises(CT.ConfigImportError):
        CT.import_config(doc, actor=SUP)
    assert "DEA" not in PERM.roles_for_permission("user.delete")
    assert "ZDEG" in ST.vocab_codes("degrees")


def test_export_then_import_replays_policy_history_into_a_fresh_group(db, policy):
    policy.declare_policy_group("src", doc="source")
    PS.supersede("src", "2020-I", {"limit": 1}, note="baseline")
    PS.supersede("src", "2022-I", {"limit": 2}, note="raised")
    doc = CT.export_config()

    # Simulate importing into a fresh install that only has "dst" declared
    # (same shape, different name -- policy_store has no rename, so this
    # exercises the replay mechanism directly against a document built by
    # hand from the export's version list).
    policy.declare_policy_group("dst", doc="destination")
    replay_doc = {"acadstack_config_version": CT.DOCUMENT_VERSION,
                  "policy": {"dst": doc["policy"]["src"]}}
    report = CT.import_config(replay_doc)
    assert [e["status"] for e in report["policy"]["dst"]] == \
        ["applied", "applied"]
    assert PS.resolve("dst", "2020-I").payload_dict() == {"limit": 1}
    assert PS.resolve("dst", "2022-I").payload_dict() == {"limit": 2}


# ===================== workflows and milestones =====================

def test_export_includes_every_workflow_and_the_milestone_sequence(db):
    doc = CT.export_config()
    assert set(doc["workflows"]) == set(WF.names())
    assert doc["workflows"]["enrolment"] == WF.load("enrolment").to_json()
    assert [m["code"] for m in doc["settings"]["vocab"]["milestones"]][:2] == \
        ["JOINING", "DC_PROPOSED"]


def test_export_then_import_restores_an_edited_workflow(db):
    base = WF.baseline("course")
    edited = dataclasses.replace(base, locked_message="Locked, sorry.")
    WF.store(edited)
    doc = CT.export_config(include_permissions=False)
    WF.store(base)

    report = CT.import_config(doc)
    assert WF.load("course").locked_message == "Locked, sorry."
    assert "course" in report["workflows_applied"]


def test_export_then_import_restores_an_edited_milestone_sequence(db):
    items = ST.vocab("milestones") + [{"code": "PUBLICATION",
                                       "label": "Publication", "sequence": 85,
                                       "applies_to": "PHD"}]
    ST.save_setting("vocab.milestones", items)
    doc = CT.export_config(include_permissions=False)
    ST.delete_setting("vocab.milestones")

    CT.import_config(doc)
    assert "PUBLICATION" in MS.codes()


def test_import_rejects_an_invalid_workflow_and_writes_nothing(db):
    definition = dict(WF.baseline("course").to_json(), match_on="bogus")
    doc = {"acadstack_config_version": CT.DOCUMENT_VERSION,
           "settings": {"enrolment": {"max_credits_per_session": 30}},
           "workflows": {"course": definition}}
    with pytest.raises(CT.ConfigImportError, match="workflow: match_on"):
        CT.import_config(doc)
    assert ST.setting("enrolment.max_credits_per_session") != 30
    assert not DB.WorkflowDefinition.select().exists()


def test_import_cannot_remove_a_reserved_code(db):
    doc = {"acadstack_config_version": CT.DOCUMENT_VERSION,
           "settings": {"vocab": {"enrolment_statuses": [
               it for it in ST.vocab("enrolment_statuses")
               if it["code"] != "ENRO"]}}}
    with pytest.raises(CT.ConfigImportError, match="ENRO"):
        CT.import_config(doc)
    assert "ENRO" in ST.vocab_codes("enrolment_statuses")


# ===================== roles and their grants in one document =====================

def _roles_doc(roles, grants):
    return {"acadstack_config_version": CT.DOCUMENT_VERSION,
            "settings": {"vocab": {"roles": roles}, PERM.GROUP: grants}}


def test_import_can_add_a_role_and_grant_it_permissions(db):
    roles = ST.vocab("roles") + [{"code": "LIB", "label": "Librarian"}]
    CT.import_config(_roles_doc(roles, {"course.save": ["ACA", "LIB"]}),
                     actor=SUP)
    assert PERM.role_has_permission("LIB", "course.save")


def test_import_can_stop_granting_a_role_and_remove_it(db):
    ST.save_setting("vocab.roles", ST.vocab("roles") +
                    [{"code": "LIB", "label": "Librarian"}])
    ST.save_setting("permission.course.save", ["ACA", "LIB"])
    roles = [it for it in ST.vocab("roles") if it["code"] != "LIB"]
    CT.import_config(_roles_doc(roles, {"course.save": ["ACA"]}), actor=SUP)
    assert "LIB" not in ST.vocab_codes("roles")
