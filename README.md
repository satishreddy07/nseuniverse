# NSE Universe — Intraday Trading Intelligence

A personal, analysis-first NSE intraday research platform. The first release focuses on reliable data contracts, explicit freshness/quality checks, deterministic analytics, and tests before broker integration or trading signals are added.

## Principles

- **No fabricated market data:** missing, stale, malformed, or partial inputs stay visibly unavailable.
- **Evidence before signals:** every future signal must expose its inputs, timestamp, and limitations.
- **Analysis-only by default:** no order placement or automatic execution in this foundation.
- **Reproducible testing:** deterministic unit tests and replayable market snapshots.
- **Secrets stay local:** never commit API keys, access tokens, session cookies, or broker credentials.

## Current foundation

- Project packaging and test setup.
- UTC-aware timestamp and finite-number validation.
- Typed market-data snapshot contracts.
- A starter health/quality report.
- Architecture and trading-rule documents.

## Quick start

Python 3.11+ is recommended.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux/Codespaces: source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest
```

## Project status

This is an early foundation, not a production trading system. Broker streaming, option-chain calculations, VWAP, order-flow proxies, sector analysis, signal calibration, and replay/backtesting will be added in later phases. Any probability shown in a future UI must be empirically calibrated; it must not be presented as a guarantee.

## Configuration

Copy `.env.example` to `.env` for local configuration. Never commit `.env`. Broker credentials are intentionally not required by the foundation.
