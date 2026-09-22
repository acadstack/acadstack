"""Smoke coverage for the course-enrolment endpoints.

Phase 5 rewrote every handler in api_course_enrolment.py into a thin
adapter over domain.enrolment / domain.transcript. Only
/change_enroll_status had tests before (test_enrolment_state_machine.py),
so these exercise the remaining routes end to end -- request in,
envelope out -- to catch anything the rewrite got wrong. They assert the
contract the frontend depends on (status, and the shape of the body),
not the full behaviour of the logic underneath.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import models as DB  # noqa: E402
from conftest import create_user, login_as  # noqa: E402

ACAD_SESSION = "2024-I"
_seq = 0


def _course(ltp="3-1-0-5-3"):
    global _seq
    _seq += 1
    return DB.Course.create(code=f"SM{100 + _seq}", title="Smoke Course",
                            ltp=ltp, status="APP")


def _offering(status="E", slot="A", acad_session=ACAD_SESSION):
    return DB.CourseOffering.create(course=_course(), acad_session=acad_session,
                                    status=status, slot=slot, dept_name="CSE")


def _student(login_id, degree="BTE", dept="CSE", year="2022"):
    global _seq
    _seq += 1
    # Roll numbers must match api_common.roll_number_valid(): 20yy + 2-4
    # letters + up to 4 digits.
    return create_user("STU", login_id, org_id=f"2022stu{_seq}",
                       dept_name=dept, degree=degree, year_of_entry=year)


def _enrolment(offering, student, enrol_type="C", enrol_status="ENRO",
               grade="A"):
    return DB.CourseEnrollment.create(course_offering=offering, student=student,
                                      enrol_type=enrol_type,
                                      enrol_status=enrol_status, grade=grade)


def _open_session(acad_session=ACAD_SESSION):
    """Marks the session as the one currently running, which is what
    makes it a 'current academic session' for the fees check."""
    today = date.today()
    DB.AcademicCalendar.create(acad_session=acad_session, event_code="SESSION_S",
                               event_value=(today - timedelta(days=30)).strftime("%Y-%m-%d"))
    DB.AcademicCalendar.create(acad_session=acad_session, event_code="SESSION_E",
                               event_value=(today + timedelta(days=30)).strftime("%Y-%m-%d"))


def _paid_fees(student, txn_no, acad_session=ACAD_SESSION):
    return DB.FeesTransaction.create(
        student=student, acad_session=acad_session, fees_txn_amt=1000,
        fees_txn_no=txn_no, fees_txn_dt=date.today(), fees_txn_bank="Bank",
        doc_file_name="receipt.pdf")


def _open_add_drop(acad_session=ACAD_SESSION):
    today = date.today()
    DB.AcademicCalendar.create(acad_session=acad_session, event_code="ADD_DROP_S",
                               event_value=(today - timedelta(days=5)).strftime("%Y-%m-%d"))
    DB.AcademicCalendar.create(acad_session=acad_session, event_code="ADD_DROP_E",
                               event_value=(today + timedelta(days=5)).strftime("%Y-%m-%d"))


# ============================== views ==============================

def test_coe_view_returns_the_enrolment(client):
    offering = _offering()
    ce = _enrolment(offering, _student("stu_view"))
    login_as(client, create_user("ACA", "aca_view").login_id)

    res = client.get(f"/acadstack/coe_view/{ce.id}")

    assert res.json["status"] == "OK", res.json
    assert res.json["body"]["id"] == ce.id
    assert res.json["body"]["enrol_status"] == "ENRO"


def test_coe_view_refuses_someone_elses_enrolment(client):
    offering = _offering()
    ce = _enrolment(offering, _student("stu_owner"))
    login_as(client, _student("stu_nosy").login_id)

    res = client.get(f"/acadstack/coe_view/{ce.id}")

    assert res.json["status"] == "ERROR"
    assert res.json["body"] == "You are not allowed to view this enrolment!"


def test_coe_save_updates_an_existing_enrolment(client):
    _open_add_drop()
    offering = _offering()
    ce = _enrolment(offering, _student("stu_save"), enrol_status="IPEN")
    login_as(client, create_user("ACA", "aca_save").login_id)

    res = client.post("/acadstack/coe_save",
                      json={"id": ce.id, "enrol_status": "ENRO",
                            "enrol_type": "C", "remarks": "ok by aca"})

    assert res.json["status"] == "OK", res.json
    assert res.json["body"]["enrol_status"] == "ENRO"
    assert DB.CourseEnrollment.get_by_id(ce.id).remarks == "ok by aca"


def test_get_course_enrollments_lists_students(client):
    offering = _offering()
    _enrolment(offering, _student("stu_list1"))
    _enrolment(offering, _student("stu_list2"))
    login_as(client, create_user("ACA", "aca_list").login_id)

    res = client.get(f"/acadstack/get_course_enrollments/{offering.id}")

    assert res.json["status"] == "OK", res.json
    assert len(res.json["body"]) == 2
    assert {"id", "student", "org_id", "attendance"} <= set(res.json["body"][0])


def test_get_course_enrollments_on_empty_offering_is_an_error(client):
    offering = _offering()
    login_as(client, create_user("ACA", "aca_empty").login_id)

    res = client.get(f"/acadstack/get_course_enrollments/{offering.id}")

    assert res.json["status"] == "ERROR"
    assert res.json["body"] == "No enrolments found for course offering!"


def test_student_academics_returns_per_session_performance(client):
    student = _student("stu_acad")
    _enrolment(_offering(), student, grade="A")
    login_as(client, student.login_id)

    res = client.get(f"/acadstack/get_student_academics/{student.id}")

    assert res.json["status"] == "OK", res.json
    body = res.json["body"]
    assert "password_hashed" not in body
    credit = body["enrollments"]["C"]
    assert credit["acad_sessions"] == [ACAD_SESSION]
    assert credit["enrollments"][ACAD_SESSION]["sgpa"] == 10.0


def test_student_cannot_read_another_students_academics(client):
    other = _student("stu_target")
    login_as(client, _student("stu_peeker").login_id)

    res = client.get(f"/acadstack/get_student_academics/{other.id}")

    assert res.json["status"] == "ERROR"
    assert "Illegal access!" in res.json["body"]


def test_get_passed_courses_lists_passing_grades_only(client):
    student = _student("stu_pass")
    passed = _enrolment(_offering(), student, grade="B")
    _enrolment(_offering(), student, grade="F")
    login_as(client, student.login_id)

    res = client.get(f"/acadstack/get_passed_courses/{student.id}")

    assert res.json["status"] == "OK", res.json
    assert res.json["body"]["codes"] == [passed.course_offering.course.code]


# ============================== actions ==============================

def test_drop_by_academic_section_records_a_rejection(client):
    _open_add_drop()
    ce = _enrolment(_offering(), _student("stu_drop"), enrol_status="ENRO")
    login_as(client, create_user("ACA", "aca_drop").login_id)

    res = client.get(f"/acadstack/drop_withdraw_course/{ce.id}/DROP")

    assert res.json["status"] == "OK", res.json
    # ACA/DEA dropping a course records ASREJ rather than DROP.
    assert DB.CourseEnrollment.get_by_id(ce.id).enrol_status == "ASREJ"


def test_drop_rejects_an_unknown_status(client):
    ce = _enrolment(_offering(), _student("stu_baddrop"))
    login_as(client, create_user("ACA", "aca_baddrop").login_id)

    res = client.get(f"/acadstack/drop_withdraw_course/{ce.id}/ZZZZ")

    assert res.json["status"] == "ERROR"
    assert "Only drop/withdraw allowed" in res.json["body"]


def test_bulk_enrol_enrols_every_matching_student(client):
    offering = _offering()
    _student("stu_bulk1")
    _student("stu_bulk2")
    create_user("STU", "stu_other", org_id="2019oth", dept_name="CSE",
                degree="BTE", year_of_entry="2019")
    login_as(client, create_user("ACA", "aca_bulk").login_id)

    res = client.get(f"/acadstack/co_bulkenrol/2022stu/{offering.id}")

    assert res.json["status"] == "OK", res.json
    assert "Enrolled 2 students" in res.json["body"]
    assert DB.CourseEnrollment.select().where(
        DB.CourseEnrollment.course_offering == offering).count() == 2


def test_bulk_enrol_rejects_a_malformed_pattern(client):
    offering = _offering()
    login_as(client, create_user("ACA", "aca_badbulk").login_id)

    res = client.get(f"/acadstack/co_bulkenrol/nope/{offering.id}")

    assert res.json["status"] == "ERROR"
    assert res.json["body"] == "Invalid entry number pattern!"


def test_enrol_request_goes_to_instructor_pending(client):
    _open_add_drop()
    offering = _offering(slot="A")
    DB.CourseSlotTiming.create(slot="A", week_day=0, start_time=900,
                               end_time=1000)
    _open_session()
    student = _student("stu_enrol")
    DB.CourseCategory.create(offering=offering, degree="BTE", dept="CSE",
                             category="PC", for_entry_years="2022")
    _paid_fees(student, "TXN1")
    login_as(client, student.login_id)

    res = client.post("/acadstack/enroll_in_courses",
                      json={"user_id": student.id, "co_ids": [offering.id],
                            "enrol_type": "C"})

    assert res.json["status"] == "OK", res.json
    assert res.json["body"] == "Enrollment requested successfully!"
    ce = DB.CourseEnrollment.get(
        DB.CourseEnrollment.course_offering == offering)
    assert ce.enrol_status == "IPEN"


def test_enrol_request_without_courses_is_rejected(client):
    _open_session()
    student = _student("stu_nocourse")
    _paid_fees(student, "TXN2")
    login_as(client, student.login_id)

    res = client.post("/acadstack/enroll_in_courses",
                      json={"user_id": student.id, "co_ids": [],
                            "enrol_type": "C"})

    assert res.json["status"] == "ERROR"
    assert res.json["body"] == "Please select a course to enrol!"


def test_enrol_request_blocked_when_fees_are_unpaid(client):
    _open_add_drop()
    offering = _offering()
    student = _student("stu_nofees")
    login_as(client, student.login_id)

    res = client.post("/acadstack/enroll_in_courses",
                      json={"user_id": student.id, "co_ids": [offering.id],
                            "enrol_type": "C"})

    assert res.json["status"] == "ERROR"
    assert "fees payment details" in res.json["body"]


# ============================== worklists / exports ==============================

def test_instructor_worklist_returns_both_buckets(client):
    offering = _offering()
    ce = _enrolment(offering, _student("stu_work"), enrol_status="IPEN")
    instructor = create_user("FAC", "instr_work")
    DB.CourseInstructor.create(offering=offering, instructor=instructor,
                               is_coordinator=True)
    login_as(client, instructor.login_id)

    res = client.get("/acadstack/get_instructor_courses_enrol")

    assert res.json["status"] == "OK", res.json
    assert [x["id"] for x in res.json["body"]["instructor_enrol"]] == [ce.id]
    assert res.json["body"]["advisor_enrol"] == []


def test_advisor_worklist_is_reachable(client):
    login_as(client, create_user("ACA", "aca_adv").login_id)

    res = client.get("/acadstack/get_advisor_courses_enrol")

    assert res.json["status"] == "OK", res.json
    assert isinstance(res.json["body"], list)


def test_enrolment_csv_download(client):
    offering = _offering()
    _enrolment(offering, _student("stu_csv"))
    login_as(client, create_user("ACA", "aca_csv").login_id)

    res = client.get(f"/acadstack/download_course_enrollments/{offering.id}")

    assert res.status_code == 200
    assert "attachment" in res.headers["Content-Disposition"]


def test_students_cannot_download_enrolment_csv(client):
    offering = _offering()
    student = _student("stu_nocsv")
    _enrolment(offering, student)
    login_as(client, student.login_id)

    res = client.get(f"/acadstack/download_course_enrollments/{offering.id}")

    assert res.json["status"] == "ERROR"
    assert res.json["body"] == "Students cannot download!"


def test_department_enrolment_export_is_broken_by_unquoted_user_join(client):
    """Characterises a PRE-EXISTING bug, unrelated to this refactor: the
    generate_course_enrolments query in sql_statements.toml joins
    `user` unquoted, and `user` is reserved in Postgres, so the route
    has never produced a file. Locked in here rather than fixed, so the
    fix (quoting the identifier) is a deliberate change with a test to
    flip. See docs/service-layer.md, "bugs found, not fixed"."""
    offering = _offering()
    _enrolment(offering, _student("stu_export"))
    login_as(client, create_user("ACA", "aca_export").login_id)

    res = client.get(
        f"/acadstack/download_course_enrolments/-/-/{ACAD_SESSION}")

    assert res.json["status"] == "ERROR"
    assert res.json["body"] == "Error when loading enrolment data as CSV."
