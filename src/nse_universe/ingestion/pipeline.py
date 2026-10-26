"""Validate, persist, and summarize normalized option-chain snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from nse_universe.history.sqlite_store import SQLiteOptionSnapshotStore
from nse_universe.options.models import OptionChainSnapshot
from nse_universe.options.oi_trends import OITrendReport, summarize_oi_trends
from nse_universe.validation.market_data import age_seconds


@dataclass(frozen=True, slots=True)
class IngestionResult:
    snapshot_id: int
    underlying: str
    observed_at: datetime
    age_seconds: float
    stored: bool
    trend_report: OITrendReport | None
    warnings: tuple[str, ...]


class OptionSnapshotIngestor:
    """Ingest normalized snapshots supplied by any broker/provider adapter.

    This class deliberately does not log in to a broker or parse provider-specific
    payloads. The adapter should normalize and validate broker messages into an
    OptionChainSnapshot before calling ingest().
    """

    def __init__(
        self,
        store: SQLiteOptionSnapshotStore,
        *,
        max_age_seconds: float = 10.0,
        history_window: int = 20,
        top_n: int = 5,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if max_age_seconds < 0:
            raise ValueError("max_age_seconds must be non-negative")
        if history_window < 2:
            raise ValueError("history_window must be at least 2")
        if top_n < 1:
            raise ValueError("top_n must be positive")
        self.store = store
        self.max_age_seconds = float(max_age_seconds)
        self.history_window = int(history_window)
        self.top_n = int(top_n)
        self.clock = clock or (lambda: datetime.now().astimezone())

    def ingest(self, snapshot: OptionChainSnapshot) -> IngestionResult:
        now = self.clock()
        age = age_seconds(snapshot.observed_at, now=now)
        warnings: list[str] = []
        if age > self.max_age_seconds:
            warnings.append(
                f"Snapshot is stale ({age:.2f}s old; limit {self.max_age_seconds:.2f}s)."
            )
        if not snapshot.complete:
            warnings.append("Snapshot is marked incomplete; aggregate metrics may be understated.")

        # Store raw normalized evidence even if stale so it can be audited/replayed.
        # The caller must heed warnings and must not treat stale snapshots as live signals.
        snapshot_id = self.store.save(snapshot)
        recent = self.store.recent(snapshot.underlying, limit=self.history_window)
        report = None
        if len(recent) >= 2:
            report = summarize_oi_trends(recent, top_n=self.top_n)
            warnings.extend(report.warnings)
        else:
            warnings.append("Trend report unavailable until at least two snapshots exist.")
        return IngestionResult(
            snapshot_id=snapshot_id,
            underlying=snapshot.underlying,
            observed_at=snapshot.observed_at,
            age_seconds=age,
            stored=True,
            trend_report=report,
            warnings=tuple(dict.fromkeys(warnings)),
        )
