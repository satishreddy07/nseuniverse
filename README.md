# NSE Universe — Intraday Trading Intelligence

A personal, analysis-first NSE intraday research platform. The project establishes normalized data contracts, explicit freshness/quality checks, deterministic option-chain analytics, and tests before broker integration or trading signals are added.

## Principles

- **No fabricated market data:** missing, stale, malformed, or partial inputs remain visibly unavailable.
- **Evidence before signals:** analytics expose their inputs, timestamps, scope, and limitations.
- **Analysis-only by default:** no order placement or automatic execution.
- **Reproducible testing:** deterministic unit tests and replayable snapshots.
- **Secrets stay local:** never commit API keys, access tokens, session cookies, or broker credentials.

## Current foundation

- Python package and pytest configuration.
- UTC-aware timestamp and finite-number validation.
- Normalized market observation contract that preserves missing exchange timestamps.
- Immutable option contract and option-chain snapshot models with basic validation.
- Overall/supplied-chain, ATM, and nearby-strike PCR calculations. Zero call OI yields an unavailable PCR, not infinity.
- Snapshot-to-snapshot OI deltas, price deltas, and explicitly contract-level price/OI quadrant labels.
- Chain completeness and missing call/put contract checks.
- SQLite-backed option snapshot history with chronological retrieval and idempotent timestamp upserts.
- Multi-snapshot OI trend summaries: net call/put OI change, supplied-chain PCR drift, top call/put additions and unwinding, and explicit data-quality warnings.
- Provider-neutral ingestion pipeline that persists normalized snapshots, flags stale/incomplete data, and produces trend reports after at least two snapshots.
- Optional Kotak Neo adapter using the maintained `kotakneoapi` SDK and modern async SFeed market-data API, with normalized tick models and local fixture tests.
- Browser-based Kotak Neo login screen (optional Streamlit dependency); credentials are session-only and are not saved to files.
- Local Kotak scrip-master CSV loader using the documented `pSymbol` token, `pExchSeg` segment and `pTrdSymbol` symbol mappings; it never fabricates contract tokens.
- Market-data-only preflight CLI to inspect a local master, resolve exact symbols, authenticate with hidden TOTP input, print received ticks, and fail on stale/missing subscriptions.
- Tick cache with per-instrument freshness checks and explicit missing/stale subscription reporting.
- Touchline, depth and full-depth subscription modes; normalized best bid/ask and aggregate buy/sell quantities when supplied by the feed.
- Explicit option-chain snapshot builder that omits stale/missing/OI-less contracts and marks partial snapshots incomplete.
- Architecture and trading analytics rules; secret/local-data exclusions in `.gitignore`.

**Scope note:** PCR over supplied contracts only describes those contracts. Treat it as a full-chain metric only when the chain's coverage is known complete. Price/OI quadrant labels for individual options are heuristics, not a directional market signal or a calibrated probability.

## Quick start (Codespaces or local)

Python 3.11+ is recommended.

```bash
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux/Codespaces: source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest
```

## Open the browser login page

Install the optional broker and web dependencies, then launch the app in your Codespace:

```bash
python -m pip install -e ".[kotak-neo,web]"
streamlit run src/nse_universe/web_app.py
```

Open the forwarded Streamlit port from the Codespaces **Ports** tab and keep its visibility **Private**. Enter the Kotak Neo consumer key, registered mobile number, UCC, MPIN and current TOTP in the form. The form clears after submission; credentials are held in server-side session memory and are not written to a file. This page currently checks login only; it does not yet start the live market feed or display the trading dashboard.

## Next phases

1. Add CI and expand domain contracts.
2. Add futures VWAP, sector strength, breadth, and explicitly labelled order-flow proxies.
3. Run `python -m nse_universe.providers.preflight --master data/nse_fo.csv --segment nse_fo --search NIFTY` to inspect a current local master, then verify a live Kotak Neo session during market hours; the preflight CLI reports stale/missing subscriptions.
4. Add snapshot replay, walk-forward evaluation, and calibrated signal research.

This is an early foundation, not a production trading system. A future score must not be presented as a probability without out-of-sample calibration. Live order execution remains out of scope until separately specified and risk-reviewed.
