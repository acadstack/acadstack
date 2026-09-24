# Schema migrations

Plain `.sql` files, applied in filename order by `schema_migrations.py`, at
most once each (tracked by filename in the `schema_migrations` table).

## Adding a migration

1. Name the file `NNNN_short_description.sql`, where `NNNN` is the next
   zero-padded sequence number (e.g. `0002_add_grading_policy_table.sql`).
   Filenames sort and apply in plain lexical order, so always increment.
2. Write it defensively, so it is safe to run against *either* an
   existing deployment that needs the change, *or* a brand-new database
   where `models.py create_schema()` already created the schema in its
   current (post-change) shape:
   - `ALTER TABLE ... ADD COLUMN IF NOT EXISTS ...`
   - `CREATE TABLE IF NOT EXISTS ...` / `CREATE INDEX IF NOT EXISTS ...`
   - `DROP ... IF EXISTS ...`
   - Guard anything else (renames, constraint changes) with a
     `DO $$ ... IF NOT EXISTS (...) THEN ... END IF; END $$;` block.
3. Keep one logical change per file. The whole file runs inside a single
   transaction, so partial application of one file is not a concern, but
   small files keep review and rollback-by-hand easier.
4. Never edit a migration file that has already shipped/been applied
   anywhere. Add a new one instead.
5. This directory is for schema changes only (DDL). Default/seed data
   belongs in `default_seed_data.py`, which runs after migrations on every
   startup and only inserts rows that are missing.

## What does NOT need a migration

Adding a brand-new table that's also added to `models.py`'s
`create_schema()` list does not strictly need a migration file:
`create_schema()` runs `CREATE TABLE IF NOT EXISTS` for every model on
every startup, so a new table appears on existing deployments for free.
Migrations exist for what `create_schema()` cannot do: `ALTER`-ing a table
that already exists (new/changed/dropped columns, indexes, constraints).
When in doubt, add the migration anyway -- it's a no-op once applied.

## 0001_baseline.sql

A no-op marker (comment only). It exists so `schema_migrations` has a row
after the first startup post-upgrade, and so future migrations have a
concrete "migrations start here" anchor to number from. Everything before
it is captured by `models.py` as it stood at the time this tooling was
introduced.
