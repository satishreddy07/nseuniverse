"""Validated immutable contracts for normalized option-chain snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from nse_universe.validation.market_data import require_aware_datetime, require_finite_number

OptionType = Literal["CE", "PE"]


@dataclass(frozen=True, slots=True)
class OptionContract:
    strike: float
    option_type: OptionType
    open_interest: int
    observed_at: datetime
    change_in_oi: int | None = None
    volume: int | None = None
    last_price: float | None = None
    instrument: str | None = None

    def __post_init__(self) -> None:
        strike = require_finite_number(self.strike, field_name="strike")
        if strike <= 0:
            raise ValueError("strike must be positive")
        object.__setattr__(self, "strike", strike)
        if self.option_type not in ("CE", "PE"):
            raise ValueError("option_type must be CE or PE")
        _require_nonnegative_int(self.open_interest, "open_interest")
        if self.change_in_oi is not None and (
            isinstance(self.change_in_oi, bool) or not isinstance(self.change_in_oi, int)
        ):
            raise ValueError("change_in_oi must be an integer or None")
        if self.volume is not None:
            _require_nonnegative_int(self.volume, "volume")
        if self.last_price is not None:
            price = require_finite_number(self.last_price, field_name="last_price")
            if price < 0:
                raise ValueError("last_price must be non-negative")
            object.__setattr__(self, "last_price", price)
        require_aware_datetime(self.observed_at, field_name="observed_at")
        if self.instrument is not None and not self.instrument.strip():
            raise ValueError("instrument must be non-empty when provided")


@dataclass(frozen=True, slots=True)
class OptionChainSnapshot:
    underlying: str
    spot_price: float
    observed_at: datetime
    contracts: tuple[OptionContract, ...]
    complete: bool

    def __post_init__(self) -> None:
        if not self.underlying.strip():
            raise ValueError("underlying must not be empty")
        spot = require_finite_number(self.spot_price, field_name="spot_price")
        if spot <= 0:
            raise ValueError("spot_price must be positive")
        object.__setattr__(self, "spot_price", spot)
        require_aware_datetime(self.observed_at, field_name="observed_at")
        if not isinstance(self.contracts, tuple):
            object.__setattr__(self, "contracts", tuple(self.contracts))
        if not isinstance(self.complete, bool):
            raise ValueError("complete must be a boolean")
        seen: set[tuple[float, OptionType]] = set()
        for contract in self.contracts:
            if not isinstance(contract, OptionContract):
                raise ValueError("contracts must contain OptionContract values")
            key = (contract.strike, contract.option_type)
            if key in seen:
                raise ValueError(f"duplicate option contract: {key}")
            seen.add(key)


def _require_nonnegative_int(value: object, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
