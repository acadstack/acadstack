"""In-process extension points for institution-specific behaviour.

AcadStack is deployed by different institutions whose academic rules
differ in ways configuration cannot express -- an approval chain with an
extra step, a different notification channel, a locally computed
eligibility rule. Those institutions need to replace a *behaviour*, not
just a value.

The mechanism is deliberately small and in-process: AcadStack is a
modular monolith by decision, and an override point is not a reason to
introduce a network boundary.

* Core declares an extension point and registers the stock
  implementation with :func:`extension_point`.
* A deployment overrides it with :func:`override`, either from a local
  module or from a pip-installed package that advertises an
  ``acadstack.plugins`` entry point.
* Domain code calls it with :func:`call`, which always resolves to the
  override if one is registered and to the default otherwise.

One implementation wins, rather than a chain of listeners: these points
return a decision (the next enrolment status, say), and "all of them run
in some order" has no meaningful answer for a decision. Points that
genuinely fan out (notifications) can be given a list-valued
implementation by the institution that needs it.

Example plugin package::

    # setup.cfg / pyproject.toml of the institution's package
    [project.entry-points."acadstack.plugins"]
    iitrpr = "iitrpr_acadstack.hooks:register"

    # iitrpr_acadstack/hooks.py
    from domain import plugins

    def register():
        @plugins.override(plugins.ENROLMENT_NEXT_STATUS)
        def next_status(actor, ownership, current_status, action):
            ...
"""

import logging
import threading
from typing import Callable, Dict, Optional

# ---- Names of the extension points core declares. Keep them here so
# ---- they can be imported without importing the domain module that
# ---- defines the default (which would be a cycle).

#: Decide the enrolment status an approve/reject action moves a record
#: to. See domain.enrolment.default_next_enrol_status for the signature
#: and the stock implementation.
ENROLMENT_NEXT_STATUS = "enrolment.next_status"

#: Notify interested parties that an enrolment's status changed.
#: Signature: (enrolment_id, old_record=None) -> None
ENROLMENT_NOTIFY = "enrolment.notify_status_change"


class _Point:
    __slots__ = ("name", "default", "override", "override_source")

    def __init__(self, name: str):
        self.name = name
        self.default: Optional[Callable] = None
        self.override: Optional[Callable] = None
        self.override_source: Optional[str] = None


_lock = threading.Lock()
_points: Dict[str, _Point] = {}


def _point(name: str) -> _Point:
    p = _points.get(name)
    if p is None:
        p = _points[name] = _Point(name)
    return p


def extension_point(name: str) -> Callable:
    """Decorator registering ``func`` as the stock implementation of
    ``name``. Applied by core domain modules at import time."""

    def decorate(func: Callable) -> Callable:
        with _lock:
            _point(name).default = func
        return func

    return decorate


def override(name: str) -> Callable:
    """Decorator registering an institution's replacement for ``name``.

    Registering twice for the same point is allowed but logged at
    WARNING: two plugins fighting over one behaviour is a deployment
    mistake worth seeing in the log rather than a silent last-wins.
    """

    def decorate(func: Callable) -> Callable:
        source = f"{getattr(func, '__module__', '?')}.{getattr(func, '__qualname__', '?')}"
        with _lock:
            p = _point(name)
            if p.override is not None and p.override is not func:
                logging.warning(
                    "Extension point '%s' already overridden by %s; "
                    "replacing it with %s.", name, p.override_source, source)
            p.override = func
            p.override_source = source
        logging.info("Extension point '%s' overridden by %s.", name, source)
        return func

    return decorate


def implementation(name: str) -> Callable:
    """The callable currently in force for ``name``."""
    p = _points.get(name)
    if p is None or (p.default is None and p.override is None):
        raise LookupError(f"No implementation registered for extension "
                          f"point '{name}'.")
    return p.override or p.default


def call(name: str, *args, **kwargs):
    """Invoke the implementation in force for ``name``."""
    return implementation(name)(*args, **kwargs)


def is_overridden(name: str) -> bool:
    p = _points.get(name)
    return bool(p and p.override)


def registered() -> dict:
    """Introspection for diagnostics and, later, the admin GUI."""
    return {
        name: {
            "default": getattr(p.default, "__qualname__", None),
            "override": p.override_source,
        }
        for name, p in sorted(_points.items())
    }


def clear_overrides() -> None:
    """Drops every registered override, keeping the stock defaults.
    For tests; not used by the running app."""
    with _lock:
        for p in _points.values():
            p.override = None
            p.override_source = None


def load_plugins(group: str = "acadstack.plugins") -> list:
    """Imports every installed distribution advertising ``group`` and
    calls the object the entry point names, so it can register its
    overrides. Called once from ``create_app``.

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
