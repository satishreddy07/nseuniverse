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

## Next phases

1. Add CI and expand domain contracts.
2. Add futures VWAP, sector strength, breadth, and explicitly labelled order-flow proxies.
3. Integrate Kotak Neo streaming behind a provider adapter; test reconnects, freshness, and partial data.
4. Add snapshot replay, walk-forward evaluation, and calibrated signal research.

This is an early foundation, not a production trading system. A future score must not be presented as a probability without out-of-sample calibration. Live order execution remains out of scope until separately specified and risk-reviewed.
