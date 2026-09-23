"""The acting user, as data.

Domain functions need to know who is acting -- to check ownership, to
stamp audit columns, to decide an approval transition. Today that
knowledge is read straight out of ``quart.session`` by
``api_common.is_user_in_role()`` / ``logged_in_user()``, which is what
makes the logic untestable and unusable outside a request (see
``api_reports.__process_credits_gen_request``, a background job that
calls into enrolment logic with no session at all).

So the acting user becomes an explicit first argument: an :class:`Actor`,
built once at the HTTP boundary by ``api_common.current_actor()`` and
passed down. Jobs build one with :meth:`Actor.system`.
"""

from dataclasses import dataclass
from typing import Optional, Sequence, Union

import permissions as PERM

# Role code used for actors that are not a logged-in human (scheduled
# jobs, CLI scripts). Deliberately not a real role code from the roles
# vocabulary, so has_role() never matches a privileged branch by
# accident.
SYSTEM_ROLE = "SYS"


@dataclass(frozen=True)
class Actor:
    """Who is performing a domain operation.

    Attributes mirror what the session carries plus the ``User`` row id,
    which ownership SQL needs. Frozen because a domain function must not
    be able to edit who it is acting as.
    """

    login_id: str
    role: str
    user_id: Optional[int] = None
    degree: Optional[str] = None
    dept_name: Optional[str] = None
    org_id: Optional[str] = None
    is_system: bool = False

    @classmethod
    def system(cls, login_id: str = "system"):
        """An actor for code running outside any request (jobs, scripts).

        ``txn_login_id`` stamping keeps working, and no role branch
        matches, so a job cannot accidentally inherit ACA privileges.
        """
        return cls(login_id=login_id, role=SYSTEM_ROLE, is_system=True)

    def has_role(self, roles: Union[str, Sequence[str]]) -> bool:
        """Whether this actor holds one of ``roles``.

        ``roles`` may be a single role code, a list of codes, or a
        comma-separated string such as ``"DEA,ACA,RES"`` -- the string
        form is split into codes before the membership test, so a role
        code that happens to be a substring of another never matches by
        accident (Phase 8 fixed this; it used to be a substring test).
        """
        codes = roles.split(",") if isinstance(roles, str) else roles
        return self.role in codes

    def can(self, permission: str) -> bool:
        """Whether this actor's role holds the named permission, per the
        DB-backed permission->role mapping (see ``permissions.py``)."""
        return PERM.role_has_permission(self.role, permission)

    def describe(self) -> str:
        return f"{self.login_id} ({self.role})"
