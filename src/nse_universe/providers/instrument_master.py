"""Local instrument-master parsing and lookup for Kotak Neo scrip-master CSVs.

Download the current scrip master using the authenticated SDK/dashboard workflow,
then load the relevant CSV locally. This module deliberately does not guess tokens.
"""
from __future__ import annotations
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

@dataclass(frozen=True, slots=True)
class Instrument:
    token: str
    exchange_segment: str
    trading_symbol: str
    instrument_type: str | None = None
    expiry: str | None = None
    strike: float | None = None
    option_type: str | None = None
    lot_size: int | None = None

class InstrumentMaster:
    """Validated lookup over a current Kotak scrip-master CSV file."""
    def __init__(self, instruments: Iterable[Instrument], *, source_path: str | None = None) -> None:
        by_key: dict[tuple[str, str], Instrument] = {}
        by_symbol: dict[tuple[str, str], Instrument] = {}
        for item in instruments:
            key = (item.exchange_segment, item.token)
            if key in by_key:
                raise ValueError(f"Duplicate instrument key in master: {key}")
            by_key[key] = item
            symbol_key = (item.exchange_segment, item.trading_symbol.upper())
            if symbol_key not in by_symbol:
                by_symbol[symbol_key] = item
        if not by_key:
            raise ValueError("Instrument master contains no usable instruments")
        self._by_key = by_key
        self._by_symbol = by_symbol
        self.source_path = source_path

    @classmethod
    def from_csv(cls, path: str | Path, *, default_segment: str | None = None) -> "InstrumentMaster":
        file_path = Path(path)
        instruments: list[Instrument] = []
        with file_path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                raise ValueError("Instrument master CSV has no header")
            for row in reader:
                # Kotak's transformed master uses pSymbol (segment), pTrdSymbol
                # (human-readable contract), and typically pScripRefKey (token).
                segment = _first(row, "pSymbol", "exchange_segment", "exchangeSegment") or default_segment
                symbol = _first(row, "pTrdSymbol", "trading_symbol", "tradingSymbol", "symbol")
                token = _first(row, "pScripRefKey", "instrument_token", "exchange_token", "token", "pSymbolName")
                if not segment or not symbol or not token:
                    continue
                expiry = _first(row, "lExpiryDate", "expiry", "expiry_date")
                strike_raw = _first(row, "dStrikePrice;", "dStrikePrice", "strike_price", "strike")
                option_type = _first(row, "pOptionType", "option_type", "right")
                lot_raw = _first(row, "lLotSize", "lot_size")
                try:
                    strike = float(strike_raw) if strike_raw not in (None, "", "-1", "-1.0") else None
                except ValueError:
                    strike = None
                try:
                    lot_size = int(float(lot_raw)) if lot_raw not in (None, "") else None
                except ValueError:
                    lot_size = None
                instruments.append(Instrument(
                    token=str(token).strip(), exchange_segment=str(segment).strip(),
                    trading_symbol=str(symbol).strip(), instrument_type=_first(row, "pInstType", "instrument_type", "type"),
                    expiry=expiry, strike=strike, option_type=option_type, lot_size=lot_size,
                ))
        return cls(instruments, source_path=str(file_path))

    def get(self, exchange_segment: str, token: str) -> Instrument | None:
        return self._by_key.get((exchange_segment, str(token)))

    def by_symbol(self, exchange_segment: str, trading_symbol: str) -> Instrument | None:
        return self._by_symbol.get((exchange_segment, trading_symbol.upper()))

    def search(self, text: str, *, exchange_segment: str | None = None, limit: int = 50) -> tuple[Instrument, ...]:
        if limit < 1:
            raise ValueError("limit must be positive")
        needle = text.upper()
        matches = (item for item in self._by_key.values()
                   if needle in item.trading_symbol.upper()
                   and (exchange_segment is None or item.exchange_segment == exchange_segment))
        return tuple(sorted(matches, key=lambda item: (item.exchange_segment, item.trading_symbol))[:limit])

    def __len__(self) -> int:
        return len(self._by_key)

def _first(row: dict[str, str | None], *keys: str) -> str | None:
    for key in keys:
        value = row.get(key)
        if value is not None and value.strip():
            return value.strip()
    return None
