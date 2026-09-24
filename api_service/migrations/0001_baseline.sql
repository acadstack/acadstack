-- Effective-dated academic policy: the database-side half of the
-- immutability guarantee in models.py (PolicyVersion,
-- ClosedAcademicSession) and policy_store.py.
--
-- The two tables themselves are created by models.py create_schema(),
-- which runs before this file on every startup path (acadstack_app.py,
-- demo_data.py, migrate.py). What peewee cannot express, and what this
-- file adds, is the part that makes immutability structural rather than
-- a convention the application is trusted to follow:
--
--   1. a session-ordinal function, so the denormalised ordinal columns
--      cannot disagree with the session strings they are derived from;
--   2. triggers that reject any UPDATE/DELETE of policy that a closed
--      session has already been computed under, and any INSERT of policy
--      effective from an already-closed session.
--
-- The ORM guards in models.py exist as well, and give better error
-- messages, but this codebase executes hand-written SQL through
-- db.execute_sql() and peewee's bulk .update()/.delete() never call
-- Model.save(). An admin GUI, a stray script, or psql must hit the same
-- wall, so the rule lives here too.
--
-- Written to be replayable: every object is created with OR REPLACE /
-- IF NOT EXISTS guards, so this file can run again against a schema it
-- already built without erroring.


-- ---------------------------------------------------------------- 1.
-- Session ordinal: YYYY-S -> integer, matching acad_session.ordinal()
-- exactly. Ordinal is year*12 + the month the session starts, counted
-- from the start of the academic year, so concurrent sessions on
-- different calendars (a semester's "I" and a quarter's "T1") land on
-- the same ordinal -- which is the correct answer to "which ruleset was
-- in force", since whatever was in force that month governs both.
--
--   semester   I=0   II=6  S=10
--   quarter    T1=0  T2=3  T3=6  T4=9
--
-- tests/test_acad_session.py asserts this function and the Python one
-- agree, so the two implementations cannot drift.
--
-- IMMUTABLE (a pure function of its argument) is what lets it be used in
-- a CHECK constraint. It RAISEs rather than returning NULL for a bad
-- session, because a CHECK that evaluates to NULL passes -- returning
-- NULL here would silently accept exactly the malformed rows the
-- constraint exists to reject.
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


-- ---------------------------------------------------------------- 2.
-- Tie each denormalised ordinal to its session string. Without this, a
-- row could claim to be effective from 2021-I while sorting as a
-- different instant, and every resolution built on the ordinal index
-- would be wrong.
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
END
$$;


-- ---------------------------------------------------------------- 3.
-- Policy rows that a closed session has been computed under are final.
--
-- A row is protected when a closed session sits at or after its
-- effective_from. That is deliberately conservative: a version
-- superseded before any session it governed closed is still frozen,
-- because it was in force at the time and may have been referenced.
--
-- For an UPDATE the check uses the LOWER of the stored and proposed
-- ordinals, so a sealed version cannot be edited AND an unsealed one
-- cannot be dragged back into sealed history. Rows governing only open
-- sessions remain fully writable -- correcting next year's not-yet-
-- effective ruleset is meant to work.
--
-- The guards in sections 3 and 4 RAISE with plpgsql's default SQLSTATE
-- (P0001, raise_exception), which nothing else in this schema uses:
-- policy_store.py recognises a refusal by it and reports the message as
-- PolicyImmutableError. Give any other RAISE here an explicit ERRCODE.
CREATE OR REPLACE FUNCTION acadstack_policyversion_guard()
RETURNS trigger
LANGUAGE plpgsql
AS $fn$
DECLARE
    ref_ord integer;
    seal_ord integer;
BEGIN
    IF TG_OP = 'DELETE' THEN
        ref_ord := OLD.effective_from_ord;
    ELSE
        ref_ord := LEAST(OLD.effective_from_ord, NEW.effective_from_ord);
    END IF;

    SELECT MAX(session_ord) INTO seal_ord FROM closedacademicsession;

    IF seal_ord IS NOT NULL AND seal_ord >= ref_ord THEN
        RAISE EXCEPTION
            'Policy version % for group % (effective %) is sealed: academic '
            'sessions up to % are closed and were computed under it. Policy '
            'is superseded by inserting a later version, never by % of an '
            'existing one.',
            OLD.id, OLD.policy_group, OLD.effective_from_session,
            (SELECT acad_session FROM closedacademicsession
             WHERE session_ord = seal_ord LIMIT 1),
            lower(TG_OP);
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$fn$;

DROP TRIGGER IF EXISTS policyversion_no_sealed_writes ON policyversion;
CREATE TRIGGER policyversion_no_sealed_writes
    BEFORE UPDATE OR DELETE ON policyversion
    FOR EACH ROW EXECUTE FUNCTION acadstack_policyversion_guard();


-- New policy may only take effect from a session that is still open.
-- Inserting a version effective from a closed session would restate the
-- rules that session's results were already computed under, which is the
-- same harm as editing a sealed row.
CREATE OR REPLACE FUNCTION acadstack_policyversion_insert_guard()
RETURNS trigger
LANGUAGE plpgsql
AS $fn$
DECLARE
    seal_ord integer;
BEGIN
    SELECT MAX(session_ord) INTO seal_ord FROM closedacademicsession;

    IF seal_ord IS NOT NULL AND seal_ord >= NEW.effective_from_ord THEN
        RAISE EXCEPTION
            'Cannot add policy for group % effective from %: academic '
            'sessions up to % are already closed. New policy must take '
            'effect from a session that is still open.',
            NEW.policy_group, NEW.effective_from_session,
            (SELECT acad_session FROM closedacademicsession
             WHERE session_ord = seal_ord LIMIT 1);
    END IF;

    RETURN NEW;
END;
$fn$;

DROP TRIGGER IF EXISTS policyversion_no_backdated_inserts ON policyversion;
CREATE TRIGGER policyversion_no_backdated_inserts
    BEFORE INSERT ON policyversion
    FOR EACH ROW EXECUTE FUNCTION acadstack_policyversion_insert_guard();


-- ---------------------------------------------------------------- 4.
-- Session closure is append-only. If a closure record could be edited or
-- removed, every guard above could be unlocked by first "reopening" the
-- session -- so the seal itself has to be the thing that cannot move.
CREATE OR REPLACE FUNCTION acadstack_closed_session_guard()
RETURNS trigger
LANGUAGE plpgsql
AS $fn$
BEGIN
    RAISE EXCEPTION
        'Academic session % cannot be % : session closure records are '
        'append-only, because policy immutability is anchored to them.',
        OLD.acad_session,
        CASE TG_OP WHEN 'DELETE' THEN 'reopened' ELSE 'modified' END;
END;
$fn$;

DROP TRIGGER IF EXISTS closedacadsession_append_only ON closedacademicsession;
CREATE TRIGGER closedacadsession_append_only
    BEFORE UPDATE OR DELETE ON closedacademicsession
    FOR EACH ROW EXECUTE FUNCTION acadstack_closed_session_guard();
