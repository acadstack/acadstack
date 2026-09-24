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


def save_permission_mapping(values: dict, actor) -> dict:
    """Saves permission->role mapping changes, guarded against lockout.

    ``values`` is ``{permission_name: [role_code, ...]}`` for the
    permissions being changed (settings_store keys, i.e. without the
    "permission." prefix are also accepted and normalized here).
    Refuses a save that would drop the acting user's own role from
    MANAGE_PERMISSIONS -- an admin must always be able to get back in.
    """
    normalized = {
        (k if k.startswith(f"{GROUP}.") else f"{GROUP}.{k}"): v
        for k, v in values.items()
    }
    manage_key = f"{GROUP}.{MANAGE_PERMISSIONS}"
    if manage_key in normalized and actor.role not in normalized[manage_key]:
        raise AcadStackException(
            "You cannot remove your own role from "
            f"'{MANAGE_PERMISSIONS}' -- this would lock every "
            "administrator out of managing permissions. Have another "
            "administrator make this change instead.")
    return ST.save_settings(normalized, login_id=actor.login_id)


#: Every role code except STU -- the shape of "any staff member, not a
#: student" that recurs across the inline checks this phase converts.
ALL_BUT_STU = [r for r in VD.codes("roles") if r != "STU"]

#: Every role code except STU and PLA -- nav.json's "-STU,-PLA" shape.
ALL_BUT_STU_PLA = [r for r in VD.codes("roles") if r not in ("STU", "PLA")]

#: Every role code except PLA -- nav.json's "-PLA,*" shape.
ALL_BUT_PLA = [r for r in VD.codes("roles") if r != "PLA"]

#: All role codes -- nav.json's "*" shape.
ALL_ROLES = VD.codes("roles")


# ===================== DECLARATIONS =====================
# One Spec per permission. The default is the role list that reproduces
# today's behaviour at the call site(s) the permission replaces -- see
# each Spec's doc for exactly which @rbac(roles=[...])/is_user_in_role()/
# Actor.has_role() site(s) it replaces, and docs/architecture.md's RBAC
# section for the overall design.

def _spec(name, default, doc):
    return ST.Spec(name, list, default=default, item_type=str,
                    choices=VD.codes("roles"), doc=doc)


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
              "Search for users/students. Replaces api_auth.user_find "
              "and api_auth.find_students (same authority, collapsed) "
              "and gates nav.json's 'Find Students' link."),
        _spec("user.view_others", ALL_BUT_STU,
              "View another user's profile (a student may only view "
              "their own)."),
        _spec("user.edit_any", ["ACA", "SUP"],
              "Edit another user's profile (a user may always edit "
              "their own)."),
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
        _spec("fees.manage_others_txn", ALL_BUT_STU,
              "Submit/view/delete another student's fee-transaction "
              "records (a student may always act on their own). "
              "Replaces three api_auth.py sites with identical authority."),

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
              "View/edit course slot timings. Replaces api_course.py's "
              "and api_dc.py's identical 'ACA,DEA' string-form checks."),
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

        # --- grades ---
        _spec("grades.upload", ["ACA", "FAC", "DEA"],
              "Upload grades for a course offering."),
        _spec("grades.export", ["ACA", "DEA", "SUP"],
              "View/download grade reports and gradesheets. Collapses "
              "eight sites across api_grades.py and api_reports.py that "
              "already shared this authority under inconsistent "
              "spacing/ordering."),
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
              "an enrolment's status directly. Collapses four sites in "
              "domain/enrolment.py and validation_checks.py, including "
              "one that used the buggy comma-string substring form."),
        _spec("enrolment.decide_as_owner", ["FAC", "HOD"],
              "Enrolment approval workflow: approve/reject as the "
              "offering's coordinating instructor and/or the student's "
              "batch advisor. Replaces the has_role(['FAC', 'HOD']) "
              "branch of the old approval chain."),
        _spec("enrolment.decide_advisor_pending", ["HOD"],
              "Enrolment approval workflow: approve/reject any enrolment "
              "pending advisor approval, with no ownership check. "
              "Replaces the has_role('HOD') branch of the old chain."),

        # --- feedback ---
        _spec("feedback.manage_form", ["ACA", "DEA"],
              "Create/edit a feedback form."),
        _spec("feedback.view_reports", ["ACA", "DEA"],
              "View feedback statistics/reports. Collapses three "
              "identically-gated api_feedback.py download endpoints."),
        _spec("feedback.view_instructor_feedback", ["FAC", "ACA", "DEA"],
              "View an instructor's feedback."),
        _spec("feedback.submit", ["STU"], "Submit course feedback."),

        # --- reports ---
        _spec("reports.generate", ["ACA", "DEA"],
              "Generate/view the general academic reports (fees, "
              "enrolments, feedback stats, credits, dept-wise averages, "
              "faculty scores, degree-wise students). Collapses eleven "
              "identically-gated sites across api_reports.py and one in "
              "api_dc.py."),
        _spec("reports.view", ALL_BUT_STU,
              "View the credits-earned / lecture-count reports "
              "(students excluded)."),
        _spec("reports.notify_credit_violation", ["ACA", "SUP"],
              "Trigger a credit-violation notification."),
        _spec("reports.view_cgpa_sgpa", ["ACA", "DEA", "GUE"],
              "View the CGPA/SGPA report."),

        # --- doctoral committee / PhD ---
        _spec("dc.mark_attendance", ["ACA", "FAC"], "Mark attendance."),
        _spec("dc.view_instructor_academics", ["ACA", "FAC", "HOD", "DEA"],
              "View an instructor's academic workload."),
        _spec("dc.view_advisor_detail", ["FAC", "ACA", "DEA", "HOD"],
              "View a batch advisor's detail."),
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
              "DC-membership ownership. Collapses two api_dc.py sites."),
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
        # These gate a nav.json menu entry whose current role list does
        # not exactly match any backend permission above (nav has always
        # been filtered slightly differently -- sometimes stricter,
        # sometimes looser -- than the endpoint it links to; preserved
        # exactly rather than silently unified with a same-named backend
        # permission that would change who sees the link).
        _spec("nav.user_search", ["SUP", "DEA", "ACA", "RES"],
              "nav.json: 'Find User' menu link."),
        _spec("nav.user_create", ["SUP", "DEA", "ACA"],
              "nav.json: 'New User' menu link."),
        _spec("nav.upload_user_faces", ["ACA", "DEA"],
              "nav.json: 'Upload User Faces' menu link."),
        _spec("nav.add_users", ["ACA", "DEA", "SUP"],
              "nav.json: 'Add Users' menu link."),
        _spec("nav.manage_batch_advisors", ["ACA", "DEA", "SUP"],
              "nav.json: 'Manage Batch Advisors' menu link."),
        _spec("nav.view_attendance", [],
              "nav.json: 'View Attendance' menu link. Pre-existing bug, "
              "preserved rather than silently fixed: the old role string "
              "was '-STU,-PLA' with no trailing '*', so under the old "
              "substring-containment check NO role code was ever a "
              "substring of that literal string -- this link has never "
              "actually been visible to anyone. Flagged for a follow-up "
              "decision; the evident intent was ALL_BUT_STU_PLA."),
        _spec("nav.general_access", ALL_BUT_PLA,
              "nav.json: menu links open to everyone but PLA -- "
              "'Courses Offered For Enrolment', 'Courses Available For "
              "Offering', 'Slotwise Courses', 'Search Doctoral Committe', "
              "'My Progress Reports'."),
        _spec("nav.offer_course", ["FAC", "ACA"],
              "nav.json: 'Offer a Course For Enrolment' menu link."),
        _spec("nav.create_course", ["ACA", "FAC"],
              "nav.json: 'Create New Course' menu link."),
        _spec("nav.bulk_create_courses", ["ACA"],
              "nav.json: 'Bulk Create Courses' menu link."),
        _spec("nav.bulk_enrol", ["ACA"],
              "nav.json: 'Bulk Enrol in Course' menu link."),
        _spec("nav.upload_grades", ["FAC", "ACA"],
              "nav.json: 'Upload Grades' menu link."),
        _spec("nav.view_academic_events", ALL_ROLES,
              "nav.json: 'Academic Events' menu link (everyone)."),
        _spec("nav.generate_credits_data", ["ACA", "SUP"],
              "nav.json: 'Generate Students Credits Data' menu link."),
        _spec("nav.my_work", ["FAC"],
              "nav.json: the 'My Work' menu -- 'Courses Offered', "
              "'Courses Created', 'Action Pending'."),
        _spec("nav.create_feedback", ["ACA"],
              "nav.json: 'Create Feedback' menu link."),
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
              "nav.json: 'Submit Progress Report' menu link."),
    ],
    doc="Named permissions: which roles may do what. Replaces the raw "
        "role lists formerly spelled out at each @rbac(roles=[...]) "
        "decorator and is_user_in_role()/Actor.has_role() call site. "
        "Editable through save_permission_mapping(), which refuses a "
        "save that would remove the acting admin's own access to "
        "system.manage_permissions."
)
