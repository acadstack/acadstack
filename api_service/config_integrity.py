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

Three kinds of usage are checked, for a code being removed from
"vocab.<name>":

1. Business-table columns that store codes from that vocabulary
   (VOCAB_MODEL_FIELDS below) -- e.g. Person.degree for "degrees".
2. Other settings whose value is drawn from the same vocabulary -- any
   declared Spec whose `choices` matches the vocabulary's codes, e.g. a
   permission's role list for "roles".
3. Transitions of a workflow whose `status_vocab` names this vocabulary,
   via `from_status`/`to_status` (skipping the "*"/"_new"/"=" sentinels,
   which are not codes) -- whether the workflow is stored (edited through
   the workflow editor) or still its shipped baseline.

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__status__ = "Development"
"""

from typing import Optional

import models as M
import settings_store as ST
import vocab_defaults as VD
from domain import workflow as WF

VOCAB_GROUP = "vocab"

#: vocab name -> [(Model, field_name), ...] of business-table columns
#: whose values are codes from that vocabulary. Deliberately only the
#: fields that store a SINGLE vocabulary's codes unambiguously; a few
#: soft-referencing fields in models.py (MilestoneDefinition.applies_to,
#: AcademicMilestone.milestone) name a code from a concept that isn't
#: cleanly one vocabulary and are left out rather than guessed at.
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
}

#: Sentinels used in WorkflowTransition.from_status/to_status that are
#: never real vocabulary codes (see models.py's WorkflowTransition doc).
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


def settings_usages(vocab_name: str, code: str) -> list:
    """Other declared settings whose value is drawn from this same
    vocabulary and still names `code`. Matched by comparing a Spec's
    `choices` to the vocabulary's codes, so it covers every current and
    future role-valued (etc.) setting without a hand-maintained list --
    e.g. every "permission.*" entry and "course_offering.hide_stats_from"
    for "roles"."""
    codes = set(VD.codes(vocab_name)) if vocab_name in VD.ALL else set()
    if code not in codes:
        codes = codes | {code}  # still check even if already removed from defaults
    found = []
    for group, gs in ST.declared_groups().items():
        if group == VOCAB_GROUP:
            continue
        for name, spec in gs.specs.items():
            if not spec.choices or set(spec.choices) != codes:
                continue
            key = f"{group}.{name}"
            value = ST.setting(key)
            hit = (code in value) if isinstance(value, list) else (value == code)
            if hit:
                found.append(key)
    return found


def workflow_usages(vocab_name: str, code: str) -> list:
    """Transitions of any workflow whose status_vocab names this
    vocabulary that still name `code` as a from_status/to_status. Reads
    each workflow as workflow.load() resolves it -- the stored definition
    saved through the workflow editor, else the shipped baseline -- so a
    code is protected whichever one is in force. Inactive transitions
    count too, since re-activating one must not strand anything."""
    if code in _WORKFLOW_SENTINELS:
        return []
    found = []
    for name in WF.names():
        wf = WF.load(name)
        if wf.status_vocab != vocab_name:
            continue
        count = sum(1 for t in wf.transitions
                    if code in (t.from_status, t.to_status))
        if count:
            found.append(f"{count} transition(s) of the '{name}' workflow")
    return found


def usages_of(vocab_name: str, code: str) -> list:
    """Every place `code` is still used, across all three checks."""
    return (model_usages(vocab_name, code) +
            settings_usages(vocab_name, code) +
            workflow_usages(vocab_name, code))


def _removed_codes(vocab_name: str, new_items) -> set:
    old_codes = {it["code"] for it in ST.vocab(vocab_name) if isinstance(it, dict)}
    new_codes = {it["code"] for it in new_items if isinstance(it, dict)} \
        if isinstance(new_items, list) else set()
    return old_codes - new_codes


def _check_removed_codes(vocab_name: str, removed: set, action: str) -> list:
    errors = []
    for code in sorted(removed):
        usages = usages_of(vocab_name, code)
        if usages:
            errors.append(
                f"Cannot {action} '{code}' from vocab.{vocab_name}: still "
                f"referenced by {', '.join(usages)}.")
    return errors


def _removal_errors(key: str, new_value) -> list:
    """The referential-integrity errors (if any) from writing `new_value`
    to `key`. Empty for any key outside the "vocab" group, or for a vocab
    write that doesn't drop a still-used code."""
    try:
        group, name = ST.split_key(key)
    except ValueError:
        return []  # save_settings() reports the bad key
    if group != VOCAB_GROUP:
        return []
    removed = _removed_codes(name, new_value)
    return _check_removed_codes(name, removed, "remove")


def guarded_save_settings(values: dict, login_id: Optional[str] = None) -> dict:
    """ST.save_settings(), with a referential-integrity pre-check applied
    to every "vocab.*" key in `values`: a code present in the currently
    effective list but absent from the proposed one must not still be in
    use. Raises SettingValidationError (before any write) if it is; keys
    outside the vocab group pass straight through, unchecked."""
    errors = []
    for key, new_items in values.items():
        errors.extend(_removal_errors(key, new_items))
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
