"""Characterization tests for enrolment approval (``change_enroll_status``)
and the enrolment save route (``coe_save``).

Tests whose name starts with a bug code (C11, S5, ...) pin behaviour that
looks wrong; flip them when fixing it.
"""

import pytest

import models as M
from conftest import enrol, make_offering, make_user, set_event_window

SESSION = "2026-I"


@pytest.fixture
def setup(db):
    """A BTE student with a pending enrolment in an offering whose coordinator
    is ``ins``; ``adv`` is the student's batch advisor."""
    ins = make_user("ins", role="FAC")
    adv = make_user("adv", role="FAC")
    stu = make_user("stu", role="STU", degree="BTE", year_of_entry="2024")
    M.BatchAdvisors.create(user=adv, year_of_entry="2024", for_degree="BTE")
    co = make_offering(acad_session=SESSION, instructor=ins)
    ce = enrol(stu, co, enrol_status="IPEN")
    set_event_window(SESSION, "COURSE_REG")
    return {"ins": ins, "adv": adv, "stu": stu, "co": co, "ce": ce}


async def change_status(client, ids, status):
    res = await client.post("/acadstack/change_enroll_status",
                            json={"ids": ids, "status": status})
    return await res.get_json()


def status_of(ce):
    return M.CourseEnrollment.get_by_id(ce.id).enrol_status


def set_status(ce, status):
    M.CourseEnrollment.update(enrol_status=status).where(
        M.CourseEnrollment.id == ce.id).execute()


# ---- change_enroll_status ----

@pytest.mark.parametrize("role,action,expected", [
    ("ACA", "approve", "ENRO"), ("ACA", "reject", "ASREJ"),
    ("DEA", "approve", "ENRO"), ("DEA", "reject", "ASREJ"),
])
async def test_academic_section_decides_directly(client, auth, setup, role, action, expected):
    make_user("boss", role=role)
    await auth.login("boss")
    assert (await change_status(client, [setup["ce"].id], action))["status"] == "OK"
    assert status_of(setup["ce"]) == expected


async def test_instructor_approval_moves_to_advisor(client, auth, setup):
    await auth.login("ins")
    assert (await change_status(client, [setup["ce"].id], "approve"))["status"] == "OK"
    assert status_of(setup["ce"]) == "APEN"


async def test_instructor_rejection(client, auth, setup):
    await auth.login("ins")
    await change_status(client, [setup["ce"].id], "reject")
    assert status_of(setup["ce"]) == "IREJ"


async def test_any_action_other_than_approve_rejects(client, auth, setup):
    await auth.login("ins")
    await change_status(client, [setup["ce"].id], "whatever")
    assert status_of(setup["ce"]) == "IREJ"


async def test_advisor_approval_after_instructor(client, auth, setup):
    set_status(setup["ce"], "APEN")
    await auth.login("adv")
    assert (await change_status(client, [setup["ce"].id], "approve"))["status"] == "OK"
    assert status_of(setup["ce"]) == "ENRO"


async def test_advisor_rejection(client, auth, setup):
    set_status(setup["ce"], "APEN")
    await auth.login("adv")
    await change_status(client, [setup["ce"].id], "reject")
    assert status_of(setup["ce"]) == "AREJ"


async def test_c11_advisor_can_approve_ipen_straight_to_enro(client, auth, setup):
    await auth.login("adv")
    assert (await change_status(client, [setup["ce"].id], "approve"))["status"] == "OK"
    assert status_of(setup["ce"]) == "ENRO"


async def test_instructor_who_is_also_advisor_approves_in_two_steps(client, auth, setup):
    M.BatchAdvisors.update(user=setup["ins"]).execute()
    await auth.login("ins")
    await change_status(client, [setup["ce"].id], "approve")
    assert status_of(setup["ce"]) == "APEN"
    await change_status(client, [setup["ce"].id], "approve")
    assert status_of(setup["ce"]) == "ENRO"


async def test_instructor_who_is_also_advisor_rejects_as_advisor(client, auth, setup):
    M.BatchAdvisors.update(user=setup["ins"]).execute()
    await auth.login("ins")
    await change_status(client, [setup["ce"].id], "reject")
    assert status_of(setup["ce"]) == "AREJ"


async def test_hod_of_any_department_can_decide_advisor_pending(client, auth, setup):
    set_status(setup["ce"], "APEN")
    make_user("hod", role="HOD", dept_name="MEC")
    await auth.login("hod")
    assert (await change_status(client, [setup["ce"].id], "approve"))["status"] == "OK"
    assert status_of(setup["ce"]) == "ENRO"


async def test_hod_cannot_decide_instructor_pending(client, auth, setup):
    make_user("hod", role="HOD")
    await auth.login("hod")
    assert (await change_status(client, [setup["ce"].id], "approve"))["status"] == "ERROR"
    assert status_of(setup["ce"]) == "IPEN"


async def test_unrelated_faculty_cannot_decide(client, auth, setup):
    make_user("fac", role="FAC")
    await auth.login("fac")
    body = await change_status(client, [setup["ce"].id], "approve")
    assert body["status"] == "ERROR"
    assert "privileges" in body["body"]
    assert status_of(setup["ce"]) == "IPEN"


async def test_c11_non_coordinator_instructor_cannot_approve(client, auth, setup):
    co_ins = make_user("coins", role="FAC")
    M.CourseInstructor.create(offering=setup["co"], instructor=co_ins, is_coordinator=False)
    await auth.login("coins")
    assert (await change_status(client, [setup["ce"].id], "approve"))["status"] == "ERROR"
    assert status_of(setup["ce"]) == "IPEN"


async def test_student_cannot_change_status(client, auth, setup):
    await auth.login("stu")
    assert (await change_status(client, [setup["ce"].id], "approve"))["status"] == "ERROR"
    assert status_of(setup["ce"]) == "IPEN"


async def test_faculty_cannot_decide_outside_add_drop_window(client, auth, setup):
    M.AcademicCalendar.delete().execute()
    set_event_window(SESSION, "COURSE_REG", open_=False)
    await auth.login("ins")
    body = await change_status(client, [setup["ce"].id], "approve")
    assert body["status"] == "ERROR"
    assert "add/drop not open" in body["body"]
    assert status_of(setup["ce"]) == "IPEN"


async def test_academic_section_decides_outside_add_drop_window(client, auth, setup):
    M.AcademicCalendar.delete().execute()
    make_user("aca", role="ACA")
    await auth.login("aca")
    await change_status(client, [setup["ce"].id], "approve")
    assert status_of(setup["ce"]) == "ENRO"


async def test_faculty_cannot_decide_on_finished_offering(client, auth, setup):
    M.CourseOffering.update(status="F").execute()
    await auth.login("ins")
    assert (await change_status(client, [setup["ce"].id], "approve"))["status"] == "ERROR"
    assert status_of(setup["ce"]) == "IPEN"


async def test_batch_is_all_or_nothing(client, auth, setup):
    other_co = make_offering("CS999", acad_session=SESSION)
    other_ce = enrol(setup["stu"], other_co, enrol_status="IPEN")
    await auth.login("ins")
    body = await change_status(client, [setup["ce"].id, other_ce.id], "approve")
    assert body["status"] == "ERROR"
    assert status_of(setup["ce"]) == "IPEN"


async def test_empty_selection(client, auth, setup):
    await auth.login("ins")
    assert (await change_status(client, [], "approve"))["status"] == "ERROR"


# ---- coe_save ----

async def coe_save(client, payload):
    return await (await client.post("/acadstack/coe_save", json=payload)).get_json()


async def test_s5_student_can_insert_enrolment_with_any_grade(client, auth, setup):
    co = make_offering("CS200", acad_session=SESSION)
    await auth.login("stu")
    body = await coe_save(client, {"course_offering": co.id, "student": setup["stu"].id,
                                   "enrol_type": "C", "enrol_status": "ENRO", "grade": "A"})
    assert body["status"] == "OK"
    ce = M.CourseEnrollment.get((M.CourseEnrollment.course_offering == co.id))
    assert (ce.enrol_status, ce.grade) == ("ENRO", "A")


async def test_s5_student_can_set_own_grade_on_update(client, auth, setup):
    await auth.login("stu")
    body = await coe_save(client, {"id": setup["ce"].id, "enrol_status": "ENRO", "grade": "A"})
    assert body["status"] == "OK"
    ce = M.CourseEnrollment.get_by_id(setup["ce"].id)
    assert (ce.enrol_status, ce.grade) == ("ENRO", "A")


async def test_student_cannot_update_others_enrolment(client, auth, setup):
    make_user("stu2", role="STU")
    await auth.login("stu2")
    body = await coe_save(client, {"id": setup["ce"].id, "enrol_status": "DROP"})
    assert body["status"] == "ERROR"
    assert status_of(setup["ce"]) == "IPEN"


async def test_update_rejects_unknown_status(client, auth, setup):
    make_user("aca", role="ACA")
    await auth.login("aca")
    body = await coe_save(client, {"id": setup["ce"].id, "enrol_status": "BOGUS"})
    assert body["status"] == "ERROR"
    assert "Unknown enrolment status" in body["body"]


async def test_update_without_status_fails_generically(client, auth, setup):
    make_user("aca", role="ACA")
    await auth.login("aca")
    body = await coe_save(client, {"id": setup["ce"].id, "grade": "B"})
    assert body == {"status": "ERROR", "body": "Error when saving course enrollment details."}
    assert M.CourseEnrollment.get_by_id(setup["ce"].id).grade == "NA"


async def test_unrelated_faculty_cannot_update(client, auth, setup):
    make_user("fac", role="FAC")
    await auth.login("fac")
    body = await coe_save(client, {"id": setup["ce"].id, "enrol_status": "ENRO"})
    assert body["status"] == "ERROR"
    assert status_of(setup["ce"]) == "IPEN"


async def test_coordinator_can_update(client, auth, setup):
    await auth.login("ins")
    body = await coe_save(client, {"id": setup["ce"].id, "enrol_status": "ENRO",
                                   "remarks": "ok"})
    assert body["status"] == "OK"
    ce = M.CourseEnrollment.get_by_id(setup["ce"].id)
    assert (ce.enrol_status, ce.remarks, ce.txn_no) == ("ENRO", "ok", 2)


async def test_stale_txn_no_is_rejected(client, auth, setup):
    make_user("aca", role="ACA")
    await auth.login("aca")
    body = await coe_save(client, {"id": setup["ce"].id, "enrol_status": "ENRO",
                                   "txn_no": 7})
    assert body["status"] == "ERROR"
    assert status_of(setup["ce"]) == "IPEN"
