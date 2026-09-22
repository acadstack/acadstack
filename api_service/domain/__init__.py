"""The AcadStack domain (service) layer.

Modules in this package hold business logic as plain functions over the
Peewee models, with explicit inputs and return values. They are the layer
the ``api_*.py`` HTTP adapters call into, and the layer that background
jobs (``bg_tasks.py``, ``api_reports.py``) can reuse without faking an
HTTP request.

Rules for everything under ``domain/`` -- see docs/service-layer.md for
the reasoning:

1. No ``quart`` import, and in particular no ``quart.session`` read. The
   acting user arrives as an explicit :class:`domain.context.Actor`
   argument.
2. No ``api_common`` import (it is the HTTP adapter's toolbox and reads
   the session). ``domain.persistence`` provides the session-free
   equivalents of ``save_entity``/``update_entity``.
3. Domain functions are ``def``, not ``async def``. Nothing in here does
   network I/O that would benefit from the event loop; staying
   synchronous is what makes these callable from scripts and jobs.
4. Policy arrives as data (see :mod:`domain.policy`), not by calling the
   settings accessor ad hoc, so a test can pass arbitrary policy.

``tests/test_domain_boundaries.py`` enforces 1-3 mechanically.
"""
