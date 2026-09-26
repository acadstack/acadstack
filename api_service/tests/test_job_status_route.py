"""GET /job_status/<job_key> must be pollable by every role that can submit
a background job: reports.generate (credits report) and grades.export
(bulk grade-sheet download)."""
import permissions as PERM
from conftest import create_user, login_as


def _poll(app, client, key, owner):
    app.extensions.setdefault("tasks", {})[key] = {
        "owner": owner, "status": "running", "result": None,
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
        res = _poll(app, client, "grades-job", "exporter")
    assert res.json["status"] == "OK", res.json
    assert res.json["body"]["status"] == "running"


def test_reports_generate_holder_can_poll_job_status(app, client):
    create_user("ACA", "reporter")
    with client:
        login_as(client, "reporter")
        res = _poll(app, client, "report-job", "reporter")
    assert res.json["status"] == "OK", res.json


def test_role_without_either_permission_cannot_poll_job_status(app, client):
    create_user("STU", "stu1")
    with client:
        login_as(client, "stu1")
        res = _poll(app, client, "some-job", "stu1")
    assert res.json["status"] == "ERROR"


def test_only_the_submitter_can_read_a_job(app, client):
    create_user("ACA", "reporter")
    create_user("DEA", "other")
    app.extensions.setdefault("tasks", {})["done-job"] = {
        "owner": "reporter", "status": "done", "result": "secret",
        "completed_at": None, "error": None}
    with client:
        login_as(client, "other")
        res = client.get("/acadstack/job_status/done-job")
    assert res.json["status"] == "ERROR"
    # The submitter's result is still there for them.
    assert "done-job" in app.extensions["tasks"]
