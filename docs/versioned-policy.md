# Effective-dated academic policy

How AcadStack stores academic rules that change over time, and why that is a
different thing from a system setting.

Code: `api_service/acad_session.py`, `api_service/policy_store.py`,
the grading group declared in `api_service/domain/policy.py`, the `PolicyVersion` /
`ClosedAcademicSession` models in `api_service/models.py`, and
`api_service/migrations/0003_versioned_policy_store.sql`.

---

## 1. Why policy is not a setting

An institution amends its academic regulations; it does not retroactively rewrite
them. A 2019 transcript has to keep computing under the 2019 rules forever, even
after the grade-point map or the earned-credit grade set changes for later
sessions. Policy is therefore not a value you overwrite — it is a series of
versions, each owning a range of academic sessions, and any of it may need such a
range: grade-to-point maps, earned-credit grade sets, pass marks, credit
requirements.

A flat, overwritable setting cannot express this. Reaching for one forces the
rule itself to encode the range, typically as a branch on the academic year:

```python
if academic_session_year > 2021:
    ec_grades = {"A", "A-", "B", "B-", "C", "C-"}
elif academic_session_year < 2021:
    ec_grades = {"A", "A-", "B", "B-", "C"}
else:
    ...
```

which pushes every subsequent amendment into the same function as one more
branch, and gives an admin no way to record a change without a code deploy.

The failure mode this design exists to prevent is specific and quiet: an admin
opens a settings screen, corrects the grade point map, saves, and every
historical transcript in the system silently changes. Nothing errors. Nobody
notices until a student queries a degree certificate issued four years ago.

---

## 2. Two stores, not one overloaded one

`SystemSetting` and `settings_store.py` are a flat, mutable
`group.name -> value` store. The obvious question is whether
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
contain and turns it into the `GradingPolicy` the computation takes; a
payload that will not build is rejected at write time, not discovered
mid-transcript.

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

Sessions are deliberately **not** ranked on one arbitrary within-year order
such as `T1 < T2 < T3 < T4 < I < II < S`. That ordering is a fiction as soon
as two calendars run concurrently: two sessions beginning in the same
calendar month must resolve to the same ruleset, and a rank-based order
cannot express that — it would place them an arbitrary number of ranks
apart instead of tying them. Migration `0004_session_type_month_ordinals.sql`
computes the month-offset ordinal for every stored session record.

**A session is governed by the policy in force at its start.** Because
sessions span several months while the timeline is monthly, a policy change
can take effect *during* a session — and with parallel calendars it
routinely does, since a boundary in one calendar falls inside a session of
the other. A change effective from `2021-T2` (October, a clean quarter
boundary) lands in the middle of semester I; semester I keeps the rules it
began under and semester II picks the new ones up. That is also the right
academic answer: you do not restate the rules a student is already being
graded under.

Chronology has exactly one definition: `acad_session.sorted_sessions()`.
`domain/transcript.py` calls it to order a student's sessions rather than
keeping a private copy of the suffix order, and
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

## 7. Scope: a version governs an instant, not a cohort

A policy version is in force for an *instant* on the shared monthly
timeline (§4), so every session beginning in that month — across every
calendar an institution runs — resolves to the same version. This is a
hard boundary on what effective-dating alone can express: a rule that
needs to answer differently for two sessions naming the same instant (for
example, a semester programme's `2021-I` and a quarter programme's
`2021-T1`, both starting July) cannot be represented as one effective-dated
series, because the store is answering "what ruleset governs this point in
time," not "what ruleset governs this specific calendar."

```
Jul 2021  ──►  one instant  ──►  one ruleset, shared by 2021-I and 2021-T1
```

A rule that genuinely needs to vary by calendar, or by cohort, belongs to a
different axis of variation than effective-dating: it is a scoping
question ("whose rules are these"), not a timing question ("when did they
start"). §10's proposed cohort-scoped session modes are the mechanism for
that axis — a policy dimension orthogonal to, and layered on top of, the
effective-dating described here.

---

## 8. The grading policy payload

`domain/policy.py` declares the `grading` group's payload shape and turns a
stored (or baseline) version into the `GradingPolicy` the computation
takes. `load_grading_policy(acad_session)` resolves the ruleset in force
for a session, preferring a stored version and falling back to the in-code
baseline; `resolve_grading_policy(acad_session)` is the stored-only
counterpart, for when the caller needs to know what is actually recorded
rather than what's authoritative for a transcript.

`compute_cgpa_sgpa_ec` (`domain/transcript.py`) carries no policy of its
own — every rule that can vary by degree or by session lives in the
payload:

- **Degree classification is data.** A ruleset maps degree code ->
  programme class (`degree_classes`, with `default_degree_class` for
  anything unlisted) and holds one `programme_rules` block per class. Class
  names are arbitrary, and a block may carry its own `grade_points` —
  which is how a grade-definition change scoped to one programme class
  becomes one complete version.
- **Grade sets are `frozenset`s**, matched by real set membership rather
  than string containment, with one exception: `credit_enrol_type_match`
  (`"substring"`, the default, or `"exact"`) governs whether enrolment-type
  membership (`credit_enrol_types`, e.g. `"C,CM,CC"`) is matched by
  substring or by exact membership. Because it is a versioned field, an
  institution can adopt `"exact"` matching effective from an open session
  without altering how any historical transcript was computed.
- **The LTP format is policy** (`separator`, `field_count`,
  `credits_index`, `required_indices`, `format_label`) rather than a
  hardcoded five-part `L-T-P-S-C` assumption.
- **The SGPA/CGPA denominators stay in code**, as `sgpa_denominator()` and
  `cgpa_denominator()`. They are structural: every term is an accumulator
  the computation defines, and what each one *means* is already
  configurable through the grade sets above. Making the formula itself
  configurable would take an expression language evaluated against grade
  data, or a row of booleans enumerating every combination someone might
  imagine; changing this arithmetic changes what SGPA *means*, which
  deserves a review and a test rather than an admin screen. They are
  functions with one definition, shared by every caller including
  `courses_perf_filtered`. Only the rounding is configurable
  (`gpa_decimal_places`).
- **`passed_course_grades` has one home**, shared by the computation and
  the `get_passed_courses` HTTP handler. It is deliberately a separate
  field from `cgpa_grades` rather than derived from it: `"S"` is a pass but
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

### Known limitations

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

## 9. Open extension: recording what was published

`StudentCredits` (`models.py`) stores `cgpa`, `sgpa`, `cred_earned`,
`cred_registered`, `cred_earned_total` per `(student, acad_session)`. Today
it is written by exactly one place — `__process_credits_gen_request` in
`api_reports.py`, a background job an ACA/DEA triggers by hand — and that
writer **upserts**: re-running it overwrites the previous figures in
place. Nothing reads it back; every transcript recomputes from raw
enrolments each time. So the table is not currently authoritative for
anything, and correspondingly there is no existing read path that a
redesign would need to migrate.

That recomputation should stay the source of truth for "what do the rules
say, given the enrolment data as it stands" — versioned policy is what
makes that reproducible, since the ruleset is pinned to the session rather
than to whatever the code says today. But it cannot answer "what did we
tell the student in 2021," a fact about the past that no recomputation can
recover once anything upstream changes (a re-evaluation, a late withdrawal,
a corrected grade entry). Both questions are legitimate and distinct;
`StudentCredits` is where the second one's answer would be recorded.

The design this section proposes, only meaningful once the rules an
institution actually runs are stored as policy versions rather than
implied by code:

1. **Repurpose `StudentCredits`** rather than add a third table — it has
   no readers today, so there is nothing to break, and a second table
   covering the same ground would be the "one overloaded concept" problem
   this whole design (§2) exists to avoid, in reverse.
2. **Record provenance alongside the figures**: the resolved
   `PolicyVersion` id per policy group, and a digest of the inputs
   (enrolment ids, grades, enrol types, credits) that produced them.
   Without provenance, a later mismatch is unattributable.
3. **Make it append-only, sealed the same way policy is.** Change the
   unique key from `(student, acad_session)` to
   `(student, acad_session, revision)`, change the writer from upsert to
   append, and reuse `ClosedAcademicSession` as the seal. A correction
   becomes a new revision with a reason, never an `UPDATE`; the transcript
   shows the latest revision, an audit shows the chain.
4. **Reconcile, and make a mismatch loud.** Recompute and compare against
   the frozen figures for a closed session on a schedule (and after any
   policy supersede touching a closed session's group); report
   differences rather than silently overwriting either side. This is what
   catches a rule change whose effect on already-published results wasn't
   fully understood.
5. **Derive the cumulative figure rather than freezing it**, since
   `cred_earned_total` is cumulative across sessions and a correction to
   an early session would otherwise invalidate every later snapshot. If
   the cumulative figure genuinely has to be frozen because it appears on
   an issued document, a correction implies re-issuing later revisions
   too — worth making explicit rather than letting the numbers quietly
   disagree.

This is sequenced after cohort-scoped session modes (§10): what a result
must record as provenance includes which calendar the cohort was on, so
freezing results is not worth building before that lands.

## 10. Open extension: cohort-scoped session modes

Session mode (semester / trimester / quarter) is, today, an institution-wide
choice expressed by which suffixes `acad_session.SESSION_TYPES` declares.
Some institutions need a single cohort — one degree, department and entry
year — to run on a different mode for a bounded period (a batch moved to a
trimester-like schedule for one term, then back), while the rest of the
institution stays on its usual calendar. That is a cohort-scoped
assignment, layered on top of the timeline in §4 rather than a change to
it: **which** calendar a cohort follows over a period is a different
question from **when** a policy version takes effect, and the two need to
compose (§7).

Sketch of the shape this would take:

- **A mode registry with globally unique suffixes.** A new mode's suffixes
  must not collide with an existing one's (adding trimester `T1`/`T2`/`T3`
  would collide with the existing quarter `T1..T4`), so the ordinal stays
  unambiguous. No existing session string is ever rewritten, which is what
  keeps the immutable SQL ordinal function and its `CHECK` constraint
  intact.
- **Cohort calendar assignment as an append-only, effective-dated series**,
  keyed on `(degree, dept, entry_year)`, with the end of each assignment
  derived from the next row — the same mechanism `PolicyVersion` uses.
- **A scope on policy versions**, resolved most-specific-first (e.g.
  `BTE:2023` → `BTE` → institution-wide), since calendar assignment cannot
  be folded into a payload: two cohorts of the same degree can need
  different answers at the same instant.

Validity rules a cohort's calendar assignment would need to enforce: a
switch may only take effect at a boundary of the outgoing mode (a running
term already has attendance, grades and fees attached to it); a cohort's
assignments must tile its timeline with no gap or overlap; and an offering
serving cohorts on different modes must be refused.
