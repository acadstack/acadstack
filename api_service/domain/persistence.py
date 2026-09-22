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

    ``actor=None`` reproduces what ``save_entity(outside_request=True)``
    has always written: the literal string "None" in ``txn_login_id``.
    """
    obj.txn_login_id = actor.login_id if actor else "None"
    obj.upd_ts = DT.now()
    obj.ins_ts = DT.now()
    return obj.save()


def update(entity: Type[M.BaseModel], obj: M.BaseModel,
           actor: Optional[Actor], exclude=None) -> int:
    """Updates ``obj`` with an optimistic-locking check on ``txn_no``.

    Returns the number of rows affected: 0 means another transaction
    updated the row first, and callers treat that as a failure.
    ``actor=None`` writes "Out of request", as ``update_entity`` does.
    """
    txn_no = int(obj.txn_no)
    obj.txn_no = 1 + txn_no  # For optimistic locking
    obj.upd_ts = DT.now()
    obj.txn_login_id = actor.login_id if actor else "Out of request"
    # NOTE: callers may pass a list they own; it is appended to, matching
    # the long-standing behaviour of api_common.update_entity.
    exclude = [] if exclude is None else exclude
    # We exclude the insert timestamp from the update
    exclude.append(getattr(entity, "ins_ts"))
    mdict = model_to_dict(obj, recurse=False, exclude=exclude)
    return entity.update(mdict).where(
        (entity.txn_no == obj.txn_no - 1) &  # Optimistic locking check
        (entity.id == obj.id)).execute()
