"""Tests for config_integrity.py: referential-integrity checks that block
a "vocab.*" write from silently orphaning rows/settings that still use a
code being removed.
"""
import dataclasses
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conftest import create_user  # noqa: E402

import config_integrity as CI  # noqa: E402
import models as DB  # noqa: E402
import settings_store as ST  # noqa: E402
from domain import workflow as WF  # noqa: E402


# ===================== model_usages =====================

def test_model_usages_finds_a_referencing_row(db):
    create_user("STU", "stu1", degree="ZDEG")
    assert any("Person" in u for u in CI.model_usages("degrees", "ZDEG"))


def test_model_usages_is_empty_for_an_unused_code(db):
    assert CI.model_usages("degrees", "NOBODYHASTHIS") == []


def test_model_usages_checks_every_mapped_field(db):
    # BatchAdvisors.for_degree is also mapped for "degrees"; a code used
    # only there (not on any Person) must still be found.
    u = create_user("HOD", "hod1")
    DB.BatchAdvisors.create(user=u, for_degree="ONLYADVISED", year_of_entry="2020")
    assert any("BatchAdvisors" in x for x in CI.model_usages("degrees", "ONLYADVISED"))


# ===================== settings_usages =====================

def test_settings_usages_finds_a_role_in_a_permission_mapping(db):
    found = CI.settings_usages("roles", "SUP")
    assert any(f.startswith("permission.") for f in found)


def test_settings_usages_is_empty_for_an_unused_role(db):
    assert CI.settings_usages("roles", "NOSUCHROLE") == []


# ===================== workflow_usages =====================

@pytest.fixture
def edited_course_workflow(db):
    """The course workflow as saved through the workflow editor, with an
    extra transition naming a status the baseline doesn't use."""
    base = WF.baseline("course")
    WF.store(dataclasses.replace(base, transitions=base.transitions + (
        WF.Transition(priority=9999, from_status="TESTSTAT", to_status="=",
                      label="Test", permission="course.save"),)))
    return "course"


def test_workflow_usages_covers_the_baseline_when_nothing_is_stored(db):
    assert not DB.WorkflowDefinition.select().exists()
    found = CI.workflow_usages("course_statuses", "APP")
    assert found and "'course' workflow" in found[0]


def test_workflow_usages_finds_a_transition_saved_through_the_editor(
        db, edited_course_workflow):
    found = CI.workflow_usages("course_statuses", "TESTSTAT")
    assert found == ["1 transition(s) of the 'course' workflow"]


def test_workflow_usages_ignores_sentinels(db, edited_course_workflow):
    assert CI.workflow_usages("course_statuses", "=") == []
    assert CI.workflow_usages("course_statuses", "*") == []


def test_workflow_usages_is_scoped_to_the_named_vocab(db, edited_course_workflow):
    assert CI.workflow_usages("degrees", "TESTSTAT") == []


def test_guarded_save_blocks_removing_a_status_an_edited_workflow_uses(
        db, edited_course_workflow):
    items = ST.vocab("course_statuses") + [{"code": "TESTSTAT", "label": "T"}]
    ST.save_settings({"vocab.course_statuses": items})
    with pytest.raises(ST.SettingValidationError) as ei:
        CI.guarded_save_settings({"vocab.course_statuses": items[:-1]})
    assert "TESTSTAT" in str(ei.value) and "workflow" in str(ei.value)


# ===================== guarded_save_settings =====================

def test_guarded_save_settings_blocks_removal_of_a_referenced_code(db):
    items = ST.vocab("degrees") + [{"code": "ZDEG", "label": "Z Degree"}]
    ST.save_settings({"vocab.degrees": items})
    create_user("STU", "stu2", degree="ZDEG")

    without_it = [it for it in items if it["code"] != "ZDEG"]
    with pytest.raises(ST.SettingValidationError) as ei:
        CI.guarded_save_settings({"vocab.degrees": without_it})
    assert "ZDEG" in str(ei.value)
    # Rejected -- the stored list must be untouched.
    assert "ZDEG" in ST.vocab_codes("degrees")


def test_guarded_save_settings_allows_removal_of_an_unreferenced_code(db):
    items = ST.vocab("degrees") + [{"code": "ZDEG2", "label": "Z2"}]
    ST.save_settings({"vocab.degrees": items})

    without_it = [it for it in items if it["code"] != "ZDEG2"]
    CI.guarded_save_settings({"vocab.degrees": without_it})
    assert "ZDEG2" not in ST.vocab_codes("degrees")


def test_guarded_save_settings_ignores_non_vocab_keys(db):
    CI.guarded_save_settings({"enrolment.max_credits_per_session": 40})
    assert ST.setting("enrolment.max_credits_per_session") == 40


# ===================== guarded_delete_setting =====================

def test_guarded_delete_setting_blocks_reset_that_drops_a_referenced_code(db):
    items = ST.vocab("degrees") + [{"code": "ZDEG3", "label": "Z3"}]
    ST.save_settings({"vocab.degrees": items})
    create_user("STU", "stu3", degree="ZDEG3")

    with pytest.raises(ST.SettingValidationError) as ei:
        CI.guarded_delete_setting("vocab.degrees")
    assert "ZDEG3" in str(ei.value)
    assert "ZDEG3" in ST.vocab_codes("degrees")


def test_guarded_delete_setting_allows_reset_when_nothing_is_orphaned(db):
    items = ST.vocab("degrees") + [{"code": "ZDEG4", "label": "Z4"}]
    ST.save_settings({"vocab.degrees": items})

    CI.guarded_delete_setting("vocab.degrees")
    assert "ZDEG4" not in ST.vocab_codes("degrees")
