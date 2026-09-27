"""PDF report routes. Rendering needs WeasyPrint's system libraries (Pango);
these tests are skipped where they are missing."""

import pytest

from conftest import enrol, make_offering, make_user

try:
    import weasyprint  # noqa: F401
except OSError:
    pytest.skip("WeasyPrint system libraries (Pango) not installed", allow_module_level=True)


async def test_semester_grade_sheet_pdf(client, auth):
    stu = make_user("stu", role="STU", org_id="2023CSB1001", degree="BTE",
                    year_of_entry="2023", deg_type_spec="MCBME")
    enrol(stu, make_offering(acad_session="2024-I", status="F"), grade="A")
    make_user("aca", role="ACA")
    await auth.login("aca")
    res = await client.get("/acadstack/download_sem_grade/2024-I/2023CSB1001/C")
    assert res.status_code == 200
    data = await res.get_data()
    assert data.startswith(b"%PDF")
