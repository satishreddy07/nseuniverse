"""Transparent OI trend summaries across a chronological snapshot window."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from nse_universe.options.models import OptionChainSnapshot
from nse_universe.options.oi_analysis import compare_open_interest


@dataclass(frozen=True, slots=True)
class ContractOITrend:
    strike: float
    option_type: str
    first_oi: int
    latest_oi: int
    net_change: int
    observations: int


@dataclass(frozen=True, slots=True)
class OITrendReport:
    underlying: str
    start_at: datetime
    end_at: datetime
    snapshot_count: int
    complete_snapshot_count: int
    call_oi_change: int
    put_oi_change: int
    pcr_start: float | None
    pcr_latest: float | None
    top_call_additions: tuple[ContractOITrend, ...]
    top_put_additions: tuple[ContractOITrend, ...]
    top_call_unwinding: tuple[ContractOITrend, ...]
    top_put_unwinding: tuple[ContractOITrend, ...]
    warnings: tuple[str, ...]


def summarize_oi_trends(
    snapshots: tuple[OptionChainSnapshot, ...] | list[OptionChainSnapshot],
    *,
    top_n: int = 5,
) -> OITrendReport:
    """Summarize net OI changes over a window; input must be chronological.

    PCR values are total OI PCRs for the supplied snapshot, not necessarily the
    exchange-wide PCR. Callers must confirm chain coverage before interpreting them.
    """
    data = tuple(snapshots)
    if len(data) < 2:
        raise ValueError("at least two snapshots are required")
    if isinstance(top_n, bool) or not isinstance(top_n, int) or top_n < 1:
        raise ValueError("top_n must be a positive integer")
    underlying = data[0].underlying
    if any(s.underlying != underlying for s in data):
        raise ValueError("all snapshots must refer to the same underlying")
    if any(data[i].observed_at >= data[i + 1].observed_at for i in range(len(data) - 1)):
        raise ValueError("snapshots must be strictly chronological")

    first, latest = data[0], data[-1]
    first_map = {(c.strike, c.option_type): c for c in first.contracts}
    latest_map = {(c.strike, c.option_type): c for c in latest.contracts}
    trends = []
    for key in sorted(first_map.keys() & latest_map.keys()):
        a, b = first_map[key], latest_map[key]
        trends.append(ContractOITrend(key[0], key[1], a.open_interest, b.open_interest,
                                      b.open_interest - a.open_interest, len(data)))
    calls = sum(c.open_interest for c in first.contracts if c.option_type == "CE")
    puts = sum(c.open_interest for c in first.contracts if c.option_type == "PE")
    calls_end = sum(c.open_interest for c in latest.contracts if c.option_type == "CE")
    puts_end = sum(c.open_interest for c in latest.contracts if c.option_type == "PE")
    warnings = []
    if not all(s.complete for s in data):
        warnings.append("One or more snapshots are marked incomplete; totals may be understated.")
    if first_map.keys() != latest_map.keys():
        warnings.append("Contract coverage differs between the first and latest snapshots; "
                        "per-contract trends include only contracts present in both.")
    if calls == 0:
        pcr_start = None
        warnings.append("Starting PCR unavailable because starting call OI is zero.")
    else:
        pcr_start = puts / calls
    pcr_latest = puts_end / calls_end if calls_end else None
    if calls_end == 0:
        warnings.append("Latest PCR unavailable because latest call OI is zero.")
    if len(data) > 2:
        # Ensure there are no skipped/duplicate interval timestamps; actual cadence is provider-specific.
        warnings.append("Snapshot cadence is provider-defined; gaps are not inferred or interpolated.")
    return OITrendReport(
        underlying=underlying, start_at=first.observed_at, end_at=latest.observed_at,
        snapshot_count=len(data), complete_snapshot_count=sum(s.complete for s in data),
        call_oi_change=calls_end-calls, put_oi_change=puts_end-puts,
        pcr_start=pcr_start, pcr_latest=pcr_latest,
        top_call_additions=_rank(trends, "CE", positive=True, limit=top_n),
        top_put_additions=_rank(trends, "PE", positive=True, limit=top_n),
        top_call_unwinding=_rank(trends, "CE", positive=False, limit=top_n),
        top_put_unwinding=_rank(trends, "PE", positive=False, limit=top_n),
        warnings=tuple(warnings),
    )


def _rank(
    trends: list[ContractOITrend], option_type: str, *, positive: bool, limit: int
) -> tuple[ContractOITrend, ...]:
    selected = [t for t in trends if t.option_type == option_type
                and (t.net_change > 0 if positive else t.net_change < 0)]
    selected.sort(key=lambda t: (-t.net_change if positive else t.net_change, t.strike))
    return tuple(selected[:limit])
