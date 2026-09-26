"""Security/correctness fixes in shared helpers: number parsing, random
strings, the session secret key, the face-service proxy, audit timestamps
and route registration."""
import builtins
import string
from datetime import datetime as DT

import pytest
import requests

import acadstack_app
import common as C
import face_api_proxy as fapi
import models as DB
import settings_store as ST
from domain import persistence


# ===================== common.parse_number =====================

@pytest.mark.parametrize("sval, expected", [
    ("3", 3), (" 2 ", 2), ("-1", -1), ("+4", 4),
    ("1.5", 1.5), ("1.234", 1.23), ("3.", 3.0),
    ("3/2", 1.5), ("4/2", 2.0), ("1/3", 0.33),
])
def test_parse_number_accepts_int_decimal_and_fraction(sval, expected):
    assert C.parse_number(sval) == expected


@pytest.mark.parametrize("sval", [
    "", "abc", "1/0", "3/", "1e5", "nan", "inf", "1_000", "1+1",
    "__import__('os').system('echo pwned')",
    "(1).__class__.__bases__[0].__subclasses__()",
    "2**2**2**2**2",
])
def test_parse_number_rejects_non_numbers(sval):
    assert C.parse_number(sval) is None


def test_parse_number_never_evaluates_its_input(monkeypatch):
    def _no_eval(*args, **kwargs):
        raise AssertionError("parse_number must not call eval")
    monkeypatch.setattr(builtins, "eval", _no_eval)
    assert C.parse_number("3/2") == 1.5
    assert C.parse_number("7") == 7


# ===================== common.get_rand_str =====================

def test_get_rand_str_uses_secrets(monkeypatch):
    import secrets
    calls = []
    real_choice = secrets.choice
    monkeypatch.setattr(secrets, "choice",
                        lambda seq: calls.append(1) or real_choice(seq))
    s = C.get_rand_str(size=12)
    assert len(s) == 12 and len(calls) == 12
    assert set(s) <= set(string.ascii_uppercase + string.digits)


# ===================== session secret key =====================

def test_secret_key_is_read_from_config():
    assert acadstack_app._session_secret_key(
        {"secret_key": "configured-key"}) == "configured-key"


def test_secret_key_is_generated_when_not_configured():
    a = acadstack_app._session_secret_key({"secret_key": None})
    b = acadstack_app._session_secret_key({})
    assert a and b and a != b and len(a) >= 32


def test_load_config_reads_secret_key_env(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "from-env")
    assert acadstack_app._load_config_from_env()["secret_key"] == "from-env"


# ===================== face_api_proxy timeouts =====================

@pytest.fixture
def photo(tmp_path):
    p = tmp_path / "p.jpg"
    p.write_bytes(b"not really a jpeg")
    return str(p)


def _proxy_calls(photo):
    return [
        lambda: fapi.get_face_encoding(b"img"),
        lambda: fapi.get_face_encoding_b64("aW1n"),
        lambda: fapi.get_faces_from_photo(photo),
        lambda: fapi.is_person_in_photo(photo, photo, tolerance=0.5),
        lambda: fapi.find_persons_in_photo(photo, ([], []), tolerance=0.5),
        lambda: fapi.write_text_on_image(photo, "x", (0, 0)),
        lambda: fapi.mark_person_in_photo(photo, photo, tolerance=0.5),
    ]


def test_every_face_service_call_passes_the_configured_timeout(
        db, monkeypatch, photo):
    seen = []

    def _fake_post(url, **kwargs):
        seen.append(kwargs.get("timeout"))
        raise requests.Timeout()
    monkeypatch.setattr(fapi.requests, "post", _fake_post)
    expected = ST.setting("faces.request_timeout_secs")
    calls = _proxy_calls(photo)
    for call in calls:
        with pytest.raises(C.AcadStackException, match="face-recognition"):
            call()
    assert seen == [expected] * len(calls)


# ===================== persistence.save and ins_ts =====================

def test_save_sets_ins_ts_on_insert_only(db):
    obj = DB.WorkflowNote(entity_key=1, entity_name="x", note="a")
    persistence.save(obj, None)
    original = DT(2020, 1, 1, 12, 0, 0)
    DB.WorkflowNote.update(ins_ts=original).where(
        DB.WorkflowNote.id == obj.id).execute()

    reloaded = DB.WorkflowNote.get_by_id(obj.id)
    reloaded.note = "b"
    persistence.save(reloaded, None)

    after = DB.WorkflowNote.get_by_id(obj.id)
    assert after.note == "b"
    assert after.ins_ts == original


def test_save_sets_ins_ts_for_a_new_row(db):
    before = DT.now()
    obj = DB.WorkflowNote(entity_key=1, entity_name="x",
                          ins_ts=DT(2000, 1, 1))
    persistence.save(obj, None)
    assert DB.WorkflowNote.get_by_id(obj.id).ins_ts >= before


# ===================== route registration =====================

def test_no_route_is_registered_twice(app):
    seen = set()
    dups = []
    for rule in app.url_map.iter_rules():
        key = (rule.rule, rule.endpoint, frozenset(rule.methods or ()))
        if key in seen:
            dups.append(key)
        seen.add(key)
    assert not dups, dups
