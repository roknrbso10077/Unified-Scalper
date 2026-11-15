# UNIFIED SCALPER V702 — A66 CANONICAL FINAL

**Release ID:** `UNIFIED-SCALPER-V702-A66-CANONICAL-FINAL`  
**Release date:** 2026-11-15  
**Canonical executable:** `main.py`  
**Base runtime lineage:** A64  
**Production decision:** `NO_GO_UNATTENDED_LIVE`

## Operational status

This distribution is for offline validation, monitoring, and supervised Paper/Shadow research only. It is **not approved for unattended live trading**. A66 does not claim profitability and does not authorize real orders through the research-only strategy lanes.

Live-pilot configuration remains off by default. لا يكفي المفتاح الأول وحده لتفعيل التداول؛ يجب أن يكون الإعداد الداخلي مفعّلًا ومفتاحا المشغّل موجودين، مع اجتياز كل بوابات التنفيذ وEdge والرصيد والحماية والمخاطر. التفعيل اليدوي يتطلب ضبط `UNIFIED_LIVE_PILOT_ENABLE=1` و`UNIFIED_A55_LIVE_ARM=1` صراحةً، إلى جانب الإعداد الداخلي؛ القيم الافتراضية في المثال أدناه تظل `0`. CI وبيئة النشر لا ينبغي أن تفعّلا هذه المفاتيح تلقائيًا:

```dotenv
UNIFIED_LIVE_PILOT_ENABLE=0
UNIFIED_A55_LIVE_ARM=0
```

The inherited A65 runtime guard also fixes the stale CONFIG reference: authorization reads the current guarded CONFIG object at decision time. That fixes an inconsistent authorization read; it does not loosen a gate. The effective default remains `MONITOR_ONLY_NO_NEW_BUYS`.

## A66 startup-safety closure

1. **Protect open positions through a market-universe boot outage.** If the initial MEXC market/universe request fails after the PositionManager and runtime heartbeat tasks are started, the runtime no longer closes the exchange and returns from `run_bot`. It remains alive in fail-closed monitor mode, preserving the independent protection and heartbeat tasks.
2. **Bounded universe recovery.** An empty universe is retried on a configurable interval (`V702_A66_UNIVERSE_EMPTY_RETRY_SEC`, default 60 seconds, clamped to 30–300 seconds). An empty CCXT market cache is reloaded once through the existing safe API wrapper before rebuilding the liquidity universe.
3. **No scan on an unverified universe.** If no manually supplied or ranked symbols are available, the scanner skips BTC context, multi-timeframe fetches, candidate generation, Builder, queue, and execution plumbing. The PositionManager, heartbeat, Supervisor and Telegram runtime remain independent.
4. **Recovery never grants live authority.** A recovered universe does not clear the initial `LIVE_BLOCKED` latch or enable buys. The distribution remains `MONITOR_ONLY_NO_NEW_BUYS` and `NO_GO_UNATTENDED_LIVE`.
5. **Validation-chain continuity.** `--validate-only` now loads and executes the A66 validator before the one-shot validation dispatch; the historical A65 → A64 → A63 → ... validator chain remains intact.

## A65 inherited changes

1. **Unified round-trip cost model.** Production Shadow PreSend and the research studies now share one estimator. A valid measured all-in result (order-book/VWAP friction plus the symbol's available taker-fee metadata) takes precedence and receives a configurable 0.05 percentage-point safety buffer. The fallback is observed spread when available, otherwise a conservative configured spread, plus two-sided slippage and round-trip fee estimate. No measured cost is added to the fallback a second time, and the old unconditional minimum floor is set to zero. The conservative fallback remains in place whenever measurement is missing or invalid. A fee rate is not assumed identical for every MEXC market.
2. **Adaptive Relative-Strength Pullback — Shadow only.** A new experimental lane ranks closed 4H relative returns against BTC, requires BTC 4H regime/efficiency and asset 1H trend alignment, waits for a 15M structural pullback, then requires a closed 5M resumption break, volume confirmation, and a chase limit. Its research geometry uses a structural stop constrained to 1.5–3.5 ATR(15M), a 1.5R first target, a modeled 50% reduction at 1.5R, and a later 15M confirmed-pivot trail. It sends no orders.
3. **Closed-candle truth.** Shadow studies no longer discard the last DataFrame row blindly. They use each candle's timeframe close time and an explicit `as_of_ms`/grace when supplied; a still-forming candle is excluded.
4. **Partial-exit cost coherence.** One all-in round-trip estimate already prices the full original position. Splitting a modeled exit into 50% plus 50% no longer creates a second artificial full round-trip cost. The 15M trailing stop cannot use a pivot confirmed before the virtual entry.
5. **Default live-pilot safety.** `V702_LIVE_PILOT_ENABLE` defaults to false. The emergency-off variable, two operator keys, Spot/Long-only rules, Edge/Builder eligibility, score/liquidity/risk/protection gates and KillSwitch remain in force.
6. **Release identity.** A65 introduced its own distribution identity while preserving A64 as base runtime lineage; A66 appends the startup-protection closure without changing that lineage.

## Strategy coverage and what was deliberately not added

- The package retains its existing `SWING_PULLBACK`, `MTF_PULLBACK`, `RELATIVE_STRENGTH_LEADER`, `COMPRESSION_EXPANSION`, `BREAKOUT_RETEST`, `VWAP_RECLAIM_RS_5M`, and `MICRO_SWEEP_RECLAIM_1M` code paths. The new Adaptive RS lane is additive and research-only; production strategy admission is unchanged.
- The Efficiency Ratio concept is used as a BTC 4H regime filter inside the new research lane, not as permission to bypass production regime filters.
- A separate RSI-only mean-reversion engine and an external “Xiznit Scalper” clone were not added. An oversold RSI value alone is not a reversal signal, and the package has no verified specification or licensed source for the external named system.
- Futures/short selling was not added. The product remains Spot LONG_ONLY; futures require a separate risk, execution, liquidation, and protection design.
- MEXC native OCO/stop automation was not enabled. The package must not assume that an exchange feature is available for every symbol/account or correctly wired through the deployed CCXT adapter. Software-SL operational risk remains a live blocker until native protection is verified end to end.
- A durable Telegram Outbox was not introduced in A65 or A66. A64's digest queue and ACK/callback restoration remains; that is not represented as a transactional, crash-safe Outbox. This requires a separate idempotent persistence/reconciliation change and Telegram integration tests.
- A full historical Backtester and Walk-Forward proof were not fabricated. The supplied archive contains no historical OHLCV/book/fill dataset. A faithful replay must use timestamped exchange candles and book snapshots, and should exercise the same Candidate → Prequal → Score → Builder → Shadow PreSend → exit code paths. Until those inputs and replay parity tests exist, profitability remains unverified.

## Risk and operating boundaries

- Spot only; LONG_ONLY; Futures and short selling disabled.
- Live score floor remains **70**; hard liquidity floor remains **3,000,000 USDT**; max concurrent positions remains **2**.
- The existing **75 USDT** notional remains an upper cap, not an instruction or recommended ticket. An unconditional 10–20 USDT absolute cap was not hard-coded because the account equity, pair minimums, and fee reserve were not supplied. The existing risk-based sizing, balance/exposure/fee/SL/TP constraints, daily stop of **−2R**, and daily trade cap of **6** remain in force.
- Forbidden bases remain `PUMP`, `BNB`, `CAKE`, `AERO`, and `ETHFI`.
- `MAKER_FIRST_ENTRY_ENABLE` remains enabled where supported by the existing adapter, but a limit order is not guaranteed to be a maker fill and no maker fee is assumed without actual venue data.
- Same-candle SL/TP ambiguity remains pessimistically resolved as stop-first in the relevant Shadow studies.

## Cost semantics

All values are percentage points (`0.10` means 0.10%). The measured route is `measured_all_in + 0.05% buffer`. The fallback route uses observed spread when valid (otherwise the configured conservative spread) + two-sided slippage + configured round-trip fee. The configured baseline fallback remains conservative; it is not asserted to be each account's actual MEXC fee. Actual fees can vary by symbol, market, region, and current fee schedule. Invalid or unavailable fee/book data cannot be treated as a cheap measured fill.

## Run and validate

Target runtime: Python 3.12, Linux amd64.

```bash
python main.py --validate-only
python -u main.py
```

`--validate-only` must exit with code 0, report `bot_started=false`, and leave no background threads. The normal command starts the existing monitor/Paper/Shadow runtime; it does not override live-off defaults.

## Dependencies and deployment

`requirements.in` is the direct-dependency source. The checked-in `requirements-lock.txt` is a direct-pin seed, **not** a complete transitive hash lock. The A65 GitHub Actions workflow resolves Python 3.12/Linux amd64 hashes at CI time, performs compile/validation/tests, and builds the strict Docker image. This CI workflow was not executed by this local packaging run. Do not describe the current checked-in requirements lock as reproducible with `pip --require-hashes`.

Mount persistent storage at `/data` and set the documented `SCALPER_DB` and knowledge export paths. Never store secrets or runtime databases in this ZIP. A Docker image build and native stop functionality have not been verified in this environment.

## Release integrity

From the package root, verify:

```bash
sha256sum -c A66_SHA256SUMS.txt
```

`A66_RELEASE_MANIFEST.json` records the final archive inventory and A66 release decision. `FINAL_MANIFEST.json` is the machine-readable canonical source manifest. `A64_*` and `A65_*` files are retained as historical release evidence; `A66_SHA256SUMS.txt` is the current checksum authority.

## Production decision

**NO_GO_UNATTENDED_LIVE** remains the only supported decision. A65's Adaptive RS results remain Shadow observations, not an edge certification. Before considering a supervised pilot, correct and verify the deployed MEXC API credentials, collect real timestamped costs and execution observations, run a production-parity historical replay with walk-forward/holdout periods across market regimes, prove stop behavior and restart recovery on the target exchange/account, test Telegram delivery durability, and complete Python 3.12/Linux amd64 CI plus the Docker build.
