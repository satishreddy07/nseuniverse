"""Minimal normalized market-data contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from nse_universe.validation.market_data import require_aware_datetime, require_finite_number

QualityStatus = Literal["ok", "partial", "stale", "invalid"]


@dataclass(frozen=True, slots=True)
class MarketObservation:
    instrument: str
    value: float
    source: str
    received_at: datetime
    exchange_timestamp: datetime | None = None
    quality: QualityStatus = "ok"

    def __post_init__(self) -> None:
        if not self.instrument.strip():
            raise ValueError("instrument must not be empty")
        if not self.source.strip():
            raise ValueError("source must not be empty")
        object.__setattr__(self, "value", require_finite_number(self.value, field_name="value"))
        require_aware_datetime(self.received_at, field_name="received_at")
        if self.exchange_timestamp is not None:
            require_aware_datetime(self.exchange_timestamp, field_name="exchange_timestamp")
        if self.quality not in ("ok", "partial", "stale", "invalid"):
            raise ValueError("quality must be one of: ok, partial, stale, invalid")
