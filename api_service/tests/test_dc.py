"""Characterization tests for doctoral committee (DC) save and PhD progress
reports.

Tests whose name starts with a bug code (C9, S6, ...) pin behaviour that
looks wrong; flip them when fixing it.
"""

import pytest

import models as M
from conftest import make_user


@pytest.fixture
def people(db):
    return {
        "stu": make_user("stu", role="STU", degree="PHD"),
        "sup": make_user("sup", role="FAC"),
        "cp": make_user("cp", role="FAC"),
        "mem": make_user("mem", role="FAC"),
    }


def dc_payload(p, **extra):
    return {"student": {"user_id": p["stu"].id},
            "members": [{"role": "SU", "user_id": p["sup"].id},
                        {"role": "CP", "user_id": p["cp"].id},
                        {"role": "ME", "user_id": p["mem"].id}],
            "effective_from": "2026-01-01", "status": "DRA", **extra}


async def dc_save(client, payload):
    res = await client.post("/acadstack/dc_save", json=payload)
    return res.status_code, await res.get_json()


def make_dc(p, status="DRA", effective_from="2026-01-01"):
    dc = M.DcForStudent.create(student=p["stu"], status=status, effective_from=effective_from)
    for role, key in (("SU", "sup"), ("CP", "cp"), ("ME", "mem")):
        M.DcMember.create(dc=dc, member=p[key], role=role)
    return dc


# ---- dc_save ----

async def test_c9_new_dc_is_saved_but_response_is_500(client, auth, people):
    await auth.login("sup")
    status, _ = await dc_save(client, dc_payload(people))
    assert status == 500
    dc = M.DcForStudent.get()
    assert (dc.student_id, dc.status) == (people["stu"].id, "DRA")
    assert sorted(m.role for m in dc.dc_members) == ["CP", "ME", "SU"]
    assert [m.milestone for m in dc.acad_milestones] == ["DC Proposed"]


@pytest.mark.parametrize("drop_role", ["SU", "CP", "ME"])
async def test_supervisor_chair_and_member_are_required(client, auth, people, drop_role):
    payload = dc_payload(people)
    payload["members"] = [m for m in payload["members"] if m["role"] != drop_role]
    await auth.login("sup")
    _, body = await dc_save(client, payload)
    assert body["status"] == "ERROR"
    assert "supervisor" in body["body"]
    assert M.DcForStudent.select().count() == 0


async def test_faculty_must_be_the_supervisor(client, auth, people):
    await auth.login("mem")
    _, body = await dc_save(client, dc_payload(people))
    assert body["status"] == "ERROR"
    assert M.DcForStudent.select().count() == 0


async def test_supervisor_must_be_faculty(client, auth, people):
    M.User.update(role="HOD").where(M.User.id == people["sup"].id).execute()
    make_user("aca", role="ACA")
    await auth.login("aca")
    _, body = await dc_save(client, dc_payload(people))
    assert body == {"status": "ERROR", "body": "Only a faculty can be the supervisor!"}


async def test_supervisor_must_be_from_students_department(client, auth, people):
    M.Person.update(dept_name="MEC").where(M.Person.id == people["sup"].person_id).execute()
    await auth.login("sup")
    _, body = await dc_save(client, dc_payload(people))
    assert body["body"] == "Supervisor and student must be from same department!"


async def test_hod_of_other_department_cannot_save(client, auth, people):
    make_user("hod", role="HOD", dept_name="MEC")
    await auth.login("hod")
    _, body = await dc_save(client, dc_payload(people))
    assert body["body"] == "Only HOD of student's own dept. can make changes!"


async def test_overlapping_dc_dates_are_rejected(client, auth, people):
    dc = make_dc(people, effective_from="2025-06-01")
    M.DcForStudent.update(effective_to="2026-06-01").where(M.DcForStudent.id == dc.id).execute()
    await auth.login("sup")
    _, body = await dc_save(client, dc_payload(people))
    assert body["body"] == "DC dates overlap with an existing DC of the same student!"


async def test_open_ended_existing_dc_is_not_seen_as_overlapping(client, auth, people):
    make_dc(people, effective_from="2025-06-01")
    await auth.login("sup")
    await dc_save(client, dc_payload(people))
    assert M.DcForStudent.select().count() == 2


async def test_student_cannot_save(client, auth, people):
    await auth.login("stu")
    _, body = await dc_save(client, dc_payload(people))
    assert body["status"] == "ERROR"


async def test_faculty_cannot_edit_submitted_dc(client, auth, people):
    dc = make_dc(people, status="SUB")
    await auth.login("sup")
    _, body = await dc_save(client, dc_payload(people, id=dc.id, txn_no=1))
    assert body["status"] == "ERROR"
    assert "Insufficient privileges" in body["body"]


async def test_c9_approving_dc_adds_milestone_but_response_is_500(client, auth, people):
    dc = make_dc(people, status="SUB")
    members = [{"id": m.id, "txn_no": m.txn_no, "role": m.role, "user_id": m.member_id}
               for m in dc.dc_members]
    make_user("aca", role="ACA")
    await auth.login("aca")
    status, _ = await dc_save(client, dc_payload(people, id=dc.id, txn_no=1,
                                                 status="APP", members=members))
    assert status == 500
    dc = M.DcForStudent.get_by_id(dc.id)
    assert (dc.status, dc.txn_no) == ("APP", 2)
    assert [m.milestone for m in dc.acad_milestones] == ["DC Approved"]


# ---- progress reports (/ppr_save) ----

async def ppr_save(client, payload):
    return await (await client.post("/acadstack/ppr_save", json=payload)).get_json()


def make_ppr(p, dc, status="DRA", acad_session="2026-I"):
    dcm = M.DcMember.get((M.DcMember.dc == dc) & (M.DcMember.member == p["mem"]))
    return M.PhDProgressReport.create(student=p["stu"], dc_member=dcm, status=status,
                                      acad_session=acad_session, note="n")


async def test_dc_member_creates_draft_report(client, auth, people):
    dc = make_dc(people)
    await auth.login("mem")
    body = await ppr_save(client, {"student": people["stu"].id, "acad_session": "2026-I",
                                   "note": "fine", "status": "APP"})
    assert body["status"] == "OK"
    ppr = M.PhDProgressReport.get()
    assert (ppr.status, ppr.note) == ("DRA", "fine")
    assert ppr.dc_member.dc_id == dc.id


async def test_report_uses_first_dc_membership_of_the_user_for_any_student(client, auth, people):
    other_stu = make_user("stu2", role="STU", degree="PHD")
    other_dc = M.DcForStudent.create(student=other_stu, status="APP")
    first = M.DcMember.create(dc=other_dc, member=people["mem"], role="ME")
    make_dc(people)
    await auth.login("mem")
    await ppr_save(client, {"student": people["stu"].id, "acad_session": "2026-I", "note": "x"})
    assert M.PhDProgressReport.get().dc_member_id == first.id


async def test_duplicate_report_is_rejected(client, auth, people):
    dc = make_dc(people)
    make_ppr(people, dc)
    await auth.login("mem")
    body = await ppr_save(client, {"student": people["stu"].id, "acad_session": "2026-I",
                                   "note": "again"})
    assert body["status"] == "ERROR"
    assert "already submitted" in body["body"]


async def test_non_member_cannot_create_report(client, auth, people):
    make_dc(people)
    make_user("fac", role="FAC")
    await auth.login("fac")
    body = await ppr_save(client, {"student": people["stu"].id, "acad_session": "2026-I",
                                   "note": "x"})
    assert body == {"status": "ERROR", "body": "You must be a DC member!"}


async def test_student_cannot_save_report(client, auth, people):
    make_dc(people)
    await auth.login("stu")
    body = await ppr_save(client, {"student": people["stu"].id, "acad_session": "2026-I",
                                   "note": "x"})
    assert body["status"] == "ERROR"
    assert M.PhDProgressReport.select().count() == 0


@pytest.mark.parametrize("old,new,allowed", [
    ("DRA", "SUB", True), ("SUB", "DRA", False), ("DRA", "APP", False),
    ("APP", "DRA", False), ("DRA", "DRA", True),
])
async def test_member_status_transitions(client, auth, people, old, new, allowed):
    dc = make_dc(people)
    ppr = make_ppr(people, dc, status=old)
    await auth.login("mem")
    body = await ppr_save(client, {"id": ppr.id, "student": people["stu"].id,
                                   "status": new, "txn_no": 1})
    assert (body["status"] == "OK") == allowed
    assert M.PhDProgressReport.get_by_id(ppr.id).status == (new if allowed else old)


async def test_chair_approves_submitted_report(client, auth, people):
    dc = make_dc(people)
    ppr = make_ppr(people, dc, status="SUB")
    await auth.login("cp")
    body = await ppr_save(client, {"id": ppr.id, "student": people["stu"].id,
                                   "status": "APP", "txn_no": 1})
    assert body["status"] == "OK"
    assert M.PhDProgressReport.get_by_id(ppr.id).status == "APP"


async def test_s6_non_chair_member_can_approve_report(client, auth, people):
    # is_dc_chair is async but called without await; the coroutine is truthy.
    dc = make_dc(people)
    ppr = make_ppr(people, dc, status="SUB")
    await auth.login("mem")
    body = await ppr_save(client, {"id": ppr.id, "student": people["stu"].id,
                                   "status": "APP", "txn_no": 1})
    assert body["status"] == "OK"
    assert M.PhDProgressReport.get_by_id(ppr.id).status == "APP"


async def test_academic_section_can_make_any_transition(client, auth, people):
    dc = make_dc(people)
    ppr = make_ppr(people, dc, status="APP")
    make_user("aca", role="ACA")
    await auth.login("aca")
    body = await ppr_save(client, {"id": ppr.id, "student": people["stu"].id,
                                   "status": "DRA", "txn_no": 1})
    assert body["status"] == "OK"
    assert M.PhDProgressReport.get_by_id(ppr.id).status == "DRA"
