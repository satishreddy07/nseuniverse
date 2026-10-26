"""Safe local preflight CLI for Kotak Neo market-data connectivity.

This command only reads market data. It never places orders or persists credentials.
"""
from __future__ import annotations

import argparse
import asyncio
from getpass import getpass
from datetime import datetime, timezone
from typing import Sequence

from nse_universe.providers.instrument_master import Instrument, InstrumentMaster
from nse_universe.providers.kotak_neo import KotakNeoAdapter, KotakNeoConfig
from nse_universe.providers.tick_cache import TickCache


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect a local Kotak scrip master or run a market-data-only feed preflight."
    )
    parser.add_argument("--master", required=True, help="Path to current local scrip-master CSV")
    parser.add_argument("--segment", default="nse_fo", help="Exchange segment (default: nse_fo)")
    parser.add_argument("--search", help="Search symbols in the master without logging in")
    parser.add_argument(
        "--instrument", action="append", default=[], metavar="SEGMENT:SYMBOL",
        help="Exact instrument to subscribe to; repeat for multiple instruments",
    )
    parser.add_argument("--feed-type", choices=("touchline", "depth", "full_depth"), default="touchline")
    parser.add_argument("--seconds", type=float, default=15.0, help="Run duration (default: 15 seconds)")
    parser.add_argument("--max-age", type=float, default=5.0, help="Stale threshold in seconds")
    return parser


def resolve_instruments(master: InstrumentMaster, specs: Sequence[str]) -> tuple[Instrument, ...]:
    selected: list[Instrument] = []
    seen: set[tuple[str, str]] = set()
    for spec in specs:
        if ":" not in spec:
            raise ValueError(f"Instrument must be SEGMENT:SYMBOL, got {spec!r}")
        segment, symbol = (part.strip() for part in spec.split(":", 1))
        if not segment or not symbol:
            raise ValueError(f"Instrument must be SEGMENT:SYMBOL, got {spec!r}")
        instrument = master.by_symbol(segment, symbol)
        if instrument is None:
            raise ValueError(f"No exact symbol {symbol!r} in segment {segment!r}")
        key = (instrument.exchange_segment, instrument.token)
        if key in seen:
            raise ValueError(f"Duplicate instrument selection: {spec}")
        seen.add(key)
        selected.append(instrument)
    if not selected:
        raise ValueError("Select at least one exact --instrument SEGMENT:SYMBOL")
    if len(selected) > 3000:
        raise ValueError("Kotak Neo SFeed supports at most 3000 subscribed tokens")
    return tuple(selected)


async def run_preflight(
    adapter: KotakNeoAdapter,
    instruments: Sequence[Instrument],
    *,
    feed_type: str,
    seconds: float,
    max_age_seconds: float,
) -> int:
    if seconds <= 0:
        raise ValueError("--seconds must be positive")
    if max_age_seconds < 0:
        raise ValueError("--max-age must be non-negative")
    cache = TickCache(max_age_seconds=max_age_seconds)
    tokens = [(item.exchange_segment, item.token) for item in instruments]
    end_time = asyncio.get_running_loop().time() + seconds
    count = 0
    print(f"Starting market-data-only preflight for {len(instruments)} instrument(s).")
    async def consume() -> None:
        nonlocal count
        async for tick in adapter.stream(tokens, feed_type=feed_type):
            cache.update(tick)
            count += 1
            symbol = tick.trading_symbol or next(
                (item.trading_symbol for item in instruments if item.token == tick.instrument_token
                 and item.exchange_segment == tick.exchange_segment),
                tick.instrument_token,
            )
            exchange_time = tick.exchange_timestamp.isoformat() if tick.exchange_timestamp else "unavailable"
            print(
                f"TICK {symbol} token={tick.instrument_token} ltp={tick.last_traded_price:g} "
                f"oi={tick.open_interest if tick.open_interest is not None else 'unavailable'} "
                f"volume={tick.volume if tick.volume is not None else 'unavailable'} "
                f"exchange_time={exchange_time} received_at={tick.received_at.isoformat()}"
            )
            if asyncio.get_running_loop().time() >= end_time:
                break
    try:
        async with asyncio.timeout(seconds):
            await consume()
    except TimeoutError:
        pass
    now = datetime.now(timezone.utc)
    statuses = cache.stale_or_missing(tokens, now=now, max_age_seconds=max_age_seconds)
    print(f"\nSUMMARY ticks_received={count} instruments={len(instruments)} feed_type={feed_type}")
    for item in instruments:
        status = cache.status(item.exchange_segment, item.token, now=now, max_age_seconds=max_age_seconds)
        label = "STALE_OR_MISSING" if status.stale else "FRESH"
        print(
            f"{label} symbol={item.trading_symbol} segment={item.exchange_segment} token={item.token} "
            f"age_seconds={status.age_seconds if status.age_seconds is not None else 'never'} "
            f"oi={'available' if status.last_tick and status.last_tick.open_interest is not None else 'unavailable'}"
        )
    if statuses:
        print("PREFLIGHT FAILED: one or more selected instruments had no fresh tick.")
        return 2
    print("PREFLIGHT PASSED: all selected instruments produced fresh ticks.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.seconds <= 0:
        raise SystemExit("--seconds must be positive")
    if args.max_age < 0:
        raise SystemExit("--max-age must be non-negative")
    try:
        master = InstrumentMaster.from_csv(args.master)
        if args.search is not None:
            results = master.search(args.search, exchange_segment=args.segment, limit=100)
            print(f"Found {len(results)} matching instrument(s) (display limited to 100):")
            for item in results:
                print(
                    f"{item.exchange_segment}:{item.trading_symbol} token={item.token} "
                    f"type={item.instrument_type or '-'} expiry={item.expiry or '-'} "
                    f"strike={item.strike if item.strike is not None else '-'} "
                    f"option_type={item.option_type or '-'} lot_size={item.lot_size or '-'}"
                )
            return 0 if results else 1
        instruments = resolve_instruments(master, args.instrument)
        print(f"Loaded {len(master)} instruments from {master.source_path}.")
        print("Selected instruments:")
        for item in instruments:
            print(f"  {item.exchange_segment}:{item.trading_symbol} token={item.token}")
        config = KotakNeoConfig.from_env()
        totp = getpass("Current Kotak Neo TOTP (input hidden): ").strip()
        adapter = KotakNeoAdapter(config)
        adapter.authenticate(totp=totp)
        print("Authentication completed; credentials and TOTP will not be printed.")
        return asyncio.run(run_preflight(
            adapter, instruments, feed_type=args.feed_type,
            seconds=args.seconds, max_age_seconds=args.max_age,
        ))
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"PREFLIGHT ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
