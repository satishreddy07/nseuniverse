# Trading Analytics Rules

These are design constraints, not trade recommendations.

## Data integrity
Do not publish metrics when required inputs are absent or invalid. Keep zero distinct from missing. Flag stale, partial, duplicated, out-of-order, and inconsistent observations. Derived metrics record calculation time and source timestamps.

## Options and open interest
Report strike-level call/put OI, interval OI change, volume, IV when available, and bid/ask context when provided. Every PCR must state its formula and strike scope. ATM/nearby windows are explicit and configurable.

OI change alone does not prove whether positions were opened or closed by buyers or sellers. Buildup/unwinding labels are heuristics and require price context.

## VWAP and order flow
VWAP specifies instrument, session boundary, price basis, and volume source. Do not mix index values with futures volume. If aggressor-side trade data is unavailable, label order-flow measures as proxies.

## Signals and probabilities
Neutral/no-trade is a valid outcome. Missing or stale critical features suppress a signal. A score is not a probability unless calibrated against historical out-of-sample outcomes. Probability outputs must document target event, horizon, sample size, calibration method, and evaluation period. Backtests must avoid look-ahead bias and account for realistic costs and fills.

## Execution
The initial product is analysis-only: no order placement, position modification, or unattended trading. Any later execution feature requires separate specification, explicit authorization, risk limits, a kill switch, broker-state reconciliation, and paper-trading evidence.
