"""Referential-integrity checks on configuration changes.

settings_store.py validates a value against its own Spec (type, choices,
bounds) but knows nothing about the business tables that store a
vocabulary's codes -- it is a leaf module, deliberately unaware of
models.py's business tables (see its module docstring). That is exactly
the gap this module closes: removing a code from a "vocab.*" setting (or
resetting one to its declared default) can silently orphan every row that
still carries it -- a degree code an enrolment references, a role code a
permission mapping still grants, a status code a workflow transition table
still names. Nothing in Postgres catches this today, because vocabularies
are settings_store rows, not real tables with foreign keys.

This module wraps settings_store's write functions the same way
permissions.save_permission_mapping() wraps them for its own dangerous
case (see that module): the guard sits IN FRONT of ST.save_settings()/
ST.delete_setting(), inspecting the specific change for the one thing that
could break silently, and raises before any write if it would. It does not
attempt a general "is this safe" analysis -- only "does removing this
vocab code orphan something we can find."

Four kinds of usage are checked, for a code being removed from
"vocab.<name>":

1. Business-table columns that store codes from that vocabulary
   (VOCAB_MODEL_FIELDS below) -- e.g. Person.degree for "degrees".
2. Other settings whose value is drawn from the same vocabulary -- any
   declared Spec whose `choices_vocab` names it, e.g. a permission's role
   list for "roles".
3. Items of another vocabulary that name the code in one of their fields
   (VOCAB_ITEM_REFS) -- e.g. a milestone's `applies_to` degree.
4. Workflows: transitions of a workflow whose `status_vocab` names this
   vocabulary, via `from_status`/`to_status` (skipping the "*"/"_new"/"="
   sentinels, which are not codes), and for "milestones" any
   `milestone.record` effect naming the code -- whether the workflow is
   stored (edited through the workflow editor) or still its shipped
   baseline.

Codes the application itself depends on are protected separately, by
settings_store's vocab validator (see vocab_defaults.py's "reserved").

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__status__ = "Development"
"""

from typing import Optional

import models as M
import settings_store as ST
from domain import workflow as WF

VOCAB_GROUP = "vocab"

#: vocab name -> [(Model, field_name), ...] of business-table columns
#: whose values are codes from that vocabulary. Deliberately only the
#: fields that store a SINGLE vocabulary's codes unambiguously.
VOCAB_MODEL_FIELDS: dict = {
    "degrees": [
        (M.Person, "degree"),
        (M.CourseCategory, "degree"),
        (M.BatchAdvisors, "for_degree"),
    ],
    "roles": [(M.User, "role")],
    "course_statuses": [(M.Course, "status")],
    "offering_statuses": [(M.CourseOffering, "status")],
    "enrolment_statuses": [(M.CourseEnrollment, "enrol_status")],
    "enrolment_types": [(M.CourseEnrollment, "enrol_type")],
    "grades": [(M.CourseEnrollment, "grade")],
    "attendance_codes": [(M.StudentAttendance, "attend")],
    "dc_roles": [(M.DcMember, "role")],
    "dc_statuses": [(M.DcForStudent, "status")],
    "departments": [
        (M.Person, "dept_name"),
        (M.CourseOffering, "dept_name"),
        (M.CourseCategory, "dept"),
    ],
    "course_types": [(M.CourseCategory, "category")],
    "course_slots": [(M.CourseOffering, "slot"), (M.CourseSlotTiming, "slot")],
    "course_freqs": [(M.Course, "freq")],
    "form_types": [(M.FeedbackForm, "form_type")],
    "person_categories": [(M.Person, "category")],
    "degree_types": [(M.Person, "deg_type")],
    "ppr_statuses": [(M.PhDProgressReport, "status")],
    "student_statuses": [(M.Person, "current_status")],
    "minor_conc_specializations": [(M.Person, "deg_type_spec")],
    "milestones": [(M.AcademicMilestone, "milestone")],
}

#: vocab name -> [(other vocab, item field), ...] where items of the other
#: vocabulary name a code from this one.
VOCAB_ITEM_REFS: dict = {
    "degrees": [("milestones", "applies_to")],
}

#: Sentinels used in a transition's from_status/to_status that are never
#: real vocabulary codes (see domain/workflow.py's ANY/NEW/SAME).
_WORKFLOW_SENTINELS = {"*", "_new", "="}


def model_usages(vocab_name: str, code: str) -> list:
    """Business-table rows still carrying `code` for this vocabulary."""
    found = []
    for model, field_name in VOCAB_MODEL_FIELDS.get(vocab_name, []):
        field = getattr(model, field_name)
        count = (model.select()
                 .where((field == code) & (model.is_deleted == False))  # noqa: E712
                 .count())
        if count:
            found.append(f"{count} {model.__name__}.{field_name} row(s)")
    return found


def _effective(key: str, pending: Optional[dict]):
    """The value `key` will have once `pending` (a batch being saved) is."""
    return pending[key] if pending and key in pending else ST.setting(key)


def settings_usages(vocab_name: str, code: str,
                    pending: Optional[dict] = None) -> list:
    """Other declared settings whose value is drawn from this vocabulary
    (their Spec's `choices_vocab`) and still names `code` -- e.g. every
    "permission.*" role list for "roles". Values in `pending` (the batch
    being saved) replace stored ones."""
    found = []
    for group, gs in ST.declared_groups().items():
        if group == VOCAB_GROUP:
            continue
        for name, spec in gs.specs.items():
            if spec.choices_vocab != vocab_name:
                continue
            key = f"{group}.{name}"
            value = _effective(key, pending)
            hit = (code in value) if isinstance(value, list) else (value == code)
            if hit:
                found.append(key)
    return found


def vocab_item_usages(vocab_name: str, code: str,
                      pending: Optional[dict] = None) -> list:
    """Items of other vocabularies naming `code` (VOCAB_ITEM_REFS)."""
    found = []
    for other, field_name in VOCAB_ITEM_REFS.get(vocab_name, []):
        items = _effective(f"{VOCAB_GROUP}.{other}", pending)
        hits = [it["code"] for it in items
                if isinstance(it, dict) and it.get(field_name) == code]
        if hits:
            found.append(f"vocab.{other} item(s) {', '.join(hits)}")
    return found


def _names_code(vocab_name: str, wf, t, code: str) -> bool:
    if wf.status_vocab == vocab_name and code in (t.from_status, t.to_status):
        return True
    return vocab_name == "milestones" and any(
        step.name == "milestone.record" and step.params.get("code") == code
        for step in t.effects)


def workflow_usages(vocab_name: str, code: str) -> list:
    """Transitions of any workflow that still name `code`: as a
    from_status/to_status when the workflow's status_vocab is this
    vocabulary, or as the milestone a `milestone.record` effect records.
    Reads each workflow as workflow.load() resolves it -- the stored
    definition, else the shipped baseline -- so a code is protected
    whichever one is in force. Inactive transitions count too, since
    re-activating one must not strand anything."""
    if code in _WORKFLOW_SENTINELS:
        return []
    found = []
    for name in WF.names():
        wf = WF.load(name)
        count = sum(1 for t in wf.transitions
                    if _names_code(vocab_name, wf, t, code))
        if count:
            found.append(f"{count} transition(s) of the '{name}' workflow")
    return found


def usages_of(vocab_name: str, code: str,
              pending: Optional[dict] = None) -> list:
    """Every place `code` is still used, across all four checks, with the
    settings in `pending` (the batch being saved) taken as already saved."""
    return (model_usages(vocab_name, code) +
            settings_usages(vocab_name, code, pending) +
            vocab_item_usages(vocab_name, code, pending) +
            workflow_usages(vocab_name, code))


def _removed_codes(vocab_name: str, new_items) -> set:
    old_codes = {it["code"] for it in ST.vocab(vocab_name) if isinstance(it, dict)}
    new_codes = {it["code"] for it in new_items if isinstance(it, dict)} \
        if isinstance(new_items, list) else set()
    return old_codes - new_codes


def _check_removed_codes(vocab_name: str, removed: set, action: str,
                         pending: Optional[dict] = None) -> list:
    errors = []
    for code in sorted(removed):
        usages = usages_of(vocab_name, code, pending)
        if usages:
            errors.append(
                f"Cannot {action} '{code}' from vocab.{vocab_name}: still "
                f"referenced by {', '.join(usages)}.")
    return errors


def _removal_errors(key: str, new_value, pending: dict) -> list:
    """The referential-integrity errors (if any) from writing `new_value`
    to `key` as part of the batch `pending`. Empty for any key outside the
    "vocab" group, or for a vocab write that doesn't drop a still-used
    code."""
    try:
        group, name = ST.split_key(key)
    except ValueError:
        return []  # save_settings() reports the bad key
    if group != VOCAB_GROUP:
        return []
    removed = _removed_codes(name, new_value)
    return _check_removed_codes(name, removed, "remove", pending)


def guarded_save_settings(values: dict, login_id: Optional[str] = None) -> dict:
    """ST.save_settings(), with a referential-integrity pre-check applied
    to every "vocab.*" key in `values`: a code present in the currently
    effective list but absent from the proposed one must not still be in
    use, counting the other values in the same batch as already saved (so
    one save can stop granting a role and remove it). Raises
    SettingValidationError (before any write) if it is; keys outside the
    vocab group pass straight through, unchecked."""
    errors = []
    for key, new_items in values.items():
        errors.extend(_removal_errors(key, new_items, values))
    if errors:
        raise ST.SettingValidationError(errors)
    return ST.save_settings(values, login_id=login_id)


def guarded_delete_setting(key: str, login_id: Optional[str] = None) -> bool:
    """ST.delete_setting(), with the same pre-check applied when `key` is
    a "vocab.*" setting being reverted to its declared default."""
    try:
        group, name = ST.split_key(key)
    except ValueError:
        return ST.delete_setting(key, login_id=login_id)
    if group != VOCAB_GROUP:
        return ST.delete_setting(key, login_id=login_id)

    spec = ST.spec_for(key)
    default_items = spec.default if spec else []
    removed = _removed_codes(name, default_items)
    errors = _check_removed_codes(name, removed, "reset")
    if errors:
        raise ST.SettingValidationError(errors)
    return ST.delete_setting(key, login_id=login_id)
