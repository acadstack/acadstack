"""Idempotent default-data seeder.

Runs on every app startup, after migrations. Each entry in SEED_SPECS is a
(model, rows) pair; every row is inserted with
``INSERT ... ON CONFLICT DO NOTHING`` (mirroring the pattern already used
by dates_save() in api_wflow.py), so a row already present -- whether
because a previous startup seeded it or because an institution configured
its own value under the same unique key -- is left untouched. This is
purely additive: it never issues UPDATE/DELETE, so it is always safe to
run, in any order, any number of times.

SEED_SPECS is intentionally empty right now: no policy has been moved to
a database-backed table yet (see docs/refactor-plan.md, Phase 1 builds
the tooling; Phases 2-4 move actual values). Later phases append entries
here as they introduce settings/vocabulary rows that need to reach
existing installs on upgrade.

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__status__ = "Development"
"""

import logging
from typing import Type

import peewee as ORM

# List of (Model, [row_dict, ...]) pairs. Populated by later phases as
# they introduce DB-backed defaults that must reach existing installs.
SEED_SPECS: list[tuple[Type[ORM.Model], list[dict]]] = []


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

    if not inserted_counts:
        logging.info("No default seed data to insert.")

    return inserted_counts
