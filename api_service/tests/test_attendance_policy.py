"""Tests for the minimum-attendance policy (settings_store's "attendance"
group) and its exposure through static_data_dict() -- flag-only per
product decision: nothing is blocked by it, it only surfaces as
MinAttendancePercentRequired for the frontend to shade a percentage that
falls below it.
"""
import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import api_common as apiVC  # noqa: E402
import settings_store as ST  # noqa: E402
from settings_store import save_setting  # noqa: E402


def _in_request(app, fn):
    async def _run():
        async with app.test_request_context("/acadstack/"):
            return fn()
    return asyncio.run(_run())


def test_min_percent_required_has_a_sensible_default(db):
    assert ST.setting("attendance.min_percent_required") == 75.0


def test_min_percent_required_is_saveable_within_bounds(db):
    save_setting("attendance.min_percent_required", 60.0)
    assert ST.setting("attendance.min_percent_required") == 60.0


def test_min_percent_required_rejects_out_of_range_values(db):
    with pytest.raises(ST.SettingValidationError):
        save_setting("attendance.min_percent_required", 150.0)
    with pytest.raises(ST.SettingValidationError):
        save_setting("attendance.min_percent_required", -1.0)


def test_static_data_dict_exposes_the_effective_threshold(app, db):
    sd = _in_request(app, apiVC.static_data_dict)
    assert sd["MinAttendancePercentRequired"] == 75.0

    save_setting("attendance.min_percent_required", 65.0)
    sd = _in_request(app, apiVC.static_data_dict)
    assert sd["MinAttendancePercentRequired"] == 65.0
