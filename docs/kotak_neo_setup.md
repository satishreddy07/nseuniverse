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
- Reconnect/backoff, instrument-master download, and option-chain-to-contract mapping remain next steps. Do not treat an empty or stale stream as a valid signal.
