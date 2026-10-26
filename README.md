# NSE Universe — Intraday Trading Intelligence

A personal, analysis-first NSE intraday research platform. The first release establishes data contracts, explicit freshness/quality checks, deterministic validation, and tests before broker integration or trading signals are added.

## Principles

- **No fabricated market data:** missing, stale, malformed, or partial inputs remain visibly unavailable.
- **Evidence before signals:** future signals must expose inputs, timestamps, and limitations.
- **Analysis-only by default:** no order placement or automatic execution.
- **Reproducible testing:** deterministic unit tests and replayable snapshots.
- **Secrets stay local:** never commit API keys, access tokens, session cookies, or broker credentials.

## Current foundation

- Python package and pytest configuration.
- UTC-aware timestamp and finite-number validation.
- Normalized market observation contract that preserves missing exchange timestamps.
- Architecture and trading analytics rules.
- Secret/local-data exclusions in `.gitignore`.

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
2. Implement options-chain normalization and ATM/near-ATM OI/PCR analytics.
3. Add futures VWAP, sector strength, breadth, and explicitly labelled order-flow proxies.
4. Integrate Kotak Neo streaming behind a provider adapter; test reconnects, freshness, and partial data.
5. Add snapshot replay, walk-forward evaluation, and calibrated signal research.

This is an early foundation, not a production trading system. A future score must not be presented as a probability without out-of-sample calibration. Live order execution remains out of scope until separately specified and risk-reviewed.
