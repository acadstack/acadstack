"""Session-free persistence helpers.

``api_common.save_entity``/``update_entity`` stamp the ``BaseModel``
audit columns from ``quart.session``, which makes every write reachable
only from inside a request. The stamping logic lives here instead and
takes the acting :class:`domain.context.Actor`; ``api_common`` keeps its
two functions as thin wrappers that resolve the actor from the session,
so no other module had to change.
"""

from datetime import datetime as DT
from typing import Optional, Type

from playhouse.shortcuts import model_to_dict

import models as M
from domain.context import Actor


def save(obj: M.BaseModel, actor: Optional[Actor]):
    """Inserts (or saves) ``obj``, stamping audit columns.

    ``actor=None`` (a write outside a request) leaves ``txn_login_id`` NULL.
    """
    obj.txn_login_id = actor.login_id if actor else None
    obj.upd_ts = DT.now()
    obj.ins_ts = DT.now()
    return obj.save()


def update(entity: Type[M.BaseModel], obj: M.BaseModel,
           actor: Optional[Actor], exclude=None) -> int:
    """Updates ``obj`` with an optimistic-locking check on ``txn_no``.

    Returns the number of rows affected: 0 means another transaction
    updated the row first, and callers treat that as a failure.
    ``actor=None`` (a write outside a request) leaves ``txn_login_id`` NULL.
    """
    txn_no = int(obj.txn_no)
    obj.txn_no = 1 + txn_no  # For optimistic locking
    obj.upd_ts = DT.now()
    obj.txn_login_id = actor.login_id if actor else None
    # Copied, not appended to: api_common.update_entity used to declare
    # `exclude=[]` and append to it, so the shared default list grew for
    # the life of the process and a caller's own list came back longer
    # than they passed it.
    exclude = list(exclude) if exclude else []
    # We exclude the insert timestamp from the update
    exclude.append(getattr(entity, "ins_ts"))
    mdict = model_to_dict(obj, recurse=False, exclude=exclude)
    return entity.update(mdict).where(
        (entity.txn_no == obj.txn_no - 1) &  # Optimistic locking check
        (entity.id == obj.id)).execute()
