# UNIFIED SCALPER V702 — VERIFIED A84 RECOVERY / PARTIAL A85 SAFETY CORRECTION

**Recovery revision:** `A84-RECOVERY-A85-PARTIAL-2026-11-20`  
**Canonical executable:** `main.py` · **Archive limit:** 99 files  
**Entry authority:** `MONITOR_ONLY_NO_NEW_BUYS` / `NO_GO_UNATTENDED_LIVE`

## What is actually included

- Preserves the A84 source package, its 99-file inventory, the original strategy engines, risk controls, lifecycle, SQLite telemetry, reconciliation, protection and Telegram text/outbox paths.
- The existing BTC directional macro gate is observational by default (`V410_FAMILY_MACRO_DIRECTION_GATE_ENABLE=0`); missing/unknown context and confirmed crash/extreme/hard-reject conditions remain fail-closed. Symbol-local HTF, structure, volume, liquidity, fee, spread, risk and PreSend gates are retained.
- The existing Strategy Router evaluates nine built-in detectors, collapses correlated hits into six confluence groups, returns one candidate and caps the confluence bonus at 1.5 ranking points. This is a bounded Router enhancement, not a newly implemented full-market consensus system.
- A83 stablecoin `USDC/USDT` research code is retained but **disabled by default** (`STABLECOIN_MM_ENABLE=0`). When explicitly enabled it remains `SHADOW` only, `STABLECOIN_MM_LIVE_ARM=0`, with no exchange order authority. The fallback fee assumption remains 0.1% per side, so the default 12 bps spread ceiling cannot satisfy the positive net-edge rule.
- The two live arming switches remain explicitly off: `UNIFIED_LIVE_PILOT_ENABLE=0` and `UNIFIED_A55_LIVE_ARM=0`.

## A85 scope not yet implemented in this package

The following requested A85 deliverables are **not present** and are not claimed as complete: the dedicated `A85_MARKET_INTELLIGENCE_ENGINE`; full staged 500-pair radar/fair-rotation service beyond existing A79/A80 research paths; new complete BTC/ETH breadth and sector-rotation dashboard; end-to-end unified technical/SMC feature catalogue and cross-strategy statistical consensus beyond the existing Router confluence; the complete A85 trade-plan authority and expiry state machine; automatic multi-timeframe PNG chart renderer with Telegram `sendPhoto`; the expanded `/market`, `/top`, `/ready`, `/waiting`, `/analyze`, `/chart` and related read-only intelligence command suite; and the complete A85 walk-forward performance/adaptive research layer. Existing project capabilities remain, but they are not substitutes for those new A85 deliverables.

## A83 stablecoin monitor — explicit opt-in

- Default: `STABLECOIN_MM_ENABLE=0`, `STABLECOIN_MM_MODE=SHADOW`, `STABLECOIN_MM_LIVE_ARM=0`.
- To start the read-only monitor intentionally, set `STABLECOIN_MM_ENABLE=1` in the deployment environment and retain `STABLECOIN_MM_MODE=SHADOW` and `STABLECOIN_MM_LIVE_ARM=0`. An existing `.env`, Railway or Render variable overrides the package default.
- The 0.1%/side fallback fee equals 20 bps round trip before estimated slippage. The maximum permitted spread is 12 bps. Therefore the economic gate should reject quotes under the fallback assumption; do not set a zero-fee override unless the exact account/API/pair fee is independently confirmed.
- Telegram queueing is not delivery acknowledgement. Shadow results are not actual exchange fills or realized PnL.

## Validation and scope honesty

- The clean recovery source passed `compileall`, `--validate-only`, and the 58-module regression suite (619 passed, 1 historical-fixture skip, 0 failed) in this environment.
- No authenticated MEXC session, live order, real Telegram delivery acknowledgement, Docker target build, long-duration soak, or profitability validation was performed.
- This is a verified recovery release of the existing code with an A83 safe-default correction. It is **not a completed A85 Market Intelligence & Visual Analyst release**.

---

## Historical A82 — Higher-low Swing discovery and research diagnostics

**Current feature revision:** `A82-CLOSED-CANDLE-HIGHER-LOW-SWING-AND-RESEARCH-ERROR-TRUTH-2026-11-18` (historical A66 canonical distribution identity retained).
**Canonical executable:** `main.py` · **Archive limit:** 99 files · **Mode:** `MONITOR_ONLY_NO_NEW_BUYS` / `NO_GO_UNATTENDED_LIVE`.

## A82 — Swing structure coverage and research diagnostics

- Adds a distinct `SWING_HIGHER_LOW_RECLAIM` detector using confirmed swing pivots from fully closed 1H candles. A rising pair of confirmed lows creates a `WATCH` setup when local recovery, volume, RSI and extension conditions are acceptable. It does not require BTC-relative data merely to preserve an early watchlist idea.
- A setup can become `CONFIRMED` only after a confirmed higher high and closed-1H reclaim of the latest structural high, local 1H and 4H trend confirmation, volume/RSI constraints, and the existing bearish-BTC local strength contract. Existing PreQual, ranking, market-quality, cost, PreSend and execution gates remain authoritative.
- Stop reference is calculated below the confirmed structural low with the existing 0.35%-4.0% risk bound. If this geometry is invalid or exceeds the bound, the new setup is not emitted. Swing outcome observation remains based on closed 1H candles and is virtual/read-only.
- Repairs an A79 supplemental-fetch exception accounting hole: if an exception escapes the fetch helper, `failed` is reconciled to `attempted - ok`, the exception is reduced to a credential-redacted token, and the digest now exposes timeout, error and leading reject reasons.
- Feature switch: `V702_A82_SWING_HIGHER_LOW_ENABLE=1`; pivot significance is controlled by `V702_A82_SWING_HIGHER_LOW_MIN_PIVOT_DELTA_ATR=0.05`. Disable or adjust only after reviewing the evidence; neither setting changes live entry authority.

### Swing stop guidance

For multi-day Swing ideas, use a structural invalidation below the confirmed 4H/1H swing low with an ATR buffer; a 15m close is generally too sensitive to ordinary pullbacks for that holding horizon. A 15m close/invalidation belongs to an intraday setup, not a multi-day Swing thesis. A close-only stop is not a substitute for a hard protective order during a fast gap or crash. This release is monitor-only and creates no exchange-side stop orders.

### Google Colab

1. Upload `FINAL_PRODUCTION_RELEASE.zip` to the Colab session and extract it:
   `!unzip -q /content/FINAL_PRODUCTION_RELEASE.zip -d /content/unified_scalper`
2. Install dependencies and enter the project directory:
   `!pip install -r /content/unified_scalper/requirements.txt`
   `%cd /content/unified_scalper`
3. Run the safe validation first:
   `!python main.py --validate-only`
4. For a monitor-only run, copy `.env.example` to `.env`, keep `UNIFIED_LIVE_PILOT_ENABLE=0`, `UNIFIED_A55_LIVE_ARM=0`, and `UNIFIED_MONITOR_ONLY_SCAN_ENABLE=1`, then provide only the optional Telegram credentials needed for notices. Do not add MEXC trading credentials for this audit/paper workflow. Start with `!python main.py` only after confirming those switches and the Colab runtime storage policy. Colab ephemeral disks may be reset; use a persistent mounted drive path for SQLite only if you understand the access implications.

## A77 — Micro Telegram follow-up

- Each initial 1m Micro Shadow opportunity uses the existing opportunity-link formatter: MEXC Spot TradingView chart plus a Telegram channel/bot link only when a public username/URL is configured. No private message permalink is invented.
- An alerted Micro sample that later resolves creates one durable outcome notification: `TP1`, `SL`, `TIMEOUT`, or `AMBIGUOUS_DATA_GAP`. Outcome data is persisted atomically with the sample update and has a unique sample key, so retrying a failed Telegram enqueue does not duplicate the result.
- Result messages show signal ID, Entry, Stop, Target, reference Exit, bars, gross R, modeled costs and net R/net percent. An ambiguous candle-data gap is explicitly not scored. Same-candle stop/target is still Stop-first.
- A previous-day daily report is queued once after 00:05 Africa/Cairo time. It shows each of the five intraday Shadow strategies separately: sample count, resolved count, TP1, SL, timeout, ambiguous and average modeled net R/percent. It is a study summary, not a performance guarantee.
- New controls are in `.env.example`: `V702_INTRADAY_SHADOW_OUTCOME_TELEGRAM_ENABLE`, `V702_INTRADAY_SHADOW_OUTCOME_TELEGRAM_MAX_PER_BATCH`, `V702_INTRADAY_SHADOW_DAILY_TELEGRAM_ENABLE`, `V702_INTRADAY_SHADOW_DAILY_TIMEZONE`, `V702_INTRADAY_SHADOW_DAILY_REPORT_HOUR`, and `V702_INTRADAY_SHADOW_DAILY_REPORT_MINUTE`.

**Telegram link configuration:** each Micro alert/result reuses the shared link formatter. TradingView/MEXC links are generated from the symbol; a clickable Telegram channel/bot URL is included only when a public Telegram URL or username is configured (`TELEGRAM_OPPORTUNITY_PUBLIC_URL`, `TELEGRAM_PUBLIC_URL`/`TELEGRAM_CHANNEL_URL`, `TELEGRAM_PUBLIC_CHAT_USERNAME`, or public username aliases). A private numeric chat ID cannot be converted into a public message permalink.

**Verification:** all 58 packaged test modules passed in twelve non-overlapping groups: **599 passed, 1 historical fixture skipped, 0 failed**. Compilation: `compileall` and explicit `py_compile` passed for all 73 Python files. `python main.py --validate-only`: exit 0, `bot_started=false`, `live_threads=[]`. ZIP: 99 unique files, CRC clean, exact manifest inventory. No real Telegram network delivery/ACK, live exchange order/fill, or profitability was tested. `TelegramDispatcher.enqueue` success means accepted into the application outbox, not confirmed delivered to the Telegram client. Micro TP/SL messages are virtual closed-candle outcomes, not exchange orders/fills or realized PnL. No live authority or strategy gate is relaxed.

---

# UNIFIED SCALPER V702 — A75 FINAL PRODUCTION AUDIT INTEGRATION

**Release ID:** `UNIFIED-SCALPER-V702-A66-CANONICAL-FINAL+A75-AUDIT-INTEGRATION` (historical A66 distribution identity retained; A75 is the active audit closure)  
**Release date:** 2026-11-17 (A75 validation, lifecycle, HTF observability, data-integrity and monitor-only command closures)  
**Canonical executable:** `main.py`  
**Base runtime lineage:** A64  
**Production decision:** `NO_GO_UNATTENDED_LIVE`


## A75 — final production audit integration (2026-11-17)

A75 integrates the reproducible audit fixes into the existing package without adding files, removing strategy engines, loosening acceptance thresholds, changing Spot LONG-only scope, or granting Hunter/order execution authority.

- **Validation:** final A66 validation is the conjunction of the inherited validator, A66 startup checks and A72 checks. A72 failure is terminal. `--validate-only` now runs after A74/A75 installation so the final effective runtime wrappers are included.
- **Existing positions:** if a private MEXC client exists but startup position/exit reconciliation fails, a bounded exponential-backoff task retries reconciliation. It starts the dedicated PositionManager only after a healthy protection cycle is proven. This recovery does not unblock new entries; missing credentials cannot be repaired by software retry.
- **Telegram operator commands:** the polling controller can run in Monitor-only. Read-only `/help`, `/commands`, `/ping`, `/digest` and `/opportunities` remain available; account-mutating commands are rejected without a verified private client and appropriate live authority.
- **BTC regime:** candidate policy regime uses the latest closed BTC 4H candle and advances its confirmation count only once per distinct closed candle. The descriptive macro label and candidate-policy label remain separately visible; the policy is not silently relaxed.
- **Hunter data quality:** closed-candle validation derives freshness from the actual last retained timestamp, rejects stale/non-contiguous histories, and retains enough hourly history for the 7-day observation horizon. RSI edge cases are explicit (100 on uninterrupted gains, 0 on uninterrupted losses, 50 on a flat sequence).
- **Lifecycle and outcomes:** terminal `COMPLETED`/`INVALIDATED`/`EXPIRED` setups cannot be resurrected with the same identity; initial price geometry and cost assumptions are frozen in the setup snapshot; post-expiry candles are excluded; data gaps remain UNKNOWN and cannot be treated as stop/target outcomes. Active record pagination rotates to avoid fixed-prefix starvation.
- **Cost and score semantics:** zero fee/slippage is a valid explicit input; negative/non-finite cost inputs and negative spread fail closed. `volume_quality` is never coerced into `volume_ratio`. Technical, execution, regime-fit and composite rank floors are separately labelled.
- **Observability:** `/digest` includes Hunter scanned/created/active/error/data-gap counts, candidate policy regime source/confirmations, and the 1D MTF lane attempted/ok/failed/covered counters. `/opportunities` lists persisted active Hunter observations read-only.
- **Async I/O and alerts:** Hunter's SQLite operations in the market scan are offloaded from the event loop. The Hunter records an alert as delivered only after dispatcher success ACK, preserves pending state separately, and keeps a failed send retryable. Telegram delivery is at-least-once, not exactly-once.

**Still not certified/fully closed:** no transactional semantic Telegram outbox or durable deferral of every rate-limited terminal event has been proven under process-kill tests; no dedicated single-writer actor, automated backup/restore test, broad `main.py` modularization, 3,402-exception severity audit, complete undefined-name warning classification, per-strategy market-data contract split, full transitive hash lock, Docker/Python 3.12 build, 512 MiB memory/soak test, or live MEXC/Telegram integration test was completed here. The target environment, account, and real exchange were unavailable. Treat these as explicit residual release gates, not as passed checks.

A75 regression tests were added to the existing test module for RSI edge cases, explicit zero/invalid cost inputs, terminal lifecycle and frozen geometry, post-expiry outcome filtering, actual last-candle timestamps after null filtering, unique-bar Regime confirmation, A72 validator failure propagation, and monitor-only Telegram command authorization. The package remains `NO_GO_UNATTENDED_LIVE` and `MONITOR_ONLY_NO_NEW_BUYS`.

## A73 — confirmed opportunities, TradingView and swing follow-up (2026-11-16)

- Telegram no longer sends `WATCH` / forming setups. They remain persisted internally for diagnostics and can advance later.
- `PREQUAL_PASS` alone is not a Telegram confirmation. A canonical `SCORE_PASS`, the existing named closed-candle technical trigger, or canonical `PRESEND_PASS` is required for the corresponding alert state. Technical-only confirmation is labelled clearly and is not represented as execution-ready.
- Opportunity messages include a MEXC Spot TradingView chart link, strategy style, analytical entry, invalidation, TP1/TP2/TP3 and the closed-candle monitoring horizon.
- Existing `SWING` strategy candidates retain their timeframe/style metadata, deduplicate by the relevant closed-bar anchor instead of per-scan generated time, and are followed on closed 1h candles with a default 7-day observation lifetime. Intraday opportunities continue to be followed on closed 5m candles.
- TP/SL outcome notifications are based on closed OHLC reference touches only. If one candle touches stop and target, stop is conservatively counted first. This does not prove order execution, fill, fees, realized PnL, or profitability.
- No strategy engine was added, no entry/risk/cost gate was relaxed, and no new exchange polling was added for the Hunter follow-up. The release remains `MONITOR_ONLY_NO_NEW_BUYS` / `NO_GO_UNATTENDED_LIVE`.

## A71 — integrated corrective production audit (2026-11-16)

A71 is a corrective integration layer over the A70 package identity. It does not change the A66 distribution tag or relax strategy, risk, entry, or execution gates. It closes the startup source-parsing memory spike, frozen-candidate diversity mutation, fallback ranking constructor, cached-Universe fallback NameError, fail-open observability self-test exception, exact PositionManager identity coverage, unresolved Shadow sample retention, and bounded terminal Telegram Outbox retention. It also centralizes legacy validate-only aliases and logs an explicit one-shot validation exit.

**Verification:** full offline suite `535 passed, 1 skipped, 0 failed` (64.72s); `python -u main.py --validate-only` passed 23 checks with exit 0, `bot_started=false`, peak RSS 551,132 KiB (538.21 MiB). This measured peak is below the earlier ~1001 MiB audit measurement but remains above 512 MiB. Railway's actual memory quota and termination reason were not available; OOM is not confirmed.

**Railway operator checks:** use `python -u main.py` as the persistent Start Command; mount a persistent Volume at `/data`; set `SCALPER_DB=/data/unified_scalper.db`; disable every validate-only variable; keep `UNIFIED_LIVE_PILOT_ENABLE=0` and `UNIFIED_A55_LIVE_ARM=0`; and confirm a memory limit with adequate headroom. The monitor-only runtime uses an unauthenticated public MEXC Spot client for discovery; MEXC keys and wallet balance are not required unless recovered private positions/order intents need account reconciliation or protection. Do not use an HTTP health path unless the service actually serves HTTP; the packaged healthcheck is a process/container heartbeat check with a 360-second Docker start period.

The package remains `NO_GO_UNATTENDED_LIVE` / `MONITOR_ONLY_NO_NEW_BUYS`. Railway deployment, real MEXC orders, native stop protection, real Telegram delivery and profitability are not certified.

## Operational status

This distribution is for offline validation, monitoring, and supervised Paper/Shadow research only. It is **not approved for unattended live trading**. A66 does not claim profitability and does not authorize real orders through the research-only strategy lanes.

Live-pilot configuration remains off by default. لا يكفي المفتاح الأول وحده لتفعيل التداول؛ يجب أن يكون الإعداد الداخلي مفعّلًا ومفتاحا المشغّل موجودين، مع اجتياز كل بوابات التنفيذ وEdge والرصيد والحماية والمخاطر. التفعيل اليدوي يتطلب ضبط `UNIFIED_LIVE_PILOT_ENABLE=1` و`UNIFIED_A55_LIVE_ARM=1` صراحةً، إلى جانب الإعداد الداخلي؛ القيم الافتراضية في المثال أدناه تظل `0`. CI وبيئة النشر لا ينبغي أن تفعّلا هذه المفاتيح تلقائيًا:

```dotenv
UNIFIED_LIVE_PILOT_ENABLE=0
UNIFIED_A55_LIVE_ARM=0
```

The inherited A65 runtime guard also fixes the stale CONFIG reference: authorization reads the current guarded CONFIG object at decision time. That fixes an inconsistent authorization read; it does not loosen a gate. The effective default remains `MONITOR_ONLY_NO_NEW_BUYS`.

## A70 — entrypoint identity closure (2026-11-16)

A70 fixes a boot-order defect in `main.py`: the A69 canonical audit-identity closure previously appeared below the `if __name__ == "__main__": main()` call. A persistent service could enter `main()` before that closure executed, and the one-shot `--validate-only` path could exit before it. The identity closure now executes before both the validation CLI branch and the persistent entrypoint. The stable A66 distribution tag, A69 merged-audit identity, live-authority gates, and strategy behavior are preserved; A70 is an additive package identity/ordering closure only.

A dedicated regression now checks source ordering (`A70` closure → A69 identity merge → validation CLI → `__main__` → `main()`), active runtime identity fields, and boot-log identity fields. The distribution is still offline/monitor-only and is not certified for unattended live trading.

## A67 — Intelligent Opportunity Hunter (read-only)

A67 adds an independent opportunity-discovery and follow-up layer without changing the canonical BUY authority. It consumes the **existing bounded `market_data_map` only** (no added exchange requests), observes actual candidates from the existing 18 strategy engines, and records canonical pipeline transitions.

### Opportunity states

- **WATCH:** a measured setup is forming. The Telegram message names the measured evidence and the conditions still required.
- **CONFIRMED:** a named trigger from a fully closed candle (explicitly labelled *technical-only*) or a canonical `SCORE_PASS`. `PREQUAL_PASS` is recorded internally but does not by itself trigger a Telegram alert.
- **TRADEABLE:** emitted only after canonical `PRESEND_PASS`. This means the candidate passed the existing pre-send checks; it does **not** mean an order was sent, accepted, or filled.
- **INVALIDATED / EXPIRED:** the stored thesis is closed when a closed price crosses its invalidation level or its bounded lifetime expires.
- **COMPLETED:** A68 has recorded a final TP3 touch in the shadow-reference ledger; this is not an executed trade or realized profit.

States move forward only. Terminal rows are not resurrected by stale candidate events. Records persist in the SQLite `opportunity_hunter` table. Telegram state alerts are rate-limited and include analytical entry reference, invalidation level and scenario TP1/TP2/TP3 levels (not executable orders or guaranteed targets), with delivery status callbacks; they never grant execution authority.

### Pattern lanes and evidence

The bounded closed-candle scanner evaluates **BREAKOUT_CONTINUATION**, **PULLBACK_RECLAIM**, **MEAN_REVERSION**, and **RELATIVE_STRENGTH_LEADER**. It uses closed 5m/15m bars, validates OHLC relationships, rejects duplicate timestamps and stale/short history, and compares relative strength with BTC when the BTC 15m snapshot is present. The layer also observes genuine long Spot USDT candidates emitted by the existing strategy engines; it does not fabricate engine invocations or change their scoring.

Default resource limits: a configured ceiling of 240 symbols per cycle, 6 new pattern alerts per scan, and a hard maximum of 3 alerts per minute; the internal ranking floor remains 55/100, the intraday opportunity TTL is 3,600 seconds, the Swing candidate observation TTL defaults to 604,800 seconds (7 days), and the active-record cap is 1,200. **240 is not the actual scan count:** the Hunter reads only keys already present in `market_data_map`. That map is bounded upstream by the existing deep-scan selection (V699 targets normal=130, elevated=150, starving=170 when that arbiter is active; actual coverage can be lower when snapshots fail validation). No additional exchange request is made for Hunter discovery. Delivery callbacks are preserved on the direct dispatcher path, so the 3/minute hard cap is enforced locally rather than sacrificing ACK/failure handling. The Hunter score is a ranking heuristic, **not** a probability of profit or a validated edge. Candidate and technical confirmations remain distinct from the canonical execution pipeline.

The feature remains active in monitor-only mode: `MONITOR_ONLY_NO_NEW_BUYS`. `WATCH` rows are stored but not delivered to Telegram; a message is sent only after a closed-bar trigger, canonical `SCORE_PASS`, or canonical `PRESEND_PASS`. Every opportunity alert carries a TradingView MEXC Spot chart link. Intraday follow-up uses closed 5m candles; candidates explicitly marked `SWING` use closed 1h candles and a 7-day default lifetime. TP/SL results are shadow reference touches, not order fills or realized profits. No live BUY, exchange execution, risk/score/liquidity gate relaxation, or profitability claim is added. Live MEXC and Telegram delivery still require target-environment verification.

### A72 — independent public discovery and descriptive BTC macro

The monitor-only process uses a dedicated unauthenticated MEXC Spot client for public market data. It does not run private-balance/TruthSeal preflight merely to publish opportunities. A separate authenticated account client is created only when recovered open positions or unresolved execution intents require private reconciliation/protection; failure of that private client does not terminate the public scan.

BTC macro is fetched/classified independently before the empty-Universe defer. Its report can be `BULLISH`, `BEARISH`, `NEUTRAL`, or `UNKNOWN`; no bullish macro regime is required for the macro report or for running public discovery. This is **not** a blanket bypass of strategy-specific regime/crash, local-evidence, risk, liquidity, cost, or protection policies. The Telegram macro digest is informational and rate-limited. Opportunity alerts still require valid market data plus an actual candidate/idea from the existing discovery lanes, and require Telegram token/chat configuration for delivery.

## A68 — Closed-candle TP/SL outcome follow-up

A68 closes the missing outcome leg in A67. Every persisted active Hunter idea is now re-evaluated against the **already available closed 5-minute OHLC candles** for its symbol. The configured discovery ceiling is 240, but actual discovery remains bounded by the already-populated `market_data_map` and its upstream deep-scan target. Previously tracked symbols outside the discovery slice are still followed whenever their market snapshot is present in the current `market_data_map`. No extra exchange request is made for the outcome monitor.

### Recorded shadow outcomes

- `SHADOW_TP1_TOUCHED`, `SHADOW_TP2_TOUCHED`, `SHADOW_TP3_TOUCHED`: a fully closed 5m candle's high reached the fixed reference target.
- `SHADOW_STOP_HIT`, `SHADOW_STOP_AFTER_TP1`, `SHADOW_STOP_AFTER_TP2`: a fully closed 5m candle's low reached the fixed reference stop after the indicated target history.
- `SHADOW_EXPIRED_WITHOUT_TARGET`, `SHADOW_EXPIRED_AFTER_TP1`, `SHADOW_EXPIRED_AFTER_TP2`: the idea expired before the next terminal event.
- `COMPLETED`: terminal lifecycle state when TP3 is reached. `INVALIDATED` remains the terminal state for the reference stop; `EXPIRED` remains time-based expiry.

Only candles that opened after the opportunity was recorded are eligible. The signal candle and any candle already in progress at observation time are skipped. If one 5m candle touches both stop and a target, the event is labelled ambiguous and the stop is counted first; OHLC data cannot prove which level traded first. Target/stop geometry is frozen when a candidate is first persisted so later scans cannot silently rewrite its historical levels. Schema changes are additive SQLite migrations; existing opportunity rows are retained.

The SQLite `opportunity_hunter` row stores outcome state, bounded event history, last processed closed candle, finality and reason. The scan summary exposes `outcome_summary`, update counts and event counts, and Telegram outcome alerts show the event sequence. The message explicitly says a shadow price touch is **not** a real exchange fill, an order execution or net profit.

### Executed positions are a separate ledger

Actual positions already inside the canonical execution path continue to be handled by `PositionManager` and its protection/reconciliation paths, including TP1/TP2 exit handling and SL/exit finalization. A68 does not replace or mutate that order manager. The A68 shadow result must never be substituted for a real position's fill, fee, realized P&L or stop order state. Live MEXC protection and Telegram delivery remain unverified until tested on the target account/service.

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
- A66 audit closure adds a SQLite-backed Telegram Outbox persisted before queue admission, with explicit `QUEUED / SENDING / RETRY_PENDING / DELIVERED / DEAD_LETTER` states and restart replay. Delivery semantics are **at-least-once**, so a crash after Telegram accepts a message but before the local ACK is committed can produce a duplicate. Semantic in-process callbacks are not persisted/restored, and live Telegram delivery has not been tested. Telegram remains observability/control only and grants no execution authority.
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

Copy `.env.example` to `.env` only on the operator's local machine or persistent deployment volume. Enter exchange credentials through a secret manager where possible; never commit `.env`, fill credentials into `.env.example`, or include them in a release ZIP. The sample keeps both live-authority switches set to `0`.

```bash
python main.py --validate-only
python -u main.py
```

`--validate-only` must exit with code 0, report `bot_started=false`, and leave no background threads. It is a **one-shot diagnostic command**, never a persistent service command. The normal command starts the existing monitor/Paper/Shadow runtime; it does not override live-off defaults.

### Google Colab (validation / supervised Paper only)

Upload `FINAL_PRODUCTION_RELEASE.zip` in a Colab cell, then run:

```python
from google.colab import files
files.upload()  # choose FINAL_PRODUCTION_RELEASE.zip
```

```bash
!unzip -q FINAL_PRODUCTION_RELEASE.zip -d /content/unified-scalper
%cd /content/unified-scalper
!python --version
!python -m pip install -r requirements.txt
!python -m compileall -q .
!python -m pytest -q
!python -u main.py --validate-only
```

To receive Telegram alerts, configure the bot token and chat ID in a separate Colab cell without writing the token into notebook source:

```python
import os
from getpass import getpass
os.environ["TELEGRAM_BOT_TOKEN"] = getpass("Telegram bot token: ")
os.environ["TELEGRAM_CHAT_ID"] = input("Telegram chat ID: ").strip()
os.environ["UNIFIED_LIVE_PILOT_ENABLE"] = "0"
os.environ["UNIFIED_A55_LIVE_ARM"] = "0"
```

Then start the read-only monitor in a foreground cell:

```bash
!python -u main.py
```

The declared target is Python 3.12; confirm the Colab runtime version before installing. In the monitor-only release, public MEXC market discovery does **not** require MEXC API keys or wallet balance. Telegram opportunity/macro alerts require `TELEGRAM_BOT_TOKEN` (or `TELEGRAM_TOKEN`) and `TELEGRAM_CHAT_ID` (or `TELEGRAM_CHAT`); without them the scan may continue, but no Telegram message can be delivered. MEXC private credentials are only needed when the database contains recovered open positions or unresolved order intents that must be reconciled/protected. If those private credentials are absent/invalid, public discovery continues, but existing position protection is explicitly reported as unverified and no new execution is enabled. Keep `UNIFIED_LIVE_PILOT_ENABLE=0` and `UNIFIED_A55_LIVE_ARM=0`. Never paste secret values into notebook cells or output. `python -u main.py` is a foreground process and Colab can disconnect or reset at any time; Colab is not a persistent production host and this release remains `NO_GO_UNATTENDED_LIVE`.

### Railway persistent-service settings

Set the Railway **Start Command** to exactly:

```bash
python -u main.py
```

Do not add `--validate-only`. Ensure these variables are absent or set to `0` in the Railway service:

```dotenv
UNIFIED_V699_VALIDATE_ONLY=0
UNIFIED_V702_VALIDATE_ONLY=0
UNIFIED_VALIDATE_ONLY=0
```

Any one of those variables set to `1` deliberately switches the process to the one-shot validator, which exits instead of starting the bot. The terminal marker
`[V702-VALIDATE-EXIT] one_shot=true bot_started=false` proves that the service was started in validation mode. A repeated boot cycle without that marker is **not enough** to establish the cause; inspect the last complete log lines and the full traceback, if any. In particular, a terminal `[V702-CRASH]` block must be diagnosed from its actual exception and stack, not from the synthetic self-test messages above it.

The supplied Railway screenshots show repeated startup/self-test sequences with log timestamps from approximately `2026-11-15 22:28:12` through `22:30:33` UTC (approximately `2026-11-16 00:28`–`00:30` Africa/Cairo) and a `Crashed` service state. The Railway header displays short revision `f00fb90a`; the ZIP contains no `.git` metadata or Railway deployment settings, so this cannot be matched to the archive source. The captured excerpts do not show the terminal `[V702-VALIDATE-EXIT]` marker, the new `[V702-STARTUP-PHASE]` boundary markers, or a complete `[V702-CRASH]` traceback. A one-shot validator command, an import/config failure, a runtime dependency/client failure, or a platform resource limit therefore remain possibilities; none is proven by these screenshots alone.

The screenshot's `ENV-BOOT` telemetry reports `dotenv_loaded=False` while the MEXC key/secret and Telegram token/chat presence flags are `True`. This means the absence of a project-root `.env` file is not, by itself, evidence that Railway secrets are missing. The screenshot's `MSE.selftest`, `stage=selftest`, and synthetic `DailyCB-R5` rows are test-generated diagnostics; they are not proof of a live market loss or an actual candidate failure. The revised service logs now publish the active A66 distribution tag and current A66 operational patch consistently (while retaining the A64 compatibility identity and A51 historical field), expose A69 as a separate merged-audit revision, and mark validation completion, epoch arming, and entry into `run_bot` separately.

A further screenshot supplied on 2026-11-16 shows Railway deployment revision `9d951f72` with status `Crashed` and another repeated startup sequence (visible log times around 14:56:17–14:56:30). It again shows `api_secret_present=True`, `telegram_token_present=True`, and `telegram_chat_present=True`; the `__boom__`, `T17/T18 stage=selftest`, and DailyCB synthetic loss rows remain expected test probes. The visible capture does not include the final `V702-STARTUP-PHASE` / `V702-CRASH` tail or a traceback. This short revision cannot be matched to the ZIP because `.git` metadata and Railway deployment settings are not included. Root cause remains unproven; compare the Railway Start Command with `python -u main.py`, make sure no `--validate-only` argument or `UNIFIED_V699_VALIDATE_ONLY` / `UNIFIED_V702_VALIDATE_ONLY` / `UNIFIED_VALIDATE_ONLY` flag is active, and inspect the final traceback and memory metrics. The local validate-only peak was about 539 MiB RSS in this audit environment; it is a measurement to compare with the service memory limit, not proof of OOM. See section 20 of `FINAL_AUDIT_REPORT.md`.

**Runtime credential separation (A72):** `MONITOR_ONLY_NO_NEW_BUYS` creates an unauthenticated public MEXC Spot client for tickers, markets, OHLCV, and order-book data. No API key, private account access, or wallet balance is required to discover/read-only opportunities. If recovered positions or unresolved execution intents exist, the runtime may create a separate authenticated client to reconcile/protect them; if credentials are absent or invalid, public discovery continues but protection of those existing positions is explicitly `UNVERIFIED` and new execution stays blocked. Telegram delivery requires `TELEGRAM_BOT_TOKEN` (or `TELEGRAM_TOKEN`) plus `TELEGRAM_CHAT_ID` (or `TELEGRAM_CHAT`). Without those Telegram values, alerts cannot be delivered even if scanning works. A bad MEXC private API key must not disable public discovery. Secrets are never logged. Keep MEXC withdrawal permission disabled and keep all live arms at `0`.

For durable state, attach a Railway Volume at `/data` and set `SCALPER_DB=/data/unified_scalper.db` (plus the documented knowledge/export paths). `SCALPER_DB` and Telegram display/link aliases supplied in `.env` are applied after dotenv loading; process-injected variables retain precedence. Temporary files named `/tmp/v702_r4_streak_*.db` or `/tmp/v702_a42_selftest_*.db` are isolated, disposable self-test databases; they are not evidence that the production ledger is configured to `/tmp`.

## Dependencies and deployment

`requirements.in` is the direct-dependency source. The checked-in `requirements-lock.txt` is a direct-pin seed, **not** a complete transitive hash lock. The GitHub Actions workflow is kept at its historical path `.github/workflows/a65-production-audit.yml` for compatibility with existing release-contract tests, but its current workflow name, artifact, builder, and Docker image tags are A66. It resolves Python 3.12/Linux amd64 hashes at CI time, performs compile/validation/tests, and builds the strict Docker image. This CI workflow was not executed by this local packaging run. Do not describe the current checked-in requirements lock as reproducible with `pip --require-hashes`.

Mount persistent storage at `/data` and set the documented `SCALPER_DB` and knowledge export paths. Never store secrets or runtime databases in this ZIP. A Docker image build and native stop functionality have not been verified in this environment.

## Release integrity

The consolidated Arabic engineering audit and current verification evidence are in `FINAL_AUDIT_REPORT.md`.

From the package root, verify:

```bash
sha256sum -c A66_SHA256SUMS.txt
```

`A66_RELEASE_MANIFEST.json` records the final archive inventory and A66 release decision. `FINAL_MANIFEST.json` is the machine-readable canonical source manifest. `A64_*` and `A65_*` files are retained as historical release evidence; `A66_SHA256SUMS.txt` is the current checksum authority.

## Production decision

**NO_GO_UNATTENDED_LIVE** remains the only supported decision. A65's Adaptive RS results remain Shadow observations, not an edge certification. A66 audit closure additionally separates full-close TP1 economics from the actually sold TP1 fraction, binds Edge evidence to the current economic-model fingerprint and Benjamini–Hochberg FDR result, and rejects unverified candle gaps rather than assigning invented outcomes. Before considering a supervised pilot, correct and verify the deployed MEXC API credentials, collect real timestamped costs and execution observations, run a production-parity historical replay with walk-forward/holdout periods across market regimes, prove stop behavior and restart recovery on the target exchange/account, test Telegram delivery durability, and complete Python 3.12/Linux amd64 CI plus the Docker build.


## A69 — merged production-audit closures (2026-11-15)

- `V702ExpansionShadow` remains in the package and remains directly testable, but its independent 1m polling task is **disabled by default** to avoid duplicating the active 5m counterfactual research stream. Explicit opt-in remains available.
- When enabled, its OHLCV reads use the central `safe_api_call` wrapper under a `knowledge_ohlcv_expansion_*` research label. Forbidden bases are excluded before a sample is queued; unknown spread is stored as SQL `NULL`, not a fictitious zero.
- The 1m tracker marks a gap greater than 90 seconds as `AMBIGUOUS_DATA_GAP` and does not publish net R for that path. Non-ambiguous outcomes use `unified_round_trip_cost_model`; the residual after TP1 uses the same configured fee-covered break-even formula as the live exit manager.
- Hunter Telegram delivery callbacks remain intact. Because callback-bearing messages use the direct queue to preserve ACK/failure semantics, the Hunter now hard-caps all its own alerts at 3 per minute, even if a larger configuration value is supplied.
- The cumulative package-audit revision includes `A69-DOTENV-CONFIG-LOAD-ORDER-CLOSURE-2026-11-15`. The stable A66 release tag and R40 runtime identity remain compatibility identifiers; neither is a claim that the package contains only A66 code.

The package remains `NO_GO_UNATTENDED_LIVE` and `MONITOR_ONLY_NO_NEW_BUYS`. A real MEXC connection, native stop verification, real Telegram delivery, target-platform Docker/CI, a complete transitive hash lock, and profitability from real fills are not established by offline tests.


## 2026-11-16 — Numeric risk-input closure

`SizingEngine.decide` now rejects non-finite Entry/SL/TP inputs and invalid spread/price geometry before reading the balance or calculating a quantity. Rejections are tagged `invalid_price_geometry`. The release also lists the optional Telegram environment-variable names in `.env.example`; every value remains blank/commented. See `FINAL_AUDIT_REPORT.md` section 18 for the rerun results and the remaining Python 3.12, dependency, Docker, Railway, and live-integration limits. This change does **not** lift `NO_GO_UNATTENDED_LIVE` or enable live entries.

## A74 — quality-first opportunities, stablecoin hard exclusion and independent Swing discovery (2026-11-17)

A74 adds a stricter **read-only opportunity research layer** to the existing A66/A67/A68/A73 package. The canonical executable remains `main.py`; the established A70 package identity is preserved and A74 is recorded as a separate Hunter feature revision.

### Alert admission (strong opportunities only)

`WATCH` rows remain available in the SQLite research ledger, but they are not sent as opportunity alerts. A `CONFIRMED` Hunter alert must pass all independent gates: technical score at least 82/100, execution score at least 65/100, higher-timeframe regime score at least 50/100, observed spread no greater than 0.15 percentage points, 24-hour quote volume at least 2,000,000 USDT, and estimated net TP1 reward/risk at least 0.80 after the round-trip cost estimate. A recognized signal-family condition must also pass (volume, breakout chase, positive absolute momentum for relative strength, and the corresponding 1H/4H context). The score is a ranking measure, not a probability of profit.

The bot now reports Technical Quality, Execution Quality and Regime Fit separately. An excellent chart pattern with poor spread/depth/cost is not promoted to a strong opportunity. Missing spread/volume/liquidity evidence fails closed rather than being treated as zero-cost execution.

### Hard stablecoin exclusion

The canonical stablecoin-base denylist now applies unconditionally at the shared stablecoin predicate used by MSE discovery, candidate handoff/preflight and the execution builder. The optional legacy filter toggle cannot re-allow a stablecoin. The Hunter also applies an explicit fail-closed guard. Examples blocked include USDC, USDT, DAI, FDUSD, TUSD, USDD, USDP, PYUSD, EURC, RLUSD and the other configured stable bases. Gold-backed XAUT/PAXG are not classified as stablecoins by this list.

### Intraday and Swing discovery

Intraday continues to use closed 5m/15m market data. A74 adds an independent 1H discovery lane with closed 4H directional confirmation for Swing Breakout, Swing Pullback Reclaim and Swing Relative Strength. Existing MSE strategy candidates marked `SWING` are also retained. Swing outcomes are evaluated on closed 1H candles with a default seven-day observation lifetime; intraday outcomes use closed 5m candles. No additional exchange polling was added: the Hunter uses the existing `market_data_map` only.

Breakout Chase Filter prevents a new strong alert when the closed price is more than 0.65 ATR beyond the measured resistance; far-extended setups are retained as non-alert research candidates where the existing scan produces them. Pullback and mean-reversion confirmation require supportive relative volume. Relative-strength setups require positive absolute momentum as well as BTC-relative outperformance.

### Confluence and deduplication

Different strategy detections on the same symbol/cycle are displayed as confluence on one idea, not independent risk allocations. Initial alerts for the same symbol are rate-limited for 15 minutes. The cooldown timestamp is stored in SQLite after Telegram delivery ACK, so it survives process restarts. Follow-up outcome events are not suppressed by this initial-alert cooldown.

### Shadow outcome and net result tracking

Each persisted idea follows its immutable reference Entry/SL/TP geometry until TP3, SL, expiry, or a data-gap expiry. TP1/TP2/TP3 are modeled using the configured exit weights (default 50% / 30% / 20% when Runner Mode is enabled). The modeled round-trip cost uses observed spread plus two taker fees and two per-side slippage estimates (defaults sourced from the existing project TAKER_FEE_PCT and small-net slippage settings). The ledger records estimated net return, net R, estimated cost and evaluated exit fraction. When data is missing at expiry, the whole-scenario result is **UNKNOWN**, not a fabricated win/loss. If one closed candle touches both SL and a target, SL is counted first conservatively.

These figures are Paper/Shadow reference estimates only; they do not prove an exchange fill, actual fees, realized PnL, or profitability. A partial target touch is never reported as a completed net result for the remaining position.

### Safety and operating mode

A74 does not create orders, enable futures, relax Prequal/Score/PreSend/risk gates, or change the live entry policy. The distribution remains `MONITOR_ONLY_NO_NEW_BUYS` / `NO_GO_UNATTENDED_LIVE`. Keep `UNIFIED_LIVE_PILOT_ENABLE=0` and `UNIFIED_A55_LIVE_ARM=0` during monitoring and validation.

### A74 strong-only policy notes

- The shared stablecoin base-asset denylist is mandatory; `V531_STABLECOIN_FILTER_ENABLE=0` cannot re-enable stablecoin base assets. This is an asset filter, not a guarantee that every supported quote currency is tradable.
- The Hunter uses measured volume evidence for recognized and unknown strategy families. Unknown patterns cannot pass the strong alert gate without measured volume >= 1.0x.
- Initial setup alerts are subject to the Technical / Execution / Regime gates, cost-adjusted Net R:R and the per-symbol persistent delivery-ACK cooldown. Outcome updates remain deliverable even during that cooldown.
- The independent Swing detector requires closed 1H setup candles and closed 4H direction confirmation. It uses the bounded existing market snapshot universe, not every possible exchange listing. The strategy remains Spot-long; no Futures short-side scanner was added.
- Net outcome fields are modeled Shadow estimates using configured fee, spread, slippage and existing exit-weight assumptions. They are not actual account PnL or evidence of profitability. Missing price history at expiry is `UNKNOWN`.


## A75 — نتيجة آخر تدقيق للحزمة المستلمة (2026-11-17)

آخر إعادة تحقق على الحزمة المرفوعة أثبتت 73/73 Python compile، و557 اختبارًا ناجحًا مع اختبار تاريخي واحد متخطى، ونجاح `--validate-only` مع `bot_started=false` و`live_threads=[]`. يشرح `FINAL_AUDIT_REPORT.md` سبب رفض PULLBACK في BTC bearish ورفض السبريد المرتفع، ويفصل حالة ASTER الظلية عن الصفقة المنفذة. لم تُخفف بوابات المخاطر ولم يُضف مسار Shorts/Futures. لا يثبت هذا التدقيق الربحية أو سلامة التداول الحي؛ Python 3.12/Docker وتكامل MEXC/Telegram الحقيقي ما زالت غير مختبرة في هذه البيئة. راجع القسم 22 للتفاصيل وحدود إعادة الهيكلة.


## A76 — Micro Shadow visibility and liquidity evidence

A76 fixes the A9 research-lane selection bug where top relative-strength leaders were prepended to the whole cohort and could consume the micro-liquidity slots before the 1m scan. A new rotating selector reserves approximately half of the bounded batch for eligible micro-liquidity symbols (when both core and micro pools are populated); RS leaders can occupy only a small portion of the core allocation. Runtime logs now expose `core_selected`, `micro_selected`, `rs_leaders`, and fetch/alert counts.

New closed-candle 1m micro samples can create a separate persistent Telegram Shadow alert. Messages are labelled `MICRO SHADOW 1M — MONITOR ONLY`, include reference levels and modeled costs, and explicitly state that they are not live opportunities or orders. The persistent alert table applies symbol cooldown and TTL expiry; a successfully queued message is not described as delivered until Telegram itself acknowledges it. Disable this path with `V702_INTRADAY_SHADOW_TELEGRAM_ALERTS_ENABLE=0`; cap and timing are adjustable with the other A76 variables in `.env`.

`LSA_V1` is an optional evidence schema for future liquidation-to-Spot absorption research. It requires timestamped/source-labelled liquidation, OI, funding, Spot buy/sell-volume and reclaim evidence. A75/A76 does not ship a Futures or Spot-CVD provider, therefore this dimension remains `UNAVAILABLE` unless a real provider is connected. It is informative only and cannot authorize orders. The existing `LIQUIDITY_ACCEPTANCE_RECLAIM` strategy is retained; there is no duplicate LTR strategy. Narrative/Smart-Money, event/Parrondo and cash-secured Put remain outside the Spot scalper.

A76 does not relax the bearish macro family policy, spread ceiling, post-cost profitability filter or any execution/protection gate. The core `MICRO_TREND_CONTINUATION` may still be rejected in bearish BTC macro conditions by design. The new Telegram lane is only for the independent A9 1m research patterns and remains `SHADOW_ONLY_NO_ORDERS`.

## A78 — Micro quality-first alert admission (2026-11-18)

The A78 Micro correction keeps all three 1m strategies in the read-only research ledger, but separates **sample creation** from **Telegram alert admission**. A technically valid 1m pattern is no longer sent merely because the detector fired.

An initial Micro Telegram alert now requires all of the following by default:

- A positive, observed bid/ask spread. Missing, zero, or non-positive spread is treated as unavailable and priced with the configured conservative fallback; it is never interpreted as a zero-cost book.
- The modeled all-in round trip is at most 0.50 percentage points, with estimated net target return at least 0.15% and estimated net target reward at least 0.75R.
- Closed 5m and 15m candles confirm asset trend (5m close above a rising EMA20; 15m close above EMA20), and the asset's 15m return over four bars is not weaker than BTC by the configured minimum.
- Recent 5m/15m/BTC 15m history is sufficiently long, timestamp-aligned, and free of recent candle gaps.

`MICRO_PULLBACK_RECLAIM_1M` remains fully detected and evaluated in Shadow, but its initial Telegram alerts are paused by default pending a larger, independent validation sample. TP/SL/timeout outcome notices are still generated for samples that received a qualified initial alert. This is not a live execution gate, does not select candidates for the canonical MSE, and cannot create orders.

New `.env` controls are documented in `.env.example`: `V702_INTRADAY_MICRO_ALERT_REQUIRE_MTF_CONFIRMATION`, `V702_INTRADAY_MICRO_MTF_MIN_CANDLES`, `V702_INTRADAY_MICRO_ALERT_MIN_NET_PROFIT_PCT`, `V702_INTRADAY_MICRO_ALERT_MIN_NET_R`, `V702_INTRADAY_MICRO_ALERT_MAX_ROUND_TRIP_COST_PCT`, `V702_INTRADAY_MICRO_ALERT_MIN_RS_15M_PCT`, and `V702_INTRADAY_MICRO_PULLBACK_ALERTS_ENABLE`. The runtime defaults are the conservative values described above.

The research report now exposes per-strategy `micro_alert_eligible_samples`, `micro_alert_suppressed_samples`, and suppression reasons, as well as the effective alert-quality policy. Alert messages show the observed spread and closed-timeframe/BTC-relative confirmation evidence. Historical records are not retroactively reclassified.

All A78 changes are monitor-only. `V702_INTRADAY_SHADOW_LIVE_ENABLE` remains hard-false and the canonical entry policy remains `MONITOR_ONLY_NO_NEW_BUYS`. The new gates are intended to reduce weak alerts and improve the quality of opportunities watched; they do not prove a higher realized win rate. Continue paper/Shadow validation and do not enable unattended live trading based on these changes.

## A79/A80 — broad read-only research coverage and Telegram health (2026-11-18)

A79/A80 widen the **research universe** without lowering the canonical trading universe requirements. Up to 500 active Spot/USDT symbols with 24h quote turnover of at least 250,000 USDT are eligible for research discovery, subject to stablecoin/forbidden-market exclusions. Up to 32 additional symbols are fetched per cycle with fair rotation, active Swing follow-up priority, concurrency up to 16 and a 30-second bounded budget. With 46-50 eligible markets, the supplemental cohort is expected to cover the broad universe over a small number of cycles; larger universes rotate progressively. This is not a promise that every listing is fetched on every cycle. The canonical core scanner liquidity floor remains 3M USDT and its `market_data_map` is not mutated by supplemental reads.

The same supplemental 5m/15m/1H/4H context is available to the five A9 Shadow engines. The 1m tape remains fetched only for a bounded rotating batch of up to 32 symbols. Quote turnover uses one shared fallback chain: exchange `quoteVolume`, `baseVolume × last`, then venue-specific turnover fields such as `volValue`. This fixes the prior case where `eligible=0` could be reported despite a populated market ticker snapshot. Market and OHLCV errors remain fail-closed and are surfaced in the `A80-RESEARCH-COVERAGE` counters.

Swing discovery covers breakout continuation, breakout retest, pre-breakout compression, pullback/reclaim, relative strength and early local-recovery WATCH states. Forming patterns remain `WATCH`; they are not confirmed buy alerts. Under descriptive BTC `BEARISH`, local relative-strength recoveries may be watched, but the confirmed-long contract still requires closed local 1H/4H confirmation, positive absolute momentum and measured BTC-relative outperformance. The canonical regime/crash/PreQual/score/spread/cost/PreSend gates remain unchanged.

Telegram command setup now separates inbound polling from outbound delivery: `getMe` and successful `deleteWebhook` are required before polling; `/status` is a read-only digest alias in MONITOR_ONLY; command control is labelled ACTIVE only after a successful `getUpdates` response. A failed startup `sendMessage` is recorded as outbound-degraded but no longer disables inbound `/status` polling. HTTP 409 suspends the poller and requires the operator to remove duplicate Railway replicas/webhooks. Canonical read-only opportunity alerts may be delivered in MONITOR_ONLY when all existing opportunity quality/cost rules pass; this does not grant order authority.

Swing outcome checks use closed 1H candles. Structural stop references use bounded 0.35%-4.0% risk geometry; TP reference levels use 1.8R/2.8R/4.0R, subject to A74 quality, spread, volume and modeled net-cost checks. These are research references, not exchange orders or verified profitability. Defaults remain `MONITOR_ONLY_NO_NEW_BUYS`; `WATCH` remains non-tradeable, and no live orders are enabled.


### A80 release verification

The A80 source package was validated with 594 passing tests and one skipped historical A51-log fixture across 58 test modules; no test failures remain. A80-focused tests passed 14/14 and the A80 self-test passed 10/10. All 73 Python source files compiled, and `--validate-only` exited successfully without starting the bot or live threads. The ZIP contains exactly 99 files. Actual Telegram network delivery, authenticated exchange connectivity, live fills, and profitability remain unverified.


### A81 configuration-wiring fix (2026-11-18)

A81 corrects two research-lane configuration mismatches: A9 intraday Shadow `MIN_QUOTE_VOLUME_USDT` and `MAX_SYMBOLS_PER_CYCLE` now load from the documented environment variables; A79 supplemental research now honors its configured minimum quote turnover, bounded concurrency, and cycle budget instead of hard-coded values. These settings affect research coverage only. The canonical tradable Spot universe still requires at least **3,000,000 USDT 24h quote turnover** (and strategy/tier policies may require more); the 250,000 USDT A79 floor and 500,000 USDT A9 shadow floor do not authorize a live entry. `MONITOR_ONLY_NO_NEW_BUYS` remains the effective entry policy.


### A81 verification status

A81 final validation: 595 passed, 1 historical fixture skipped, 0 failed (596 collected across 58 test modules); 73/73 Python files compile; `--validate-only` exits 0 without starting the bot or live threads. The clean ZIP contains 99 files and passes CRC/manifest checks. The audit environment did not have `ccxt` or `aiosqlite` installed, so networked exchange/Telegram integration, target-runtime soak, live fills and profitability were not verified.

## A83 — USDC/USDT Shadow spread-capture lane (2026-11-19)

A83 adds an independent, read-only MEXC Spot research lane for `USDC/USDT`. It is **disabled by default** (`STABLECOIN_MM_ENABLE=0`) and can be intentionally enabled in read-only `SHADOW` mode by setting `STABLECOIN_MM_ENABLE=1`. An existing deployment `.env` or platform variable overrides the package default. It reads the public order book and public trade prints through CCXT; it does not require wallet access for the Shadow lane and does not submit exchange orders. Where the normalized trade aggressor side is missing, it can derive the taker side from MEXC raw `isBuyerMaker` metadata. `STABLECOIN_MM_LIVE_ARM` is informational only and cannot arm execution.

The Shadow lifecycle is persisted in SQLite (`stablecoin_mm_cycles` and `stablecoin_mm_events`) and restores an active cycle after restart. It tracks a simulated passive BUY quote, partial market-print fills, a cost-aware SELL quote, partial exits and a closed-cycle net estimate. A price touching a limit is **not** counted as a fill: public trade prints must cross the simulated price, or execute at the exact price after the visible queue-ahead estimate has been consumed. This remains an L2 approximation, not exchange-confirmed execution or a full queue-position reconstruction.

Eligibility checks include valid non-crossed book, spread ceiling, USDC/USDT depeg band around 1.00, minimum depth on both sides, recent trade-flow evidence, estimated maker fees, slippage allowance, and a minimum net-edge / minimum-dollar-profit floor. The default fee model is a deliberately conservative fallback of `0.001` (0.1%) per side. A public `market.maker` value from CCXT is deliberately **not** treated as proof of the account-specific fee, because public market metadata may expose a generic/default rate. `STABLECOIN_MM_MAKER_FEE_RATE_OVERRIDE=0` is accepted only as an operator-supplied assumption after verifying the exact account, pair, and current fee terms; the code does not verify that promotion itself. With the default 0.1%/side fallback, 20 bps of round-trip fees exceed the default 12 bps spread ceiling, so no quote should pass until a verified lower maker-fee assumption is configured. This fail-closed behavior is intentional. The daily report is UTC and is queued through the existing durable Telegram Outbox.

The current implementation is a **Shadow research engine**, not a live market-making bot. The following are not claimed: actual exchange fills, realized wallet PnL, verified personal fee rate, historical profitability, or 24/7 MEXC/Telegram soak. A83 live order submission is intentionally absent; the existing canonical `MONITOR_ONLY_NO_NEW_BUYS` policy and all other live risk gates are unchanged.

See `.env.example` for A83 settings. For an intentional shadow run, set `STABLECOIN_MM_ENABLE=1`, keep `STABLECOIN_MM_MODE=SHADOW`, retain a durable `SCALPER_DB` mount, and leave `STABLECOIN_MM_LIVE_ARM=0`. Shadow monitoring starts automatically when `STABLECOIN_MM_ENABLE=1`; the task now retries transient market-metadata failures, and sends periodic Telegram status with the last reject reason plus observed spread/net-edge/required-edge metrics. It still will not fabricate trades: with a 0.1%/side fallback (20 bps round-trip) and a 12 bps spread ceiling, it correctly rejects every quote as economically unviable until a verified account/pair fee assumption is configured.


## A84 — A79 research fetch and A83 data-integrity closure (2026-11-19)

A84 fixes the undefined monitor-scan helper used by the A79 supplemental 5m/15m/1H/4H fetch. With monitor-only scanning authorized, the bounded supplemental fetch can execute again; with scanning disabled, it returns without exchange reads. Its snapshots remain marked research-only and are never added to the canonical trading map.

The A83 Shadow stablecoin simulator now fails closed on non-finite top-of-book values, non-finite print volume/prices, missing exchange book timestamps, and future-dated public prints. The default fee assumption remains 0.1% per maker side; with the default 12 bps maximum spread, the lane should reject quotes unless a lower account/pair fee has been independently confirmed and explicitly configured. No trade orders are possible in this A83 path.

The supplied 2026-11-18 Micro Shadow report was negative across the reported strategies. Accordingly, no Micro engine was promoted to live execution and no bearish family-policy gate was weakened. The broader A79 data collection is for additional read-only research and WATCH-level discovery only. It is not a promise of frequent opportunities or daily income.

A84 regression coverage includes scan authorization, research-map isolation, non-finite book/print rejection, timestamp freshness and future-print handling. See `FINAL_AUDIT_REPORT.md` for the full evidence and final test totals.


## A85 — BTC directional policy removal, multi-detector confluence and A83 auto-monitor (2026-11-19)

- BTC BULLISH/NEUTRAL/BEARISH is now **observational** in the canonical family policy by default (`V410_FAMILY_MACRO_DIRECTION_GATE_ENABLE=0`). This removes the prior family-wide directional veto, not market safety: missing macro context still fails closed; confirmed `CRASH`/`EXTREME`/`HARD_REJECT` severity remains an unconditional blocker; each coin must still pass its own closed-candle HTF/local structure, liquidity, spread, fee, scoring, queue and pre-send gates. The old BTC directional veto can be restored explicitly with the environment key set to `1`.
- BTC macro values remain reported for context. The scanner's 4H structural / 15m shock assessment remains as a systemic crash guard; it is not used as a blanket bearish regime veto. Symbol-local 1H/4H and intraday confirmation are retained.
- The router continues evaluating all nine registered technical detectors in one scan and chooses one canonical candidate. Independent detector groups (pullback, breakout, sweep, momentum, mean reversion and trend) add only a small, capped corroboration score; correlated variants collapse into one group. This does not create duplicate orders or bypass any hard gate.
- A83 is disabled by default in `.env.example`. When `STABLECOIN_MM_ENABLE=1` is explicitly configured, it runs in `SHADOW`, reports startup/periodic status and detailed cost diagnostics, and retries transient data failures. It never calls order endpoints. Existing `.env` values take precedence.
- Fee fallback remains 0.1% per side until the exact account/pair rate has been verified. This means the default quote edge is intentionally non-viable versus the configured 12 bps spread cap; the worker now reports this instead of appearing silently disabled. Never set the override to zero solely because a consumer-facing promotion advertises zero fees.
- New detector confluence is an advisory score modifier only. Micro 1m strategies and all intraday research engines remain Shadow-only because the supplied outcomes were net-negative; no daily income or positive expectancy is inferred.
- Live entries remain under the existing `MONITOR_ONLY_NO_NEW_BUYS` release policy; no API keys are introduced and no live orders are submitted.
