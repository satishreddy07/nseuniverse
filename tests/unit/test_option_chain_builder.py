from datetime import datetime, timedelta, timezone
from nse_universe.providers.instrument_master import Instrument
from nse_universe.providers.kotak_neo import NormalizedTick
from nse_universe.providers.option_chain_builder import OptionChainSnapshotBuilder
from nse_universe.providers.tick_cache import TickCache


def test_builds_complete_chain_from_fresh_oi_ticks():
    now = datetime(2026, 10, 26, 9, 15, tzinfo=timezone.utc)
    instruments = [
        Instrument("1", "nse_fo", "NIFTY26000CE", strike=26000, option_type="CE"),
        Instrument("2", "nse_fo", "NIFTY26000PE", strike=26000, option_type="PE"),
    ]
    builder = OptionChainSnapshotBuilder(instruments, underlying="NIFTY")
    cache = TickCache(max_age_seconds=5)
    cache.update(NormalizedTick("1", "nse_fo", 120, now, open_interest=1000, volume=500))
    cache.update(NormalizedTick("2", "nse_fo", 110, now, open_interest=1200, volume=600))
    snapshot = builder.build(cache, spot_price=26010, observed_at=now, now=now, max_age_seconds=5)
    assert snapshot.complete is True
    assert len(snapshot.contracts) == 2
    assert {contract.option_type for contract in snapshot.contracts} == {"CE", "PE"}
    assert {contract.open_interest for contract in snapshot.contracts} == {1000, 1200}


def test_missing_stale_or_oi_less_tick_marks_chain_incomplete():
    now = datetime(2026, 10, 26, 9, 15, tzinfo=timezone.utc)
    instruments = [
        Instrument("1", "nse_fo", "NIFTY26000CE", strike=26000, option_type="CE"),
        Instrument("2", "nse_fo", "NIFTY26000PE", strike=26000, option_type="PE"),
    ]
    builder = OptionChainSnapshotBuilder(instruments, underlying="NIFTY")
    cache = TickCache(max_age_seconds=5)
    cache.update(NormalizedTick("1", "nse_fo", 120, now - timedelta(seconds=20), open_interest=1000))
    cache.update(NormalizedTick("2", "nse_fo", 110, now, open_interest=None))
    snapshot = builder.build(cache, spot_price=26010, observed_at=now, now=now, max_age_seconds=5)
    assert snapshot.complete is False
    assert snapshot.contracts == ()
