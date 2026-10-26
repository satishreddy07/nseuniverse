"""Snapshot-to-snapshot OI comparisons and cautious price/OI quadrant labels."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from nse_universe.options.models import OptionChainSnapshot, OptionContract

@dataclass(frozen=True, slots=True)
class OIChange:
    strike: float
    option_type: str
    previous_oi: int
    current_oi: int
    change_in_oi: int
    previous_price: float | None
    current_price: float | None
    price_change: float | None

@dataclass(frozen=True, slots=True)
class OIComparison:
    underlying: str
    previous_at: datetime
    current_at: datetime
    changes: tuple[OIChange, ...]
    missing_from_current: tuple[tuple[float, str], ...]
    new_in_current: tuple[tuple[float, str], ...]

def compare_open_interest(previous: OptionChainSnapshot, current: OptionChainSnapshot) -> OIComparison:
    if previous.underlying != current.underlying:
        raise ValueError("snapshots must refer to the same underlying")
    if current.observed_at <= previous.observed_at:
        raise ValueError("current snapshot must be later than previous snapshot")
    old = {(c.strike,c.option_type): c for c in previous.contracts}
    new = {(c.strike,c.option_type): c for c in current.contracts}
    changes = tuple(_make_change(old[k],new[k]) for k in sorted(old.keys() & new.keys()))
    return OIComparison(current.underlying,previous.observed_at,current.observed_at,changes,
                        tuple(sorted(old.keys()-new.keys())),tuple(sorted(new.keys()-old.keys())))

def classify_price_oi_quadrant(price_change: float, oi_change: int) -> str:
    """Contract-level heuristic only; option-premium quadrants are not an underlying signal."""
    if isinstance(price_change,bool) or not isinstance(price_change,(int,float)):
        raise ValueError("price_change must be numeric")
    if price_change>0 and oi_change>0: return "long_buildup"
    if price_change<0 and oi_change>0: return "short_buildup"
    if price_change>0 and oi_change<0: return "short_covering"
    if price_change<0 and oi_change<0: return "long_unwinding"
    return "unchanged_or_ambiguous"

def _make_change(previous: OptionContract,current: OptionContract) -> OIChange:
    delta = None if previous.last_price is None or current.last_price is None else current.last_price-previous.last_price
    return OIChange(current.strike,current.option_type,previous.open_interest,current.open_interest,
                    current.open_interest-previous.open_interest,previous.last_price,current.last_price,delta)
