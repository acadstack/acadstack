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

## 4. Ordering: sessions, not dates

Effective-dating is keyed on academic session (`YYYY-S`, `S` in
`T1..T4, I, II, S`), following `AcademicCalendar`'s precedent, not on
wall-clock dates. `acad_session.py` turns a session into an integer
ordinal — `year * 10 + rank`, so `2021-I -> 20214` — giving a total order
that resolution can binary-search.

The suffix order is `T1 < T2 < T3 < T4 < I < II < S`. That is not invented
here: it is the order `domain/transcript.py` already sorts a student's
sessions by before accumulating CGPA. `tests/test_acad_session.py` reads
that list out of the source and asserts it matches, because if the two
ever disagreed a transcript would accumulate in one order while policy
resolved in another — and a session could be graded under the rules
belonging to the session after it.

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

**1. The 2021 amendment is not chronologically monotonic — it is probably
a bug.** Expressing it as versions forced every session in the window to
be given an explicit answer, and the answers zig-zag. Under this
codebase's own session chronology (`T1..T4` precede `I`, `II`, `S` within
a year), the code's semester list `["II", "S", "T1", "T2"]` mixes the two
halves of the year, so the earned-credit set widens at `2021-T1`, reverts
at `2021-T3`, and widens again at `2021-I`; and the CGPA set takes a value
at `2021-I` that it holds for that one session only. `2021-T3` and
`2021-T4` fall into an `else` branch that logs "Unknown academic
semester".

The storage design handles it — `test_2021_phd_amendment_is_reproduced_exactly_by_versions`
reproduces all 35 sessions in the window exactly — but a rule that
zig-zags is far more likely to be a mistake than an institution's intent.
**This needs resolving with the registrar before the live rules are
moved**, because each of those turns into a stored row someone has to
defend. Pinned as `test_the_2021_amendment_is_not_chronologically_monotonic`.

**2. Grade sets are matched by substring today.** The current rules hold
grade sets as comma-separated strings and test membership with `in`, which
is substring matching, not set membership — a one-character `enrol_type`
matches `"C,CM,CC"`. Stored payloads use JSON arrays and the validator
rejects the string shape outright, so whoever moves the live rules across
must also change those membership tests to real containment and re-verify
the affected grades. The two changes cannot be made independently.

**3. The migration runner could not run any SQL containing `%`** (fixed
here). `schema_migrations.py` passed each script to peewee's
`execute_sql()`, which hands psycopg2 `params or ()` — and an empty but
*present* parameter sequence still makes psycopg2 treat `%` as a
placeholder introducer. Any migration with a `LIKE` pattern, a `to_char()`
format or a plpgsql `RAISE ... %` died with `IndexError: tuple index out
of range` before reaching the server. Migration `0003` is such a file.
Regression test:
`test_migration_containing_a_percent_sign_is_applied_verbatim`.

---

## 8. What this phase deliberately did not do

No business logic moved. `compute_cgpa_sgpa_ec` is untouched and no
ruleset is seeded into the database, so every transcript computes exactly
as it did before.

What *is* wired up is the shape. `domain/policy.py` declares the `grading`
group and builds a stored payload into the same `GradingPolicy` the
computation already takes, and `resolve_grading_policy(acad_session)` is
the effective-dated counterpart to `load_grading_policy()` — present,
tested, and not yet called by anything. The tests exercise it against the
live `DEFAULT_GRADING_POLICY` and the live `apply_phd_amendment` rather
than against copied literals, which is how we know the schema fits.

Two details make the eventual switch small:

- **A stored ruleset neutralises the amendment.** `build_grading_policy`
  sets `phd_ec_grades_amended` equal to `phd_ec_grades` (and likewise for
  the pass set), so every branch of `apply_phd_amendment` returns the
  version's own sets for any session. The computation can keep calling it
  per course, unchanged, while the store is what actually decides.
- **Arrays are joined back to strings** at the builder boundary, so the
  substring-matching quirk downstream sees no change of shape.

Moving the rules across is then its own change, and needs:

- the finding in §7.1 resolved with the registrar;
- the substring-matching fix in §7.2, which touches `build_grading_policy`
  and the membership tests together;
- a baseline ruleset seeded effective from a session earlier than any
  enrolment in the database;
- `load_grading_policy()` delegating to `resolve_grading_policy()`;
- before/after verification against real grade data for every affected
  session — not just the ones near a boundary.

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
this phase   →  policy storage + resolution                    [done]
next         →  resolve the 2021 finding with the registrar
then         →  move grading rules onto the store (+ §7.2 fix)
then         →  freeze results with provenance + reconciliation
```

Step 4 is not worth starting before step 3 lands.
