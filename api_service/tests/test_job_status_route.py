"""GET /job_status/<job_key> must be pollable by every role that can submit
a background job: reports.generate (credits report) and grades.export
(bulk grade-sheet download)."""
import permissions as PERM
from conftest import create_user, login_as


def _poll(app, client, key):
    app.extensions.setdefault("tasks", {})[key] = {
        "status": "running", "result": None,
        "completed_at": None, "error": None}
    return client.get(f"/acadstack/job_status/{key}")


def _role_with(perm, without):
    for role in ["ACA", "DEA", "HOD", "FAC", "SUP", "RES", "STU"]:
        if PERM.role_has_permission(role, perm) and \
                not PERM.role_has_permission(role, without):
            return role
    return None


def test_grades_export_holder_can_poll_job_status(app, client):
    role = _role_with("grades.export", without="reports.generate")
    assert role, "expected a role with grades.export but not reports.generate"
    create_user(role, "exporter")
    with client:
        login_as(client, "exporter")
        res = _poll(app, client, "grades-job")
    assert res.json["status"] == "OK", res.json
    assert res.json["body"]["status"] == "running"


def test_reports_generate_holder_can_poll_job_status(app, client):
    create_user("ACA", "reporter")
    with client:
        login_as(client, "reporter")
        res = _poll(app, client, "report-job")
    assert res.json["status"] == "OK", res.json


def test_role_without_either_permission_cannot_poll_job_status(app, client):
    create_user("STU", "stu1")
    with client:
        login_as(client, "stu1")
        res = _poll(app, client, "some-job")
    assert res.json["status"] == "ERROR"
