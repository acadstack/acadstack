"""Export/import of an institution's full DB-backed configuration as one
versioned JSON document.

export_config() serializes both stores (settings_store, policy_store) as
they are recorded. import_config() feeds a document back through the same
guarded write paths the admin screens use -- config_integrity's
guarded_save_settings() (Spec validation plus the vocab-code-in-use
check), permissions.save_permission_mapping() (plus its self-lockout
guard) and policy_store.supersede() -- inside one transaction, so an
imported document is held to exactly the rules a click in the admin
screen is, and either all of it applies or none of it does.

Uses: seeding a test fixture with an exact policy; cloning a configured
institution onto another install; diffing two exports to review a change.

Settings groups present in the document REPLACE this install's values.
Policy is insert-only (see policy_store), so a policy group can only ADD
versions: a version whose session already has policy recorded, or that
lands at or before the seal line, is reported as skipped rather than
failing the import -- the expected outcome of importing a fixture into an
install with its own history.

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__status__ = "Development"
"""

import logging
from typing import Optional

import config_integrity as CI
import models as M
import permissions as PERM
import policy_store as PS
import settings_store as ST
from common import AcadStackException
from domain.context import Actor

#: Bumped only if the document shape changes in a way that breaks reading
#: an older export (a field renamed or restructured, not just added).
DOCUMENT_VERSION = 1


class ConfigImportError(AcadStackException):
    """The document could not be applied, and nothing was. Carries every
    problem the failing write path reported."""

    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


def export_config(*, include_permissions: bool = True,
                  include_policy_history: bool = True) -> dict:
    """Serializes this install's full configuration into one document.

    Args:
        include_permissions: include the "permission" settings group (the
            permission->role mapping). Cloning an institution means
            cloning who may do what, so it is in by default.
        include_policy_history: include every recorded version of every
            policy group. Off only for a "current settings, no history"
            export.
    """
    settings_out = {
        group: ST.settings_in_group(group)
        for group in sorted(ST.declared_groups())
        if include_permissions or group != PERM.GROUP
    }

    policy_out = {}
    if include_policy_history:
        for group in sorted(PS.declared_groups()):
            versions = PS.versions(group)
            if versions:
                policy_out[group] = [
                    {"effective_from_session": v.effective_from,
                     "payload": v.payload_dict(),
                     "note": v.note}
                    for v in versions
                ]

    return {
        "acadstack_config_version": DOCUMENT_VERSION,
        "exported_at": M.DT.now().isoformat(),
        "settings": settings_out,
        "policy": policy_out,
    }


def _shape_errors(settings_in, policy_in) -> list:
    """Structural problems the write paths would trip over as a bare
    AttributeError/TypeError rather than report."""
    errors = []
    if not isinstance(settings_in, dict):
        errors.append("'settings' must be an object of {group: {name: value}}.")
    else:
        errors += [f"settings group {group!r}: expected an object of "
                   f"{{name: value}}."
                   for group, items in settings_in.items()
                   if not isinstance(items, dict)]
    if not isinstance(policy_in, dict):
        errors.append("'policy' must be an object of {group: [version, ...]}.")
        return errors
    for group, versions in policy_in.items():
        if not isinstance(versions, list):
            errors.append(f"policy group {group!r}: expected a list of "
                          f"versions.")
            continue
        errors += [f"policy group {group!r}, version {i}: expected an object "
                   f"with a string 'effective_from_session'."
                   for i, v in enumerate(versions)
                   if not isinstance(v, dict) or
                   not isinstance(v.get("effective_from_session"), str)]
    return errors


def import_config(document: dict, *, actor: Optional[Actor] = None,
                  login_id: Optional[str] = None) -> dict:
    """Applies an export_config()-shaped document to this install.

    Args:
        document: as produced by export_config(), or hand-written (e.g. a
            test fixture); 'settings' and 'policy' are both optional.
        actor: the importing user. Required when the document contains
            the "permission" group, which is written through
            save_permission_mapping() so its self-lockout guard applies.
        login_id: provenance for written rows. Defaults to
            actor.login_id, then the request's session user.

    Returns:
        {"settings_applied": [key, ...], "policy": {group:
        [{"effective_from_session", "status": "applied"|"skipped",
        "reason"?}, ...]}}.

    Raises:
        ConfigImportError: the document is malformed, or any write path
            rejected part of it. Nothing is written in that case.
    """
    if not isinstance(document, dict):
        raise ConfigImportError(["The document must be a JSON object."])
    version = document.get("acadstack_config_version")
    if version != DOCUMENT_VERSION:
        raise ConfigImportError(
            [f"Unsupported config document version {version!r}; this "
             f"install understands version {DOCUMENT_VERSION}."])

    settings_in = document.get("settings") or {}
    policy_in = document.get("policy") or {}
    errors = _shape_errors(settings_in, policy_in)
    if errors:
        raise ConfigImportError(errors)

    permissions = settings_in.get(PERM.GROUP)
    if permissions and actor is None:
        raise ConfigImportError(
            [f"The document contains '{PERM.GROUP}' settings (the "
             f"permission->role mapping); importing it requires the acting "
             f"user, so the self-lockout guard can be applied."])
    values = {f"{group}.{name}": value
              for group, items in settings_in.items() if group != PERM.GROUP
              for name, value in items.items()}
    login_id = login_id or (actor.login_id if actor else None) or \
        ST.current_login_id()

    try:
        with M.db.atomic():
            applied = []
            # Permissions first, so a document that stops granting a role
            # and removes it from vocab.roles passes the in-use check.
            if permissions:
                applied += PERM.save_permission_mapping(permissions, actor)
            if values:
                applied += CI.guarded_save_settings(values, login_id=login_id)
            policy_report = {
                group: [_supersede(group, v, login_id) for v in versions]
                for group, versions in policy_in.items()
            }
    except Exception as ex:
        # The writes above refreshed this worker's caches from inside the
        # transaction that just rolled back.
        ST.invalidate_cache()
        PS.invalidate_cache()
        if isinstance(ex, AcadStackException):
            raise ConfigImportError(getattr(ex, "errors", None) or [str(ex)]) \
                from ex
        raise

    logging.info(f"Imported configuration document by {login_id}: "
                 f"{len(applied)} setting(s), "
                 f"{sum(len(v) for v in policy_report.values())} policy "
                 f"version(s) attempted.")
    return {"settings_applied": sorted(applied), "policy": policy_report}


def _supersede(group: str, version: dict, login_id: Optional[str]) -> dict:
    session = version["effective_from_session"]
    try:
        PS.supersede(group, session, version.get("payload"),
                     note=version.get("note"), login_id=login_id)
        return {"effective_from_session": session, "status": "applied"}
    except PS.PolicyImmutableError as ex:
        return {"effective_from_session": session, "status": "skipped",
                "reason": str(ex)}
