from datetime import datetime, timedelta, timezone

import pytest

from nse_universe.validation.market_data import (
    age_seconds, is_finite_number, is_fresh, require_aware_datetime,
    require_finite_number, to_utc,
)


def test_finite_number_accepts_finite_values():
    assert is_finite_number(10)
    assert is_finite_number(1.25)


@pytest.mark.parametrize("value", [True, False, "1", None, float("nan"), float("inf"), -float("inf")])
def test_finite_number_rejects_invalid_values(value):
    assert not is_finite_number(value)


def test_require_finite_number_names_invalid_field():
    with pytest.raises(ValueError, match="last_price"):
        require_finite_number(float("nan"), field_name="last_price")


def test_naive_datetime_is_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        require_aware_datetime(datetime(2026, 1, 1, 9, 15))


def test_to_utc_normalizes_offset():
    local = datetime(2026, 1, 1, 9, 15, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    assert to_utc(local) == datetime(2026, 1, 1, 3, 45, tzinfo=timezone.utc)


def test_age_and_freshness_use_explicit_limit():
    now = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    observed = now - timedelta(seconds=5)
    assert age_seconds(observed, now=now) == 5
    assert is_fresh(observed, now=now, max_age_seconds=5)
    assert not is_fresh(observed, now=now, max_age_seconds=4)


def test_future_observation_is_rejected():
    now = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="future"):
        age_seconds(now + timedelta(seconds=1), now=now)
