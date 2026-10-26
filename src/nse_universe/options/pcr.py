from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
from typing import Iterable
from nse_universe.options.models import OptionContract

@dataclass(frozen=True, slots=True)
class PCRResult:
    put_oi: int
    call_oi: int
    pcr: float | None
    scope: str
    contract_count: int
    reason_unavailable: str | None = None

def calculate_pcr(contracts: Iterable[OptionContract], *, scope: str = "supplied_chain") -> PCRResult:
    items = tuple(contracts)
    if not scope.strip(): raise ValueError("scope must not be empty")
    if not items: return PCRResult(0, 0, None, scope, 0, "no contracts supplied")
    puts = sum(c.open_interest for c in items if c.option_type == "PE")
    calls = sum(c.open_interest for c in items if c.option_type == "CE")
    if calls == 0: return PCRResult(puts, calls, None, scope, len(items), "call OI is zero; PCR is undefined")
    ratio = puts / calls
    return PCRResult(puts, calls, ratio if isfinite(ratio) else None, scope, len(items))

def find_atm_strike(spot_price: float, strikes: Iterable[float]) -> float:
    if isinstance(spot_price, bool) or not isinstance(spot_price, (int, float)) or not isfinite(spot_price) or spot_price <= 0:
        raise ValueError("spot_price must be a finite positive number")
    values = set()
    for strike in strikes:
        if isinstance(strike, bool) or not isinstance(strike, (int, float)) or not isfinite(strike) or strike <= 0:
            raise ValueError("strikes must be finite positive numbers")
        values.add(float(strike))
    if not values: raise ValueError("at least one strike is required")
    return min(values, key=lambda value: (abs(value - float(spot_price)), value))

def calculate_atm_pcr(contracts: Iterable[OptionContract], *, spot_price: float) -> PCRResult:
    items = tuple(contracts)
    atm = find_atm_strike(spot_price, (c.strike for c in items))
    return calculate_pcr((c for c in items if c.strike == atm), scope=f"ATM strike {atm:g}")

def calculate_nearby_pcr(contracts: Iterable[OptionContract], *, spot_price: float, strike_count_each_side: int = 2) -> PCRResult:
    if isinstance(strike_count_each_side, bool) or not isinstance(strike_count_each_side, int) or strike_count_each_side < 0:
        raise ValueError("strike_count_each_side must be a non-negative integer")
    items = tuple(contracts)
    atm = find_atm_strike(spot_price, (c.strike for c in items))
    strikes = sorted({c.strike for c in items})
    index = strikes.index(atm)
    lo, hi = max(0, index-strike_count_each_side), min(len(strikes), index+strike_count_each_side+1)
    chosen = set(strikes[lo:hi])
    return calculate_pcr((c for c in items if c.strike in chosen), scope=f"nearby strikes {strikes[lo]}–{strikes[hi-1]} around ATM {atm:g}")
