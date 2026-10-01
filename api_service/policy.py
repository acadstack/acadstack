"""Permission checks.

The code checks permissions, never roles. A role is a named set of
permissions, stored in the RolePermission table and edited by users who hold
``permissions.manage``.

A permission is named ``area.action``, optionally with a scope suffix that
limits which records it covers:
    ``:any``   every record
    ``:dept``  records of the actor's own department
    ``:own``   records the actor is linked to: the actor themself, or the
               course they teach, the student they supervise, and so on;
               the linking rule is given where the check is made
    ``:pg``    courses of level PG or ALL only

``@require("area.action")`` lets a request through when the actor holds the
permission at any scope; ``Actor.allowed()`` then checks the record at hand.

The ``roster.*`` permissions mark the roles whose users count as a kind of
person (student, instructor, department head, academic section); the code
finds those roles with ``roles_with()``.

The role -> permissions map is cached in this process (the app runs as a
single process); saving clears the cache, so a change made directly with SQL
is seen after a restart.
"""

import inspect
import logging
from dataclasses import dataclass
from functools import wraps

from quart import jsonify, session

import models as M

ADMIN_PERM = "permissions.manage"

_role_perms = None


def _cached_grants() -> dict:
    global _role_perms
    if _role_perms is None:
        loaded = {}
        for rp in M.RolePermission.select():
            loaded.setdefault(rp.role, set()).add(rp.permission)
        _role_perms = {r: frozenset(p) for r, p in loaded.items()}
    return _role_perms


def perms_of(role: str) -> frozenset:
    return _cached_grants().get(role, frozenset())


def roles_with(perm: str) -> list:
    """Codes of the roles granted ``perm``, e.g. the roles whose users count
    as students for ``roster.student``."""
    return sorted(r for r, p in _cached_grants().items() if perm in p)


def clear_cache():
    global _role_perms
    _role_perms = None


@dataclass(frozen=True)
class Actor:
    """The logged-in user making the request."""
    id: int
    login_id: str
    role: str
    dept: str
    perms: frozenset

    def has(self, code: str) -> bool:
        """Holds exactly this permission code, e.g. ``fees.view:any``."""
        return code in self.perms

    def can(self, perm: str) -> bool:
        """Holds the permission at any scope."""
        return perm in self.perms or any(p.startswith(perm + ":") for p in self.perms)

    def allowed(self, perm: str, **scopes) -> bool:
        """Holds the permission unscoped or at ``:any``, or at a scope ``s``
        whose check ``scopes[s]()`` passes. The checks run only when needed."""
        if perm in self.perms or f"{perm}:any" in self.perms:
            return True
        return any(f"{perm}:{s}" in self.perms and check() for s, check in scopes.items())

    @property
    def own_records_only(self) -> bool:
        """Holds no permission that covers every record."""
        return not any(p.endswith(":any") for p in self.perms)


def current_actor():
    u = session.get("user")
    if not u:
        return None
    return Actor(u["id"], u["login_id"], u["role"], u.get("dept"), perms_of(u["role"]))


def require(perm: str, alert: bool = False):
    """Decorator for views: the request needs a logged-in user who holds
    ``perm`` at some scope. With ``alert``, a refusal is reported as an
    access violation, which also locks the account of a user who may act
    only on their own records (a student)."""
    def decor(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            actor = current_actor()
            if not actor:
                msg = "Login required to access this operation."
                logging.warning(msg)
                return jsonify({"status": "ERROR", "body": msg})
            if not actor.can(perm):
                msg = "You do not have required permissions to access."
                logging.warning(f"{actor.login_id} lacks {perm}.")
                if alert:
                    # Imported here: create_email imports this module.
                    from create_email import send_access_violation_alert
                    send_access_violation_alert(f"User {actor.login_id} attempted "
                                                f"{func.__name__} without {perm}.")
                    msg += " This incident has been reported."
                return jsonify({"status": "ERROR", "body": msg})
            # Some views are plain functions; their result is not awaitable.
            result = func(*args, **kwargs)
            if inspect.isawaitable(result):
                result = await result
            return result

        wrapper.permission = perm
        return wrapper
    return decor


def all_grants():
    return {
        "roles": [{"code": r.code, "label": r.label} for r in M.Role.select().order_by(M.Role.code)],
        "permissions": [{"code": p.code, "description": p.description}
                        for p in M.Permission.select().order_by(M.Permission.code)],
        "grants": {r: sorted(p) for r, p in _grant_rows().items()},
    }


def _grant_rows():
    rows = {}
    for rp in M.RolePermission.select():
        rows.setdefault(rp.role, set()).add(rp.permission)
    return rows


def save(role: str, label: str, perms, actor: Actor):
    """Creates or relabels a role and replaces its permissions. Raises
    ValueError if the input is invalid or would take ``permissions.manage``
    away from the actor's own role."""
    if not role or len(role) > 4:
        raise ValueError("Role code must be 1 to 4 characters.")
    perms = set(perms or [])
    unknown = perms - {p.code for p in M.Permission.select(M.Permission.code)}
    if unknown:
        raise ValueError(f"Unknown permissions: {', '.join(sorted(unknown))}")
    if role == actor.role and ADMIN_PERM not in perms:
        raise ValueError(f"You cannot remove {ADMIN_PERM} from your own role.")
    with M.db.atomic():
        existing = M.Role.get_or_none(M.Role.code == role)
        if existing:
            if label and label != existing.label:
                existing.label = label
                existing.save()
        elif label:
            M.Role.create(code=role, label=label)
        else:
            raise ValueError("A new role needs a label.")
        M.RolePermission.delete().where(M.RolePermission.role == role).execute()
        if perms:
            M.RolePermission.insert_many(
                [{"role": role, "permission": p} for p in sorted(perms)]).execute()
    clear_cache()
