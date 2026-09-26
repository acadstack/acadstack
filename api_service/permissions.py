"""Named permissions, backed by the ``"permission"`` settings_store group.

Authority is granted through named permissions rather than a raw role list
spelled out at each call site -- an ``@rbac(roles=[...])`` decorator, an
inline ``is_user_in_role()``/``Actor.has_role()`` check -- which would let
the same authority end up written inconsistently in different places, and
would mean auditing every site by hand to add a role.

Every one of those decisions has a name (``course.approve``,
``grades.export``, ...) and the name's current role list lives in one
place: the ``SystemSetting`` rows of the ``"permission"`` settings group
(declared in ``settings_store.py``, seeded in ``default_seed_data.py``).
Renaming, adding, or removing a role now means editing that mapping, not
every call site.

This module is the read (and guarded write) API over that group. It is a
leaf module -- it only imports ``settings_store`` and ``vocab_defaults``,
never ``quart`` or ``api_common`` -- so it is safe to import from the
domain layer (``domain/context.py``'s ``Actor.can()``) the same way
``domain/policy.py``'s ``load_*`` functions read ``settings_store``
directly.
"""

from typing import Sequence

import settings_store as ST
import vocab_defaults as VD
from common import AcadStackException

GROUP = "permission"

#: The permission that gates editing the permission->role mapping itself.
#: Seeded to SUP only; see save_permission_mapping()'s lockout guard.
MANAGE_PERMISSIONS = "system.manage_permissions"


def roles_for_permission(name: str) -> list:
    """The role codes currently granted the named permission."""
    return ST.setting(f"{GROUP}.{name}")


def role_has_permission(role_code: str, name: str) -> bool:
    """Whether ``role_code`` holds the named permission."""
    return role_code in roles_for_permission(name)


def permissions_for_role(role_code: str) -> list:
    """Every declared permission ``role_code`` currently holds, sorted.

    Used to hand the frontend the acting user's permission set (alongside
    ``nav``), so ``webapp/src/main.js`` can gate UI without duplicating
    the mapping.
    """
    group = ST.declared_groups().get(GROUP)
    if not group:
        return []
    return sorted(
        name for name in group.specs
        if role_code in (ST.setting(f"{GROUP}.{name}") or [])
    )


def normalized(values: dict) -> dict:
    """``values`` keyed by full settings_store key ("permission.<name>"),
    whether or not the caller included the prefix."""
    return {
        (k if k.startswith(f"{GROUP}.") else f"{GROUP}.{k}"): v
        for k, v in values.items()
    }


def check_no_self_lockout(values: dict, actor) -> None:
    """The guard save_permission_mapping() applies, on its own.

    Raises AcadStackException if ``values`` (as accepted by
    save_permission_mapping()) would drop ``actor``'s own role from
    MANAGE_PERMISSIONS -- an admin must always be able to get back in.
    """
    manage_key = f"{GROUP}.{MANAGE_PERMISSIONS}"
    values = normalized(values)
    if manage_key in values and \
            actor.role not in (values[manage_key] or []):
        raise AcadStackException(
            "You cannot remove your own role from "
            f"'{MANAGE_PERMISSIONS}' -- this would lock every "
            "administrator out of managing permissions. Have another "
            "administrator make this change instead.")


def save_permission_mapping(values: dict, actor) -> dict:
    """Saves permission->role mapping changes, guarded against lockout.

    ``values`` is ``{permission_name: [role_code, ...]}`` for the
    permissions being changed (settings_store keys, i.e. with the
    "permission." prefix, are also accepted and normalized here).
    Refuses a save that would drop the acting user's own role from
    MANAGE_PERMISSIONS (see check_no_self_lockout()).
    """
    check_no_self_lockout(values, actor)
    return ST.save_settings(normalized(values), login_id=actor.login_id)


def describe_mapping(actor) -> dict:
    """The permission->role mapping as the admin screen renders it: every
    declared permission with its doc, default and current roles, plus the
    role vocabulary for the matrix columns. ``actor_role`` lets the screen
    show up front which cell the lockout guard will refuse to clear."""
    group = ST.declared_groups()[GROUP]
    return {
        "roles": [{"code": r["code"], "label": r["label"]}
                  for r in ST.vocab("roles")],
        "permissions": [
            {
                "name": name,
                "prefix": name.split(".", 1)[0],
                "doc": spec.doc,
                "default": list(spec.default),
                "roles": list(roles_for_permission(name) or []),
            }
            for name, spec in sorted(group.specs.items())
        ],
        "group_doc": group.doc,
        "manage_permission": MANAGE_PERMISSIONS,
        "actor_role": actor.role,
    }


#: Every role code except STU -- the shape of "any staff member, not a
#: student" that recurs across many of the permissions below.
ALL_BUT_STU = [r for r in VD.codes("roles") if r != "STU"]

#: Every role code except PLA -- nav.json's "-PLA,*" shape.
ALL_BUT_PLA = [r for r in VD.codes("roles") if r != "PLA"]

#: Every role code except STU and PLA -- nav.json's "-STU,-PLA,*" shape.
ALL_BUT_STU_PLA = [r for r in VD.codes("roles") if r not in ("STU", "PLA")]

#: All role codes -- nav.json's "*" shape.
ALL_ROLES = VD.codes("roles")


# ===================== DECLARATIONS =====================
# One Spec per permission. The default is the role list an institution
# starts with out of the box. See docs/architecture.md's RBAC section for
# the overall design.

def _spec(name, default, doc):
    # Validated against the live role vocabulary, so a role an institution
    # adds can be granted permissions straight away.
    return ST.Spec(name, list, default=default,
                    choices_vocab="roles", doc=doc)


ST.declare_group(
    GROUP,
    [
        # --- system / user management ---
        _spec("system.manage_permissions", ["SUP"],
              "Edit the permission->role mapping itself. An admin can "
              "never remove their own role from this permission."),
        _spec("system.manage_workflows", ["SUP"],
              "Edit the approval workflow transition tables "
              "(domain/workflow.py)."),
        _spec("system.manage_settings", ["SUP"],
              "Edit DB-backed system settings and controlled vocabularies "
              "(settings_store.py) through the admin GUI."),
        _spec("system.manage_academic_policy", ["SUP"],
              "Create new versions of effective-dated academic policy "
              "(policy_store.py), e.g. the grade point map. Kept as its "
              "own permission rather than folded into "
              "system.manage_settings: policy of record can retroactively "
              "affect how a transcript reads, which is categorically more "
              "dangerous than an operational knob like a semester date, "
              "so an institution can delegate settings without also "
              "delegating this."),
        _spec("system.close_academic_session", ["SUP", "DEA"],
              "Close an academic session (policy_store.close_session), "
              "sealing the academic policy in force up to it. Cannot be "
              "undone. Separate from system.manage_academic_policy "
              "because closing follows results being declared -- an "
              "academic-office act -- rather than writing policy, and "
              "holders of it can view (not change) the policy screen "
              "they close sessions from."),
        _spec("system.export_config", ["SUP"],
              "Export the full configuration document (config_transfer.py) "
              "-- every settings/vocab group INCLUDING the permission->role "
              "mapping, plus full policy history. Broader than "
              "system.manage_settings/system.manage_academic_policy, which "
              "each see only their own slice; kept separate so those two "
              "can be delegated without also handing out a full-install "
              "config dump."),
        _spec("system.import_config", ["SUP"],
              "Import a configuration document (config_transfer.py), "
              "overwriting every settings/vocab group it names and adding "
              "any policy version it names that this install can still "
              "accept. The single most powerful write in the admin "
              "surface -- can rewrite the permission->role mapping and "
              "every operational setting in one call -- so it is not "
              "folded into any of the narrower settings/policy/permission "
              "permissions."),
        _spec("system.view_active_users", ["ACA", "SUP", "DEA"],
              "View the list of currently active users."),
        _spec("user.search", ALL_BUT_STU,
              "Search for users/students. Also gates nav.json's 'Find "
              "Students' menu link."),
        _spec("user.view_others", ALL_BUT_STU,
              "View another user's profile (a student may only view "
              "their own)."),
        _spec("user.edit_any", ["ACA", "SUP"],
              "Edit any field of any user's record, including their own "
              "role/degree/status (without it a user may edit only their "
              "own name, email and gender)."),
        _spec("user.bulk_create", ["ACA", "SUP"],
              "Bulk-create users from an upload."),
        _spec("user.delete", ["SUP"], "Delete a user."),
        _spec("user.assign_advisor", ["ACA", "DEA"],
              "Assign batch advisors."),
        _spec("user.upload_document", ALL_BUT_STU,
              "Upload a document to a student's user record."),
        _spec("user.view_document", ["ACA", "DEA"],
              "View another user's uploaded documents (the owner may "
              "always view their own)."),
        _spec("user.bulk_upload_faces", ["ACA"],
              "Bulk-upload face images for photo-based attendance."),
        _spec("faces.upload_own", ALL_BUT_STU,
              "Set or replace your own reference photo for photo-based "
              "attendance. Students are excluded by default, since a "
              "student could otherwise swap in someone else's face. "
              "user.edit_any holders may set anyone's photo."),
        _spec("fees.manage_others_txn", ALL_BUT_STU,
              "Submit/view/delete another student's fee-transaction "
              "records (a student may always act on their own)."),

        # --- courses ---
        _spec("course.save", ["ACA", "FAC", "DEA", "HOD", "RES"],
              "Create/edit a course."),
        _spec("course.edit_any", ["ACA", "DEA", "RES"],
              "Edit a course authored by someone else, in any department "
              "(the author may always edit their own)."),
        _spec("course.edit_in_dept", ["HOD"],
              "Edit a course authored by someone else in the actor's own "
              "department (the course's department is its author's)."),
        _spec("course.edit_locked_status", ["DEA", "ACA", "RES"],
              "Edit a course that is already Approved or Retired."),
        _spec("course.bulk_create", ["ACA", "DEA"],
              "Bulk-create courses from an upload."),
        _spec("course.manage_slot_timings", ["ACA", "DEA"],
              "View/edit course slot timings."),
        _spec("course.submit", ["FAC"],
              "Course approval workflow: submit a course to the HoD."),
        _spec("course.hod_review", ["HOD"],
              "Course approval workflow: forward a course to the council "
              "or return it to the faculty."),
        _spec("course.final_approve", ["DEA", "ACA"],
              "Course approval workflow: approve a course or return it "
              "to the department."),
        _spec("course_offering.save", ["ACA", "FAC", "DEA", "HOD"],
              "Create/edit a course offering."),
        _spec("course_offering.edit_after_close", ["ACA", "DEA"],
              "Edit a course offering that has finished/been cancelled."),
        _spec("course_offering.edit_any", ["ACA", "DEA", "HOD"],
              "Edit a course offering without being its coordinating "
              "instructor."),
        _spec("course_offering.view_stats", ALL_BUT_STU,
              "View a course's grade and attendance statistics across its "
              "offerings (api_course_offering.fetch_stats)."),
        _spec("course_offering.view_all_running", ["ACA", "DEA", "SUP"],
              "See every running course offering rather than only the "
              "ones the actor instructs."),

        # --- grades ---
        _spec("grades.upload", ["ACA", "FAC", "DEA"],
              "Upload grades for a course offering."),
        _spec("grades.upload_any", ["ACA", "DEA"],
              "Upload grades for a course offering without being its "
              "coordinating instructor (narrower than grades.upload -- "
              "no FAC, who must still be the coordinator)."),
        _spec("grades.export", ["ACA", "DEA", "SUP"],
              "View/download grade reports and gradesheets."),
        _spec("grades.view_distribution", ["DEA", "ACA"],
              "View the grade distribution report (narrower than "
              "grades.export -- no SUP)."),
        _spec("grades.download_reports", ALL_BUT_STU,
              "Download CGPA/SGPA and category-wise-earned-credits "
              "reports (students excluded, all staff roles allowed)."),

        # --- enrolment ---
        _spec("enrolment.view_instructor_courses", ["FAC", "ACA", "DEA"],
              "View the courses a user instructs, for enrolment."),
        _spec("enrolment.view_advisor_courses", ["ADV", "ACA", "DEA", "HOD"],
              "View the courses a user advises, for enrolment."),
        _spec("enrolment.bulk_enrol", ["ACA", "DEA"],
              "Bulk-enrol students in a course."),
        _spec("enrolment.download_for_grades", ["FAC", "ACA", "DEA"],
              "Download a course's enrolment list for grading."),
        _spec("enrolment.download_csv", ALL_BUT_STU,
              "Download enrolment data as CSV."),
        _spec("enrolment.request", ["ACA", "STU"],
              "Request/submit course enrolment."),
        _spec("enrolment.change_status", ["ACA", "DEA", "FAC", "HOD"],
              "Change an enrolment's approval status."),
        _spec("enrolment.override", ["ACA", "DEA"],
              "Bypass the instructor/advisor approval chain and decide "
              "an enrolment's status directly."),
        _spec("enrolment.decide_as_owner", ["FAC", "HOD"],
              "Enrolment approval workflow: approve/reject as the "
              "offering's coordinating instructor and/or the student's "
              "batch advisor."),
        _spec("enrolment.decide_advisor_pending", ["HOD"],
              "Enrolment approval workflow: approve/reject any enrolment "
              "pending advisor approval, with no ownership check."),
        _spec("enrolment.view_grades_export", ["ACA", "DEA", "HOD"],
              "Include grades in a course offering's enrolment export "
              "without being its coordinating instructor."),

        # --- feedback ---
        _spec("feedback.manage_form", ["ACA", "DEA"],
              "Create/edit a feedback form."),
        _spec("feedback.view_reports", ["ACA", "DEA"],
              "View feedback statistics/reports."),
        _spec("feedback.view_instructor_feedback", ["FAC", "ACA", "DEA"],
              "View an instructor's feedback."),
        _spec("feedback.submit", ["STU"], "Submit course feedback."),

        # --- reports ---
        _spec("reports.generate", ["ACA", "DEA"],
              "Generate/view the general academic reports (fees, "
              "enrolments, feedback stats, credits, dept-wise averages, "
              "faculty scores, degree-wise students)."),
        _spec("reports.view", ALL_BUT_STU,
              "View the credits-earned / lecture-count reports "
              "(students excluded)."),
        _spec("reports.notify_credit_violation", ["ACA", "SUP"],
              "Trigger a credit-violation notification."),
        _spec("reports.view_cgpa_sgpa", ["ACA", "DEA", "GUE"],
              "View the CGPA/SGPA report."),

        # --- doctoral committee / PhD ---
        _spec("dc.mark_attendance", ["ACA", "FAC"], "Mark attendance."),
        _spec("dc.mark_attendance_any", ["ACA", "DEA"],
              "Mark attendance for a course offering without being its "
              "coordinating instructor. Currently only ever grants ACA "
              "in practice: the endpoint's own dc.mark_attendance "
              "permission excludes DEA, so a DEA actor never reaches "
              "this check."),
        _spec("dc.view_instructor_academics", ["ACA", "FAC", "HOD", "DEA"],
              "View an instructor's academic workload."),
        _spec("dc.view_advisor_detail", ["FAC", "ACA", "DEA", "HOD"],
              "View a batch advisor's detail."),
        _spec("dc.view_daywise_attendance", ["SUP", "ACA", "DEA", "HOD"],
              "View a course offering's day-wise attendance without "
              "being (one of) its instructors."),
        _spec("dc.download_degree_wise_students", ["ACA", "DEA", "HOD"],
              "Download the degree-wise student list."),
        _spec("dc.save", ["ACA", "FAC", "DEA", "HOD"],
              "Create/edit a doctoral committee."),
        _spec("dc.override_status", ["ACA", "DEA"],
              "DC workflow: the academic section's rows -- move a DC "
              "between any non-draft statuses."),
        _spec("dc.edit_as_supervisor", ["FAC"],
              "DC workflow: edit/submit a DC in Draft or Returned to "
              "Supervisor, as its supervisor."),
        _spec("dc.edit_as_hod", ["HOD"],
              "DC workflow: forward/return a DC Submitted to or "
              "Returned to the HoD of the student's department."),
        _spec("dc.dean_approval", ["DEA"],
              "DC workflow: approve a DC forwarded to the Dean, or "
              "return it to the HoD."),
        _spec("dc.view_dc_students", ALL_BUT_STU,
              "View the list of students under DC formation."),
        _spec("dc.manage_any", ["ACA", "DEA", "SUP"],
              "Act on any student's DC/progress-report data, bypassing "
              "DC-membership ownership."),
        _spec("dc.manage_progress_report", ALL_BUT_STU,
              "Submit a PhD progress report."),
        _spec("student.export_list", ["PLA"],
              "Export the student list (Placement cell)."),

        # --- workflow / calendar ---
        _spec("academic_calendar.manage_dates", ["ACA", "DEA"],
              "Manage academic calendar dates."),
        _spec("workflow_notes.manage", ALL_BUT_STU,
              "Add/delete workflow notes."),

        # --- nav.json-only permissions ---
        # These gate a nav.json menu entry whose role list does not
        # exactly match the backend permission the link's endpoint
        # enforces (sometimes stricter, sometimes looser -- see each
        # Spec's doc for the specific gap). Kept separate rather than
        # folded onto that backend permission, which would silently
        # change who sees the link.
        _spec("nav.user_search", ["SUP", "DEA", "ACA", "RES"],
              "nav.json: 'Find User' menu link -- narrower than "
              "user.search, which the /user_find lookup behind it "
              "enforces: HOD, FAC, GUE, PLA and ADV can search but do "
              "not see this link."),
        _spec("nav.user_create", ["SUP", "DEA", "ACA"],
              "nav.json: 'New User' menu link -- broader than "
              "user.edit_any, which /user_save requires to create a "
              "user: DEA sees this link but cannot save a new user."),
        _spec("nav.upload_user_faces", ["ACA", "DEA"],
              "nav.json: 'Upload User Faces' menu link -- broader than "
              "user.bulk_upload_faces, which the upload endpoint "
              "enforces: DEA sees this link but the upload is "
              "rejected."),
        _spec("nav.add_users", ["ACA", "DEA", "SUP"],
              "nav.json: 'Add Users' menu link -- broader than "
              "user.bulk_create, which the endpoint enforces: DEA sees "
              "this link but the bulk-create is rejected."),
        _spec("nav.manage_batch_advisors", ["ACA", "DEA", "SUP"],
              "nav.json: 'Manage Batch Advisors' menu link -- broader "
              "than user.assign_advisor, which the endpoint enforces: "
              "SUP sees this link but cannot assign advisors."),
        _spec("nav.view_attendance", ALL_BUT_STU_PLA,
              "nav.json: 'View Attendance' menu link, open to every "
              "role except STU and PLA."),
        _spec("nav.general_access", ALL_BUT_PLA,
              "nav.json: menu links open to everyone but PLA -- "
              "'Courses Offered For Enrolment', 'Courses Available For "
              "Offering', 'Slotwise Courses', 'Search Doctoral Committe', "
              "'My Progress Reports'."),
        _spec("nav.offer_course", ["FAC", "ACA"],
              "nav.json: 'Offer a Course For Enrolment' menu link -- "
              "narrower than course_offering.save, which the endpoint "
              "enforces: DEA and HOD can save a course offering but do "
              "not see this link."),
        _spec("nav.create_course", ["ACA", "FAC"],
              "nav.json: 'Create New Course' menu link -- narrower "
              "than course.save, which the endpoint enforces: DEA, HOD "
              "and RES can save a course but do not see this link."),
        _spec("nav.bulk_create_courses", ["ACA"],
              "nav.json: 'Bulk Create Courses' menu link -- narrower "
              "than course.bulk_create: DEA can bulk-create courses "
              "but does not see this link."),
        _spec("nav.bulk_enrol", ["ACA"],
              "nav.json: 'Bulk Enrol in Course' menu link -- narrower "
              "than enrolment.bulk_enrol: DEA can bulk-enrol but does "
              "not see this link."),
        _spec("nav.upload_grades", ["FAC", "ACA"],
              "nav.json: 'Upload Grades' menu link -- narrower than "
              "grades.upload: DEA can upload grades but does not see "
              "this link."),
        _spec("nav.view_academic_events", ALL_ROLES,
              "nav.json: 'Academic Events' menu link (everyone)."),
        _spec("nav.generate_credits_data", ["ACA", "SUP"],
              "nav.json: 'Generate Students Credits Data' menu link -- "
              "differs from reports.generate, which the endpoint "
              "enforces: SUP sees this link but cannot generate the "
              "data, while DEA can generate it but does not see this "
              "link."),
        _spec("nav.my_work", ["FAC"],
              "nav.json: the 'My Work' menu -- 'Courses Offered', "
              "'Courses Created', 'Action Pending'."),
        _spec("nav.create_feedback", ["ACA"],
              "nav.json: 'Create Feedback' menu link -- narrower than "
              "feedback.manage_form: DEA can create a feedback form "
              "but does not see this link."),
        _spec("nav.reports_manage", ["ACA", "SUP", "DEA"],
              "nav.json: menu links open to ACA/SUP/DEA -- 'Feedback "
              "Stats', 'Dept Wise Feedback Average', 'Course Wise "
              "Faculty Feedback Score', 'Question Wise Faculty Feedback "
              "Score', 'Course Wise Grade Distribution', 'Student "
              "Strength Degree/Course wise'."),
        _spec("nav.reports_broad", ["ACA", "SUP", "DEA", "RES", "FAC"],
              "nav.json: 'Check Total Credits', 'Check Category-wise "
              "Credits', 'Generate Course Enrolments' menu links."),
        _spec("nav.student_self_service", ["STU"],
              "nav.json: student-only self-service menu links -- "
              "'Student Record', 'Fees Payment Record', 'Course "
              "Feedback', 'Pay Fees Online', 'Profile Photo'."),
        _spec("nav.pending_tasks", ["HOD", "DEA"],
              "nav.json: 'Pending Tasks' menu link."),
        _spec("nav.cgpa_sgpa", ["ACA", "SUP", "DEA", "GUE"],
              "nav.json: 'Generation of CGPA and SGPA report' menu "
              "link (broader than reports.view_cgpa_sgpa -- includes "
              "SUP)."),
        _spec("nav.submit_progress_report", ["FAC", "ACA", "HOD", "DEA"],
              "nav.json: 'Submit Progress Report' menu link -- narrower "
              "than dc.manage_progress_report, which /ppr_save "
              "enforces: RES, SUP, GUE, PLA and ADV can submit a "
              "progress report but do not see this link."),
    ],
    doc="Named permissions: which roles may do what. Editable through "
        "save_permission_mapping(), which refuses a save that would "
        "remove the acting admin's own access to "
        "system.manage_permissions."
)
