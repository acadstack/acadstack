"""The institute identity settings, as used in emails, the login page, the
web app and the report templates."""

import pytest
from jinja2.sandbox import SecurityError

import common as C
import create_email
import models as M
import settings
from conftest import enrol, make_offering, make_user


@pytest.mark.parametrize("key, value", [
    ("institute_name", " IIT"), ("institute_place", 1),
    ("app_url", "www.example.org"), ("app_url", "https://a b"),
    ("terms_url", "www.example.org"), ("terms_url", "https://a b"),
    ("guide_url", "www.example.org"), ("guide_url", "https://a b"),
    ("help_email", "nobody"), ("help_email", "a@b, c@d"),
    ("broadcast_emails", "a@b.org"), ("broadcast_emails", ["a@b.org", "x"]),
])
def test_identity_settings_reject_invalid_values(db, key, value):
    with pytest.raises(ValueError):
        settings.save(key, value)


def test_identity_settings_are_blank_by_default(db):
    assert [settings.get(k) for k in ("institute_name", "institute_place", "app_url",
                                      "terms_url", "guide_url", "help_email")] == [""] * 6
    assert settings.get("broadcast_emails") == []


def test_new_user_email_names_the_app_url_when_set(db):
    render = getattr(create_email, "__make_email_body")
    assert "Please visit" not in render("new_user.txt", {"login_id": "u1", "app_url": ""})
    settings.save("app_url", "https://uni.example.org/acadstack")
    text = render("new_user.txt", {"login_id": "u1", "app_url": settings.get("app_url")})
    assert "Please visit https://uni.example.org/acadstack to login." in text
    assert "You will have to request a new password" in text


@pytest.fixture
def sent(client, monkeypatch):
    out = []
    monkeypatch.setattr(C.emailer, "send_mail", lambda to, subj, body: out.append(to))
    return out


def test_events_alert_goes_to_broadcast_emails(sent):
    create_email.send_events_alert_email(["a"], [])
    assert sent == []
    settings.save("broadcast_emails", ["x@example.org", "y@example.org"])
    create_email.send_events_alert_email(["a"], [])
    assert sent == ["x@example.org,y@example.org"]


async def test_access_violation_alert_goes_to_help_email(app, sent):
    async with app.test_request_context("/"):
        create_email.send_access_violation_alert("oops")
        assert sent == []
        settings.save("help_email", "help@example.org")
        create_email.send_access_violation_alert("oops")
    assert sent == ["help@example.org"]


async def test_login_page_shows_institute_and_help(client, app, tmp_path):
    (tmp_path / "default.html").write_text(
        "<head><!--INSTITUTE_META--></head><body><!--TERMS_LINE--><!--GUIDE_LINE-->"
        "<!--HELP_LINE--></body>")
    app.static_folder = str(tmp_path)
    page = await (await client.get("/acadstack/")).get_data(as_text=True)
    assert page == "<head></head><body></body>"
    settings.save("institute_name", "Uni <One>")
    settings.save("help_email", "help@example.org")
    settings.save("terms_url", "https://uni.example.org/terms")
    settings.save("guide_url", "https://uni.example.org/guide")
    page = await (await client.get("/acadstack/")).get_data(as_text=True)
    assert '<meta name="author" content="Uni &lt;One&gt;">' in page
    assert 'href="mailto:help@example.org"' in page
    assert 'href="https://uni.example.org/terms" target="_blank">terms of use</a>' in page
    assert 'href="https://uni.example.org/guide" target="_blank">User Guide</a>' in page


async def test_current_user_carries_help_email(client, auth):
    make_user("aca", role="ACA")
    settings.save("help_email", "help@example.org")
    expected = {"help_email": "help@example.org", "terms_url": "", "guide_url": ""}
    res = await auth.login("aca")
    assert (await res.get_json())["body"]["institute"] == expected
    res = await client.get("/acadstack/current_user")
    assert (await res.get_json())["body"]["institute"] == expected


def test_template_in_override_folder_is_used(tmp_path):
    shipped = C.fill_template("report_templates", "degree.html", _certificate_data())
    assert "Bachelor of Technology" in shipped
    (tmp_path / "degree.html").write_text("Own wording for {{name}}")
    assert C.fill_template("report_templates", "degree.html", {"name": "Asha"},
                           str(tmp_path)) == "Own wording for Asha"
    # a template the folder lacks comes from the shipped ones
    assert "Bachelor of Technology" in C.fill_template(
        "report_templates", "degree.html", _certificate_data(), str(tmp_path / "none"))


def test_certificate_escapes_text_fields():
    html = C.fill_template("report_templates", "degree.html", _certificate_data(
        institute_name="Arts <& Science>", printed_name="B<b>Tech"))
    assert "ARTS &lt;&amp; SCIENCE&gt;" in html and "B&lt;b&gt;Tech" in html


def test_override_template_is_sandboxed(tmp_path):
    (tmp_path / "degree.html").write_text("{{ ''.__class__.__mro__ }}")
    with pytest.raises(SecurityError):
        C.fill_template("report_templates", "degree.html", {}, str(tmp_path))


def _certificate_data(**fields):
    return {"name": "Asha Rao", "entry_no": "X1", "doc_sr_no": "1/2", "degree": "B.Tech",
            "degree_level": "UG", "printed_name": "Bachelor of Technology",
            "specialisation": "", "dept_name": "Physics", "thesis_title": "",
            "static_file_path": "", "institute_name": "", "institute_place": "",
            "convocation_date": "", **fields}


def test_certificate_uses_institute_settings_and_program_attrs():
    html = C.fill_template("report_templates", "degree.html", _certificate_data(
        institute_name="Open University", institute_place="Springfield",
        convocation_date="30 December 2022", printed_name="Master of Arts",
        specialisation="Specialization in Poetry"))
    for text in ("OPEN UNIVERSITY", "Given at Springfield", "on 30 December 2022.",
                 "Master of Arts", "(Specialization in Poetry)"):
        assert text in html


def test_certificate_leaves_out_blank_identity_and_date():
    html = C.fill_template("report_templates", "degree.html", _certificate_data())
    assert "Given at" not in html and "<h1" not in html
    assert 'font-size: 32px;">on ' not in html


def test_grade_sheet_uses_program_attrs_and_institute_name():
    data = {"enrollments": {"2022-I": {"courses": [], "ec": 0, "cec": 0, "sgpa": 0,
                                       "cgpa": 0}},
            "name": "Asha Rao", "entry_no": "x1", "degree": "M.TECH(POWER)",
            "degree_level": "PG", "printed_name": "Master of Technology",
            "specialisation": "Specialization in Power", "dept_name": "EE",
            "deg_type": "REG", "static_file_path": "", "institute_name": "Open University",
            "date_issue": ""}
    html = C.fill_template("report_templates", "consolidatedGradeSheetnew.html", data)
    assert "MASTER OF TECHNOLOGY IN EE (SPECIALIZATION IN POWER)" in html
    assert "OPEN%20UNIVERSITY</text>" in html
    html = C.fill_template("report_templates", "consolidatedGradeSheetnew.html",
                           {**data, "institute_name": ""})
    assert "<svg" not in html
    # characters that are special in HTML or in a URL must not cut the data: URI
    html = C.fill_template("report_templates", "consolidatedGradeSheetnew.html",
                           {**data, "institute_name": "King's #1 <College>"})
    assert "KING%26%2339%3BS%20%231%20%26lt%3BCOLLEGE%26gt%3B</text>" in html


@pytest.fixture
def html_of(monkeypatch):
    """The HTML the PDF routes would turn into a PDF."""
    import api_grades
    pages = []
    monkeypatch.setattr(api_grades, "_html_to_pdf",
                        lambda html, *a, **k: pages.append(html) or b"%PDF")
    return pages


async def _degree_certificate(client, auth, tmp_path, convocation_date):
    M.VocabItem.create(vocab="Degrees", code="MTE", label="M.Tech", attrs={
        "level": "PG", "printed_name": "Master of Technology",
        "specialisation": "Specialization in Power"})
    M.VocabItem.create(vocab="Departments", code="EE", label="Electrical Engineering")
    make_user("stu", role="STU", org_id="2022EEM1001", degree="MTE", dept_name="EE")
    make_user("aca", role="ACA")
    await auth.login("aca")
    return await client.get("/acadstack/download_degree_certifcate/2022EEM1001", query_string={
        "hi_name": "hn", "doc_sr_no": "1-2", "convocation_date": convocation_date})


async def test_degree_certificate_takes_the_convocation_date(client, auth, tmp_path, html_of):
    settings.save("institute_name", "Open University")
    settings.save("institute_place", "Springfield")
    res = await _degree_certificate(client, auth, tmp_path, "2022-12-05")
    assert (await res.get_data()).startswith(b"%PDF")
    for text in ("OPEN UNIVERSITY", "Given at Springfield", "on 5 December 2022.",
                 "Master of Technology", "(Specialization in Power)"):
        assert text in html_of[0]
    html_of.clear()
    await client.get("/acadstack/download_degree_certifcate/2022EEM1001")
    assert "December" not in html_of[0]


async def test_degree_certificate_prints_the_serial_number_as_typed(client, auth, tmp_path, html_of):
    # No thesis title: the certificate of every non-PhD student
    res = await _degree_certificate(client, auth, tmp_path, "")
    assert (await res.get_data()).startswith(b"%PDF")
    assert "Sr. No. 1-2" in html_of[0]


async def test_degree_certificate_refuses_a_bad_convocation_date(client, auth, tmp_path, html_of):
    res = await _degree_certificate(client, auth, tmp_path, "5-Dec-2022")
    body = await res.get_json()
    assert body["status"] == "ERROR" and "convocation date" in body["body"]
    assert html_of == []


async def test_degree_certificate_uses_the_template_in_the_upload_folder(
        client, auth, tmp_path, html_of):
    (tmp_path / "report_templates").mkdir()
    (tmp_path / "report_templates" / "degree.html").write_text(
        "{{institute_name}} awards {{name}} on {{convocation_date}}")
    settings.save("institute_name", "Open University")
    await _degree_certificate(client, auth, tmp_path, "2022-12-05")
    assert html_of == ["Open University awards Stu User on 5 December 2022"]


async def test_semester_grade_sheet_prints_the_session_and_program_as_named(
        client, auth, html_of, grading_schemes):
    M.VocabItem.create(vocab="Degrees", code="BA", label="B.A.", attrs={
        "level": "UG", "printed_name": "Bachelor of Arts"})
    stu = make_user("stu", role="STU", org_id="x1", degree="BA", year_of_entry="2027")
    enrol(stu, make_offering(acad_session="Fall 2027", status="F"), grade="A")
    make_user("aca", role="ACA")
    await auth.login("aca")
    await client.get("/acadstack/download_sem_grade/Fall 2027/x1/C")
    assert "Fall 2027" in html_of[0] and "BACHELOR OF ARTS IN" in html_of[0]
    assert "SEMESTER OF ACADEMIC YEAR" not in html_of[0]


def test_grade_sheet_prints_session_codes_as_named():
    data = {"enrollments": {"Fall 2027": {"courses": [], "ec": 0, "cec": 0, "sgpa": 0,
                                          "cgpa": 0}},
            "name": "Asha Rao", "entry_no": "x1", "degree": "BA", "degree_level": "UG",
            "printed_name": "Bachelor of Arts", "specialisation": "", "dept_name": "",
            "deg_type": "", "static_file_path": "", "institute_name": "", "date_issue": ""}
    html = C.fill_template("report_templates", "consolidatedGradeSheetnew.html", data)
    assert html.count("Fall 2027") == 2  # the row and the graduation note
    assert "Sem-" not in html and "ACADEMIC YEAR" not in html
