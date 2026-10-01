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
    "hidden_enrol_types": ([], lambda v: type(v) is list and all(
                               type(c) is str and c in _codes("EnrolTypes") for c in v),
                           "Enrolment types that are not offered."),
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
