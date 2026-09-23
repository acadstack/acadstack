-- 0004: session ordinals become month offsets on a shared timeline.
--
-- WHY
-- ---
-- Migration 0003 ordered sessions by an arbitrary within-year rank
-- (T1 < T2 < T3 < T4 < I < II < S, ordinal = year*10 + rank). That order
-- is a fiction once an institution runs more than one academic calendar:
-- a quarter-based programme's 2021-T1 and a semester-based programme's
-- 2021-I both BEGIN the academic year, but the old scheme placed them
-- four ranks apart. Effective-dated policy resolved on that scheme gives
-- two concurrent sessions different rulesets, which is how the "PhD
-- passing grades introduced in 2021" rule came to look as though it
-- oscillated between tracks.
--
-- The new scheme is ordinal = year*12 + (month the session starts,
-- counted from the start of the academic year). Concurrent sessions get
-- EQUAL ordinals, which is the correct answer to "which ruleset was in
-- force": whatever was in force that month governs both. See
-- acad_session.py, whose SESSION_TYPES table this function mirrors, and
-- tests/test_acad_session.py, which asserts the two cannot drift.
--
--   semester   I=0   II=6  S=10
--   quarter    T1=0  T2=3  T3=6  T4=9
--
-- WHAT THIS DOES
-- --------------
--   1. refuses to run if recomputing would collide two policy versions
--      of one group onto the same ordinal (nothing to merge them by);
--   2. drops the two CHECK constraints, which call the old function;
--   3. redefines the function;
--   4. recomputes both denormalised ordinal columns -- with the
--      immutability triggers suspended, since they exist precisely to
--      forbid the UPDATE this migration has to perform;
--   5. re-adds the CHECK constraints, which revalidates every row.
--
-- Step 4 is the only place in this codebase permitted to write sealed
-- policy rows. It is safe because it changes how a session is NUMBERED,
-- not which session a row is effective from: effective_from_session is
-- untouched, and the CHECK re-added in step 5 proves the numbers match
-- the (unchanged) session strings.


-- ---------------------------------------------------------------- 1.
-- Collision preflight. Two versions of one group at, say, 2021-I and
-- 2021-T1 are distinct rows today and the same instant afterwards. There
-- is no defensible automatic answer, so stop and make a human decide.
DO $$
DECLARE
    clash text;
BEGIN
    SELECT string_agg(detail, '; ') INTO clash FROM (
        SELECT policy_group || ' @ ' ||
               string_agg(effective_from_session, ', '
                          ORDER BY effective_from_session) AS detail
        FROM policyversion
        WHERE is_deleted = false
        GROUP BY policy_group,
                 substring(effective_from_session from 1 for 4)::integer * 12
                 + CASE substring(effective_from_session from 6)
                       WHEN 'T1' THEN 0 WHEN 'T2' THEN 3
                       WHEN 'T3' THEN 6 WHEN 'T4' THEN 9
                       WHEN 'I'  THEN 0 WHEN 'II' THEN 6
                       WHEN 'S'  THEN 10 END
        HAVING count(*) > 1
    ) AS collisions;

    IF clash IS NOT NULL THEN
        RAISE EXCEPTION
            'Cannot renumber session ordinals: these policy versions '
            'would land on the same instant, because the sessions they '
            'are effective from run concurrently: %. Resolve by hand '
            '(supersede one from a later session) before applying 0004.',
            clash
            USING ERRCODE = '23505';  -- unique_violation
    END IF;
END $$;


-- ---------------------------------------------------------------- 2.
ALTER TABLE policyversion
    DROP CONSTRAINT IF EXISTS policyversion_ord_matches_session;
ALTER TABLE closedacademicsession
    DROP CONSTRAINT IF EXISTS closedacadsession_ord_matches_session;


-- ---------------------------------------------------------------- 3.
-- Mirrors acad_session.ordinal(). IMMUTABLE (a pure function of its
-- argument) is what lets it be used in a CHECK constraint. It RAISEs
-- rather than returning NULL for a bad session, because a CHECK that
-- evaluates to NULL passes -- returning NULL here would silently accept
-- exactly the malformed rows the constraint exists to reject.
CREATE OR REPLACE FUNCTION acadstack_session_ordinal(sess text)
RETURNS integer
LANGUAGE plpgsql
IMMUTABLE STRICT
AS $fn$
BEGIN
    IF sess !~ '^[0-9]{4}-(T[1-4]|II|I|S)$' THEN
        RAISE EXCEPTION 'Malformed academic session %. Expected YYYY-S '
                        'where S is one of T1, T2, T3, T4, I, II, S.', sess
            USING ERRCODE = '22023';  -- invalid_parameter_value
    END IF;
    RETURN substring(sess from 1 for 4)::integer * 12
         + CASE substring(sess from 6)
               -- quarter
               WHEN 'T1' THEN 0
               WHEN 'T2' THEN 3
               WHEN 'T3' THEN 6
               WHEN 'T4' THEN 9
               -- semester
               WHEN 'I'  THEN 0
               WHEN 'II' THEN 6
               WHEN 'S'  THEN 10
           END;
END;
$fn$;


-- ---------------------------------------------------------------- 4.
-- Renumber. The triggers installed by 0003 forbid writing sealed policy
-- rows and forbid updating closure records at all, so they are suspended
-- for exactly these two statements. DISABLE TRIGGER USER leaves system
-- triggers (foreign keys, unique indexes) in force, so the collision the
-- preflight looked for would still be caught here as a backstop.
ALTER TABLE policyversion DISABLE TRIGGER USER;
ALTER TABLE closedacademicsession DISABLE TRIGGER USER;

UPDATE policyversion
   SET effective_from_ord = acadstack_session_ordinal(effective_from_session)
 WHERE effective_from_ord
       <> acadstack_session_ordinal(effective_from_session);

UPDATE closedacademicsession
   SET session_ord = acadstack_session_ordinal(acad_session)
 WHERE session_ord <> acadstack_session_ordinal(acad_session);

ALTER TABLE closedacademicsession ENABLE TRIGGER USER;
ALTER TABLE policyversion ENABLE TRIGGER USER;


-- ---------------------------------------------------------------- 5.
-- Re-tie each denormalised ordinal to its session string. Adding the
-- constraint revalidates every existing row, so if step 4 missed
-- anything this migration fails rather than leaving the index wrong.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                   WHERE conname = 'policyversion_ord_matches_session') THEN
        ALTER TABLE policyversion
            ADD CONSTRAINT policyversion_ord_matches_session
            CHECK (effective_from_ord
                   = acadstack_session_ordinal(effective_from_session));
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                   WHERE conname = 'closedacadsession_ord_matches_session') THEN
        ALTER TABLE closedacademicsession
            ADD CONSTRAINT closedacadsession_ord_matches_session
            CHECK (session_ord = acadstack_session_ordinal(acad_session));
    END IF;
END $$;
