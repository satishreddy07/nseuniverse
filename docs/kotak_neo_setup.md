# Kotak Neo live market-data setup

This integration uses the official kotakneoapi Python SDK and its modern async SFeed market-data WebSocket. Kotak's older HS market feed was scheduled for deprecation on 15 September 2026; use the maintained SDK/SFeed flow rather than legacy WebSocket examples.

Official references:
- SDK repository: https://github.com/Kotak-Neo/kotak-neo-python
- SFeed guide: https://github.com/Kotak-Neo/kotak-neo-python/blob/main/docs/guides/websocket.md
- Kotak feed migration notice: https://www.kotakneo.com/bulletins/trade-api-market-feed-migration-15-september-2026/

## 1. Install the optional SDK

    python -m pip install -e ".[kotak-neo,dev]"

## 2. Set local environment variables

Set these in Codespaces Secrets or your local environment, not in committed files:
- KOTAK_NEO_CONSUMER_KEY — application access token/consumer key from the Neo Trade API dashboard.
- KOTAK_NEO_MOBILE_NUMBER — registered mobile number including country code.
- KOTAK_NEO_UCC — client code/UCC.
- KOTAK_NEO_MPIN — MPIN used for session validation.
- KOTAK_NEO_ENVIRONMENT — optional, defaults to prod.

A current TOTP is passed to adapter.authenticate(totp=...) at runtime; do not hard-code it or commit an authenticator secret. Never paste credentials into chat or source control.

## 3. Stream market ticks

    import asyncio
    from nse_universe.providers.kotak_neo import KotakNeoAdapter, KotakNeoConfig

    async def main():
        adapter = KotakNeoAdapter(KotakNeoConfig.from_env())
        adapter.authenticate(totp=input("Current Kotak Neo TOTP: ").strip())
        # Replace with verified tokens from the latest broker scrip master.
        tokens = [("nse_cm", "Nifty 50"), ("nse_fo", "YOUR_VERIFIED_FO_TOKEN")]
        async for tick in adapter.stream(tokens):
            print(tick)

    asyncio.run(main())

The token pairs above are illustrative. Use valid exchange segment/token pairs from the current scrip master and keep subscriptions within the 3,000-token cap.

## Scope and safety
- This layer only authenticates and reads market data; it exposes no order-placement methods.
- SDK/live credentials are not required for unit tests; normalization is tested with local fixtures.
- A successful connection has not been verified against your account from GitHub. First run a market-data-only session and verify symbols, timestamps, and feed permissions.
- Missing OI/volume/timestamps remain unavailable rather than being fabricated.
- The official SDK documents automatic reconnect/re-authentication/re-subscription. This adapter relies on that behavior; the tick cache separately detects instruments that have stopped updating. Verify this with your account and network before relying on it.\n- The instrument master is loaded from a locally downloaded current CSV; automatic authenticated download and contract-expiry selection remain to be wired to the SDK. Do not treat an empty or stale stream as a valid signal.


## Instrument master and depth

Download the current CSV from Kotak Neo's authenticated scrip-master workflow, then load it locally:

    from nse_universe.providers.instrument_master import InstrumentMaster
    master = InstrumentMaster.from_csv("data/nse_fo.csv")
    matches = master.search("NIFTY", exchange_segment="nse_fo")
    print(matches[:10])

Use `master.get("nse_fo", token)` to resolve a token or `master.by_symbol("nse_fo", trading_symbol)` for an exact symbol. Confirm the CSV columns and selected contract/expiry before subscribing; the loader skips rows without segment, token, and symbol. Keep downloaded market data local and do not commit it.

For depth-capable subscriptions, use `adapter.stream(tokens, feed_type="depth")` or `feed_type="full_depth"`. The adapter exposes aggregate buy/sell quantities and best bid/ask where present. This is a snapshot of the SDK feed, not a complete reconstructed order-by-order tape. Use `TickCache(max_age_seconds=5)` to detect missing/stale tick updates; choose the freshness threshold to match the instrument/feed cadence.


## Build a normalized option-chain snapshot

After loading the latest instrument master, explicitly select contracts for one underlying and one expiry, then feed their latest ticks through the freshness-aware builder:

    from datetime import datetime, timezone
    from nse_universe.providers.option_chain_builder import OptionChainSnapshotBuilder
    from nse_universe.providers.tick_cache import TickCache

    # selected_contracts must be verified CE/PE instruments for one expiry.
    builder = OptionChainSnapshotBuilder(selected_contracts, underlying="NIFTY")
    cache = TickCache(max_age_seconds=5)
    # In your stream loop: cache.update(tick)
    snapshot = builder.build(
        cache,
        spot_price=spot_ltp,
        observed_at=datetime.now(timezone.utc),
        now=datetime.now(timezone.utc),
        max_age_seconds=5,
    )
    # Feed this snapshot to OptionSnapshotIngestor; incomplete chains stay marked incomplete.

The builder does not infer expiry selection or invent OI. A missing/stale tick or missing OI omits that contract and marks the chain incomplete. Keep the spot price from a verified live index/spot instrument; do not use a futures price as spot.
