"""The approval workflows: one plain function per chain.

Each takes the acting user, the record's current status, the requested
action or status and any facts about the record the caller looked up, and
returns the next status or raises AcadStackException. They never touch the
database or the session.
"""

from common import AcadStackException


def enrolment_next_status(actor, status, action, is_instructor, is_advisor):
    """Enrolment approval: the course coordinator approves IPEN -> APEN,
    then the batch advisor APEN -> ENRO. ``action`` is "approve"; anything
    else rejects."""
    approve = action == "approve"
    if actor.has("enrolments.edit:any"):
        return "ENRO" if approve else "ASREJ"
    # Instructors and batch advisors approve their step through
    # enrolments.approve:own.
    own = actor.has("enrolments.approve:own")
    # User is course instructor
    if own and is_instructor and not is_advisor:
        return "APEN" if approve else "IREJ"
    # User is batch advisor
    if own and is_advisor and not is_instructor:
        return "ENRO" if approve else "AREJ"
    # User is both instructor and batch advisor
    if own and is_instructor and is_advisor and status == "IPEN":
        return "APEN" if approve else "AREJ"
    if own and is_instructor and is_advisor and status == "APEN":
        return "ENRO" if approve else "AREJ"
    # Advisor's step for any enrolment
    if actor.has("enrolments.approve:any") and status == "APEN":
        return "ENRO" if approve else "AREJ"
    raise AcadStackException("You do not have privileges to change one or more enrollments!")


# DC statuses each scope of dc.edit may change, and the statuses it may
# move them to: the supervisor drafts (or deletes the draft) and submits to
# the HoD, the HoD forwards to the Dean or returns to the supervisor.
# dc.edit:any (Dean, academic section) makes any change, including approving.
_DC_STEPS = {
    "own": ({None, "DRA", "RTS"}, {"DRA", "SUB", "DEL"}),
    "dept": ({None, "SUB", "RTH"}, {"DRA", "SUB", "FTD", "RTS"}),
}


def dc_next_status(actor, old_status, requested):
    """DC approval: DRA -> SUB (supervisor), SUB -> FTD or RTS (HoD),
    FTD -> APP or RTH (Dean). ``old_status`` is None for a new DC."""
    if actor.has("dc.edit:any"):
        return requested
    steps = [s for scope, s in _DC_STEPS.items() if actor.has(f"dc.edit:{scope}")]
    if not any(old_status in editable for editable, _ in steps):
        raise AcadStackException("Insufficient privileges to change  "
                                 "Please contact academic section.")
    if requested != old_status and \
            not any(old_status in editable and requested in targets
                    for editable, targets in steps):
        raise AcadStackException(f"Cannot change the DC status from {old_status} "
                                 f"to {requested}!")
    return requested


def ppr_next_status(actor, old_status, requested, is_chair):
    """PhD progress report: a DC member submits the draft (DRA -> SUB) and
    the DC chair approves it (SUB -> APP). ppr.edit:any makes any change,
    but only the DC chair may leave a report approved."""
    if old_status != requested and not actor.has("ppr.edit:any") \
            and f"{old_status}>{requested}" not in ("DRA>SUB", "SUB>APP"):
        raise AcadStackException("Cannot change the report status!")
    if requested == "APP" and not is_chair:
        raise AcadStackException("Only DC chair can approve the report!")
    return requested
