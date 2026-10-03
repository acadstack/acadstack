"""Tests for an offering's evaluation components (``/eval_components``,
``/eval_components_save``) and their columns in the grades CSV download."""

import pytest

import models as M
from conftest import enrol, make_offering, make_user


@pytest.fixture
def setup(db):
    ins = make_user("ins", role="FAC")
    co = make_offering(status="R", instructor=ins)
    M.Course.update(evaluation={"mse": "30", "ese": "50", "hwa": "20", "qui": "0"}).execute()
    return {"ins": ins, "co": co}


async def get_comps(client, co_id):
    return await (await client.get(f"/acadstack/eval_components/{co_id}")).get_json()


async def save(client, co_id, components):
    res = await client.post("/acadstack/eval_components_save",
                            json={"course_offering": co_id, "components": components})
    return await res.get_json()


async def test_defaults_come_from_the_course_evaluation_plan(client, auth, setup):
    await auth.login("ins")
    body = await get_comps(client, setup["co"].id)
    assert body["status"] == "OK"
    assert body["body"] == {"saved": False, "components": [
        {"code": "MSE", "label": "Mid-Sem Written Exam", "weight": 30.0},
        {"code": "ESE", "label": "End-Sem Written Exam", "weight": 50.0},
        {"code": "HWA", "label": "Homework/Assignments", "weight": 20.0}]}
    assert M.EvalComponent.select().count() == 0


async def test_coordinator_saves_components_unrelated_to_the_course_plan(client, auth, setup):
    await auth.login("ins")
    body = await save(client, setup["co"].id, [
        {"code": "lab_1", "label": "Lab 1", "weight": 15},
        {"code": "Viva", "label": "Viva voce", "weight": ""}])
    assert body["status"] == "OK"
    assert body["body"] == {"saved": True, "components": [
        {"code": "LAB_1", "label": "Lab 1", "weight": 15.0},
        {"code": "VIVA", "label": "Viva voce", "weight": None}]}
    assert (await get_comps(client, setup["co"].id))["body"] == body["body"]


async def test_save_replaces_the_list(client, auth, setup):
    await auth.login("ins")
    await save(client, setup["co"].id, [{"code": "A", "label": "A"}, {"code": "B", "label": "B"}])
    body = await save(client, setup["co"].id, [{"code": "B", "label": "Bee", "weight": 40}])
    assert body["body"]["components"] == [{"code": "B", "label": "Bee", "weight": 40.0}]


@pytest.mark.parametrize("comps, msg", [
    ([{"code": "MSE", "label": "x"}, {"code": "mse", "label": "y"}], "repeated"),
    ([{"code": "MID SEM", "label": "x"}], "Invalid component code"),
    ([{"code": "ABCDEFGHIJK", "label": "x"}], "Invalid component code"),
    ([{"code": "GRADE", "label": "x"}], "column of the grades CSV"),
    ([{"code": "MSE", "label": ""}], "give a name"),
    ([{"code": "MSE", "label": "x", "weight": 120}], "between 0 and 100"),
])
async def test_invalid_components_rejected(client, auth, setup, comps, msg):
    await auth.login("ins")
    body = await save(client, setup["co"].id, comps)
    assert body["status"] == "ERROR" and msg in body["body"]
    assert M.EvalComponent.select().count() == 0


async def test_non_coordinator_cannot_save(client, auth, setup):
    other = make_user("other", role="FAC")
    M.CourseInstructor.create(offering=setup["co"], instructor=other, is_coordinator=False)
    await auth.login("other")
    body = await save(client, setup["co"].id, [{"code": "MSE", "label": "x"}])
    assert body["status"] == "ERROR" and "coordinator" in body["body"]


async def test_component_with_scores_cannot_be_removed(client, auth, setup):
    ec = M.EvalComponent.create(offering=setup["co"], code="MSE", label="Mid-sem")
    ce = enrol(make_user("s1", org_id="2024CSB1001"), setup["co"])
    M.EvalScore.create(enrolment=ce, component=ec, score=50)
    await auth.login("ins")
    body = await save(client, setup["co"].id, [{"code": "ESE", "label": "End-sem"}])
    assert body["status"] == "ERROR" and "has scores" in body["body"]
    assert [c.code for c in M.EvalComponent.select()] == ["MSE"]


async def test_grades_download_has_the_requested_component_columns(client, auth, setup):
    mse = M.EvalComponent.create(offering=setup["co"], code="MSE", label="Mid-sem")
    M.EvalComponent.create(offering=setup["co"], code="LAB", label="Lab")
    ce1 = enrol(make_user("s1", org_id="2024CSB1001"), setup["co"], grade="A")
    enrol(make_user("s2", org_id="2024CSB1002"), setup["co"])
    M.EvalScore.create(enrolment=ce1, component=mse, score=72.5)
    await auth.login("ins")
    res = await client.get(f"/acadstack/download_enrollments_for_grades/{setup['co'].id}"
                           "?components=mse,lab")
    lines = (await res.get_data(as_text=True)).splitlines()
    assert lines[0].lower() == "first_name,last_name,roll_no,grade,code,mse,lab"
    assert lines[1].endswith("2024CSB1001,A,CS101,72.5,")
    assert lines[2].endswith("2024CSB1002,NA,CS101,,")
