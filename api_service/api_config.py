"""View functions for exporting/importing the full configuration document
(config_transfer.py).

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__status__ = "Development"
"""

from quart import Blueprint
from quart.views import request

import api_common as apiVC
import config_transfer as CT
from common import rbac

_EXPORT_PERM = "system.export_config"
_IMPORT_PERM = "system.import_config"


def init_routes(bp: Blueprint):
    bp.add_url_rule('/config_export', view_func=config_export,
                     methods=['GET'])
    bp.add_url_rule('/config_import', view_func=config_import,
                     methods=['POST'])


@rbac(permissions=[_EXPORT_PERM])
async def config_export():
    include_permissions = \
        request.args.get("include_permissions", "true") != "false"
    include_policy_history = \
        request.args.get("include_policy_history", "true") != "false"
    doc = CT.export_config(
        include_permissions=include_permissions,
        include_policy_history=include_policy_history)
    return apiVC.ok_json(doc)


@rbac(permissions=[_IMPORT_PERM])
async def config_import():
    fd = await apiVC.json_body()
    document = fd.get("document") if isinstance(fd, dict) else None
    if not isinstance(document, dict):
        return apiVC.error_json(
            "Please supply the configuration document to import.")
    report = CT.import_config(document, actor=apiVC.current_actor())
    return apiVC.ok_json(report)
