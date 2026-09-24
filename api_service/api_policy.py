"""View functions for the versioned academic-policy admin screen.

There is deliberately no update/delete route here: policy_store.supersede()
is the only write operation on stored policy (see policy_store.py's module
docstring), so this module only ever adds a new version.

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__status__ = "Development"
"""

from quart import Blueprint
from quart.views import request

import api_common as apiVC
import policy_store as PS
from common import rbac

_PERM = "system.manage_academic_policy"


def init_routes(bp: Blueprint):
    bp.add_url_rule('/policy_groups', view_func=policy_groups, methods=['GET'])
    bp.add_url_rule('/policy_versions/<string:group>',
                     view_func=policy_versions, methods=['GET'])
    bp.add_url_rule('/policy_validate', view_func=policy_validate,
                     methods=['POST'])
    bp.add_url_rule('/policy_supersede', view_func=policy_supersede,
                     methods=['POST'])


def _version_json(v: PS.ResolvedPolicy) -> dict:
    return {
        "version_id": v.version_id,
        "group": v.group,
        "effective_from": v.effective_from,
        "effective_to": v.effective_to,
        "is_sealed": v.is_sealed,
        "note": v.note,
        "recorded_by": v.recorded_by,
        "recorded_ts": v.recorded_ts,
        # Concrete, already-recorded sessions this version was/is in force
        # for -- alongside effective_from/effective_to, which name the
        # governed range itself (open-ended when effective_to is None).
        "closed_sessions_governed": [s for s in PS.closed_sessions()
                                     if v.covers(s)],
        "payload": v.payload_dict(),
    }


@rbac(permissions=[_PERM])
async def policy_groups():
    groups = PS.declared_groups()
    return apiVC.ok_json([{"name": name, "doc": spec.doc}
                          for name, spec in sorted(groups.items())])


@rbac(permissions=[_PERM])
async def policy_versions(group):
    spec = PS.spec_for(group)
    if spec is None:
        return apiVC.error_json(f"No such policy group: {group}")
    return apiVC.ok_json({
        "group": group,
        "doc": spec.doc,
        "seal_line": PS.seal_line(),
        "versions": [_version_json(v) for v in PS.versions(group)],
    })


@rbac(permissions=[_PERM])
async def policy_validate():
    """Dry-runs a proposed ruleset through the group's builder/validator
    without storing it, so the UI can check a draft before superseding."""
    fd = await request.get_json(force=True)
    PS.validate_payload(fd.get("group"), fd.get("payload"))
    return apiVC.ok_json("Payload is valid.")


@rbac(permissions=[_PERM])
async def policy_supersede():
    fd = await request.get_json(force=True)
    group = fd.get("group")
    effective_from_session = fd.get("effective_from_session")
    payload = fd.get("payload")
    if not group or not effective_from_session or \
            not isinstance(payload, dict):
        return apiVC.error_json(
            "Please supply the policy group, the session this version "
            "takes effect from, and the complete ruleset payload.")
    PS.supersede(group, effective_from_session, payload,
                 note=fd.get("note"),
                 login_id=apiVC.current_login_id())
    return apiVC.ok_json({
        "group": group,
        "seal_line": PS.seal_line(),
        "versions": [_version_json(v) for v in PS.versions(group)],
    })
