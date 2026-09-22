-- Adds Course.s_hours/credits, computed once server-side from ltp's L/T/P
-- (S = 2L - T + 0.5P, C = L + 0.5P) instead of being re-derived by every
-- query that needs them. See common.compute_course_ltp(), which is now the
-- only place that formula is evaluated (it used to be implemented twice,
-- once in Python and again in SQL).
--
-- Backfills existing rows using the same formula, applied to whatever L/T/P
-- is already stored (ltp's first three dash-separated fields), regardless
-- of what its own S/C suffix currently says -- several existing rows have a
-- suffix that does not actually match their own L/T/P (see the
-- demo_data.py / sql_statements.toml fixes in this same change).
-- REAL to match peewee's FloatField (models.py Course.s_hours/credits),
-- so an upgraded deployment ends up with the same column type
-- create_schema() would generate on a fresh install.
ALTER TABLE course ADD COLUMN IF NOT EXISTS s_hours REAL;
ALTER TABLE course ADD COLUMN IF NOT EXISTS credits REAL;

UPDATE course
SET s_hours = ROUND(
        2 * split_part(ltp, '-', 1)::numeric
          - split_part(ltp, '-', 2)::numeric
          + split_part(ltp, '-', 3)::numeric / 2, 2),
    credits = ROUND(
        split_part(ltp, '-', 1)::numeric
          + split_part(ltp, '-', 3)::numeric / 2, 2)
WHERE ltp IS NOT NULL
  AND ltp ~ '^[0-9]+(\.[0-9]+)?-[0-9]+(\.[0-9]+)?-[0-9]+(\.[0-9]+)?'
  AND (s_hours IS NULL OR credits IS NULL);
