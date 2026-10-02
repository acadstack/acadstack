"""Tests for the stored permissions: every role keeps the access the role
checks gave it, the menus follow the permissions, and grants can be changed
but not in a way that locks the admin out."""

import json
import re
from pathlib import Path

import pytest

import common as C
import models as M
import policy as P
import settings
from conftest import enrol, make_offering, make_user, set_event_window

ROLES = ["STU", "ACA", "FAC", "HOD", "DEA", "SUP", "GUE", "PLA", "ADV", "RES"]
PUBLIC = "public"
LOGIN = ROLES


def _but(*excl):
    return sorted(r for r in ROLES if r not in excl)


# Who could call each route through the role checks this replaced: the
# @rbac(roles=...) list, or LOGIN for a bare @rbac.
ROLE_CHECKS = {
    "assign_advisor": ['ACA', 'DEA'],
    "attendance_find": LOGIN,
    "bulk_add_courses": ['ACA', 'DEA'],
    "bulk_add_users": ['ACA', 'SUP'],
    "bulk_download_sem_grade": ['ACA', 'DEA', 'SUP'],
    "bulk_enrol_in_course": ['ACA', 'DEA'],
    "cgpa_sgpa": ['ACA', 'DEA', 'GUE'],
    "change_enroll_status": ['ACA', 'ADV', 'DEA', 'FAC', 'HOD'],
    "course_enrollment_save": LOGIN,
    "course_enrollment_view": LOGIN,
    "course_find": LOGIN,
    "course_lect_in_session": LOGIN,
    "course_lookup": LOGIN,
    "course_offering_find": LOGIN,
    "course_offering_lookup": LOGIN,
    "course_offering_lookup_all": LOGIN,
    "course_offering_save": ['ACA', 'DEA', 'FAC', 'HOD'],
    "course_offering_view": LOGIN,
    "course_save": ['ACA', 'DEA', 'FAC', 'HOD', 'RES'],
    "course_view": LOGIN,
    "course_wise_faculty_score": ['ACA', 'DEA'],
    "credits_earned_report": LOGIN,
    "dates_save": ['ACA', 'DEA'],
    "dates_search": LOGIN,
    "dc_details": LOGIN,
    "dc_save": ['ACA', 'DEA', 'FAC', 'HOD'],
    "dc_search": LOGIN,
    "degree_wise_students": ['ACA', 'DEA'],
    "delete_doc": LOGIN,
    "delete_student_reg_fees_data": LOGIN,
    "download_catwise_earned_credits": LOGIN,
    "download_cgpa_sgpa": LOGIN,
    "download_consolidated_grade_sheet": ['ACA', 'DEA', 'SUP'],
    "download_course_enrollments": LOGIN,
    "download_course_enrolments": LOGIN,
    "download_course_wise_faculty_score": ['ACA', 'DEA'],
    "download_degree_certifcate": ['ACA', 'DEA', 'SUP'],
    "download_degree_wise_students": ['ACA', 'DEA', 'HOD'],
    "download_dept_wise_avg": ['ACA', 'DEA'],
    "download_enrollments_for_grades": ['ACA', 'DEA', 'FAC'],
    "download_feedback_stats": ['ACA', 'DEA'],
    "download_grade_distribution": ['ACA', 'DEA'],
    "download_grade_status": ['ACA', 'DEA', 'SUP'],
    "download_quewise_facfeedbk_score": ['ACA', 'DEA'],
    "download_sem_grade": ['ACA', 'DEA', 'SUP'],
    "drop_withdraw_course": LOGIN,
    "earned_credit_check": LOGIN,
    "enroll_in_courses": ['ACA', 'STU'],
    "fetch_stats": LOGIN,
    "find_advisor": LOGIN,
    "find_students": LOGIN,
    "gen_prk": PUBLIC,
    "generate_course_enrolments": ['ACA', 'DEA'],
    "generate_dept_wise_avg": ['ACA', 'DEA'],
    "generate_feedback_stats": ['ACA', 'DEA'],
    "generate_grade_status": ['ACA', 'DEA', 'SUP'],
    "generate_semester_grade": ['ACA', 'DEA', 'SUP'],
    "generate_students_credits_info": ['ACA', 'DEA'],
    "get_active_feedback_form": LOGIN,
    "get_active_users": ['ACA', 'DEA', 'SUP'],
    "get_advisor_courses_enrol": ['ACA', 'ADV', 'DEA', 'HOD'],
    "get_advisor_detail": ['ACA', 'DEA', 'FAC', 'HOD'],
    "get_background_task_status": ['ACA', 'DEA'],
    "get_bulk_gradesheets": ['ACA', 'DEA', 'SUP'],
    "get_class_photo": LOGIN,
    "get_course_attd_on_date": LOGIN,
    "get_course_enrollments": LOGIN,
    "get_current_user_and_nav": PUBLIC,
    "get_daywise_attendance": LOGIN,
    "get_dc_students": LOGIN,
    "get_doc": LOGIN,
    "get_feedback_forms": LOGIN,
    "get_fees_payment_transactions": ['ACA', 'DEA'],
    "get_fees_txn_image": LOGIN,
    "get_image": LOGIN,
    "get_instructor_academics": ['ACA', 'DEA', 'FAC', 'HOD'],
    "get_instructor_courses_enrol": ['ACA', 'DEA', 'FAC'],
    "get_instructor_feedback": ['ACA', 'DEA', 'FAC'],
    "get_my_photo": LOGIN,
    "get_open_events": LOGIN,
    "get_passed_courses": LOGIN,
    "get_ppr": LOGIN,
    "get_pprs_for_student": LOGIN,
    "get_running_courses": LOGIN,
    "get_settings": ['SUP'],
    "get_slotwise_courses": LOGIN,
    "get_static_data": LOGIN,
    "get_vocab": ['SUP'],
    "get_student_academics": LOGIN,
    "get_student_attendance_details": LOGIN,
    "get_student_docs": LOGIN,
    "get_student_reg_fees_data": LOGIN,
    "grade_distribution": ['ACA', 'DEA'],
    "grades_upload": ['ACA', 'DEA', 'FAC'],
    "index": PUBLIC,
    "instructor_lookup": LOGIN,
    "is_dc_chair": LOGIN,
    "kface_add": LOGIN,
    "kface_bulk_add": ['ACA'],
    "load_course_slot_timings": ['ACA', 'DEA'],
    "load_feedback_form": LOGIN,
    "login": PUBLIC,
    "logout": PUBLIC,
    "mark_attendance": ['ACA', 'FAC'],
    "notify_credit_violation": ['ACA', 'SUP'],
    "oauth_verify": PUBLIC,
    "offerings_of_course": LOGIN,
    "que_wise_facfeedbkp_score": ['ACA', 'DEA'],
    "reset_password": PUBLIC,
    "save_course_instructor_feedback": LOGIN,
    "save_course_slot_timings": ['ACA', 'DEA'],
    "save_feedback_form": ['ACA', 'DEA'],
    "save_progress_report": LOGIN,
    "save_registration_fees_txn_info": LOGIN,
    "save_setting": ['SUP'],
    "save_vocab": ['SUP'],
    "student_enrolments_for_fb": LOGIN,
    "student_lookup": LOGIN,
    "upload_student_doc": LOGIN,
    "user_delete": ['SUP'],
    "user_find": LOGIN,
    "user_save": LOGIN,
    "user_view": LOGIN,
    "wfnote_delete": LOGIN,
    "wfnote_find": LOGIN,
    "wfnote_save": LOGIN,
}

# Routes whose body refused a role outright; that check is now the route's
# permission.
INLINE_GATES = {
    # if is_user_in_role("STU"): return error
    **{ep: _but("STU") for ep in (
        "user_find", "find_students", "upload_student_doc", "wfnote_save", "wfnote_delete",
        "download_course_enrollments", "download_course_enrolments", "download_cgpa_sgpa",
        "download_catwise_earned_credits", "credits_earned_report", "course_lect_in_session",
        "earned_credit_check", "get_dc_students", "save_progress_report")},
    # role in config "hide_course_stats_from" (["STU"])
    "fetch_stats": _but("STU"),
    # if not is_user_in_role("STU"): return error
    "save_course_instructor_feedback": ["STU"],
}

# Routes where a role got through the gate but could never get past the body:
# the attendance ones only to an instructor of the course, which the
# instructor lookup never offers students or the placement cell; the progress
# report ones only to a DC member of the student, which a student never is.
NARROWED = {
    "get_daywise_attendance": _but("STU", "PLA"),
    "get_course_attd_on_date": _but("STU", "PLA"),
    "get_ppr": _but("STU"),
    "get_pprs_for_student": _but("STU"),
    "is_dc_chair": _but("STU"),
}

NEW_ROUTES = {"get_permissions": ["SUP"], "save_role_permissions": ["SUP"],
              "close_session": ["ACA"],
              # users.edit at any scope passes the gate; the body then needs users.edit:any
              "admin_gen_prk": LOGIN,
              # no permission: the body requires a logged-in user
              "change_password": PUBLIC}

EXPECTED = {**ROLE_CHECKS, **INLINE_GATES, **NARROWED, **NEW_ROUTES}

# The scopes each role gets, from the checks inside the routes they replaced.
SCOPES = {
    # user_view/get_image: if STU and not own: error
    "users.view": {"own": ["STU"], "any": _but("STU")},
    # user_save: is_admin = is_user_in_role(["ACA", "SUP"]); others only themselves
    "users.edit": {"own": _but("ACA", "SUP"), "any": ["ACA", "SUP"]},
    # __is_doc_access_allowed: ACA/DEA or own
    "student_docs.access": {"own": _but("ACA", "DEA"), "any": ["ACA", "DEA"]},
    # fees: if STU and not own: error
    "fees.view": {"own": ["STU"], "any": _but("STU")},
    "fees.submit": {"own": ["STU"], "any": _but("STU")},
    # delete fees: not ACA/DEA/SUP and not own: error
    "fees.delete": {"own": _but("ACA", "DEA", "SUP"), "any": ["ACA", "DEA", "SUP"]},
    # get_instructor_academics: FAC only own
    "instructors.view": {"own": ["FAC"], "any": ["ACA", "DEA", "HOD"]},
    # course_save: author, or HOD/ACA/DEA/RES; RES only PG courses
    "courses.edit": {"own": ["FAC"], "pg": ["RES"], "any": ["ACA", "DEA", "HOD"]},
    # get_running_courses: not ACA/DEA/SUP: own only
    "offerings.view_running": {"own": _but("ACA", "DEA", "SUP"), "any": ["ACA", "DEA", "SUP"]},
    # co_save: HOD of the dept; coordinator unless ACA/DEA/HOD
    "offerings.edit": {"own": ["FAC"], "dept": ["HOD"], "any": ["ACA", "DEA"]},
    # get_student_academics etc.: STU only own
    "students.academics": {"own": ["STU"], "any": _but("STU")},
    # enroll_in_courses: STU only own
    "enrolments.enrol": {"own": ["STU"], "any": ["ACA"]},
    # validate_enrolment_change: STU only own
    "enrolments.change": {"own": ["STU"], "any": _but("STU")},
    # is_enrollment_owner_valid: FAC instructor, HOD of dept, ACA/DEA any
    "enrolments.edit": {"own": ["FAC"], "dept": ["HOD"], "any": ["ACA", "DEA"]},
    # change_enroll_status: FAC/HOD/ADV by ownership; HOD any APEN
    "enrolments.approve": {"own": ["ADV", "FAC", "HOD"], "any": ["ACA", "DEA", "HOD"]},
    # get_advisor_courses_enrol: HOD query by department
    "enrolments.pending_advisor": {"own": ["ACA", "ADV", "DEA"], "dept": ["HOD"]},
    # grades_upload: coordinator unless ACA/DEA
    "grades.upload": {"own": ["FAC"], "any": ["ACA", "DEA"]},
    # mark_attendance: coordinator unless ACA/DEA
    "attendance.mark": {"own": ["FAC"], "any": ["ACA"]},
    # daywise attendance: instructor unless SUP/ACA/DEA/HOD
    "attendance.view": {"own": ["ADV", "FAC", "GUE", "RES"], "any": ["ACA", "DEA", "HOD", "SUP"]},
    # get_instructor_feedback: FAC only own
    "feedback.view_instructor": {"own": ["FAC"], "any": ["ACA", "DEA"]},
    # dc_details/dc_search: STU only own
    "dc.view": {"own": ["STU"], "any": _but("STU")},
    # _raise_on_invalid_dc_change: FAC supervisor, HOD of dept, ACA/DEA any
    "dc.edit": {"own": ["FAC"], "dept": ["HOD"], "any": ["ACA", "DEA"]},
    # __is_dc_member_or_admin: ACA/DEA/SUP or DC member
    "ppr.view": {"own": _but("STU", "ACA", "DEA", "SUP"), "any": ["ACA", "DEA", "SUP"]},
    "ppr.edit": {"own": _but("STU", "ACA", "DEA", "SUP"), "any": ["ACA", "DEA", "SUP"]},
}

# Permissions checked only inside route bodies, from the role lists there.
INNER = {
    "courses.edit_approved": ["ACA", "DEA", "RES"],  # is_course_status_valid_for_current_user
    "offerings.edit_closed": ["ACA", "DEA"],          # validate_coff_status
    "faces.replace": _but("STU"),                     # kface_add: STU may not replace
    # role == "STU"/"FAC"/"ACA" where the code selects a kind of person
    "roster.student": ["STU"],
    "roster.instructor": ["FAC"],
    "roster.acad_section": ["ACA"],
}


def _holders(code):
    return sorted(r for r in ROLES if code in P.perms_of(r))


def _can(role, perm):
    return P.Actor(0, "", role, "", P.perms_of(role)).can(perm)


def test_every_route_keeps_its_access(app, db):
    routes = {ep.split(".", 1)[1]: fn for ep, fn in app.view_functions.items()
              if not ep.endswith("static")}
    assert set(routes) == set(EXPECTED)
    actual = {}
    for ep, fn in routes.items():
        perm = getattr(fn, "permission", None)
        actual[ep] = PUBLIC if perm is None else [r for r in ROLES if _can(r, perm)]
    expected = {ep: v if v == PUBLIC else sorted(v) for ep, v in EXPECTED.items()}
    assert {ep: v if v == PUBLIC else sorted(v) for ep, v in actual.items()} == expected


@pytest.mark.parametrize("perm", sorted(SCOPES))
def test_scopes_match_the_checks_they_replace(db, perm):
    assert {s: _holders(f"{perm}:{s}") for s in SCOPES[perm]} == \
        {s: sorted(r) for s, r in SCOPES[perm].items()}
    assert M.Permission.select().where(M.Permission.code.startswith(perm + ":")).count() \
        == len(SCOPES[perm])


@pytest.mark.parametrize("perm", sorted(INNER))
def test_inner_permissions_match_the_checks_they_replace(db, perm):
    assert _holders(perm) == sorted(INNER[perm])


SRC = Path(__file__).resolve().parent.parent
_PERM_ARG = re.compile(r'(?:require|has|can|allowed|check_own_or_any|roles_with)\(\s*"([a-z_.]+(?::[a-z]+)?)"')


def test_every_stored_permission_is_used_and_every_used_one_is_stored(db):
    used = set()
    for f in SRC.glob("*.py"):
        if f.name != "policy.py":  # defines the checks; its docstring shows examples
            used |= set(_PERM_ARG.findall(f.read_text()))
    used |= {n["perm"] for n in json.loads((SRC / "nav.json").read_text())}
    used.add(P.ADMIN_PERM)
    stored = {p.code for p in M.Permission.select()}
    base = {c.split(":")[0] for c in stored}
    assert {u for u in used if u not in stored and u not in base} == set()
    assert base - {u.split(":")[0] for u in used} == set()


@pytest.fixture
def restore_grants(db):
    roles = [(r.code, r.label) for r in M.Role.select()]
    grants = [(g.role, g.permission) for g in M.RolePermission.select()]
    yield
    M.RolePermission.delete().execute()
    M.BatchAdvisors.delete().execute()
    M.User.delete().execute()
    M.Role.delete().where(M.Role.code.not_in([c for c, _ in roles])).execute()
    M.RolePermission.insert_many([{"role": r, "permission": p} for r, p in grants]).execute()
    P.clear_cache()


async def _post(client, url, payload):
    return await (await client.post(f"/acadstack/{url}", json=payload)).get_json()


async def _nav_labels(client):
    body = await (await client.get("/acadstack/current_user")).get_json()
    nav = body["body"]["nav"]
    return {i["label"] for items in nav["menus"].values() for i in items} | \
        {i["label"] for i in nav["links"]}


@pytest.mark.parametrize("role, sees", [
    ("FAC", True), ("HOD", True), ("GUE", True), ("SUP", True), ("STU", False), ("PLA", False)])
async def test_view_attendance_menu_follows_attendance_view(client, auth, role, sees):
    make_user("u", role=role)
    await auth.login("u")
    assert ("View Attendance" in await _nav_labels(client)) == sees


@pytest.mark.parametrize("role", ["STU", "ACA", "FAC"])
async def test_student_record_menu_needs_the_own_scope(client, auth, role):
    make_user("u", role=role)
    await auth.login("u")
    assert ("Student Record" in await _nav_labels(client)) == (role == "STU")


async def test_route_denied_after_permission_is_removed(client, auth, restore_grants):
    make_user("aca", role="ACA")
    await auth.login("aca")
    assert (await _post(client, "user_find", {}))["status"] == "OK"
    actor = P.Actor(0, "", "SUP", "", P.perms_of("SUP"))
    P.save("ACA", "", P.perms_of("ACA") - {"users.find"}, actor)
    assert (await _post(client, "user_find", {}))["status"] == "ERROR"


async def test_admin_cannot_remove_own_admin_permission(client, auth, restore_grants):
    make_user("sup", role="SUP")
    await auth.login("sup")
    kept = sorted(P.perms_of("SUP") - {P.ADMIN_PERM})
    body = await _post(client, "perms_save", {"role": "SUP", "permissions": kept})
    assert body["status"] == "ERROR"
    assert P.ADMIN_PERM in P.perms_of("SUP")


async def test_admin_cannot_change_own_role_to_one_without_admin_permission(
        client, auth, restore_grants):
    sup = make_user("sup", role="SUP")
    await auth.login("sup")
    body = await _post(client, "user_save", {"id": sup.id, "role": "ACA", "txn_no": 1})
    assert body["status"] == "ERROR"
    assert M.User.get_by_id(sup.id).role == "SUP"


async def test_only_permission_admins_manage_permissions(client, auth, restore_grants):
    make_user("aca", role="ACA")
    await auth.login("aca")
    assert (await (await client.get("/acadstack/perms")).get_json())["status"] == "ERROR"
    body = await _post(client, "perms_save", {"role": "ACA", "permissions": [P.ADMIN_PERM]})
    assert body["status"] == "ERROR"
    assert P.ADMIN_PERM not in P.perms_of("ACA")


async def test_admin_adds_a_role_that_gets_exactly_its_permissions(client, auth, restore_grants):
    make_user("sup", role="SUP")
    await auth.login("sup")
    body = await _post(client, "perms_save", {"role": "AUD", "label": "Auditor",
                                              "permissions": ["app.access", "users.find"]})
    assert body["status"] == "OK"
    assert body["body"]["grants"]["AUD"] == ["app.access", "users.find"]
    sd = await (await client.get("/acadstack/get_static_data")).get_json()
    assert {"id": "AUD", "value": "Auditor", "roster": []} in sd["body"]["UserRoles"]

    await auth.logout()
    make_user("aud", role="AUD")
    await auth.login("aud")
    assert (await _post(client, "user_find", {}))["status"] == "OK"
    assert (await _post(client, "students_find", {}))["status"] == "ERROR"
    assert await _nav_labels(client) == {"Find User"}


@pytest.mark.parametrize("payload, error", [
    ({"role": "ACA", "permissions": ["no.such"]}, "Unknown permissions"),
    ({"role": "NEW", "permissions": []}, "needs a label"),
    ({"role": "TOOLONG", "label": "x", "permissions": []}, "1 to 4 characters"),
])
async def test_invalid_grants_are_rejected(client, auth, restore_grants, payload, error):
    make_user("sup", role="SUP")
    await auth.login("sup")
    body = await _post(client, "perms_save", payload)
    assert body["status"] == "ERROR" and error in body["body"]


# ---- scoped checks not covered by the flow tests ----

def _course(code, author, level="UG"):
    return M.Course.create(code=code, title="Old", ltp="3-0-0-6-3", status="DRA", author=author,
                           level=level)


@pytest.mark.parametrize("level, ok", [("PG", True), ("ALL", True), ("UG", False)])
async def test_research_section_edits_only_pg_courses(client, auth, level, ok):
    crs = _course("CS100", make_user("fac", role="FAC"), level)
    make_user("res", role="RES")
    await auth.login("res")
    body = await _post(client, "cour_save", {"id": crs.id, "title": "New", "txn_no": 1})
    assert (body["status"] == "OK") == ok
    if not ok:
        assert body["body"] == "You can edit only PG or all-level courses!"


async def test_hod_edits_any_course(client, auth):
    crs = _course("CS300", make_user("fac", role="FAC"))
    make_user("hod", role="HOD")
    await auth.login("hod")
    body = await _post(client, "cour_save", {"id": crs.id, "title": "New", "txn_no": 1})
    assert body["status"] == "OK"


@pytest.mark.parametrize("hod_dept, ok", [("CSE", True), ("EE", False)])
async def test_hod_edits_offerings_of_own_department(client, auth, hod_dept, ok):
    from conftest import make_offering
    co = make_offering(dept_name="CSE")
    make_user("hod", role="HOD", dept_name=hod_dept)
    await auth.login("hod")
    body = await _post(client, "co_save", {
        "id": co.id, "acad_session": co.acad_session, "course": {"id": co.course.id},
        "txn_no": 1, "instructors": [], "course_categories": [
            {"degree": "BTE", "dept": "CSE", "category": "PC", "for_entry_years": "2024"}]})
    if ok:
        assert body["status"] == "OK", body
    else:
        assert body == {"status": "ERROR", "body": "Only the HoD of the offering "
                        "department can make changes to the course offering."}


# ---- roster permissions: which roles count as a kind of person ----

def _add_role(code, *perms):
    actor = P.Actor(0, "", "SUP", "", P.perms_of("SUP"))
    P.save(code, code.title(), {"app.access", *perms}, actor)


async def test_role_granted_roster_instructor_appears_in_instructor_lookup(
        client, auth, restore_grants):
    _add_role("VF", "roster.instructor")
    make_user("visitor", role="VF")
    make_user("vifac", role="FAC")
    make_user("aca", role="ACA")
    await auth.login("aca")
    body = await (await client.get("/acadstack/instructor_lookup/Vi")).get_json()
    assert sorted(r["first_name"] for r in body["body"]) == ["Vifac", "Visitor"]

    _add_role("FAC")  # FAC no longer counts as instructor
    body = await (await client.get("/acadstack/instructor_lookup/Vi")).get_json()
    assert [r["first_name"] for r in body["body"]] == ["Visitor"]


async def test_role_granted_roster_student_is_looked_up_and_bulk_enrolled(
        client, auth, restore_grants):
    _add_role("EXS", "roster.student")
    s1 = make_user("s1", role="EXS", org_id="X-1", current_status="REG")
    make_user("g1", role="GUE", org_id="X-2", current_status="REG")
    make_user("aca", role="ACA")
    co = make_offering()
    await auth.login("aca")
    body = await (await client.get("/acadstack/student_lookup/X-")).get_json()
    assert [r["org_id"] for r in body["body"]] == ["X-1"]
    body = await (await client.get(f"/acadstack/co_bulkenrol/X-/{co.id}")).get_json()
    assert body["status"] == "OK", body
    assert [e.student_id for e in M.CourseEnrollment.select()] == [s1.id]


def test_offering_info_names_the_head_of_a_role_granted_offerings_edit_dept(restore_grants):
    _add_role("CHR", "offerings.edit:dept")
    make_user("chair", role="CHR", dept_name="CSE")
    make_user("other", role="CHR", dept_name="EE")
    co = make_offering(dept_name="CSE", instructor=make_user("fac", role="FAC"))
    row = M.db.execute_sql(C.sql_by_id("course_offering_info"),
                           [P.roles_with("offerings.edit:dept"), co.id]).fetchone()
    assert row[4] == "chair@example.com"


def test_offering_info_names_one_live_head_when_a_dept_has_several(restore_grants):
    _add_role("CHR", "offerings.edit:dept")
    gone = make_user("gone", role="CHR", dept_name="CSE")
    gone.is_deleted = True
    gone.save()
    make_user("chair", role="CHR", dept_name="CSE")
    make_user("cochair", role="CHR", dept_name="CSE")
    co = make_offering(dept_name="CSE", instructor=make_user("fac", role="FAC"))
    rows = M.db.execute_sql(C.sql_by_id("course_offering_info"),
                            [P.roles_with("offerings.edit:dept"), co.id]).fetchall()
    assert [r[4] for r in rows] == ["chair@example.com"]


async def test_batch_advisor_of_a_role_without_roster_instructor_can_approve(
        client, auth, restore_grants):
    _add_role("BA", "enrolments.approve:own", "enrolments.change:any")
    make_user("adv", role="BA")
    stu = make_user("stu", role="STU", degree="BTE", year_of_entry="2024")
    M.BatchAdvisors.create(user=M.User.get(M.User.login_id == "adv"),
                           year_of_entry="2024", for_degree="BTE")
    co = make_offering(acad_session="2026-I", instructor=make_user("fac", role="FAC"))
    ce = enrol(stu, co, enrol_status="APEN")
    set_event_window("2026-I", "COURSE_REG")
    await auth.login("adv")
    body = await _post(client, "change_enroll_status", {"ids": [ce.id], "status": "approve"})
    assert body["status"] == "OK", body
    assert M.CourseEnrollment.get_by_id(ce.id).enrol_status == "ENRO"


def test_grade_submission_email_goes_to_roles_granted_roster_acad_section(
        restore_grants, alerts):
    import create_email
    _add_role("REG", "roster.acad_section")
    make_user("registrar", role="REG")
    co = make_offering(instructor=make_user("fac", role="FAC"))
    create_email.send_grades_submission_email(co.id, 3)
    assert alerts[0][0] == "fac@example.com, registrar@example.com"


async def test_static_data_roles_carry_their_roster_flags(client, auth):
    make_user("aca", role="ACA")
    await auth.login("aca")
    sd = await (await client.get("/acadstack/get_static_data")).get_json()
    roster = {r["id"]: r["roster"] for r in sd["body"]["UserRoles"]}
    assert roster["STU"] == ["student"] and roster["FAC"] == ["instructor"]
    assert roster["HOD"] == [] and roster["ACA"] == ["acad_section"]
    assert roster["GUE"] == []


# ---- refusals reported as access violations ----

@pytest.fixture
def alerts(client, monkeypatch):
    import create_email
    settings.save("help_email", "help@example.org")
    sent = []
    monkeypatch.setattr(create_email.emailer, "send_mail",
                        lambda to, subject, body: sent.append((to, subject)))
    return sent


async def test_student_submitting_progress_report_is_reported_and_locked(client, auth, alerts):
    stu = make_user("stu", role="STU")
    await auth.login("stu")
    body = await _post(client, "ppr_save", {"student": stu.id})
    assert body["status"] == "ERROR" and "reported" in body["body"]
    assert [s for _, s in alerts] == ["AcadStack access violation alert"]
    assert M.User.get_by_id(stu.id).is_locked


async def test_staff_submitting_feedback_is_reported_but_not_locked(client, auth, alerts):
    aca = make_user("aca", role="ACA")
    await auth.login("aca")
    body = await _post(client, "save_course_instructor_feedback", {})
    assert body["status"] == "ERROR"
    assert [s for _, s in alerts] == ["AcadStack access violation alert"]
    assert not M.User.get_by_id(aca.id).is_locked


async def test_other_refusals_are_not_reported(client, auth, alerts):
    stu = make_user("stu", role="STU")
    await auth.login("stu")
    assert (await _post(client, "user_find", {}))["status"] == "ERROR"
    assert alerts == []
    assert not M.User.get_by_id(stu.id).is_locked
