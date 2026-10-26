"""Build normalized option-chain snapshots from verified instruments and fresh ticks."""
from __future__ import annotations

from datetime import datetime
from typing import Iterable

from nse_universe.options.models import OptionChainSnapshot, OptionContract
from nse_universe.providers.instrument_master import Instrument
from nse_universe.providers.tick_cache import TickCache


class OptionChainSnapshotBuilder:
    """Map an explicitly selected set of master instruments into a chain snapshot.

    The caller must select the correct underlying and expiry from the current scrip
    master. Missing, stale, or OI-less contracts are omitted and mark the chain
    incomplete. Both CE and PE sides must be selected for every selected strike.
    """

    def __init__(
        self,
        instruments: Iterable[Instrument],
        *,
        underlying: str,
        segment: str = "nse_fo",
    ) -> None:
        selected = tuple(
            item
            for item in instruments
            if item.exchange_segment == segment
            and item.strike is not None
            and (item.option_type or "").upper() in ("CE", "PE")
        )
        if not selected:
            raise ValueError("No option instruments with strike and CE/PE type were selected")
        keys = [(item.exchange_segment, item.token) for item in selected]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate instrument token in selected option contracts")
        sides_by_strike: dict[float, set[str]] = {}
        for item in selected:
            sides_by_strike.setdefault(item.strike, set()).add((item.option_type or "").upper())
        self._selected_pairs_complete = all(
            sides == {"CE", "PE"} for sides in sides_by_strike.values()
        )
        self.instruments = selected
        self.underlying = underlying
        self.segment = segment

    def build(
        self,
        cache: TickCache,
        *,
        spot_price: float,
        observed_at: datetime,
        now: datetime,
        max_age_seconds: float = 5.0,
    ) -> OptionChainSnapshot:
        if max_age_seconds < 0:
            raise ValueError("max_age_seconds must be non-negative")
        contracts: list[OptionContract] = []
        all_fresh_and_complete = self._selected_pairs_complete
        for item in self.instruments:
            status = cache.status(
                item.exchange_segment,
                item.token,
                now=now,
                max_age_seconds=max_age_seconds,
            )
            tick = status.last_tick
            if status.stale or tick is None or tick.open_interest is None:
                all_fresh_and_complete = False
                continue
            if status.age_seconds is None or status.age_seconds > max_age_seconds:
                all_fresh_and_complete = False
                continue
            oi = _whole_nonnegative(tick.open_interest, "open_interest")
            volume = (
                _whole_nonnegative(tick.volume, "volume")
                if tick.volume is not None
                else None
            )
            contracts.append(
                OptionContract(
                    strike=item.strike,
                    option_type=(item.option_type or "").upper(),
                    open_interest=oi,
                    observed_at=tick.exchange_timestamp or tick.received_at,
                    volume=volume,
                    last_price=tick.last_traded_price,
                    instrument=item.trading_symbol,
                )
            )
        return OptionChainSnapshot(
            underlying=self.underlying,
            spot_price=spot_price,
            observed_at=observed_at,
            contracts=tuple(contracts),
            complete=all_fresh_and_complete,
        )


def _whole_nonnegative(value: float, field_name: str) -> int:
    if value < 0 or not value.is_integer():
        raise ValueError(f"{field_name} must be a non-negative whole number")
    return int(value)
