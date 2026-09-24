"""Tests for the single-sourced controlled vocabularies:
vocab_defaults.py (the bootstrap source), the "vocab" settings group it
declares in settings_store.py, models.py's choices= derivation, and
api_common.static_data_dict()/GET /acadstack/get_static_data (the
generated replacement for the old hand-maintained static_data.json).
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import api_common as apiVC  # noqa: E402
import models as DB  # noqa: E402
import settings_store as ST  # noqa: E402
import vocab_defaults as VD  # noqa: E402
from settings_store import SettingValidationError, save_setting  # noqa: E402


# ===================== vocab_defaults.py itself =====================

def test_every_vocabulary_has_unique_non_empty_codes():
    for name, items in VD.ALL.items():
        codes = [item["code"] for item in items]
        assert codes, f"{name} must not be empty"
        assert len(codes) == len(set(codes)), \
            f"{name} has duplicate codes: {codes}"
        for item in items:
            assert item.get("code"), f"{name}: item missing code: {item}"
            assert item.get("label"), f"{name}: item missing label: {item}"


def test_static_data_keys_covers_every_vocabulary_exactly_once():
    assert set(VD.STATIC_DATA_KEYS) == set(VD.ALL)
    json_keys = [k for k, _ in VD.STATIC_DATA_KEYS.values()]
    assert len(json_keys) == len(set(json_keys)), "duplicate static_data.json key"


def test_degrees_excludes_the_confirmed_unused_orphans():
    # BTE_MC, MCE_WATER, MCE_STRUC, MME_MCPMC, JEE_PREP, ADD_INTRN used to
    # exist ONLY in the old static_data.json, with zero references anywhere
    # else in the repo (models.py, demo_data.py, ...) -- dropped as stale.
    codes = VD.codes("degrees")
    for orphan in ("BTE_MC", "MCE_WATER", "MCE_STRUC", "MME_MCPMC",
                   "JEE_PREP", "ADD_INTRN"):
        assert orphan not in codes


def test_minor_conc_specialization_collision_resolved():
    codes = VD.codes("minor_conc_specializations")
    # CTCS was listed twice (same label) -- now once.
    assert codes.count("CTCS") == 1
    # MECE was listed twice with two different meanings; MECE keeps
    # Electronics & Communication, the other was recoded to MENG.
    assert codes.count("MECE") == 1
    by_code = {i["code"]: i["label"] for i in VD.MINOR_CONC_SPECIALIZATIONS}
    assert "Electronics" in by_code["MECE"]
    assert "English" in by_code["MENG"]


# ===================== models.py choices= derivation =====================

def test_model_choices_derive_from_vocab_defaults():
    # DEGREES is a module-level constant (models.py), not a Person class
    # attribute -- see get_degree_label()'s pre-existing `self.DEGREES`,
    # which is a latent bug (Person has no such attribute) predating this
    # phase and out of scope to fix here.
    assert DB.DEGREES == VD.choices("degrees")
    assert DB.User.ROLES == VD.choices("roles")
    assert DB.Course.COURSE_STATUSES == VD.choices("course_statuses")
    assert DB.CourseOffering.CO_STATUSES == VD.choices("offering_statuses")
    assert DB.CourseEnrollment.ENROL_STATUSES == VD.choices("enrolment_statuses")
    assert DB.StudentAttendance.ATT_STATUS == VD.choices("attendance_codes")
    assert DB.DcMember.DC_ROLES == VD.choices("dc_roles")
    assert DB.PhDProgressReport.PPR_STATUSES == VD.choices("ppr_statuses")


def test_previously_choice_less_fields_now_declare_choices():
    # These fields represented one of the named vocabularies but had no
    # choices= at all before this phase (peewee choices are documentation
    # only -- not DB-enforced -- so adding them is purely additive).
    assert DB.CourseEnrollment.enrol_type.choices == VD.choices("enrolment_types")
    assert DB.CourseEnrollment.grade.choices == VD.choices("grades")
    assert DB.CourseCategory.category.choices == VD.choices("course_types")
    assert DB.DcForStudent.status.choices == VD.choices("dc_statuses")
    assert DB.CourseOffering.slot.choices == VD.choices("course_slots")


# ===================== settings_store "vocab" group =====================

def test_vocab_group_declared_with_defaults_matching_vocab_defaults():
    gs = ST.declared_groups()["vocab"]
    assert set(gs.specs) == set(VD.ALL)
    for name, spec in gs.specs.items():
        assert spec.default == VD.ALL[name]


def test_vocab_reads_fall_back_to_defaults_when_nothing_stored(db):
    assert ST.vocab("degrees") == VD.DEGREES
    assert ST.vocab_codes("roles") == VD.codes("roles")


def test_valid_grade_and_audit_grade_codes(db):
    assert set(ST.valid_grade_codes()) == set(VD.codes("grades"))
    audit_expected = {g["code"] for g in VD.GRADES if g["audit_ok"]}
    assert set(ST.valid_audit_grade_codes()) == audit_expected
    assert "A" not in ST.valid_audit_grade_codes()  # a real letter grade


def test_saving_a_vocab_value_overrides_the_default(db):
    custom = VD.DEGREES + [{"code": "ZZZ", "label": "Test Degree"}]
    save_setting("vocab.degrees", custom)
    assert "ZZZ" in ST.vocab_codes("degrees")
    # Unrelated vocabularies are untouched.
    assert ST.vocab_codes("roles") == VD.codes("roles")


def test_vocab_write_validation_rejects_malformed_items(db):
    with pytest.raises(SettingValidationError):
        save_setting("vocab.degrees", [{"code": "X"}])  # missing label
    with pytest.raises(SettingValidationError):
        save_setting("vocab.degrees", [
            {"code": "X", "label": "A"}, {"code": "X", "label": "B"},
        ])  # duplicate code


# ===================== static_data_dict() / GET get_static_data =====================

def _in_request(app, fn):
    import asyncio

    async def _run():
        async with app.test_request_context("/acadstack/"):
            return fn()
    return asyncio.run(_run())


def test_static_data_dict_shape_matches_the_old_hand_maintained_file(app, db):
    sd = _in_request(app, apiVC.static_data_dict)

    # Every old static_data.json key is present, generated instead of read
    # off disk.
    for _, (json_key, _) in VD.STATIC_DATA_KEYS.items():
        assert json_key in sd
    assert "AcademicSessions" in sd

    # Groups that used to carry a leading "-Select-" placeholder still do;
    # groups that didn't, still don't.
    assert sd["Degrees"][0] == {"id": "", "value": "-Select-"}
    assert len(sd["Degrees"]) == len(VD.DEGREES) + 1
    assert sd["DcRoles"][0] != {"id": "", "value": "-Select-"}
    assert len(sd["DcRoles"]) == len(VD.DC_ROLES)

    # Content is {id, value} pairs sourced from code/label.
    assert {"id": "PHD", "value": "PhD"} in sd["Degrees"]


def test_static_data_dict_reflects_a_stored_override(app, db):
    save_setting("vocab.dc_roles", [{"code": "XX", "label": "Extra Role"}])
    sd = _in_request(app, apiVC.static_data_dict)
    assert sd["DcRoles"] == [{"id": "XX", "value": "Extra Role"}]


def test_get_static_data_endpoint(client, auth):
    with client:
        assert auth.login().status_code == 200
        res = client.get("/acadstack/get_static_data")
    assert res.status_code == 200
    body = res.json["body"]
    assert body["Degrees"][0] == {"id": "", "value": "-Select-"}
    codes = {d["id"] for d in body["Degrees"]}
    assert "PHD" in codes
    assert "JEE_PREP" not in codes
