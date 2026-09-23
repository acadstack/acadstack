# Approval workflows as data

How AcadStack's approval chains are defined, how a request is resolved against
them, and how an institution changes a chain without touching code.

Code: `api_service/domain/workflow.py` (the engine), `domain/enrolment.py`,
`domain/dc.py`, `domain/course.py` (the three workflows and what their rows refer
to), `domain/milestones.py`, the `WorkflowDefinition` / `WorkflowTransition` /
`MilestoneDefinition` models in `models.py`, and `tests/test_workflows.py`.

---

## 1. The problem

Each approval chain used to be written as code, and each in a different place:

- **Enrolment**: a nested `if/elif` over the user's role, their relationship to
  the enrolment (course instructor, batch advisor, both) and the current status.
- **Doctoral committee**: an inline `{"HOD": "SUB,RTH", "FAC": "DRA,RTS"}` map of
  which statuses each role may *edit*. It never checked the status being moved
  *to*, so the approval graph existed only as an `actionsMap` in `DcDetails.vue`.
- **Course**: a rule that APP/RET are locked, and nothing else. The
  HAP → CAP → APP chain existed only as an `actionsMap` in `CourseDetails.vue`.

That meant an institution could not add or remove an approval step without
changing code, and for DC and course the server accepted any status the client
sent.

## 2. The model

A **workflow** is one `WorkflowDefinition` row plus its `WorkflowTransition` rows.

| `WorkflowDefinition` | |
|---|---|
| `name` | `enrolment`, `dc`, `course` |
| `status_vocab` | the controlled vocabulary its statuses come from (`enrolment_statuses`, ...) |
| `match_on` | `action` (the caller names an action: approve/reject) or `to_status` (the caller names the status it wants) |
| `pre_checks` | checks run before a transition is chosen (e.g. DC composition) |
| `checks` | checks run for every transition, after it is chosen |
| `locked_message` | shown when the user has no transition out of the record's current status |
| `denied_message` | shown when they have some, but not the one asked for |

Messages may use `{role}`, `{from_status}`, `{to_status}`, `{from_label}`,
`{to_label}`.

| `WorkflowTransition` | |
|---|---|
| `priority` | rows are tried in this order; unique per workflow |
| `from_status` | a status code, `*` (any existing status) or `_new` (a record being created) |
| `to_status` | a status code, or `=` (unchanged: an edit that keeps the record where it is) |
| `action` | for `match_on = action` workflows |
| `label` | the button label the frontend shows |
| `permission` | a named permission (`permissions.py`) the user must hold |
| `guards` | names of guards that must all hold for the row to apply; prefix `!` to negate |
| `checks` | `[{"name", "params"}]`, run after the row is chosen; a failure refuses the request |
| `effects` | `[{"name", "params"}]`, run after the record is saved |
| `is_active` | inactive rows are ignored |

### Guards, checks and effects stay in code, referenced by name

- A **guard** (`fn(ctx) -> bool`) decides whether a row *applies*. If it fails,
  the engine tries the next row. Example: `enrolment.is_instructor`.
- A **check** (`fn(ctx, **params)`) decides whether an applicable move is *allowed
  right now*, and raises with a message if not. No other row is tried. Examples:
  `enrolment.change_allowed` (add/drop window, offering status) and
  `dc.composition` (whose role counts are params, so they are data too).
- An **effect** (`fn(ctx, **params)`) runs after the save. Examples:
  `notify.enrolment`, `notify.course_updated`, and `milestone.record` with a
  milestone code.

Anything that needs a real query lives in the domain module that owns the
workflow, registered with `@WF.guard` / `@WF.check` / `@WF.effect`. Institutions
can register more from a plugin (`domain/plugins.py`). Enrolment ownership is
still computed by the batched SQL in `ownership_flags()` and handed to the guards
as precomputed `facts`, so approving a batch costs one query, not one per row.

## 3. How a request is resolved

1. The workflow's `pre_checks` run.
2. Collect the active rows leaving the record's current status whose permission
   the user holds. If there are none, raise `locked_message`.
3. Take the first of those, by priority, that matches the request and whose
   guards all hold. If none does, raise `denied_message`.
4. Run the workflow's `checks`, then the row's `checks`.
5. Save the record, then run the row's `effects`.

The locked/denied split is what reproduces the old enrolment errors exactly. An
uninvolved faculty member holds `enrolment.decide_as_owner`, so rows leave every
status and they get the "privileges" message when no guard matches. A role with
no enrolment permission at all gets "Unexpected user role".

## 4. The shipped tables

Each workflow ships a baseline table in code (`BASELINE` in its domain module).
`default_seed_data.seed_workflows()` stores it on first boot, one workflow at a
time and never merged into an edited table, so a removed step does not come
back. Until something is stored, `workflow.load()` answers from the baseline,
which is what lets domain tests run without a database.

- **Enrolment** reproduces the old chain exactly. That includes the two quirks
  `tests/test_enrolment_state_machine.py` pins: an advisor acting alone takes any
  status straight to ENRO, and an HOD may decide any APEN enrolment with no
  ownership check. `tests/test_workflows.py` compares the table with a verbatim
  copy of the old chain across every role × ownership × status × action.
- **DC** enforces the graph the UI always offered. The supervisor drafts, submits
  and deletes (DRA/RTS). The HoD of the student's department forwards or returns
  (SUB/RTH). The Dean approves or returns (FTD). The academic section moves any
  non-draft DC to any status. Creating a DC records `DC_PROPOSED`, and moving it
  to APP records `DC_APPROVED`.
- **Course** also enforces the UI's graph. The author submits DRA/HAR/CAR → HAP,
  the HoD of the course's department (its author's department, check
  `course.actor_in_course_dept`) takes HAP → CAP/HAR, and the Dean or
  academic section takes
  CAP → APP/CAR. Editing in place (`=`) is open to course editors until APP/RET,
  and after that needs `course.edit_locked_status`. Every edit of an existing
  course first passes `course.author_or_permitted`. The author may always edit.
  Holders of `course.edit_any` (ACA/DEA/RES) may edit any course, and holders of
  `course.edit_in_dept` (HOD) only their own department's.

## 5. Changing a workflow

`GET /workflow/<name>` returns the table plus the guard, check and effect names
available. `POST /workflow_save` replaces the whole table. Both need
`system.manage_workflows` (seeded to SUP). A save is refused if:

- it names an unknown status, permission, guard, check, effect or milestone;
- two rows share a priority;
- it would **strand records**: some records sit in a status they could leave
  under the current table but could not leave under the new one. Move them on
  first, or keep a transition out of that status.

Transition tables are not effective-dated like grading policy
(`versioned-policy.md`). They describe how work moves now; nothing is recomputed
from them later.

Example: to drop the HoD step from course approval, remove the
`course.hod_review` rows and the rows into HAP, then add rows DRA → CAP and
CAR → CAP with permission `course.submit`. `tests/test_workflows.py` does exactly
this.

## 6. Milestones

The PhD milestone sequence is `MilestoneDefinition` rows (code, label, sequence,
`applies_to`), seeded from `domain/milestones.BASELINE`. An `AcademicMilestone`
stores a code, and recording an unknown or inactive code is refused. Recording a
milestone the student has already reached is a no-op, so a DC that is approved,
returned and approved again does not fail on the unique index.
`POST /milestones_save` replaces the sequence. It will not remove a code that
students have reached (deactivate it instead), and a code a workflow records
must stay active.

## 7. Plugins

`ENROLMENT_NEXT_STATUS` still exists. Its default resolves the enrolment table
(guards only). An institution that overrides it keeps the old contract: its
function picks the status, the calendar check runs, and `ENROLMENT_NOTIFY`
fires. Most changes no longer need a plugin, because they are an edit to the
table.
