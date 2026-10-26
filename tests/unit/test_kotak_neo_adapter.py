from datetime import datetime, timezone
import asyncio
import pytest
from nse_universe.providers.kotak_neo import KotakNeoAdapter, KotakNeoConfig, NormalizedTick

def config():
    return KotakNeoConfig(consumer_key="test-key", mobile_number="+910000000000", ucc="TESTUCC", mpin="000000")

def test_normalize_sdk_style_message():
    now = datetime(2026, 10, 26, 9, 15, tzinfo=timezone.utc)
    tick = KotakNeoAdapter.normalize_message({
        "instrument_token": "12345", "exchange_segment": "nse_fo", "trading_symbol": "NIFTY26OCT26000CE",
        "last_traded_price": "125.5", "last_traded_quantity": "25", "volume": "2500", "open_interest": "40000",
        "exchange_timestamp": "2026-10-26T09:14:59+00:00",
    }, received_at=now)
    assert tick.instrument_token == "12345"
    assert tick.exchange_segment == "nse_fo"
    assert tick.last_traded_price == 125.5
    assert tick.volume == 2500
    assert tick.open_interest == 40000
    assert tick.received_at == now
    assert tick.exchange_timestamp == datetime(2026, 10, 26, 9, 14, 59, tzinfo=timezone.utc)

def test_normalize_rejects_missing_price_and_instrument():
    with pytest.raises(ValueError, match="last traded price"):
        KotakNeoAdapter.normalize_message({"instrument_token": "1", "exchange_segment": "nse_fo"})
    with pytest.raises(ValueError, match="instrument token"):
        KotakNeoAdapter.normalize_message({"ltp": 10})

def test_tick_validates_nonnegative_optional_fields_and_aware_time():
    with pytest.raises(ValueError, match="non-negative"):
        NormalizedTick("1", "nse_fo", 10, datetime.now(timezone.utc), volume=-1)
    with pytest.raises(ValueError, match="timezone-aware"):
        NormalizedTick("1", "nse_fo", 10, datetime(2026, 1, 1))

def test_stream_requires_authentication():
    adapter = KotakNeoAdapter(config(), client=object())
    async def run():
        async for _ in adapter.stream([("nse_fo", "1")]):
            pass
    with pytest.raises(RuntimeError, match="authenticate"):
        asyncio.run(run())

def test_config_from_env_requires_all_secrets(monkeypatch):
    for name in ("KOTAK_NEO_CONSUMER_KEY", "KOTAK_NEO_MOBILE_NUMBER", "KOTAK_NEO_UCC", "KOTAK_NEO_MPIN"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ValueError, match="KOTAK_NEO_CONSUMER_KEY"):
        KotakNeoConfig.from_env()


def test_normalizes_official_sfeed_aliases_depth_and_epoch_timestamp():
    now = datetime(2026, 10, 26, 9, 15, tzinfo=timezone.utc)
    tick = KotakNeoAdapter.normalize_message({
        "instrument_token": "44", "exchange_segment": "nse_fo", "trading_symbol": "NIFTYCE",
        "last_traded_price": 110, "last_trade_qty": 15, "volume_traded_today": 1000,
        "last_update_time": 1793006090, "open_interest": 5000,
        "total_buy_quantity": 1200, "total_sell_quantity": 900,
        "buy": [{"price": 109.5, "quantity": 30, "orders": 2}],
        "sell": [{"price": 110.0, "quantity": 25, "orders": 1}],
    }, received_at=now)
    assert tick.last_traded_quantity == 15
    assert tick.volume == 1000
    assert tick.total_buy_quantity == 1200
    assert tick.best_bid_price == 109.5
    assert tick.best_bid_quantity == 30
    assert tick.best_ask_price == 110
    assert tick.best_ask_quantity == 25
    assert tick.exchange_timestamp == datetime.fromtimestamp(1793006090, tz=timezone.utc)
