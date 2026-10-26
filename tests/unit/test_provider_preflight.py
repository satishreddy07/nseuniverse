from datetime import datetime, timezone

import pytest

from nse_universe.providers.instrument_master import Instrument, InstrumentMaster
from nse_universe.providers.preflight import resolve_instruments
from nse_universe.providers.tick_cache import TickCache
from nse_universe.providers.kotak_neo import NormalizedTick


def master():
    return InstrumentMaster([
        Instrument("101", "nse_fo", "NIFTY26OCTFUT", instrument_type="FUTIDX", expiry="2026-10-29"),
        Instrument("102", "nse_cm", "NIFTY 50", instrument_type="INDEX"),
    ])


def test_resolve_exact_symbols_across_segments():
    selected = resolve_instruments(master(), ["nse_fo:NIFTY26OCTFUT", "nse_cm:NIFTY 50"])
    assert [item.token for item in selected] == ["101", "102"]


def test_resolve_requires_exact_valid_and_unique_symbols():
    with pytest.raises(ValueError, match="exact symbol"):
        resolve_instruments(master(), ["nse_fo:NIFTY"])
    with pytest.raises(ValueError, match="Duplicate"):
        resolve_instruments(master(), ["nse_fo:NIFTY26OCTFUT", "nse_fo:NIFTY26OCTFUT"])
    with pytest.raises(ValueError, match="SEGMENT:SYMBOL"):
        resolve_instruments(master(), ["NIFTY26OCTFUT"])


def test_cache_preflight_freshness_contract():
    now = datetime(2026, 10, 26, 9, 15, tzinfo=timezone.utc)
    cache = TickCache(max_age_seconds=5)
    tick = NormalizedTick("101", "nse_fo", 25000, now, trading_symbol="NIFTY26OCTFUT")
    cache.update(tick)
    assert not cache.status("nse_fo", "101", now=now, max_age_seconds=5).stale
    assert cache.status("nse_cm", "102", now=now, max_age_seconds=5).stale
