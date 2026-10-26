# Kotak Neo live market-data setup

This integration uses the official `kotakneoapi` Python SDK and its modern async SFeed market-data WebSocket.

Official references:
- SDK repository: https://github.com/Kotak-Neo/kotak-neo-python
- SFeed guide: https://github.com/Kotak-Neo/kotak-neo-python/blob/main/docs/guides/websocket.md
- Official scrip-master documentation: https://github.com/Kotak-Neo/Kotak-Neo/blob/main/docs/market-data-apis/instruments.md

## Option A: Browser login screen

In Codespaces, run:

```bash
python -m pip install -e ".[kotak-neo,web]"
streamlit run src/nse_universe/web_app.py
```

Open the forwarded Streamlit port from the Codespaces **Ports** tab. Keep the port visibility **Private**. Enter your consumer key, registered mobile number, client/UCC, MPIN and current TOTP into the form. The form clears after submission; credentials are used in the server-side session and are not saved to a file.

The page currently verifies authentication only. It does not yet subscribe to live market data or show the trading dashboard. Do not deploy it publicly without adding proper access control, HTTPS, session expiry and production secret handling.

## Option B: CLI preflight

Install the optional SDK:

```bash
python -m pip install -e ".[kotak-neo,dev]"
```

Configure these in Codespaces Secrets or your local environment, never in committed files:
- `KOTAK_NEO_CONSUMER_KEY` — Neo Trade API consumer key.
- `KOTAK_NEO_MOBILE_NUMBER` — registered mobile number including country code.
- `KOTAK_NEO_UCC` — client code/UCC.
- `KOTAK_NEO_MPIN` — MPIN used for session validation.
- `KOTAK_NEO_ENVIRONMENT` — optional, defaults to `prod`.

A current TOTP is requested interactively by the preflight command. Do not hard-code it, commit an authenticator secret, or paste credentials into chat.

## Inspect the current instrument master

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

Inspect results; do not assume the first NIFTY match is the index, futures contract, or desired expiry.

## Run a market-data-only preflight

Choose exact symbol(s) from the search output and use the exact exchange segment and trading symbol:

```bash
python -m nse_universe.providers.preflight \
  --master data/nse_fo.csv \
  --instrument 'nse_fo:REPLACE_WITH_EXACT_FUTURES_SYMBOL' \
  --seconds 20 \
  --max-age 5
```

Repeat `--instrument SEGMENT:SYMBOL` to test multiple instruments. The command resolves exact symbols, requests TOTP with hidden input, authenticates, subscribes to market data only, prints received tick fields/timestamps, and exits nonzero if selected instruments do not produce fresh ticks.

Supported modes: `--feed-type touchline`, `--feed-type depth`, or `--feed-type full_depth`. Keep subscriptions within the SDK's documented 3,000-token cap.

## Scope and safety

- This layer only authenticates and reads market data; it exposes no order-placement methods.
- Unit tests do not require live credentials. A successful connection has not been verified against your account from GitHub.
- Missing OI, volume, or exchange timestamps remain unavailable rather than being fabricated.
- During closed-market hours, some instruments may not emit fresh ticks; run feed tests during market hours.
- Do not commit downloaded instrument masters or market data. The loader is local-only.
- Missing/stale ticks or missing OI cause the option-chain builder to omit that contract and mark the snapshot incomplete.
