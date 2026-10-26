from datetime import datetime, timezone

import pytest

from nse_universe.market_data.models import MarketObservation


def test_valid_observation_preserves_source_and_timestamps():
    ts = datetime(2026, 1, 1, 9, 15, tzinfo=timezone.utc)
    item = MarketObservation("NIFTY-FUT", 25000.5, "fixture", ts, ts)
    assert item.instrument == "NIFTY-FUT"
    assert item.value == 25000.5
    assert item.exchange_timestamp == ts
    assert item.quality == "ok"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), True])
def test_invalid_numeric_observation_is_rejected(value):
    ts = datetime(2026, 1, 1, 9, 15, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="finite number"):
        MarketObservation("NIFTY-FUT", value, "fixture", ts)


def test_naive_receive_timestamp_is_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        MarketObservation("NIFTY-FUT", 100.0, "fixture", datetime(2026, 1, 1, 9, 15))


def test_missing_exchange_timestamp_stays_missing():
    ts = datetime(2026, 1, 1, 9, 15, tzinfo=timezone.utc)
    assert MarketObservation("NIFTY-FUT", 100.0, "fixture", ts).exchange_timestamp is None
