"""Export/import of an institution's full DB-backed configuration as one
versioned JSON document.

The read side is the Phase 1 seeder (default_seed_data.py) run in reverse:
where the seeder inserts vocab_defaults.py's lists as SEED_SPECS rows and
derives the baseline grading ruleset from domain.policy to hand to
policy_store.supersede(), export_config() walks the same two stores
(settings_store, policy_store) and serializes whatever is actually
recorded -- defaults or an institution's own edits, it makes no
distinction, because by the time a value is DB-backed it has no
"institution's own" vs "seeded" flag. The write side (import_config())
feeds a document back through the same validated write paths the admin
GUI and the seeder already use (ST.save_settings, PS.supersede) rather
than writing rows directly, so an imported document is held to exactly
the same rules a click in the admin screen is.

Uses:

* Seeding a test fixture with a known, exact policy -- import a small
  fixture document instead of exercising the admin GUI/API to build up
  the same state by hand.
* Cloning a configured institution -- export from one install, import
  into another.
* Reviewing policy changes out-of-band -- export before and after a
  change and diff the two documents with any JSON diff tool.

Settings/vocab/permission groups are a snapshot: importing REPLACES this
install's effective values for every group present in the document (via
ST.save_settings(), which validates and writes atomically -- either
every value in the document is stored or, on a validation problem,
nothing is). Policy groups are different in kind: policy_store is
insert-only (see its module docstring), so a policy group in the document
can only ever ADD versions, never replace what is already recorded here.
A version whose session already has policy recorded, or that lands at or
before this install's seal line, cannot be applied; that is reported per
version rather than aborting the whole import, since it is an expected
outcome of importing a fixture into a install that already has its own
history, not a malformed document.

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__status__ = "Development"
"""

import logging
from typing import Optional

import models as M
import permissions as PERM
import policy_store as PS
import settings_store as ST
from common import AcadStackException
from domain.context import Actor

#: Bumped only if the document shape below changes in a way that breaks
#: reading an older export (e.g. a field renamed or restructured, not just
#: added). import_config() refuses to read a document from a newer major
#: version than this install understands.
DOCUMENT_VERSION = 1


class ConfigImportError(AcadStackException):
    """The document could not be applied. Carries every problem found, so
    an admin GUI (or a fixture author) sees them all at once. Raised only
    for problems knowable from the document and this install's
    declarations alone (undeclared group, wrong shape, a value that fails
    its Spec, a policy payload that fails its builder/validator) -- these
    are checked BEFORE anything is written, so a raised ConfigImportError
    always means nothing was applied. A policy version skipped because it
    would alter sealed history is not one of these: see import_config()'s
    return value."""

    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


def export_config(*, include_permissions: bool = True,
                  include_policy_history: bool = True) -> dict:
    """Serializes this install's full configuration into one document.

    Args:
        include_permissions: whether to include the "permission" settings
            group (the permission->role mapping). Excluded by the generic
            settings admin screen (api_settings.py's _EXCLUDED_GROUPS) but
            included here by default -- cloning an institution's
            configuration means cloning who is allowed to do what, too.
        include_policy_history: whether to include every recorded version
            of every policy group (grading, ...), not just the one
            currently in force. Off only for a "current settings snapshot,
            no history" export.

    Returns:
        A JSON-serializable document. See the module docstring for the
        settings-vs-policy distinction that shapes how import_config()
        applies it back.
    """
    settings_out = {}
    for group in sorted(ST.declared_groups()):
        if group == PERM.GROUP and not include_permissions:
            continue
        settings_out[group] = ST.settings_in_group(group)

    policy_out = {}
    if include_policy_history:
        for group in sorted(PS.declared_groups()):
            versions = PS.versions(group)
            if not versions:
                continue
            policy_out[group] = [
                {
                    "effective_from_session": v.effective_from,
                    "payload": v.payload_dict(),
                    "note": v.note,
                }
                for v in versions
            ]

    return {
        "acadstack_config_version": DOCUMENT_VERSION,
        "exported_at": M.DT.now().isoformat(),
        "settings": settings_out,
        "policy": policy_out,
    }


def _validate_settings_shape(settings_in: dict, declared: dict) -> tuple:
    """Returns (values, errors). `values` is a flat {"group.name": value}
    map ready for ST.validate_values(); nothing is coerced/typed yet."""
    errors = []
    values = {}
    if not isinstance(settings_in, dict):
        return {}, [f"'settings' must be an object, got "
                    f"{type(settings_in).__name__}."]
    for group, items in settings_in.items():
        if group not in declared:
            errors.append(f"settings group {group!r} is not declared on "
                          f"this install (upgrade first, or drop it from "
                          f"the document).")
            continue
        if not isinstance(items, dict):
            errors.append(f"settings group {group!r}: expected an object "
                          f"of {{name: value}}, got {type(items).__name__}.")
            continue
        for name, value in items.items():
            values[f"{group}.{name}"] = value
    return values, errors


def _validate_policy_shape(policy_in: dict, declared: dict) -> tuple:
    """Returns (parsed, errors). `parsed` is {group: [(session, payload,
    note), ...]}, already builder/validator-checked via
    PS.validate_payload() (a dry run -- nothing is stored)."""
    errors = []
    parsed = {}
    if not isinstance(policy_in, dict):
        return {}, [f"'policy' must be an object, got "
                    f"{type(policy_in).__name__}."]
    for group, versions in policy_in.items():
        if group not in declared:
            errors.append(f"policy group {group!r} is not declared on "
                          f"this install (upgrade first, or drop it from "
                          f"the document).")
            continue
        if not isinstance(versions, list):
            errors.append(f"policy group {group!r}: expected a list of "
                          f"versions, got {type(versions).__name__}.")
            continue
        group_parsed = []
        for i, v in enumerate(versions):
            label = f"policy group {group!r}, version {i}"
            if not isinstance(v, dict):
                errors.append(f"{label}: expected an object.")
                continue
            session = v.get("effective_from_session")
            payload = v.get("payload")
            if not session or not isinstance(session, str):
                errors.append(f"{label}: missing/invalid "
                              f"'effective_from_session'.")
                continue
            if not isinstance(payload, dict):
                errors.append(f"{label}: missing/invalid 'payload' "
                              f"(must be an object).")
                continue
            try:
                PS.validate_payload(group, payload)
            except PS.PolicyValidationError as ex:
                errors.append(f"{label} (effective {session}): {ex}")
                continue
            group_parsed.append((session, payload, v.get("note")))
        parsed[group] = group_parsed
    return parsed, errors


def import_config(document: dict, *, actor: Optional[Actor] = None,
                  login_id: Optional[str] = None) -> dict:
    """Applies an export_config()-shaped document to this install.

    Args:
        document: as produced by export_config() (or hand-written, e.g. a
            small test fixture -- only 'settings' and/or 'policy' need be
            present, both are optional).
        actor: the importing user, needed only when the document touches
            the "permission" settings group -- those keys are routed
            through permissions.save_permission_mapping() instead of the
            generic settings write path, so its self-lockout guard still
            applies to an imported document exactly as it does to a
            manual edit. Required if the document contains a "permission"
            group; a ValueError is raised otherwise (rather than silently
            skipping the lockout check).
        login_id: provenance to stamp on written rows. Defaults to
            actor.login_id, then the current request's session user, then
            None.

    Returns:
        A report dict: {"settings_applied": [key, ...], "policy": {group:
        [{"effective_from_session", "status": "applied"|"skipped",
        "reason"?}, ...]}}. A "skipped" policy entry is not an error --
        see the module docstring -- it means this install already has
        policy of record for that session (or later) and the import
        correctly left it alone.

    Raises:
        ConfigImportError: the document is malformed, names an undeclared
            group, or a value/payload fails validation. Nothing is
            written in this case.
    """
    if not isinstance(document, dict):
        raise ConfigImportError(
            [f"The document must be a JSON object, got "
             f"{type(document).__name__}."])

    version = document.get("acadstack_config_version")
    if version != DOCUMENT_VERSION:
        raise ConfigImportError(
            [f"Unsupported config document version {version!r}; this "
             f"install understands version {DOCUMENT_VERSION}."])

    values, errors = _validate_settings_shape(
        document.get("settings") or {}, ST.declared_groups())
    policy_payloads, policy_errors = _validate_policy_shape(
        document.get("policy") or {}, PS.declared_groups())
    errors.extend(policy_errors)

    permission_prefix = f"{PERM.GROUP}."
    permission_values = {k: v for k, v in values.items()
                         if k.startswith(permission_prefix)}
    other_values = {k: v for k, v in values.items()
                    if not k.startswith(permission_prefix)}
    if permission_values and actor is None:
        errors.append(
            f"The document contains '{PERM.GROUP}' settings (the "
            f"permission->role mapping); importing it requires the "
            f"acting user, so the self-lockout guard can be applied.")
    elif permission_values and actor is not None:
        # Mirrors permissions.save_permission_mapping()'s own guard,
        # checked here too so a lockout-violating document is rejected in
        # the validation pass -- before other_values below have been
        # written -- rather than raising mid-write after settings were
        # already applied. save_permission_mapping() still re-checks this
        # at write time; this is not a replacement for that guard, just an
        # earlier chance to fail the whole import atomically.
        manage_key = f"{PERM.GROUP}.{PERM.MANAGE_PERMISSIONS}"
        if manage_key in permission_values and \
                actor.role not in permission_values[manage_key]:
            errors.append(
                f"Cannot import '{manage_key}': it would remove the "
                f"importing user's own role from it, locking every "
                f"administrator out of managing permissions. Have another "
                f"administrator import this document instead.")

    if other_values:
        try:
            ST.validate_values(other_values)
        except ST.SettingValidationError as ex:
            errors.extend(ex.errors)
    if permission_values and actor is not None:
        try:
            ST.validate_values(permission_values)
        except ST.SettingValidationError as ex:
            errors.extend(ex.errors)

    if errors:
        raise ConfigImportError(errors)

    login_id = login_id or (actor.login_id if actor else None) or \
        ST.current_login_id()

    applied_settings = set()
    if other_values:
        applied_settings.update(ST.save_settings(
            other_values, login_id=login_id))
    if permission_values:
        applied_settings.update(PERM.save_permission_mapping(
            {k[len(permission_prefix):]: v
             for k, v in permission_values.items()}, actor))

    policy_report = {}
    for group, parsed in policy_payloads.items():
        group_report = []
        for session, payload, note in parsed:
            try:
                PS.supersede(group, session, payload, note=note,
                             login_id=login_id)
                group_report.append({"effective_from_session": session,
                                     "status": "applied"})
            except PS.PolicyImmutableError as ex:
                group_report.append({"effective_from_session": session,
                                     "status": "skipped", "reason": str(ex)})
        policy_report[group] = group_report

    logging.info(f"Imported configuration document by {login_id}: "
                 f"{len(applied_settings)} setting(s), "
                 f"{sum(len(v) for v in policy_report.values())} policy "
                 f"version(s) attempted.")
    return {"settings_applied": sorted(applied_settings),
            "policy": policy_report}
