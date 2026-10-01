"""Characterization tests for enrolment approval (``change_enroll_status``)
and the enrolment save route (``coe_save``).

Tests whose name starts with a bug code (C11, ...) pin behaviour that
looks wrong; flip them when fixing it.
"""

import pytest

import models as M
import settings
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


async def test_advisor_with_the_adv_role_can_approve(client, auth, setup):
    setup["adv"].role = "ADV"
    setup["adv"].save()
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


async def test_student_cannot_insert_enrolment(client, auth, setup):
    co = make_offering("CS200", acad_session=SESSION)
    await auth.login("stu")
    body = await coe_save(client, {"course_offering": co.id, "student": setup["stu"].id,
                                   "enrol_type": "C", "enrol_status": "ENRO", "grade": "A"})
    assert body["status"] == "ERROR"
    assert not M.CourseEnrollment.select().where(
        M.CourseEnrollment.course_offering == co.id).exists()


async def test_student_cannot_approve_own_enrolment(client, auth, setup):
    await auth.login("stu")
    body = await coe_save(client, {"id": setup["ce"].id, "enrol_status": "ENRO", "grade": "A"})
    assert body["status"] == "ERROR"
    ce = M.CourseEnrollment.get_by_id(setup["ce"].id)
    assert (ce.enrol_status, ce.grade) == ("IPEN", "NA")


async def test_student_can_drop_own_enrolment_but_not_set_grade(client, auth, setup):
    await auth.login("stu")
    body = await coe_save(client, {"id": setup["ce"].id, "enrol_status": "DROP",
                                   "grade": "A", "student": 999})
    assert body["status"] == "OK"
    ce = M.CourseEnrollment.get_by_id(setup["ce"].id)
    assert (ce.enrol_status, ce.grade, ce.student_id) == ("DROP", "NA", setup["stu"].id)


async def test_academic_section_can_insert_enrolment(client, auth, setup):
    co = make_offering("CS200", acad_session=SESSION)
    make_user("aca", role="ACA")
    await auth.login("aca")
    body = await coe_save(client, {"course_offering": co.id, "student": setup["stu"].id,
                                   "enrol_type": "C", "enrol_status": "ENRO"})
    assert body["status"] == "OK"
    ce = M.CourseEnrollment.get(M.CourseEnrollment.course_offering == co.id)
    assert (ce.student_id, ce.enrol_status) == (setup["stu"].id, "ENRO")


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


# ---- enroll_in_courses ----

import api_course_enrolment as apiCE


@pytest.fixture
def emails(monkeypatch):
    """Records the enrolments that enrolment emails are sent for."""
    sent = []
    monkeypatch.setattr(apiCE, "send_enrolment_email", lambda ce_id, **kw: sent.append(ce_id))
    return sent


@pytest.fixture
def no_fees_check(db):
    settings.save("fees_check_enabled", False)


def enrollable(code, slot, day=0, start=9, end=11, acad_session=SESSION):
    """An offering the setup student may enrol in, in a slot with one timing."""
    co = make_offering(code, acad_session=acad_session, slot=slot)
    M.CourseCategory.create(offering=co, degree="BTE", dept="CSE", category="PC",
                            for_entry_years="2024")
    M.CourseSlotTiming.create(slot=slot, week_day=day, start_time=start, end_time=end)
    return co


async def enroll(client, stu, cos, enrol_type="C"):
    res = await client.post("/acadstack/enroll_in_courses",
                            json={"user_id": stu.id, "co_ids": [co.id for co in cos],
                                  "enrol_type": enrol_type})
    return await res.get_json()


def enrolments_in(*cos):
    return M.CourseEnrollment.select().where(
        M.CourseEnrollment.course_offering.in_([co.id for co in cos])).count()


async def test_student_enrols_and_emails_go_out_after_commit(client, auth, setup, no_fees_check, emails):
    co = enrollable("CS301", "A")
    await auth.login("stu")
    body = await enroll(client, setup["stu"], [co])
    assert body == {"status": "OK", "body": "Enrollment requested successfully!"}
    ce = M.CourseEnrollment.get(M.CourseEnrollment.course_offering == co.id)
    assert (ce.enrol_status, ce.enrol_type) == ("IPEN", "C")
    assert emails == [ce.id]


async def test_c5_slot_clash_rolls_back_the_whole_request(client, auth, setup, no_fees_check, emails):
    co1 = enrollable("CS301", "A", start=9, end=11)
    co2 = enrollable("CS302", "B", start=10, end=12)
    await auth.login("stu")
    body = await enroll(client, setup["stu"], [co1, co2])
    assert body["status"] == "ERROR"
    assert enrolments_in(co1, co2) == 0
    assert emails == []


async def test_c6_audit_only_student_can_enrol(client, auth, setup, no_fees_check, emails):
    # The setup enrolment is the student's only one; make it an audit too, so
    # the student has no credit enrolments and the credit sum is NULL.
    M.CourseEnrollment.update(enrol_type="A").execute()
    set_event_window(SESSION, "WITHDRAW")
    co = enrollable("CS301", "A")
    await auth.login("stu")
    body = await enroll(client, setup["stu"], [co], enrol_type="A")
    assert body["status"] == "OK"
    assert M.CourseEnrollment.get(M.CourseEnrollment.course_offering == co.id).enrol_type == "A"


async def test_c19_student_on_trimester_session_passes_fee_check(client, auth, setup, emails):
    tri = "2026-T1"
    set_event_window(tri, "SESSION")
    set_event_window(tri, "COURSE_REG")
    M.FeesTransaction.create(student=setup["stu"], acad_session=tri, fees_txn_amt=100,
                             fees_txn_no="T1", fees_txn_dt="2026-01-01",
                             fees_txn_bank="B", doc_file_name="f")
    co = enrollable("CS301", "A", acad_session=tri)
    await auth.login("stu")
    body = await enroll(client, setup["stu"], [co])
    assert body["status"] == "OK"
    assert enrolments_in(co) == 1


async def test_student_without_fee_record_is_blocked(client, auth, setup, emails):
    set_event_window(SESSION, "SESSION")
    co = enrollable("CS301", "A")
    await auth.login("stu")
    body = await enroll(client, setup["stu"], [co])
    assert body["status"] == "ERROR"
    assert "fees" in body["body"]


async def test_c23_no_email_for_approvals_that_are_rolled_back(client, auth, setup, emails):
    other_co = make_offering("CS999", acad_session=SESSION)
    other_ce = enrol(setup["stu"], other_co, enrol_status="IPEN")
    await auth.login("ins")
    await change_status(client, [setup["ce"].id, other_ce.id], "approve")
    assert status_of(setup["ce"]) == "IPEN"
    assert emails == []


async def test_approval_email_is_sent(client, auth, setup, emails):
    await auth.login("ins")
    await change_status(client, [setup["ce"].id], "approve")
    assert emails == [setup["ce"].id]


async def test_c7_coordinator_downloads_enrolments_for_grades(client, auth, setup):
    set_status(setup["ce"], "ENRO")
    await auth.login("ins")
    res = await client.get(f"/acadstack/download_enrollments_for_grades/{setup['co'].id}")
    assert res.status_code == 200
    lines = (await res.get_data(as_text=True)).splitlines()
    assert lines[0] == "first_name,last_name,roll_no,grade,code"
    assert lines[1] == "STU,USER,STU,NA,CS101"


# ---- slot conflicts ----

from types import SimpleNamespace


def timing(day, start, end, slot="X"):
    return SimpleNamespace(week_day=day, start_time=start, end_time=end, slot=slot)


@pytest.mark.parametrize("new,existing,clash", [
    ((0, 9, 11), (0, 9, 11), True),     # identical times (same slot)
    ((0, 9, 12), (0, 10, 11), True),    # new range encloses existing
    ((0, 10, 11), (0, 9, 12), True),    # existing encloses new
    ((0, 10, 12), (0, 9, 11), True),    # partial overlap
    ((0, 9, 11), (0, 11, 12), False),   # touching
    ((0, 9, 11), (1, 9, 11), False),    # other day
])
def test_slot_conflicts(new, existing, clash):
    assert bool(apiCE.slot_conflicts([timing(*new)], [timing(*existing)])) == clash


def test_slot_conflicts_checks_every_day_of_the_new_slot():
    new = [timing(0, 9, 10), timing(2, 9, 10)]
    assert apiCE.slot_conflicts(new, [timing(2, 9, 10)]) != []


async def test_same_slot_in_same_session_clashes(client, auth, setup, no_fees_check, emails):
    co1 = enrollable("CS301", "A")
    co2 = make_offering("CS302", acad_session=SESSION, slot="A")
    M.CourseCategory.create(offering=co2, degree="BTE", dept="CSE", category="PC",
                            for_entry_years="2024")
    enrol(setup["stu"], co1, enrol_status="ENRO")
    await auth.login("stu")
    body = await enroll(client, setup["stu"], [co2])
    assert body["status"] == "ERROR"
    assert enrolments_in(co2) == 0


async def test_same_slot_in_an_earlier_session_does_not_clash(client, auth, setup, no_fees_check, emails):
    old = enrollable("CS301", "A", acad_session="2025-II")
    enrol(setup["stu"], old, enrol_status="ENRO")
    co = make_offering("CS302", acad_session=SESSION, slot="A")
    M.CourseCategory.create(offering=co, degree="BTE", dept="CSE", category="PC",
                            for_entry_years="2024")
    await auth.login("stu")
    assert (await enroll(client, setup["stu"], [co]))["status"] == "OK"


async def test_re_requesting_a_pending_enrolment_does_not_clash_with_itself(client, auth, setup, no_fees_check, emails):
    co = enrollable("CS301", "A")
    enrol(setup["stu"], co, enrol_status="IPEN")
    await auth.login("stu")
    assert (await enroll(client, setup["stu"], [co]))["status"] == "OK"


async def test_passed_courses_match_whole_grades(client, auth, setup):
    enrol(setup["stu"], make_offering("CS301"), grade="B")
    enrol(setup["stu"], make_offering("CS302"), grade="")
    await auth.login("stu")
    res = await client.get(f"/acadstack/get_passed_courses/{setup['stu'].id}")
    assert (await res.get_json())["body"] == {"codes": ["CS301"]}
