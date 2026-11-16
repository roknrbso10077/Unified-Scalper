# UNIFIED SCALPER V702 — A66 CANONICAL BASE + A67 HUNTER + A68 TP/SL OUTCOMES + A69 AUDIT CLOSURES + A70 ENTRYPOINT + A71 CORRECTIVE INTEGRATION

**Release ID:** `UNIFIED-SCALPER-V702-A66-CANONICAL-FINAL` (A67 read-only Hunter + A68 outcome follow-up + A69 config/audit closures + A70 entrypoint identity closure)  
**Release date:** 2026-11-16 (A71 corrective integration; canonical A70 lineage retained)  
**Canonical executable:** `main.py`  
**Base runtime lineage:** A64  
**Production decision:** `NO_GO_UNATTENDED_LIVE`

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
- **CONFIRMED:** either a named technical trigger from closed candles (explicitly labelled *technical-only*, not Prequal) or a canonical `PREQUAL_PASS` / `SCORE_PASS` event.
- **TRADEABLE:** emitted only after canonical `PRESEND_PASS`. This means the candidate passed the existing pre-send checks; it does **not** mean an order was sent, accepted, or filled.
- **INVALIDATED / EXPIRED:** the stored thesis is closed when a closed price crosses its invalidation level or its bounded lifetime expires.
- **COMPLETED:** A68 has recorded a final TP3 touch in the shadow-reference ledger; this is not an executed trade or realized profit.

States move forward only. Terminal rows are not resurrected by stale candidate events. Records persist in the SQLite `opportunity_hunter` table. Telegram state alerts are rate-limited and include analytical entry reference, invalidation level and scenario TP1/TP2/TP3 levels (not executable orders or guaranteed targets), with delivery status callbacks; they never grant execution authority.

### Pattern lanes and evidence

The bounded closed-candle scanner evaluates **BREAKOUT_CONTINUATION**, **PULLBACK_RECLAIM**, **MEAN_REVERSION**, and **RELATIVE_STRENGTH_LEADER**. It uses closed 5m/15m bars, validates OHLC relationships, rejects duplicate timestamps and stale/short history, and compares relative strength with BTC when the BTC 15m snapshot is present. The layer also observes genuine long Spot USDT candidates emitted by the existing strategy engines; it does not fabricate engine invocations or change their scoring.

Default resource limits: a configured ceiling of 240 symbols per cycle, 6 new pattern alerts per scan, and a hard maximum of 3 alerts per minute; the internal ranking floor remains 55/100, opportunity TTL 3,600 seconds, and active-record cap 1,200. **240 is not the actual scan count:** the Hunter reads only keys already present in `market_data_map`. That map is bounded upstream by the existing deep-scan selection (V699 targets normal=130, elevated=150, starving=170 when that arbiter is active; actual coverage can be lower when snapshots fail validation). No additional exchange request is made for Hunter discovery. Delivery callbacks are preserved on the direct dispatcher path, so the 3/minute hard cap is enforced locally rather than sacrificing ACK/failure handling. The Hunter score is a ranking heuristic, **not** a probability of profit or a validated edge. Candidate and technical confirmations remain distinct from the canonical execution pipeline.

The feature remains active in monitor-only mode: `MONITOR_ONLY_NO_NEW_BUYS`. No live BUY, exchange execution, risk/score/liquidity gate relaxation, or profitability claim is added. Live MEXC and Telegram delivery still require target-environment verification.

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
