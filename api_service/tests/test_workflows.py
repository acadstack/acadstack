"""Tests for the declarative approval workflows (domain/workflow.py).

Three things are pinned here:

1. **The enrolment table is the old if/elif chain.** An exhaustive
   comparison against a verbatim copy of the chain it replaced, for
   every role x ownership x status x action -- once against the baseline
   in code and once against the table as stored and reloaded from the
   database. (test_enrolment_state_machine.py, untouched, pins the same
   behaviour end to end over HTTP.)
2. **The DC and course tables enforce their approval graphs**, with the
   milestone and email effects on the right rows.
3. **Steps are data.** An institution can remove or add a step through
   save_workflow without code changes; edits that name unknown things,
   or would strand records in a status they can no longer leave, are
   refused.
"""
import itertools
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import models as DB  # noqa: E402
import settings_store as ST  # noqa: E402
from conftest import create_user, login_as  # noqa: E402
from domain import course as CRS  # noqa: E402
from domain import dc as DCD  # noqa: E402
from domain import enrolment as ENR  # noqa: E402
from domain import milestones as MS  # noqa: E402
from domain import workflow as WF  # noqa: E402
from domain.context import Actor  # noqa: E402
from domain.errors import PermissionDenied, PolicyViolation  # noqa: E402

WORKFLOW_TABLES = [DB.WorkflowTransition, DB.WorkflowDefinition,
                   DB.MilestoneDefinition]


@pytest.fixture
def wfdb(db):
    """``db``, plus clearing the workflow tables afterwards too: domain
    tests that run without the ``db`` fixture load workflows from
    whatever is stored, so an edited table must not outlive its test."""
    yield db
    for model in WORKFLOW_TABLES:
        model.delete().execute()


def actor(role, user_id=1, dept_name=None):
    return Actor(login_id=f"{role.lower()}{user_id}", role=role,
                 user_id=user_id, dept_name=dept_name)


# ===================== 1. enrolment == the old chain =====================

def legacy_next_enrol_status(actor, ownership, current_status, action):
    """The approval chain as it stood before the transition table,
    verbatim apart from the exception type. The oracle for the table."""
    approving = action == "approve"
    is_instructor, is_advisor = ownership[0], ownership[1]

    if actor.can("enrolment.override"):
        return "ENRO" if approving else "ASREJ"

    if actor.has_role(["FAC", "HOD"]):
        if is_instructor and not is_advisor:
            return "APEN" if approving else "IREJ"
        elif is_advisor and not is_instructor:
            return "ENRO" if approving else "AREJ"
        elif is_instructor and is_advisor and current_status == "IPEN":
            return "APEN" if approving else "AREJ"
        elif is_instructor and is_advisor and current_status == "APEN":
            return "ENRO" if approving else "AREJ"
        elif actor.has_role("HOD") and current_status == "APEN":
            return "ENRO" if approving else "AREJ"
        else:
            raise PermissionDenied(
                "You do not have privileges to change one or more enrollments!")

    raise PermissionDenied("Unexpected user role: " + str(actor.role))


def _outcome(fn, *args):
    try:
        return ("ok", fn(*args))
    except PermissionDenied as e:
        return ("denied", str(e))


MATRIX = list(itertools.product(
    ["ACA", "DEA", "FAC", "HOD", "RES", "STU", "SUP", "GUE"],
    [[False, False], [True, False], [False, True], [True, True]],
    ["IPEN", "IREJ", "APEN", "AREJ", "ENRO", "DROP", "ASREJ", "WDRAW"],
    ["approve", "reject", "something-else"],
))


def _assert_matches_legacy(workflow):
    for role, ownership, status, action in MATRIX:
        a = actor(role)
        expected = _outcome(legacy_next_enrol_status, a, ownership, status,
                            action)
        got = _outcome(ENR.default_next_enrol_status, a, ownership, status,
                       action, workflow)
        assert got == expected, (role, ownership, status, action)


def test_enrolment_baseline_table_is_the_old_chain():
    _assert_matches_legacy(ENR.BASELINE)


def test_enrolment_table_is_the_old_chain_after_a_database_round_trip(wfdb):
    WF.store(ENR.BASELINE)
    stored = WF.load("enrolment")
    assert stored == ENR.BASELINE
    _assert_matches_legacy(stored)


@pytest.mark.parametrize("name", ["enrolment", "dc", "course"])
def test_every_baseline_is_valid_and_round_trips(wfdb, name):
    base = WF.baseline(name)
    assert WF.validate(base) == []
    WF.store(base)
    assert WF.load(name) == base
    assert WF.Workflow.from_json(base.to_json()) == base


def test_seeding_stores_every_baseline(wfdb):
    from default_seed_data import seed_workflows
    assert seed_workflows() == 3
    assert seed_workflows() == 0
    for name in WF.names():
        assert WF.load(name) == WF.baseline(name)


# ===================== 2a. DC =====================

def _dc_people(dept="CSE"):
    stu = create_user("STU", "dc_stu", dept_name=dept, degree="PHD")
    sup = create_user("FAC", "dc_sup", dept_name=dept)
    cp = create_user("FAC", "dc_cp", dept_name=dept)
    me = create_user("FAC", "dc_me", dept_name=dept)
    hod = create_user("HOD", "dc_hod", dept_name=dept)
    dea = create_user("DEA", "dc_dea", dept_name="ACA")
    return dict(stu=stu, sup=sup, cp=cp, me=me, hod=hod, dea=dea)


def _dc_form(p, status, dc=None):
    form = {"student": {"user_id": p["stu"].id}, "status": status,
            "effective_from": str(date.today()),
            "members": [{"role": "SU", "user_id": p["sup"].id},
                        {"role": "CP", "user_id": p["cp"].id},
                        {"role": "ME", "user_id": p["me"].id}]}
    if dc:
        form["id"] = dc["id"]
        form["txn_no"] = dc["txn_no"]
        form["members"] = [
            {k: m.get(k) for k in ("id", "txn_no", "role", "user_id")}
            for m in dc["members"]]
    return form


def _dc_save(client, who, form):
    login_as(client, who.login_id)
    res = client.post("/acadstack/dc_save", json=form)
    client.get("/acadstack/logout")
    return res.json


def _milestones(stu):
    return sorted(m.milestone for m in DB.AcademicMilestone.select().where(
        DB.AcademicMilestone.student == stu.id))


def test_dc_happy_path_records_milestones_as_effects(client):
    p = _dc_people()

    res = _dc_save(client, p["sup"], _dc_form(p, "DRA"))
    assert res["status"] == "OK", res
    assert _milestones(p["stu"]) == [MS.DC_PROPOSED]

    for who, status in [(p["sup"], "SUB"), (p["hod"], "FTD"),
                        (p["dea"], "APP")]:
        res = _dc_save(client, who, _dc_form(p, status, res["body"]))
        assert res["status"] == "OK", (who.role, status, res)
        assert res["body"]["status"] == status

    assert _milestones(p["stu"]) == [MS.DC_APPROVED, MS.DC_PROPOSED]


def test_dc_supervisor_cannot_skip_to_approved(client):
    # The server used to accept any status from anyone who could edit
    # the DC in its current state. The table now enforces the graph.
    p = _dc_people()
    res = _dc_save(client, p["sup"], _dc_form(p, "DRA"))
    res = _dc_save(client, p["sup"], _dc_form(p, "APP", res["body"]))
    assert res["status"] == "ERROR"
    assert res["body"] == "A DC in Draft cannot be moved to Approved."


def test_dc_hod_cannot_touch_a_draft(client):
    p = _dc_people()
    res = _dc_save(client, p["sup"], _dc_form(p, "DRA"))
    res = _dc_save(client, p["hod"], _dc_form(p, "FTD", res["body"]))
    assert res["status"] == "ERROR"
    assert res["body"].startswith("Insufficient privileges")


def test_dc_hod_of_another_department_is_refused(client):
    p = _dc_people()
    other_hod = create_user("HOD", "dc_hod_ee", dept_name="EE")
    res = _dc_save(client, p["sup"], _dc_form(p, "SUB"))
    res = _dc_save(client, other_hod, _dc_form(p, "FTD", res["body"]))
    assert res == {"status": "ERROR",
                   "body": "Only HOD of student's own dept. can make changes!"}


def test_dc_composition_is_checked_first(client):
    p = _dc_people()
    form = _dc_form(p, "DRA")
    form["members"] = form["members"][:2]  # no ordinary member
    res = _dc_save(client, p["hod"], form)  # and HOD may not create
    assert res["body"] == ("At least one DC member, supervisor and the DC "
                           "chairperson is required!")


def test_dc_supervisor_must_be_faculty_in_the_students_department(client):
    p = _dc_people()
    p["sup"] = create_user("FAC", "dc_sup_ee", dept_name="EE")
    res = _dc_save(client, p["sup"], _dc_form(p, "DRA"))
    assert res["body"] == "Supervisor and student must be from same department!"


# ===================== 2b. course =====================

def _course_save(client, who, **fields):
    login_as(client, who.login_id)
    res = client.post("/acadstack/cour_save", json=fields)
    client.get("/acadstack/logout")
    return res.json


def _course_step(client, who, course, status):
    return _course_save(client, who, id=course["id"], code=course["code"],
                        title=course["title"], ltp="3-0-0", status=status)


def test_course_approval_path(client):
    fac = create_user("FAC", "crs_fac")
    hod = create_user("HOD", "crs_hod")
    dea = create_user("DEA", "crs_dea")

    res = _course_save(client, fac, code="CS701", title="T", ltp="3-0-0")
    assert res["status"] == "OK", res
    course = res["body"]
    assert course["status"] == "DRA"

    for who, status in [(fac, "HAP"), (hod, "CAP"), (dea, "APP")]:
        res = _course_step(client, who, course, status)
        assert res["status"] == "OK", (who.role, status, res)
        assert res["body"]["status"] == status

    # Approved: the author can no longer edit it.
    res = _course_step(client, fac, course, "APP")
    assert res["body"] == ("This course is already in Approved state. "
                           "Please contact the academic section to edit it.")


def _hap_course_and_other_hod(client, status, suffix):
    fac = create_user("FAC", f"crs_fac_{suffix}{status}", dept_name="CSE")
    other_hod = create_user("HOD", f"crs_hod_{suffix}{status}", dept_name="EE")
    course = _course_save(client, fac, code=f"CS7{suffix}{status}",
                          title="T", ltp="3-0-0")["body"]
    _course_step(client, fac, course, "HAP")
    return course, other_hod


@pytest.mark.parametrize("status", ["CAP", "HAR"])
def test_course_hod_of_another_department_cannot_review(client, status):
    course, other_hod = _hap_course_and_other_hod(client, status, "R")
    res = _course_step(client, other_hod, course, status)
    assert res == {"status": "ERROR",
                   "body": "You can edit only your own department's courses!"}
    assert DB.Course.get_by_id(course["id"]).status == "HAP"


@pytest.mark.parametrize("status", ["CAP", "HAR"])
def test_course_review_stays_departmental_even_with_edit_any(client, status):
    # An institution may let HODs edit any course; reviewing one is still
    # for the HoD of the course's own department.
    import permissions as PERM
    PERM.save_permission_mapping(
        {"course.edit_any": ["HOD", "ACA", "DEA", "RES"]}, actor("SUP"))
    course, other_hod = _hap_course_and_other_hod(client, status, "X")
    res = _course_step(client, other_hod, course, status)
    assert res == {"status": "ERROR", "body":
                   "Only the HoD of the course's department can review it!"}
    assert DB.Course.get_by_id(course["id"]).status == "HAP"


def test_course_hod_edits_only_their_own_departments_courses(client):
    fac = create_user("FAC", "crs_fac_e", dept_name="CSE")
    own_hod = create_user("HOD", "crs_hod_cse", dept_name="CSE")
    other_hod = create_user("HOD", "crs_hod_me", dept_name="ME")
    course = _course_save(client, fac, code="CS720", title="T",
                          ltp="3-0-0")["body"]

    res = _course_step(client, other_hod, course, "DRA")
    assert res == {"status": "ERROR",
                   "body": "You can edit only your own department's courses!"}
    res = _course_step(client, own_hod, course, "DRA")
    assert res["status"] == "OK", res


def test_course_author_cannot_approve_their_own_course(client):
    fac = create_user("FAC", "crs_fac2")
    course = _course_save(client, fac, code="CS702", title="T",
                          ltp="3-0-0")["body"]
    res = _course_step(client, fac, course, "APP")
    assert res["body"] == "A course in Draft cannot be moved to Approved."


def test_course_other_faculty_cannot_edit(client):
    fac = create_user("FAC", "crs_fac3")
    other = create_user("FAC", "crs_fac4")
    course = _course_save(client, fac, code="CS703", title="T",
                          ltp="3-0-0")["body"]
    res = _course_step(client, other, course, "DRA")
    assert res["body"] == "Cannot save course authored by another faculty!"


def test_course_actions_listed_for_the_ui(client):
    fac = create_user("FAC", "crs_fac5")
    course = _course_save(client, fac, code="CS704", title="T",
                          ltp="3-0-0")["body"]
    login_as(client, fac.login_id)
    res = client.get(f"/acadstack/workflow_actions/course/{course['id']}")
    assert res.json["status"] == "OK"
    assert [(a["label"], a["to_status"]) for a in res.json["body"]] == \
        [("Save", "DRA"), ("Submit", "HAP")]


# ===================== 3. steps are data =====================

def _without_hod_review(wf):
    """The course workflow with the HoD step removed: the author submits
    straight to the council."""
    d = wf.to_json()
    d["transitions"] = [t for t in d["transitions"]
                        if t["permission"] != "course.hod_review"
                        and t["to_status"] != "HAP"]
    d["transitions"] += [
        dict(priority=200 + i, from_status=s, to_status="CAP",
             permission="course.submit", label="Submit",
             effects=[{"name": "notify.course_updated"}])
        for i, s in enumerate(["DRA", "CAR"])]
    return d


def test_an_institution_can_remove_the_hod_step_without_code(client, wfdb):
    sup = actor("SUP")
    WF.save_workflow(sup, _without_hod_review(CRS.BASELINE))

    fac = create_user("FAC", "crs_fac6")
    course = _course_save(client, fac, code="CS705", title="T",
                          ltp="3-0-0")["body"]
    assert _course_step(client, fac, course, "HAP")["status"] == "ERROR"
    res = _course_step(client, fac, course, "CAP")
    assert res["status"] == "OK", res
    assert res["body"]["status"] == "CAP"


def test_removing_a_step_that_records_sit_in_is_refused(client, wfdb):
    fac = create_user("FAC", "crs_fac7")
    course = _course_save(client, fac, code="CS706", title="T",
                          ltp="3-0-0")["body"]
    _course_step(client, fac, course, "HAP")

    with pytest.raises(WF.InvalidWorkflow, match=r"HAP \(1\)"):
        WF.save_workflow(actor("SUP"), _without_hod_review(CRS.BASELINE))


def test_only_workflow_managers_may_edit(wfdb):
    with pytest.raises(PermissionDenied):
        WF.save_workflow(actor("ACA"), CRS.BASELINE.to_json())


@pytest.mark.parametrize("change,message", [
    ({"permission": "course.no_such"}, "unknown permission"),
    ({"to_status": "ZZZ"}, "unknown to_status"),
    ({"from_status": "ZZZ"}, "unknown from_status"),
    ({"guards": ["no.such.guard"]}, "unknown guard"),
    ({"checks": [{"name": "no.such.check"}]}, "unknown check"),
    ({"effects": [{"name": "no.such.effect"}]}, "unknown effect"),
    ({"effects": [{"name": "milestone.record",
                   "params": {"code": "NOPE"}}]}, "unknown milestone"),
    ({"priority": 110}, "duplicate priority"),
])
def test_invalid_rows_are_refused(wfdb, change, message):
    d = CRS.BASELINE.to_json()
    d["transitions"][0].update(change)
    with pytest.raises(WF.InvalidWorkflow, match=message):
        WF.save_workflow(actor("SUP"), d)


def test_workflow_admin_endpoints(client, wfdb):
    sup = create_user("SUP", "wf_admin")
    login_as(client, sup.login_id)
    res = client.get("/acadstack/workflow/dc")
    assert res.json["status"] == "OK"
    body = res.json["body"]
    assert "dc.actor_is_supervisor" in body["registered"]["checks"]
    assert body["workflow"] == DCD.BASELINE.to_json()

    res = client.post("/acadstack/workflow_save", json=body["workflow"])
    assert res.json["status"] == "OK", res.json
    assert WF.load("dc") == DCD.BASELINE



def _login_workflow_admin(client, login_id):
    sup = create_user("SUP", login_id)
    login_as(client, sup.login_id)


def test_workflow_list_and_view_endpoints(client, wfdb):
    _login_workflow_admin(client, "wf_admin2")
    res = client.get("/acadstack/workflows")
    assert res.json == {"status": "OK", "body": WF.names()}
    assert {"course", "dc", "enrolment"} <= set(res.json["body"])

    body = client.get("/acadstack/workflow/course").json["body"]
    assert [s["code"] for s in body["statuses"]] == \
        ST.vocab_codes(CRS.BASELINE.status_vocab)
    assert body["special_statuses"] == {"any": WF.ANY, "new": WF.NEW,
                                        "same": WF.SAME}
    assert "course.submit" in body["permissions"]
    assert body["registered"] == WF.registered_steps()


def test_workflow_endpoints_need_manage_workflows(client, wfdb):
    aca = create_user("ACA", "wf_aca1")
    login_as(client, aca.login_id)
    assert client.get("/acadstack/workflows").json["status"] == "ERROR"
    assert client.get("/acadstack/workflow/dc").json["status"] == "ERROR"
    res = client.post("/acadstack/workflow_save",
                      json=DCD.BASELINE.to_json())
    assert res.json["status"] == "ERROR"


def test_workflow_view_of_an_unknown_workflow(client, wfdb):
    _login_workflow_admin(client, "wf_admin3")
    res = client.get("/acadstack/workflow/nope")
    assert res.json["status"] == "ERROR"
    assert "Unknown workflow" in res.json["body"]


def test_workflow_save_reports_errors_against_their_rows(client, wfdb):
    _login_workflow_admin(client, "wf_admin4")
    d = CRS.BASELINE.to_json()
    d["transitions"][2]["permission"] = "course.no_such"
    d["transitions"][4]["guards"] = ["no.such.guard"]
    d["checks"] = [{"name": "no.such.check"}]
    res = client.post("/acadstack/workflow_save", json=d)
    assert res.json["status"] == "ERROR"
    body = res.json["body"]
    assert body["stranded"] == {}
    assert "Invalid workflow definition" in body["message"]
    by_row = {(e["row"], e["message"].split(": ", 1)[-1])
              for e in body["errors"]}
    assert by_row == {(None, "no.such.check"),
                      (2, "unknown permission 'course.no_such'."),
                      (4, "unknown guard 'no.such.guard'.")}
    assert WF.load("course") == CRS.BASELINE


@pytest.mark.parametrize("change,drop,message", [
    ({"priority": "abc"}, None, "Row 2: priority must be a whole number."),
    ({"priority": ""}, None, "Row 2: priority must be a whole number."),
    ({}, "permission", "Row 2: 'permission' is required."),
])
def test_workflow_save_reports_malformed_rows(client, wfdb, change, drop,
                                              message):
    # What a half-filled editor row sends: rejected against that row, not
    # as an unexpected server error.
    _login_workflow_admin(client, "wf_admin5")
    d = CRS.BASELINE.to_json()
    d["transitions"][1].update(change)
    if drop:
        del d["transitions"][1][drop]
    res = client.post("/acadstack/workflow_save", json=d)
    assert res.json["status"] == "ERROR", res.json
    errors = res.json["body"]["errors"]
    assert [e["row"] for e in errors] == [1]
    assert errors[0]["message"].startswith("Row 2: ")
    assert message in errors[0]["message"]


def test_workflow_save_reports_stranded_statuses(client, wfdb):
    fac = create_user("FAC", "crs_fac8")
    course = _course_save(client, fac, code="CS707", title="T",
                          ltp="3-0-0")["body"]
    _course_step(client, fac, course, "HAP")

    _login_workflow_admin(client, "wf_admin6")
    res = client.post("/acadstack/workflow_save",
                      json=_without_hod_review(CRS.BASELINE))
    assert res.json["status"] == "ERROR"
    body = res.json["body"]
    assert body["stranded"] == {"HAP": 1}
    assert [e["row"] for e in body["errors"]] == [None]
    assert "HAP (1)" in body["errors"][0]["message"]

# ===================== milestones =====================

def test_milestone_sequence_is_data(wfdb):
    assert MS.codes()[:3] == ["JOINING", MS.DC_PROPOSED, MS.DC_APPROVED]
    items = MS.definitions() + [dict(code="PUBLICATION", label="Publication",
                                     sequence=85, applies_to="PHD")]
    MS.save_definitions(actor("SUP"), items)
    assert "PUBLICATION" in MS.codes()
    assert MS.codes().index("PUBLICATION") == MS.codes().index("SYNOPSIS") + 1


def test_a_milestone_a_workflow_records_cannot_be_removed(wfdb):
    items = [d for d in MS.definitions() if d["code"] != MS.DC_APPROVED]
    with pytest.raises(PolicyViolation, match="recorded by the 'dc' workflow"):
        MS.save_definitions(actor("SUP"), items)


def test_unknown_milestones_are_refused(db):
    stu = create_user("STU", "ms_stu")
    dc = DB.DcForStudent.create(student=stu, status="DRA")
    with pytest.raises(PolicyViolation, match="Unknown academic milestone"):
        MS.record(actor("SUP"), dc.id, stu.id, "DC Approved")
