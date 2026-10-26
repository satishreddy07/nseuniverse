from datetime import datetime, timedelta, timezone
from nse_universe.providers.kotak_neo import NormalizedTick
from nse_universe.providers.tick_cache import TickCache

def tick(token, received_at):
    return NormalizedTick(token, "nse_fo", 100.0, received_at)

def test_cache_reports_fresh_stale_and_missing_ticks():
    now = datetime(2026, 10, 26, 9, 15, tzinfo=timezone.utc)
    cache = TickCache(max_age_seconds=5)
    cache.update(tick("1", now - timedelta(seconds=2)))
    cache.update(tick("2", now - timedelta(seconds=8)))
    assert not cache.status("nse_fo", "1", now=now).stale
    assert cache.status("nse_fo", "2", now=now).stale
    missing = cache.status("nse_fo", "3", now=now)
    assert missing.stale and missing.last_tick is None
    assert {x.instrument_token for x in cache.stale_or_missing([("nse_fo", "1"), ("nse_fo", "2"), ("nse_fo", "3")], now=now)} == {"2", "3"}

def test_cache_does_not_overwrite_with_older_received_tick():
    now = datetime(2026, 10, 26, 9, 15, tzinfo=timezone.utc)
    cache = TickCache()
    cache.update(tick("1", now))
    cache.update(tick("1", now - timedelta(seconds=1)))
    assert cache.latest("nse_fo", "1").received_at == now
