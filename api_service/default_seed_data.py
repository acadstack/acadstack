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
import vocab_defaults as VD

# List of (Model, [row_dict, ...]) pairs. Populated by later phases as
# they introduce DB-backed defaults that must reach existing installs.
SEED_SPECS: list[tuple[Type[ORM.Model], list[dict]]] = [
    (M.SystemSetting, [
        dict(group="vocab", name=name, is_json=True, value_json=items)
        for name, items in VD.ALL.items()
    ]),
]


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
