"""Structural interfaces shared by market-data providers."""
from __future__ import annotations
from typing import AsyncIterator, Iterable, Protocol
from nse_universe.providers.kotak_neo import NormalizedTick

class MarketDataProvider(Protocol):
    """Minimal read-only provider contract consumed by analytics services."""
    def authenticate(self, *, totp: str) -> None: ...
    def stream(self, tokens: Iterable[tuple[str, str]]) -> AsyncIterator[NormalizedTick]: ...
