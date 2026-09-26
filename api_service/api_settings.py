"""View functions for the DB-backed system settings/vocabulary admin screen.

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__status__ = "Development"
"""

from quart import Blueprint

import api_common as apiVC
import config_integrity as CI
import permissions as PERM
import settings_store as ST
from common import rbac

_PERM = "system.manage_settings"

# Groups this generic admin screen does not manage. "permission" has its
# own dedicated write path (permissions.save_permission_mapping) with a
# self-lockout guard that a plain settings_save() would bypass, and its
# own, separately-grantable permission (system.manage_permissions) -- so
# it is kept out of reach of anyone holding only system.manage_settings.
_EXCLUDED_GROUPS = {PERM.GROUP}


def _visible(items):
    return [it for it in items if it["group"] not in _EXCLUDED_GROUPS]


def init_routes(bp: Blueprint):
    bp.add_url_rule('/settings_describe', view_func=settings_describe,
                     methods=['GET'])
    bp.add_url_rule('/settings_save', view_func=settings_save,
                     methods=['POST'])
    bp.add_url_rule('/settings_delete', view_func=settings_delete,
                     methods=['POST'])
    bp.add_url_rule('/permissions_describe', view_func=permissions_describe,
                     methods=['GET'])
    bp.add_url_rule('/permissions_save', view_func=permissions_save,
                     methods=['POST'])


@rbac(permissions=[_PERM])
async def settings_describe():
    """Every declared setting/vocabulary, grouped, with its current
    effective value -- the schema the admin form renders itself from."""
    return apiVC.ok_json(_visible(ST.describe_settings()))


@rbac(permissions=[_PERM])
async def settings_save():
    fd = await apiVC.json_body()
    values = fd.get("values") or {}
    if not values:
        return apiVC.error_json("Nothing supplied to save.")
    blocked = sorted(k for k in values
                     if k.split(".", 1)[0] in _EXCLUDED_GROUPS)
    if blocked:
        return apiVC.error_json(
            "These settings are managed on a separate screen and "
            f"cannot be changed here: {', '.join(blocked)}")
    CI.guarded_save_settings(values, login_id=apiVC.current_login_id())
    return apiVC.ok_json(_visible(ST.describe_settings()))


@rbac(permissions=[_PERM])
async def settings_delete():
    """Reverts one setting to its declared default by removing its stored
    row (settings_store.delete_setting)."""
    fd = await apiVC.json_body()
    key = fd.get("key")
    if not key:
        return apiVC.error_json("Please supply the setting key to reset.")
    if key.split(".", 1)[0] in _EXCLUDED_GROUPS:
        return apiVC.error_json(
            "This setting is managed on a separate screen and cannot "
            "be reset here.")
    CI.guarded_delete_setting(key, login_id=apiVC.current_login_id())
    return apiVC.ok_json(_visible(ST.describe_settings()))


# ===================== permission->role mapping =====================
# The "permission" group excluded above, on its own screen and behind its
# own permission, written only through save_permission_mapping() so the
# self-lockout guard always applies.

@rbac(permissions=[PERM.MANAGE_PERMISSIONS])
async def permissions_describe():
    """Every declared permission with its doc, default and current roles,
    plus the role vocabulary -- see permissions.describe_mapping()."""
    return apiVC.ok_json(PERM.describe_mapping(apiVC.current_actor()))


@rbac(permissions=[PERM.MANAGE_PERMISSIONS])
async def permissions_save():
    """Saves {"values": {permission_name: [role_code, ...]}} for the
    permissions being changed; answers with the updated mapping."""
    fd = await apiVC.json_body()
    values = fd.get("values") or {}
    if not values:
        return apiVC.error_json("Nothing supplied to save.")
    actor = apiVC.current_actor()
    PERM.save_permission_mapping(values, actor)
    return apiVC.ok_json(PERM.describe_mapping(actor))
