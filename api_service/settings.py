"""The known settings, their defaults, and the checks their values must pass.

A setting with no row in the Setting table has its default. Values are cached
in this process (the app runs as a single process); saving a value clears the
cache, so a value changed directly with SQL is seen after a restart.
"""

import logging

import common as C
import models as M


def _int_between(lo, hi):
    return lambda v: type(v) is int and lo <= v <= hi


def _codes(list_name):
    return {e["id"] for e in C.static_data_json().get(list_name, []) if e["id"]}


def _label_overrides_valid(v):
    # {list: {code: label}} for the workflow lists of static_data.json
    return type(v) is dict and all(
        type(labels) is dict and labels.keys() <= _codes(lst) and
        all(type(l) is str and l.strip() for l in labels.values())
        for lst, labels in v.items())


_SCHEME_KEYS = {"name", "level", "from_session", "until_session", "grades"}
_GRADE_FLAGS = {"earns_credit", "in_cgpa", "credit_without_gpa", "excluded_from_gpa",
                "allowed_for_audit"}


def _grade_valid(g):
    # Grades are stored in a 2-character column, upper case as uploaded.
    return (type(g) is dict and g.keys() == {"grade", "points"} | _GRADE_FLAGS and
            type(g["grade"]) is str and 1 <= len(g["grade"]) <= 2 and
            g["grade"] == g["grade"].strip().upper() and g["grade"] != C.NO_GRADE and
            (g["points"] is None or (type(g["points"]) in (int, float) and g["points"] >= 0)) and
            all(type(g[f]) is bool for f in _GRADE_FLAGS))


def _grading_schemes_valid(v):
    # The shape only; the session ranges are checked when the setting is saved
    # (api_common.check_grading_schemes).
    from api_common import VOCAB_ATTRS
    return type(v) is list and all(
        type(s) is dict and s.keys() == _SCHEME_KEYS and
        type(s["name"]) is str and s["name"].strip() and
        s["level"] in VOCAB_ATTRS["Degrees"]["level"] and
        all(c is None or (type(c) is str and c) for c in (s["from_session"], s["until_session"])) and
        type(s["grades"]) is list and s["grades"] and all(_grade_valid(g) for g in s["grades"]) and
        len({g["grade"] for g in s["grades"]}) == len(s["grades"])
        for s in v)


# key: (default, check, description)
SETTINGS = {
    "max_credits": (24, _int_between(1, 100),
                    "Most credits a student may enrol for in a session."),
    "face_match_tolerance": (0.45, lambda v: type(v) in (int, float) and 0 < v <= 1,
                             "Face-match tolerance for photo attendance; lower is stricter."),
    "lockout_limit": (5, _int_between(1, 100),
                      "Wrong password-reset keys (and keys issued) per login before lockout."),
    "page_size": (25, _int_between(1, 500),
                  "Rows per page in search results."),
    "fees_check_enabled": (True, lambda v: type(v) is bool,
                           "Students must submit fee payment details before enrolling."),
    "label_overrides": ({}, _label_overrides_valid,
                        "Labels shown for workflow codes, as {list: {code: label}}."),
    # Credit ("C") stays offered: bulk enrolment creates credit enrolments.
    "hidden_enrol_types": ([], lambda v: type(v) is list and all(
                               type(c) is str and c in _codes("EnrolTypes") - {"C"} for c in v),
                           "Enrolment types that are not offered."),
    "grading_schemes": ([], _grading_schemes_valid,
                        "Grades and their rules, per program level and range of sessions."),
}

_cache = {}


def get(key):
    if key not in _cache:
        default, check, _ = SETTINGS[key]
        row = M.Setting.get_or_none(M.Setting.key == key)
        value = default
        if row is not None:
            if check(row.value):
                value = row.value
            else:
                logging.error(f"Invalid stored value {row.value!r} for setting {key}; "
                              f"using the default {default!r}.")
        _cache[key] = value
    return _cache[key]


def save(key, value):
    """Stores a value after checking it. Raises ValueError if it is invalid."""
    if key not in SETTINGS:
        raise ValueError(f"Unknown setting: {key}")
    if not SETTINGS[key][1](value):
        raise ValueError(f"Invalid value for {key}: {value!r}")
    (M.Setting.insert(key=key, value=value)
        .on_conflict(conflict_target=[M.Setting.key],
                     update={M.Setting.value: value, M.Setting.upd_ts: M.DT.now(),
                             M.Setting.txn_no: M.Setting.txn_no + 1})
        .execute())
    _cache.clear()


def all_settings():
    return [{"key": k, "value": get(k), "default": d, "description": desc}
            for k, (d, _, desc) in SETTINGS.items()]
