"""Loads institution-specific code into the running app.

AcadStack is deployed by different institutions whose academic rules
differ in ways configuration cannot express -- an approval step that
needs a locally computed eligibility rule, a different notification
channel. That code lives in the institution's own package, not here.

What an institution may change is decided by the workflow engine
(:mod:`domain.workflow`), not by this module: approval chains are
transition tables, and the logic a row refers to -- guards, checks and
effects -- is registered by name. A plugin registers *more* of those
names with :func:`domain.workflow.guard`, :func:`~domain.workflow.check`
and :func:`~domain.workflow.effect`; the institution then references
them from its stored transition table (``POST /workflow_save``). There
is deliberately no second way to replace a decision: one mechanism, one
place to look when asking why a record moved.

This module only finds and runs that registration code. It stays
in-process: AcadStack is a modular monolith by decision, and an
extension is not a reason to introduce a network boundary.

Example plugin package::

    # pyproject.toml of the institution's package
    [project.entry-points."acadstack.plugins"]
    iitrpr = "iitrpr_acadstack.hooks:register"

    # iitrpr_acadstack/hooks.py
    from domain import workflow as WF
    from domain.errors import PolicyViolation

    def register():
        @WF.check("iitrpr.no_backlogs")
        def no_backlogs(ctx, max_backlogs=0):
            if backlog_count(ctx.record.student) > max_backlogs:
                raise PolicyViolation("Clear your backlogs first.")

    # ...then add {"name": "iitrpr.no_backlogs"} to the enrolment
    # workflow's checks (or one row's) through the workflow admin screen.
"""

import logging


def load_plugins(group: str = "acadstack.plugins") -> list:
    """Imports every installed distribution advertising ``group`` and
    calls the object the entry point names, so it can register its
    workflow guards, checks and effects. Called once from
    ``create_app``.

    A plugin that fails to load is logged and skipped rather than taking
    the whole app down: a broken optional extension should not stop
    course registration.
    """
    from importlib.metadata import entry_points

    loaded = []
    try:
        eps = entry_points(group=group)
    except Exception:
        logging.exception("Could not enumerate '%s' entry points.", group)
        return loaded

    for ep in eps:
        try:
            target = ep.load()
            if callable(target):
                target()
            loaded.append(ep.name)
            logging.info("Loaded AcadStack plugin '%s' from %s.",
                         ep.name, ep.value)
        except Exception:
            logging.exception("Failed to load AcadStack plugin '%s' (%s).",
                              ep.name, getattr(ep, "value", "?"))
    return loaded
