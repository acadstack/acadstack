# Effective-dated academic policy

How AcadStack stores academic rules that change over time, why that is a
different thing from a system setting, and what still has to happen
before the live rules move onto it.

Code: `api_service/acad_session.py`, `api_service/policy_store.py`,
the grading group declared in `api_service/domain/policy.py`, the `PolicyVersion` /
`ClosedAcademicSession` models in `api_service/models.py`, and
`api_service/migrations/0003_versioned_policy_store.sql`.

---

## 1. The problem

`compute_cgpa_sgpa_ec` (`domain/transcript.py`) holds a grade-to-point
map, three different earned-credit grade sets, and this:

```python
# Adjustment for PhD passing grades introduced in 2021
if academic_session_year > 2021:
    phd_ec_grades = "A,A-,B,B-,C,C-"
elif academic_session_year < 2021:
    phd_ec_pass_grades = "A,A-,B,B-,C"
else:  # Year 2021
    ...
```

That branch is the whole argument. Policy cannot simply be *replaced*,
because a 2019 transcript has to keep computing under the 2019 rules
forever. An institution amends its regulations; it does not retroactively
rewrite them. So policy is not a value you overwrite — it is a series of
versions, each owning a range of academic sessions.

The failure mode this design exists to prevent is specific and quiet: an
admin opens a future settings screen, corrects the grade point map, saves,
and every historical transcript in the system silently changes. Nothing
errors. Nobody notices until a student queries a degree certificate issued
four years ago.

---

## 2. Two stores, not one overloaded one

Phase 2 introduced `SystemSetting` and `settings_store.py`: a flat,
mutable `group.name -> value` store. The obvious question is whether
versioned policy should be an extension of it — add `effective_from` and
`effective_to` columns, make the unique index conditional, and be done.

**It should not.** The two have opposite contracts:

| | `SystemSetting` | `PolicyVersion` |
|---|---|---|
| Contract | current value, last write wins | append-only series |
| Mutability | update in place | never; supersede only |
| Identity | `(group, name)` | `(group, effective_from_session)` |
| Unit of change | one scalar | a whole ruleset, atomically |
| Question it answers | "what is the setting now?" | "what were the rules *then*?" |
| Effect of an edit | takes effect immediately, everywhere | none on anything already computed |

Overloading one table would mean teaching a single write path two
different mutability rules and making every existing scalar setting carry
nullable effective-range columns it will never use. The mutability rule
is the part that matters: it is easy to add an `effective_from` column
and much harder to guarantee that a row nobody may edit cannot be edited.
Mixing the two in one table means the guarantee has to be conditional —
and a conditional guarantee is one `WHERE` clause away from not being a
guarantee.

### The test for where something belongs

> **If an admin changes this, must documents already issued change too?**
>
> - *No* → operational knob → `settings_store`.
>   Examples: `enrolment.disable_fees_check`, email toggles, attendance
>   thresholds used for a live warning screen.
> - *Yes, and that would be wrong* → policy of record → `policy_store`.
>   Examples: grade point maps, earned-credit grade sets, pass marks,
>   credit requirements for a degree.

A useful secondary check: if you cannot name the academic session a change
takes effect from, it is probably a setting, not policy.

### What they do share

One thing, deliberately: the `_sys.policy_version` counter. Both stores
cache their whole (tiny) table in-process and re-read only when that
number moves; every write bumps it *inside the writing transaction*, so a
worker that can see version N+1 can by definition see every row that
transaction wrote. Sharing the counter means one answer to "is my cached
configuration current?" instead of two that can disagree. The cost is one
redundant reload of store A when store B is written, which for tables this
size is not worth a second counter to avoid. `settings_store` exposes
`bump_policy_version()` for exactly this.

---

## 3. The schema

```
PolicyVersion
    policy_group            "grading"
    effective_from_session  "2021-I"
    effective_from_ord      20214        -- derived, indexed, CHECK-constrained
    payload                 {...}        -- the WHOLE ruleset, as JSON
    note                    "Senate resolution 2021/14"
    txn_login_id, ins_ts                 -- who, when (from BaseModel)
    UNIQUE (policy_group, effective_from_ord)

ClosedAcademicSession
    acad_session            "2021-II"    -- UNIQUE
    session_ord             20215
    closed_ts, note, txn_login_id
```

Three decisions are load-bearing.

**There is no `effective_to` column.** A version is in force until the
next version of the same group begins — a half-open interval whose end is
derived from the neighbouring row:

```
grading @ 2000-T1  ──────────────────────────────────>
grading @ 2021-I                 ──────────>
grading @ 2024-II                            ────────> (open)
```

This is not a space saving. If the end were stored, every supersede would
have to `UPDATE` its predecessor — which is precisely the mutation the
whole design forbids. Because the end is derived, adding a version writes
exactly one new row and touches nothing. Immutability stops being a rule
the write path has to remember and becomes a property of the shape.

**A version carries the complete ruleset, not a patch.** Resolving a 2019
transcript must not require replaying every version since. A payload is
self-contained and independently interpretable years later.

**A ruleset is one JSON document, not a row per field.** The parts of a
grading ruleset are only meaningful together — a grade-point map and the
grade sets that reference it have to move as a unit — so they version as a
unit. `domain/policy.py` declares what the grading group's payload must
contain and turns it into the `GradingPolicy` the computation already takes; a payload that will not build is
rejected at write time, not discovered mid-transcript.

---

## 4. Ordering: sessions on a shared monthly timeline

Effective-dating is keyed on academic session (`YYYY-S`), following
`AcademicCalendar`'s precedent, not on wall-clock dates. `acad_session.py`
turns a session into an integer ordinal that resolution can binary-search.

**Session types run in parallel, not in sequence.** An institution may run
more than one academic calendar at once — a semester-based B.Tech
alongside a quarter-based programme. `acad_session.SESSION_TYPES` declares
each calendar and the month its sessions begin, counted from the start of
the academic year:

| type | suffixes and month offsets |
| --- | --- |
| `semester` | `I`=0 (Jul), `II`=6 (Jan), `S`=10 (May) |
| `quarter` | `T1`=0 (Jul), `T2`=3 (Oct), `T3`=6 (Jan), `T4`=9 (Apr) |

The ordinal is `year * 12 + offset`. Two sessions that begin in the same
month therefore get **equal ordinals** — `2021-I` and `2021-T1` are
concurrent, not four ranks apart — which is the correct answer to "which
ruleset was in force": policy in force that month governs both.

The table is **append-only**. Adding a calendar or a suffix is safe;
repointing a suffix already in use would silently move every policy
boundary around it and reinterpret stored rows.

**This replaced an earlier scheme** that ranked every suffix on one
arbitrary within-year order (`T1 < T2 < T3 < T4 < I < II < S`,
`ordinal = year * 10 + rank`). That order was a fiction as soon as two
calendars were in play, and it is what made the 2021 PhD rule look as
though it oscillated between tracks (see §7). Migration
`0004_session_type_month_ordinals.sql` renumbers the stored ordinals.

**A session is governed by the policy in force at its start.** Because
sessions span several months while the timeline is monthly, a policy change
can take effect *during* a session — and with parallel calendars it
routinely does, since a boundary in one calendar falls inside a session of
the other. A change effective from `2021-T2` (October, a clean quarter
boundary) lands in the middle of semester I; semester I keeps the rules it
began under and semester II picks the new ones up. That is also the right
academic answer: you do not restate the rules a student is already being
graded under.

Chronology has exactly one definition. `domain/transcript.py` used to keep
its own `suffixes` list and sort a student's sessions by its index; it now
calls `acad_session.sorted_sessions()`, and
`tests/test_acad_session.py::test_transcript_code_keeps_no_private_session_chronology`
fails if a second copy reappears — because if the two ever disagreed a
transcript would accumulate in one order while policy resolved in another,
and a session could be graded under the rules belonging to the session
after it.

**Why the ordinal is derived from the session code, not from
`AcademicCalendar`.** Ordering by each session's configured start date
would be the more "real" chronology, and it is the wrong basis here: an
admin correcting a calendar date years later would move the boundary
between two policy versions and change transcripts already issued. The
ordering has to be a fixed property of the session itself. The same
reasoning is why session closure is an explicit recorded act rather than
"the end date has passed".

The ordinal is denormalised into a column so the guards and resolution are
plain integer comparisons, and a `CHECK` constraint ties it to the session
string via a SQL reimplementation of the same function — so a row cannot
claim to be effective from `2021-I` while sorting as `2019-T1`.
`tests/test_acad_session.py` asserts the SQL and Python implementations
agree.

Because an ordinal no longer names a single session, `from_ordinal()`
requires a session type whenever the instant is shared, and
`sessions_at_ordinal()` / `label_for_ordinal()` report all of them. The
seal line follows the same rule: `is_session_closed()` asks about one
session (matched by name), while `is_sealed()` asks about an instant.

---

## 5. Immutability

### The seal line

Closing an academic session (`policy_store.close_session`) records a row
and draws a line at that session's ordinal. From then on:

- policy effective from **at or before** the line cannot be updated or
  deleted; and
- no new policy may be introduced effective from at or before it.

Everything after the line stays fully editable — next year's
not-yet-effective ruleset must remain correctable, and it is.

The rule is conservative on purpose: a version superseded before any
session it governed was closed is still frozen, because it was in force at
the time and may have been referenced while it was.

Closure records are themselves append-only. If a closure could be deleted,
every guard below would be unlockable by first "reopening" the session, so
the anchor has to be the thing that cannot move.

### Enforced three times

| Layer | Catches | Where |
|---|---|---|
| `policy_store.supersede()` | the curated path; best error message | `policy_store.py` |
| `PolicyVersion.save()` / `delete_instance()` | any ORM caller, including code that never heard of `policy_store` | `models.py` |
| Postgres triggers | raw `db.execute_sql`, peewee bulk `.update()`/`.delete()`, psql, a future admin GUI | migration `0003` |

The third layer is not belt-and-braces. This codebase runs hand-written
SQL from `sql_statements.toml` through `db.execute_sql`, and peewee's bulk
`Model.update()` builds an `UPDATE` without ever calling `Model.save()` —
so a Python-only guard would be bypassed by ordinary, idiomatic code in
this repo. `tests/test_policy_immutability.py` tests each layer through
the path only that layer can catch.

### What an admin can and cannot do

Can: add a version effective from any open session; correct a version
that governs only open sessions; close a session.

Cannot: edit or delete a version once a session at or after its start has
closed; introduce a version effective from a closed session; move an
unsealed version back over closed sessions; reopen a closed session;
store a ruleset that will not build.

---

## 6. Resolution

```python
ruleset = policy_store.policy_for("grading", "2021-I")   # typed object
version = policy_store.resolve("grading", "2021-I")      # + provenance
```

Transcript building resolves per course, so resolution must not query. The
entire policy table is cached in-process (it will hold tens of rows for the
life of an institution) and resolution is `bisect_right` over the group's
ordinal list — no query, no allocation, no deep copy.
`tests/test_policy_store.py::test_resolution_issues_no_queries_once_warm`
pins that: 42 resolutions, zero statements.

Payloads are handed out frozen (`MappingProxyType` / tuples, built once
when the snapshot loads) rather than deep-copied per call, so sharing is
safe and free; `payload_dict()` gives a mutable copy for callers that want
to edit a ruleset and supersede with it. Typed objects are memoised per
version, so a group's builder runs at most once per version per worker
however many courses a transcript touches.

---

## 7. Findings from building this

Three things surfaced that are worth acting on separately.

**1. The 2021 PhD rule cannot be stored as one effective-dated series.**
Not "is awkward to store" — cannot. A policy version is in force for an
*instant*, so every session beginning in that month resolves to it. The
2021 rule branches on the session *suffix*, and two suffixes from
different calendars can name the same instant, at which point the rule
demands two different answers for one point in time:

| instant | sessions | earned-credit set | CGPA set |
| --- | --- | --- | --- |
| Jul 2021 | `2021-I` | widened | **widened** |
| Jul 2021 | `2021-T1` | widened | **default** |
| Jan 2022 | `2021-II` | **widened** | default |
| Jan 2022 | `2021-T3` | **default** | default |

Read per calendar the rule makes much more sense, and matches its origin:
the pandemic years, when semester- and quarter-based programmes ran side
by side. The quarter track widens the earned-credit set for `T1`/`T2` and
then reverts for `T3`/`T4` — but only because `T3`/`T4` fall through to the
`else` branch that logs "Unknown academic semester", i.e. they were never
handled at all. The semester track is monotonic in the earned-credit set,
but its CGPA set takes the widened value at `2021-I` and at no other
session in either calendar, ever.

So this was not an amendment that took effect on a date; it was
per-calendar improvisation, and no arrangement of rows could reproduce it.

**Resolved by retiring it.** The product has never been deployed, so there
are no transcripts computed under those branches to preserve. Rather than
carry the contradiction forward — either as a per-calendar in-code table or
as rows someone would have to defend — the PhD rules are now simply the
PhD rules, seeded as one baseline version, and any future change is an
ordinary new version. The characterization test that pinned all eight
branches (`test_phd_grade_c_minus_policy_matrix`) was deleted deliberately;
the note where it stood in `tests/test_gpa_computation.py` records why.

What survives is the property the episode taught us — **one instant, one
ruleset** — pinned as `test_the_store_cannot_hold_two_rulesets_for_one_instant`,
with `test_a_single_instant_amendment_resolves_across_both_calendars`
showing what a well-formed amendment looks like instead. Had this product
been live, the outcome would have been the opposite: the rule would have
had to be recorded faithfully, which is precisely the situation Phase C's
cohort-scoped policy is designed for.

**2. Grade sets used to be matched by substring — now resolved, except in
one place.** The old rules held grade sets as comma-separated strings and
tested membership with `in`, which is substring matching, not set
membership. Every one of those sets was checked against the full 16-grade
vocabulary in `vocab_defaults.py` before the change, and for every
recognised grade substring and membership agree — including `"C-"` against
`"A,A-,B,B-,C"`, where `C` is last and nothing follows it. So the
conversion to `frozenset` is behaviour-preserving, and the grade sets are
real collections now.

The one exception is **enrolment types**. `enrol_type in "C,CM,CC"` treats
a stray one-character code like `"M"` as a credit enrolment, because `"M"`
appears inside `"CM"`. None of the four real enrolment types (A, C, CM,
CC) is affected, so the quirk is only reachable with invalid data — but
`tests/test_gpa_computation.py` characterises it, so it is preserved
deliberately, as a named and *versioned* field:
`credit_enrol_type_match`, either `"substring"` (the default, today's
behaviour) or `"exact"` (correct). Because it is versioned, an institution
can adopt `"exact"` effective from an open session without altering a
single historical transcript — which is a better outcome than either
silently "fixing" it or leaving it undocumented.

**3. The migration runner did not support SQL containing a literal `%`.**
`schema_migrations.py` ran each script through peewee's `execute_sql()`,
which always passes a parameter sequence to psycopg2, even an empty one —
so psycopg2 treated every `%` in the script as a placeholder introducer.
That ruled out a `LIKE` pattern, a `to_char()` format, or the plpgsql
`RAISE ... %` substitutions migration `0003` needs. Fixed by running
migration scripts through a plain cursor with no parameter argument
(`schema_migrations._execute_script`), which skips client-side
interpolation entirely. Regression test:
`test_migration_containing_a_percent_sign_is_applied_verbatim`.

---

## 8. What this phase deliberately did not do

`domain/policy.py` declares the `grading` group and builds a stored
payload into the `GradingPolicy` the computation takes.
`load_grading_policy(acad_session)` resolves the ruleset in force for a
session, preferring a stored version and falling back to the in-code
baseline; `resolve_grading_policy(acad_session)` is the stored-only
counterpart, for when you need to know what is actually recorded.

`compute_cgpa_sgpa_ec` now carries no policy of its own, and
`tests/test_gpa_computation.py` — which characterises its behaviour to the
digit — passes unchanged, byte for byte. What changed:

- **`apply_phd_amendment` and the `phd_amendment_*` fields are gone**, along
  with every `if degree == "BTE"` / `elif degree == "PHD"`. A ruleset maps
  degree code -> programme class (`degree_classes`, with
  `default_degree_class` for anything unlisted) and holds one
  `programme_rules` block per class. Class names are arbitrary, and a block
  may carry its own `grade_points` — which is what "the grade definitions
  changed for the PhD programme" is, as one complete version.
- **Grade sets are `frozenset`s** end to end; see §7.2 for why that is
  behaviour-preserving, and for the one field that keeps an explicit match
  mode.
- **The LTP format is policy** (`separator`, `field_count`,
  `credits_index`, `required_indices`, `format_label`) rather than a
  hardcoded five-part `L-T-P-S-C` assumption.
- **The SGPA/CGPA denominators stay in code**, as `sgpa_denominator()` and
  `cgpa_denominator()`. They are structural: every term is an accumulator
  the computation defines, and what each one *means* is already
  configurable. Making the formula itself configurable would take an
  expression language evaluated against grade data, or a row of booleans
  enumerating the combinations someone happened to imagine; changing this
  arithmetic changes what SGPA *means*, which deserves a review and a test
  rather than an admin screen. They are functions so the one definition is
  shared — the CGPA formula used to be restated in `courses_perf_filtered`.
  Only the rounding is configurable (`gpa_decimal_places`).
- **`passed_course_grades` has one home.** The list of grades that count as
  a pass was typed into the `get_passed_courses` HTTP handler as well as
  the computation, with the two differing by `"S"`. They are both off the
  ruleset now, and still two fields, deliberately: `"S"` is a pass but
  cannot be a CGPA grade, and `cgpa_grades` is per programme class while
  the passed-courses listing is not — deriving one from the other would
  silently stop a PhD student's `"D"` counting as a pass.

**The baseline is seeded, so the store is the runtime source of truth.**
`default_seed_data.seed_grading_policy()` stores `DEFAULT_GRADING_POLICY`
effective from `2000-T1` on first boot, deriving the payload from
`domain.policy` rather than restating it. It is idempotent, it never
supersedes a version that already exists — so an institution's own
amendment is permanent — and if the baseline would land inside sealed
history it logs and skips rather than failing the boot.

`load_grading_policy()` still falls back to the in-code ruleset when
nothing is stored, which is what keeps `compute_cgpa_sgpa_ec` testable with
no database at all. That fallback is a convenience, not a second source of
truth: there is exactly one shipped ruleset and the seeder stores that same
object.

Two known gaps, both intentional:

- **No way to withdraw a not-yet-effective version through the public
  API.** `supersede` is the only write operation, as specified. The model
  and trigger layers do permit correcting or soft-deleting an *unsealed*
  version, so an admin screen can offer it later; it is simply not exposed
  yet. A typo in next year's ruleset is currently fixed by superseding it
  from a later session.
- **No "policy repealed" terminal state.** The latest version of a group
  is open-ended. A group that should stop applying needs a terminal
  version saying so.

---

## 9. Recommendation: `StudentCredits` and frozen results

> *Should `StudentCredits` become the frozen authoritative record once a
> session closes?*

**Yes to freezing, no to "authoritative" — and start by noticing that the
table is currently write-only.**

### What is actually there today

`StudentCredits` (`models.py`) stores `cgpa`, `sgpa`, `cred_earned`,
`cred_registered`, `cred_earned_total` per `(student, acad_session)`. It is
written by exactly one place — `__process_credits_gen_request` in
`api_reports.py`, a background job an ACA/DEA triggers by hand — and that
writer **upserts**: re-running it overwrites the previous figures in place.

Nothing reads it. Not Python, not `sql_statements.toml`, not the webapp.
Transcripts recompute from raw enrolments every time. So it is not
currently authoritative for anything; it is a stale by-product of a job
someone may or may not have run. Any plan should start from that rather
than from the assumption that it holds trustworthy history.

That is also good news: there is no read path to migrate, so the table can
be reshaped freely.

### The recommendation

**Keep recomputation as the source of truth. Add a frozen record of what
was *published*, and reconcile the two.**

The distinction is the whole point:

- *"What do the rules say, given the enrolment data as it stands?"* —
  computed, and as of this phase reproducible, because the ruleset is
  pinned to the session rather than to whatever is in the code today.
- *"What did we tell the student in 2021?"* — a fact about the past that
  no recomputation can recover once anything upstream changes.

Both are needed, and conflating them is what creates the problem. Making
the snapshot authoritative for computation sounds safer but is worse: a
legitimate correction — a re-evaluation, a late withdrawal approved by the
DEA, a grade entry fixed — would then have no honest path except mutating
the frozen record, which reintroduces exactly what this design removes.

Concretely, and **only after the grading rules are actually on the policy
store** (recording a policy version id is meaningless while the rules are
still hardcoded):

1. **Repurpose `StudentCredits`** rather than adding a third table. It has
   no readers, so there is nothing to break, and a second table covering
   the same ground would be the "one overloaded concept" problem in
   reverse.

2. **Add provenance.** A frozen figure is only worth having if you can say
   what produced it: the resolved `PolicyVersion` id per policy group, and
   a digest of the inputs (enrolment ids, grades, enrol types, credits).
   Without provenance a mismatch later is unattributable, which makes the
   snapshot near-useless for the validation this is for.

3. **Make it append-only, sealed by the same mechanism.** Change the
   unique key from `(student, acad_session)` to
   `(student, acad_session, revision)`, change the writer from upsert to
   append, and reuse `ClosedAcademicSession` as the seal — the same
   trigger pattern as `PolicyVersion`. A correction becomes a new revision
   with a reason, never an `UPDATE`. The transcript shows the latest
   revision; an audit shows the chain.

4. **Add a reconciliation check, and make a mismatch loud.** Recompute and
   compare against the frozen figures for a closed session; report
   differences, never silently overwrite. This is the snapshot-to-validate-
   against you asked for, and it catches precisely the class of bug this
   whole effort is about — someone changing a rule and not realising what
   it touched. Run it as a background job after any policy supersede that
   affects a closed session's group, and on demand.

5. **Watch `cred_earned_total`.** It is cumulative across sessions, so a
   correction to an early session invalidates the cumulative figure in
   every later snapshot. Freeze the per-session figures and derive the
   cumulative at render time; or, if the cumulative genuinely has to be
   frozen (it appears on an issued document), accept that a correction
   requires re-issuing later revisions too, and make that explicit rather
   than letting the numbers quietly disagree.

### Sequencing

```
policy storage + resolution                                    [done]
session timeline: per-calendar month ordinals                  [done]
grading rules onto the store, seeded, 2021 rule retired        [done]
cohort-scoped session modes (Phase C)                          [next]
freeze results with provenance + reconciliation                [after]
```

Phase C is what lets a single batch move between session modes for a
bounded period, which is the situation the 2021 rule was a botched attempt
at handling. Freezing results is not worth starting before it lands: what a
result must record as its provenance includes which calendar the cohort was
on.
