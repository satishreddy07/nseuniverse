"""In-memory latest-tick cache and freshness checks for live dashboards."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable
from nse_universe.providers.kotak_neo import NormalizedTick
from nse_universe.validation.market_data import age_seconds

@dataclass(frozen=True, slots=True)
class TickStatus:
    instrument_token: str
    exchange_segment: str
    age_seconds: float | None
    stale: bool
    last_tick: NormalizedTick | None

class TickCache:
    """Keep only latest ticks and report stale/missing subscriptions explicitly."""
    def __init__(self, *, max_age_seconds: float = 5.0) -> None:
        if max_age_seconds < 0:
            raise ValueError("max_age_seconds must be non-negative")
        self.max_age_seconds = float(max_age_seconds)
        self._ticks: dict[tuple[str, str], NormalizedTick] = {}

    def update(self, tick: NormalizedTick) -> None:
        key = (tick.exchange_segment, tick.instrument_token)
        current = self._ticks.get(key)
        # Prevent an out-of-order packet from overwriting a newer receive-time tick.
        if current is None or tick.received_at >= current.received_at:
            self._ticks[key] = tick

    def latest(self, exchange_segment: str, token: str) -> NormalizedTick | None:
        return self._ticks.get((exchange_segment, str(token)))

    def status(self, exchange_segment: str, token: str, *, now: datetime, max_age_seconds: float | None = None) -> TickStatus:
        tick = self.latest(exchange_segment, token)
        if tick is None:
            return TickStatus(str(token), exchange_segment, None, True, None)
        age = age_seconds(tick.received_at, now=now)
        return TickStatus(str(token), exchange_segment, age, age > self.max_age_seconds, tick)

    def stale_or_missing(self, subscriptions: Iterable[tuple[str, str]], *, now: datetime, max_age_seconds: float | None = None) -> tuple[TickStatus, ...]:
        return tuple(status for segment, token in subscriptions
                     if (status := self.status(segment, token, now=now, max_age_seconds=max_age_seconds)).stale)
