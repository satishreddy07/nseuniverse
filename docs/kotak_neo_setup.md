# Kotak Neo live market-data setup

This integration uses the official `kotakneoapi` Python SDK and its modern async SFeed market-data WebSocket. Kotak's older HS market feed was scheduled for deprecation on 15 September 2026; use the maintained SDK/SFeed flow rather than legacy WebSocket examples.

Official references:
- SDK repository: https://github.com/Kotak-Neo/kotak-neo-python
- SFeed guide: https://github.com/Kotak-Neo/kotak-neo-python/blob/main/docs/guides/websocket.md
- Official scrip-master documentation: https://github.com/Kotak-Neo/Kotak-Neo/blob/main/docs/market-data-apis/instruments.md

## 1. Install the optional SDK

```bash
python -m pip install -e ".[kotak-neo,dev]"
```

## 2. Configure secrets locally

Set these in Codespaces Secrets or your local environment, never in committed files:
- `KOTAK_NEO_CONSUMER_KEY` — Neo Trade API consumer key.
- `KOTAK_NEO_MOBILE_NUMBER` — registered mobile number including country code.
- `KOTAK_NEO_UCC` — client code/UCC.
- `KOTAK_NEO_MPIN` — MPIN used for session validation.
- `KOTAK_NEO_ENVIRONMENT` — optional, defaults to `prod`.

A current TOTP is requested interactively by the preflight command. Do not hard-code it, commit an authenticator secret, or paste credentials into chat.

## 3. Inspect the current instrument master

Download the latest segment CSV from Kotak's official scrip-master workflow and keep it local (for example, `data/nse_fo.csv`). The official transformed CSV maps:
- `pSymbol` → instrument token used by quote/WebSocket APIs.
- `pExchSeg` → exchange segment such as `nse_fo` or `nse_cm`.
- `pTrdSymbol` → human-readable trading symbol.
- `pOptionType` → option type; futures rows can use `XX`.
- `lExpiryDate` → expiry metadata; do not assume it is already a readable ISO date.
- `dStrikePrice;` → strike price in current transformed files.

**Important:** `pScripRefKey` is not the WebSocket token. Use the numeric `pSymbol` with `pExchSeg`. The loader follows this mapping and deliberately does not infer expiry from potentially inconsistent date fields.

Search the local CSV without authenticating:

```bash
python -m nse_universe.providers.preflight --master data/nse_fo.csv --segment nse_fo --search NIFTY
python -m nse_universe.providers.preflight --master data/nse_cm-v1.csv --segment nse_cm --search "Nifty 50"
```

The index's exact symbol may be case-sensitive in quote APIs and may not be represented the same way as ordinary cash-market scrips. Inspect results; do not assume the first NIFTY match is the index, futures contract, or desired expiry.

## 4. Run a market-data-only preflight

Choose exact symbol(s) from the search output. Use the exact exchange segment and trading symbol. For example, replace these placeholders with symbols that actually appear in your local current CSV:

```bash
python -m nse_universe.providers.preflight \
  --master data/nse_fo.csv \
  --instrument 'nse_fo:REPLACE_WITH_EXACT_FUTURES_SYMBOL' \
  --seconds 20 \
  --max-age 5
```

For a cash/index instrument, use the appropriate current master and segment, and confirm it is a valid feed subscription before relying on it. To test multiple instruments, repeat `--instrument SEGMENT:SYMBOL`. The command:
- resolves exact symbols from the local master; it will not guess or silently fuzzy-match;
- asks for the current TOTP with hidden input;
- authenticates and subscribes to market data only;
- prints received tick fields and timestamps;
- reports each subscription as fresh or stale/missing;
- exits nonzero if selected instruments do not produce fresh ticks within the test window.

Choose a `--max-age` suitable for the feed and instrument. During closed-market hours, some instruments may not emit fresh ticks; run the feed test during market hours before concluding that permissions or tokens are broken.

Supported modes: `--feed-type touchline`, `--feed-type depth`, or `--feed-type full_depth`. Keep subscriptions within the SDK's documented 3,000-token cap.

## Scope and safety

- This layer only authenticates and reads market data; it exposes no order-placement methods.
- Unit tests do not require live credentials. A successful connection has not been verified against your account from GitHub.
- Missing OI, volume, or exchange timestamps remain unavailable rather than being fabricated.
- The adapter relies on the SDK's documented reconnect behavior; local freshness checks flag instruments that stop updating. Verify this with your account and network before relying on it.
- Do not commit downloaded instrument masters or market data. The loader is local-only and does not automatically download a fresh master.
- A missing/stale tick or missing OI causes the option-chain builder to omit that contract and mark the snapshot incomplete. Use a verified live spot/index price as the option-chain spot price, not a futures price.
