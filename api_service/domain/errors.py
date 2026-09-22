"""Domain-level exceptions.

All of these derive from ``AcadStackException`` so that the existing
``except AcadStackException`` handlers in the api_* modules keep catching
them and keep producing the same ``{"status": "ERROR", "body": <message>}``
envelope. The subclasses exist so an adapter (or a later phase) can
distinguish "you may not do this" from "this is not valid" without
string-matching the message.
"""

from common import AcadStackException


class DomainError(AcadStackException):
    """Base class for errors raised by the domain layer."""


class PermissionDenied(DomainError):
    """The acting user is not allowed to perform this operation.

    Raised for *resource-scoped* checks that the domain owns (e.g. "you
    are neither the course instructor nor the batch advisor for this
    enrolment"). Coarse role gating still happens at the HTTP boundary,
    in the @rbac decorator -- see docs/service-layer.md, Q1.
    """


class PolicyViolation(DomainError):
    """The operation is blocked by academic policy or calendar state."""
