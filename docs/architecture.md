# Architecture

## Goal
Build an analysis-first NSE intraday decision-support platform with transparent data quality, deterministic calculations, and reproducible tests.

## Planned layers
1. **Market data adapters:** Kotak Neo streaming integration, subscriptions, reconnects, and normalized events.
2. **Normalization and quality:** instrument mapping, exchange and receive timestamps, duplicate/out-of-order checks, missing-field validation, and freshness.
3. **Analytics:** option-chain/OI changes, ATM and nearby-strike PCR, futures VWAP, order-flow proxies, sector strength, breadth, and volatility context.
4. **Signal engine:** bullish/bearish/neutral assessments with explicit evidence; no hidden defaults for missing inputs.
5. **Replay and evaluation:** recorded snapshots, deterministic replay, walk-forward testing, transaction costs, and probability calibration.
6. **Presentation:** dashboard/API after domain contracts and tests are stable.

## Data contract requirements
Each observation should preserve instrument identity, source, exchange event timestamp when available, local receive timestamp, quality status, and normalized values. A receive timestamp must never silently replace a missing exchange timestamp. Derived metrics must retain source timestamps and quality.

## Reliability and safety
- Missing data stays missing; never substitute zero or fabricated values for unavailable market data.
- Reject NaN and infinity.
- Use timezone-aware timestamps internally; convert to Asia/Kolkata for display.
- Stale or incomplete required inputs invalidate dependent signals.
- Keep provider-specific code behind adapters.
- Never log tokens, passwords, cookies, or full authentication responses.
- Live order execution remains disabled until separately specified, risk-reviewed, and tested.
