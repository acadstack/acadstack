"""Idempotent default-data seeder.

Runs on every app startup, after migrations. Each entry in SEED_SPECS is a
(model, rows) pair; every row is inserted with
``INSERT ... ON CONFLICT DO NOTHING`` (mirroring the pattern already used
by dates_save() in api_wflow.py), so a row already present -- whether
because a previous startup seeded it or because an institution configured
its own value under the same unique key -- is left untouched. This is
purely additive: it never issues UPDATE/DELETE, so it is always safe to
run, in any order, any number of times.

SEED_SPECS currently seeds one SystemSetting row per controlled
vocabulary (see vocab_defaults.py and settings_store.py's "vocab" group):
a fresh install gets vocab_defaults.py's lists in the DB on first boot; an
institution that later edits/extends a vocabulary through the admin GUI
keeps its own rows forever, since this seeder never overwrites an
existing row.

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__status__ = "Development"
"""

import logging
from typing import Type

import peewee as ORM

import models as M
import permissions as PERM
import settings_store as ST
import vocab_defaults as VD
from domain import milestones as MS

# List of (Model, [row_dict, ...]) pairs. Populated by later phases as
# they introduce DB-backed defaults that must reach existing installs.
SEED_SPECS: list[tuple[Type[ORM.Model], list[dict]]] = [
    (M.SystemSetting, [
        dict(group="vocab", name=name, is_json=True, value_json=items)
        for name, items in VD.ALL.items()
    ] + [
        # One row per named permission (permissions.py), each defaulted to
        # the role list that reproduces today's pre-Phase-8 behaviour at
        # the call site(s) it replaces. INSERT ... ON CONFLICT DO NOTHING
        # like every other seed row, so an institution that has since
        # edited a permission's role list through the admin GUI keeps it.
        dict(group=PERM.GROUP, name=name, is_json=True, value_json=spec.default)
        for name, spec in ST.declared_groups()[PERM.GROUP].specs.items()
    ]),
    # The academic milestone sequence (domain/milestones.py). Keyed on
    # code, so an institution's edited sequence is left alone.
    (M.MilestoneDefinition, MS.seed_rows()),
]


def seed_grading_policy() -> int:
    """Stores the baseline grading ruleset if the group has no version yet.

    Not a SEED_SPECS row, for two reasons. The payload is derived from
    ``domain.policy`` rather than typed out again -- a second copy of the
    grade rules is exactly what this whole refactor removed -- and the
    write has to respect the policy store's immutability rules, which a
    bulk ``INSERT ... ON CONFLICT DO NOTHING`` knows nothing about.

    Returns the number of versions stored (0 or 1). Safe to call on every
    startup: it does nothing once a version exists, and it never
    supersedes one, so an institution that has amended its rules keeps
    them forever.
    """
    # Imported here, not at module scope: domain.policy imports
    # policy_store, which imports this module's siblings, and the seeder is
    # also called from demo_data.py before the app is assembled.
    import acad_session as AS
    import policy_store as PS
    from domain import policy as POL

    already = (M.PolicyVersion
               .select()
               .where((M.PolicyVersion.policy_group == POL.GRADING) &
                      (M.PolicyVersion.is_deleted == False))  # noqa: E712
               .exists())
    if already:
        logging.info("Grading policy already recorded; not seeding.")
        return 0

    # The baseline is effective from long before any enrolment, so on an
    # install that has already closed a session it would land inside sealed
    # history and the store would rightly refuse it. Warn rather than
    # raise: a failed seed must not stop the app booting, and the in-code
    # baseline still answers every query.
    seal = M.max_closed_session_ord()
    if seal is not None and AS.ordinal(POL.BASELINE_EFFECTIVE_FROM) <= seal:
        logging.warning(
            f"Not seeding grading policy: it would take effect from "
            f"{POL.BASELINE_EFFECTIVE_FROM}, at or before the closed session "
            f"{M.seal_label()}. Record a ruleset effective from an open "
            f"session instead.")
        return 0

    PS.supersede(
        POL.GRADING, POL.BASELINE_EFFECTIVE_FROM,
        POL.grading_payload_from(POL.DEFAULT_GRADING_POLICY),
        note="Baseline academic grading rules, seeded at install.",
        login_id="SYSTEM")
    logging.info(f"Seeded baseline grading policy effective from "
                 f"{POL.BASELINE_EFFECTIVE_FROM}.")
    return 1


def seed_workflows() -> int:
    """Stores each approval workflow's baseline transition table if that
    workflow has no stored definition yet.

    Not SEED_SPECS rows: a workflow is a definition row plus its
    transitions, written together, and "seed missing rows" would merge
    the baseline into an institution's edited table -- quietly putting
    back an approval step they had removed. So it is all or nothing per
    workflow. Returns the number of workflows stored.
    """
    from domain import workflow as WF

    stored = 0
    for name in WF.names():
        if M.WorkflowDefinition.select().where(
                M.WorkflowDefinition.name == name).exists():
            continue
        WF.store(WF.baseline(name))
        logging.info(f"Seeded the baseline '{name}' workflow.")
        stored += 1
    return stored


def run_seed_defaults(seed_specs=None) -> dict:
    """Inserts any row in seed_specs that is missing, leaving existing
    rows (including institution-customized ones) untouched. Returns a
    dict of {model_name: inserted_row_count} for whatever actually got
    inserted.
    """
    specs = SEED_SPECS if seed_specs is None else seed_specs
    inserted_counts = {}

    for model, rows in specs:
        if not rows:
            continue
        pk_field = model._meta.primary_key
        result = (model.insert_many(rows)
                  .on_conflict(action="IGNORE")
                  .returning(pk_field)
                  .execute())
        inserted = len(list(result))
        inserted_counts[model.__name__] = inserted
        logging.info(f"Seed defaults for {model.__name__}: "
                     f"{inserted} of {len(rows)} candidate row(s) inserted "
                     f"(rest already present).")

    if seed_specs is None:
        # Only on the real seed run: a caller passing its own specs is
        # testing the mechanism, not provisioning an install.
        seeded = seed_grading_policy()
        if seeded:
            inserted_counts["PolicyVersion"] = seeded
        seeded = seed_workflows()
        if seeded:
            inserted_counts["WorkflowDefinition"] = seeded

    if not inserted_counts:
        logging.info("No default seed data to insert.")

    return inserted_counts
