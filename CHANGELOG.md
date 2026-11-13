# A58 — Production audit canonical closure (2026-11-11)

**Active distribution:** `UNIFIED-SCALPER-V702-A58-CANONICAL-FINAL`. The A58 layer preserves the strategy and risk model while closing release-integrity, non-blocking storage, paper-evidence, health and exchange-load inconsistencies.

- Unified release identity and production disposition: `NO_GO_UNATTENDED_LIVE`; A57 checksum artifacts are historical only, and A58 has its own manifest and SHA-256 index.
- Disabled the legacy-token-only authorization fallback; a missing canonical entry-policy resolver is a hard block.
- Routed KnowledgeOutcomeLedger work from async tasks through worker threads and one process-wide writer lock.
- Added runtime and PositionManager heartbeats; with open positions, health requires a fresh PM heartbeat from the same process boot. Startup restores/reconciles protection before scanning.
- Unified conservative round-trip cost assumptions across Paper, Shadow, sizing and live pre-send evidence.
- Applied stop-first resolution to same-candle SL/TP collisions; crash, unavailable, malformed and incomplete HTF reasons cannot enter HTF-relief learning.
- Standardized paper-ledger capacity to 20 by default and 120 maximum; selected-route paper fills require a buffered breakout, with gap fills priced at candle open.
- Added explicit operator-controlled ignored-asset list and short-lived exact-symbol ticker cache to portfolio valuation; unpriced non-ignored holdings still fail closed.
- Added a process-wide token bucket in `safe_api_call`, reserving request headroom for protection and execution ahead of scan/research.
- Added an AST contract for wrapper order and every `submit_entry(intent_context=...)` callsite.
- Shortened the operator README, clarified the A53 baseline as historical, added pytest faulthandler diagnostics and Python 3.12/linux-amd64 CI with hash-lock generation and Docker heartbeat probes.
- Preserved Spot LONG_ONLY, Futures off, score floor 70, all prior market/economic/structure/protection gates, 2-position ceiling, 75-USDT ticket ceiling and forbidden-base list. No live gate was relaxed.

**Verification boundary:** local offline tests/validation do not verify MEXC order/fill/cancel/partial-fill recovery, real Telegram delivery, target-host execution, native stop availability or profitability. Keep unattended live trading disabled.

---

## V702 A57 — certified stop-mode and first-success PM health-lease closure (2026-11-06)

- `_v702_position_manager_health_ok()` now fails closed if the production capability gate is absent, has not completed successfully, exposes no stop mode, or reports a stop mode unsupported by the canonical executor.
- The software-SL health lease now starts invalid (`0.0`) and becomes fresh only after a successful manager cycle; a task that starts but fails its first protection cycle cannot authorize a new BUY.
- Added regression coverage for uncertified/unknown stop modes and failed first PositionManager cycles. Existing Spot LONG_ONLY, forbidden-asset, two-key live arm, candidate-context, EdgeGate, economic, liquidity, risk, and execution hard gates are unchanged.
- No live keys were enabled; no exchange/Telegram network calls were made. Unattended live operation remains NO-GO pending target-runtime CI, Docker build, and controlled MEXC/Telegram/stop integration.

## V702 A56 — authorization, Shadow timestamp and software-SL health closure (2026-11-06)

- Context-free/empty-context live BUY is denied; final EdgeGate approval remains mandatory for a non-empty candidate context.
- `production_guardrails` now relies on the canonical two-key A55 arm; the legacy token is diagnostic only.
- Software-SL mode requires a fresh successful PositionManager health lease and valid protection for every open trade before new live entries.
- Shadow PreSend rejects invalid/future order-book timestamps (1s clock-skew tolerance).
- Historical release tests and manifests updated to the actual append-only A56 revision; new regression tests added.
- No strategy thresholds, position caps, SPOT LONG_ONLY rules, forbidden assets or economic gates were relaxed. Live network, Docker and profitability are not claimed.

---

# UNIFIED SCALPER V702 — release history (A58 current)

**Current distribution:** `UNIFIED-SCALPER-V702-A58-CANONICAL-FINAL` (2026-11-11). A58 is the active monitor/paper package. A57 and earlier references below are historical lineage; see `A58_FINAL_AUDIT_REPORT_AR.md`, `A58_RELEASE_MANIFEST.json`, and `A58_SHA256SUMS.txt` for the current audit, release evidence, and limitations. Historical validation logs do not describe the A58 package. Offline validation does not prove live exchange execution, Telegram delivery, deployment correctness, or profitability.
- Fixed blocked-opportunity correlation to use the last closed 5-minute candle key, so a forming candle cannot silently prevent matching the pending opportunity and its rejection notification.
- Made canonical strategy-contract timeframe authoritative during candidate normalization, preventing stale scalp metadata from overriding the MTF/SWING contract.
- Added a tracked Telegram event immediately after an actual fill, followed by a separate protection-pending/protected/protection-failed event. These messages include LIVE/PAPER mode, strategy, timeframe, actual fill quantity/price, order ID(s), stop/targets, score and trace ID; dispatcher ACK/failure callbacks now make delivery outcomes observable.
- Fixed blocked-opportunity matching to use the same closed-candle key; a filled trade whose stop setup fails is no longer returned as a false “no execution” result. Such a position emits a critical protection-failure alert, stays registered, and blocks new entries rather than being misreported as absent. Exit/stop-loss notifications carry trace metadata and an explicit stop-loss headline; enqueue rejection releases the dedupe key for retry.
- Made the canonical strategy contract authoritative at the execution boundary too, so stale SCALP/timeframe metadata cannot switch a SWING contract's risk geometry and trade record back to 5m/1m semantics.
- Added per-style generated, actually filled, closed-count and realized-R telemetry, plus top swing blockers and frame-specific trade logs. This diagnoses swing scarcity without forcing trades or relaxing regime/family/score/risk gates.
- Preserved SPOT LONG_ONLY, forbidden-asset exclusions, live score floor, and risk/economic/exposure controls. A53 remains offline-validated only; no real MEXC/Telegram execution or profitability is claimed. Production decision remains NO-GO for unattended live trading.

---

# V702 A52 — safety hardening and canonical outcome coherence (2026-10-21)

- Hardened `CompositeScorer` inputs: reject non-finite/out-of-contract numeric values and treat the `-999` HTF sentinel as missing evidence, never as a quality score. The live score floor remains 70.
- Preserved definitive `REJECTED_NO_ORDER` outcomes instead of converting them to submission-unknown in an outer exception path. If a venue order ID is already known but a persistence write fails, keep the entry latch engaged and continue reconciliation/protection instead of treating the order as absent.
- Added a persisted MEXC Spot `clientOrderId` only when the active order method supports `params`; reconciles an unknown entry by exact client ID and stays unresolved on errors or mismatch. No automated live BUY retry is enabled.
- Hardened target-only exits: account for unfilled quantities reserved by existing open targets, stop creating additional targets when an order state or create response is ambiguous, and do not clear ambiguity without explicit finite exchange quantities.
- Bounded HTF rejection memory with TTL/cap; made Telegram queue eviction settle the removed message's failure callback; made pipeline-window snapshots consistent under one lock; and bound prequal observation to the same candidate context.
- Normalized only telemetry `reason_code` buckets while retaining raw rejection details; fixed Crash Guard diagnostics and made `healthcheck.py` fail closed on non-finite heartbeat values. The configurable event-buffer validation no longer hard-requires the default 20,000 count.
- Updated release/test identity to A52 while preserving the complete A21–A49 provenance chain. Tests must validate the active distribution; historic A51 logs remain historic evidence.
- No strategies were removed. SPOT/LONG_ONLY, forbidden-asset exclusions, crash guard, family/regime restrictions, score floor, liquidity/spread/order-book gates, fees/net economics, position sizing, stops and exposure controls remain unchanged.
- Validation status: all `.py` files compile; four focused numeric/health/reason tests pass; manual deterministic mock checks pass for target reservation, ambiguous target creation, exact MEXC client-ID reconciliation, and Telegram eviction callbacks. `--validate-only` and the full current pytest suite did not terminate cleanly in this environment and are **not claimed as passing**. No real exchange/Telegram, native-stop, Docker/Railway or profitability test is claimed. Production decision remains **NO-GO for unattended live trading**.

---

# V702 A51 — early bearish-policy rejection and event-window boundary closure (2026-10-20)

- Added a bounded early prequal policy check for BEARISH non-crash candidates already disallowed by the canonical family policy. It runs after basic quote-volume/tier/spread checks and before costly order-book/HTF resolution; the policy decision, score floor, and execution gates are unchanged.
- Preserved crash-guard priority and fail-closed fallback when early policy evaluation is unavailable. No bearish live allow-list expansion or gate bypass was added.
- Aligned telemetry rolling-window bounds to integer-second buckets across event counts and retained records, preventing fractional-cutoff false counter mismatches.
- Added A51 regression tests for event-window alignment, early rejection before downstream work, and unchanged live safety contracts.
- Validation: 376/376 tests pass across four non-overlapping batches and 49 modules; `py_compile` passes; `--validate-only` exits 0 with `pass=true` and no live threads.
- Operational status remains **NO-GO for unattended live trading**: real MEXC order/protection behavior, real Telegram delivery, deployment and profitability remain unverified.

---

## 2026-10-19 — A49 final deployment hardening

- Create the parent directory for file-backed `SCALPER_DB` paths before SQLite schema initialization; expose non-writable persistent-volume permissions as a clear startup error.
- Log full tracebacks for config-validator exceptions and unexpected runtime exceptions without swallowing or converting them into a success state.
- Emit an explicit one-shot marker when `--validate-only` / validation environment flags intentionally exit without starting `run_bot`; document the correct persistent-service start command.
- Prepare `/data` as an appuser-owned directory in the image, compile copied runtime modules at Docker build time, and retain the documented caveat that a mounted volume can override image ownership.
- Trading policy and execution authority are unchanged. No live MEXC, Telegram, native-stop, Docker/Railway deployment, or profitability proof is claimed.

# V702 A49 — elite HTF-relief consistency and complete quality rejection attribution (2026-10-19)

- Fixed the elite-quality rejection attribution branch so every rejected quality dimension (HTF, volume/liquidity, score/relative strength, structure, retest, and related reasons) records its classified reason at the same rejection site. The rejection itself remains fail-closed; the change improves evidence and does not turn a rejection into a pass.
- Made the existing A36 closed-local-evidence HTF relief reusable by the later elite context gate only for PULLBACK/MTF_PULLBACK when the same candidate identity, symbol, family/mode/style, macro regime/severity, HTF state/value, 5m closed-bar evidence, and fresh 15m evidence still match. Any missing, stale, changed, or unverifiable evidence falls back to the original strict HTF floor.
- Relief affects the HTF threshold only. Score floors, structure, volume/liquidity, relative strength, retest, setup quality, chase, fees/net economics, position sizing, stop/protection, order, balance, and execution gates remain unchanged.
- Kept the global live score floor at >=70, kept the 65–69.99 band shadow-only, kept PULLBACK disallowed in BEARISH regime, and kept BEARISH_NORMAL_LSR research-only. No general bearish-market entry permission or hard-gate bypass was introduced.
- Added regression tests for successful same-candidate relief, stale/missing evidence fail-closed behavior, untouched score and liquidity gates, and exactly-once taxonomy mapping for each elite quality rejection family.
- Offline validation only. This revision does not certify live MEXC order/fill/cancel, native stop protection and recovery, real Telegram delivery, Docker build, dependency hash-lock completeness, or out-of-sample profitability. Operational decision remains **NO-GO for unattended live trading** until those release gates are completed.

---

# V702 A48 — canonical production-audit closure (2026-10-19)

- Unified candidate/stage/reason rejection attribution across the canonical rejection recorder, prequal and preflight history, and queue-handoff diagnostics. The digest now reports the unified unique-key count while retaining explicit source/stage separation; a count mismatch is visible instead of being silently inferred.
- Corrected event-time retention reporting: rolling-window drops count only drops with verified event timestamps in that window; cumulative epoch drops are separately labelled; counter disagreement makes coverage uncertain instead of fabricating a window-drop total. Delayed/out-of-order evictions are handled by sorted event-time buckets.
- Made `PRESEND_PASS` without same-candidate queue/route evidence an explicit diagnostic `PREEXEC_BLOCK`; it records the gap but does not retry or submit a new order.
- Exposed measured and required TP1-distance values in the rejection reason and added a stable `score_below_feasible_floor` reason token. The hard live score floor remains 70/100; configurable values are bounded to 70–80 and no automatic relaxation was added.
- Added a strict `BEARISH_NORMAL_LSR` counterfactual lane for research only: LIQUIDITY_SWEEP_REVERSAL, BEARISH with normal severity, score >=70, HTF >=47, volume ratio >=1.4, and quote volume at/above the existing core floor. The lane stores a hypothetical 0.5 sizing annotation only; V518 live expansion stays disabled, the lane never routes orders, and evidence still requires at least two weeks and adequate resolved samples before a policy decision.
- Extracted first-wave pure helper modules under `v702_core/{policy,scoring,pipeline,execution,telegram}` and wired them into the existing runtime as owners for reusable policy/floor/telemetry/handoff primitives. `main.py` remains the sole canonical executable; a complete monolith split is not claimed.
- Updated Docker packaging to include the new runtime helper package. Added A48-focused tests for the unified rejection façade, event-time ordering/retention, queue gap classification, score/TP1 diagnostics, shadow-only policy and release metadata.
- Preserved Spot LONG_ONLY, forbidden-asset exclusions, existing family-regime gate, minimum live score 70, core liquidity/volume/order-book/fee/net-cost/position/risk/SL/TP/native-protection gates, and the monitor-only deployment default. No gate bypass or bearish live expansion.
- Release evidence is offline only. A complete transitive hash lock could not be produced because the resolver could not reach PyPI/Python 3.12, and Docker/Railway, real MEXC order/fill/native stop, real Telegram opportunity delivery, and out-of-sample profitability were not verified. Therefore the operational decision remains **NO-GO for unattended live trading**.

---

# V702 A46 — 2026-10-18

- Corrected rolling-window event-drop attribution to use the timestamp of the actually evicted event, while keeping cycle and epoch eviction counters separate.
- Added bounded read-only macro policy evidence to the operator digest so repeated `family_regime_disallowed.macro` rejections expose strategy/family, observed regime, allowed regimes, and evidence provenance.
- Kept macro-policy allow-lists, minimum live score 70, all risk/economic/HTF/order/protection gates, denylist, and Spot LONG_ONLY behavior unchanged. No live gate bypass was introduced.
- Added regression tests for old-event eviction timing, macro evidence, and digest presentation. See the A46 audit report for measured validation and limitations.

---

# V702 A45 — 2026-10-18

- Separate pipeline telemetry ring-buffer drops by cycle, live epoch, and rolling 1-hour window; retain the backward-compatible `dropped_total` field as an explicitly epoch-scoped alias.
- Add `interval_sec`, observed-window event counts, window drop count/percentage, and explicit `cycle_dropped` / `epoch_dropped` fields to pipeline-window digests while retaining compatible `WINDOW_15M` / `WINDOW_30M` labels.
- Fix `buffer_truncated` attribution to require in-window evictions, a full retained buffer, and retained timestamps that indicate possible loss within the queried interval.
- Improve `_publish_locked` throughput with incrementally maintained stage counts and dirty-triggered top-rejection sorting; keep updates synchronous under the existing lock to preserve ordering.
- Add `starvation_root` and `root` to the starvation digest.
- Align legacy live score-floor defaults, fallbacks, and self-test diagnostics to the canonical 70/100 floor. Preserve the macro-family hard policy and bearish bridge fail-closed behavior.
- Extend the heartbeat payload with rolling telemetry metrics. Make healthcheck degradation visible above 10% drop ratio by default; failing the liveness check is opt-in to avoid potentially unsafe supervisor restarts during live position management.
- Add offline regressions for counter scope, starvation-root truth, score-floor parity, fail-closed bearish bridge, and telemetry health reporting.
- **Not implemented for safety:** automatic score-floor relaxation and MEAN_REVERSION exceptions under `BEARISH_STRESSED`; the provided evidence does not establish that these are safe policy changes.
- **Release status:** offline-validated only; NO-GO for unattended live operation until controlled live integration and profitability evidence exists.

---

# A44 — balance hysteresis, root-cause coherence, safe starvation and digest closure (2026-10-18)

- Added actionable `FUNDING_LATCH` / `OPS_LATCH` diagnosis and one transition-scoped alert hook. The funding summary surfaces exchange free USDT, minimum, 110% release threshold and block age; a missing async loop leaves the alert pending rather than consuming the transition silently.
- Added balance-unlatch hysteresis. Only approved balance-only roots can be cleared, and only with a fresh real free-balance snapshot at `free >= 1.10 * minimum`. Execution-intent/protection/kill-switch latches cannot be cleared by balance recovery.
- Unified entry-root precedence and gave balance and macro family policy their own diagnostic buckets. `family_regime_disallowed.macro` is now a distinct policy bucket; telemetry reasons do not change trade admission.
- Pinned every live score-relief floor to >=70 and suppresses V453 score relief under every detected safety hazard. `MIN_LIVE_SCORE`, `V453_SCORE_FLOOR_MIN`, and `V420_ADAPTIVE_FLOOR_MIN` are aligned at 70; V420 state itself clamps to 70. V704 retains its hard global floor.
- Distinguished opportunity starvation from global latches, reports per-cycle `safety` rejects, emits one aggregate latch-cycle event, and retains per-candidate safety checks as defense in depth.
- Added telemetry-only shadow policy attribution from existing candidate/snapshot data, family-aware read-only entry diagnostics, and 30-minute suppressed-exception stage/rate telemetry.
- Corrected the digest's early truncation so structured line partitioning sees the complete summary first; Telegram payloads are split under 1700 characters with latch/action at highest priority. Excess beyond the bounded number of parts is marked explicitly.
- Added a post-validation/live-arm guard for risk-sensitive config drift; an unvalidated or changed snapshot prevents live epoch arming. Risk keys are blocked from mutation once the live epoch is armed.
- Added regression coverage for root precedence/bucket parity, 70-point floor across V453/V699/V704, balance hysteresis, safety-latch starvation separation, telemetry-only policy shadow, bounded digest partitioning and config drift.
- Closed a secondary score-floor leak: `V420AdaptiveFloor.compute()` now clamps the stored adaptive state itself to at least 70, and V693 rescue cannot reduce it under a safety latch. Fixed `V612` to validate the *effective live floor* rather than falsely rejecting a lower intermediate family floor when the final floor remains >=70.
- Final offline verification for A44: full pytest **337 passed / 0 failed** (27.52 s); focused balance/intent/release closure suite **92 passed / 0 failed** (13.53 s); `py_compile` and `--validate-only` both exit 0, the A44 self-test passes, `hard_gate_bypass=false` and `live_threads=[]`.
- Dependency constraint note updated: a full transitive hash lock was attempted but not generated because PyPI/Python 3.12 could not be reached in this environment. No hashes were invented. A connected CI resolver and `pip --require-hashes` verification remain required.
- Preserved Spot LONG_ONLY, Futures/Short prohibition, denylist, position caps, economic/fee, volume/liquidity/depth/spread, HTF/structure, SL/TP/protection and `hard_gate_bypass=false`.
- Release boundary: offline tests and `--validate-only` cannot prove live MEXC orders/fills, exchange-native SL protection, Telegram delivery, Docker/Railway deployment or profitability. Unattended live trading remains NO-GO until controlled live integration passes.

---

# A43 — HTF crash-vs-trend discrimination and truthful depth-ratio evidence (2026-10-18)

- Corrected the global BTC bearish-severity classifier so a sequence of closed 4H lower lows alone is classified `BEARISH_STRESSED`, not `BEARISH_CRASH`. Confirmed hard-crash evidence remains blocking: missing/invalid macro evidence, explicit BTCContext `CRASH`/`BLOCK`, a closed 15m drop at or beyond the existing -6% threshold, or a drop at/beyond the existing -3% stress threshold with ATR expansion at or beyond the existing 2.5x threshold. This is a specific severity-classification correction, not a blanket trend bypass; downstream strategy/family, closed-bar HTF, score, volume, liquidity, spread, fee/net-cost, sizing, risk, order and protection gates remain active.
- Added structured `A43_BEARISH` facts with closed-bar drop %, current/reference ATR and ratio, closed 4H lows, breakdown pairs, BTC context state, thresholds, cause and explicit `decision_changed_from_a42` so the deliberate classification delta is not misreported as unchanged.
- Fixed the A9 exact-book handoff's explicit `depth_ratio=0.0` sentinel: it can be derived only from a provenance-stamped exact order book with an accepted fetch status, valid positive finite top-of-book levels, a valid timestamp and age inside the configured freshness bound. Untrusted, missing, malformed, future or stale book evidence is not promoted to a valid ratio and remains fail-closed at the relevant liquidity gate.
- Added `A43_DEPTH` numeric fields for ratio, floor, source, age, bid notional, required notional and derivation/rejection reason. The recorder itself is telemetry-only; `admission_input_derived` separately indicates when the existing liquidity gate consumed a ratio derived from the trusted exact book. Liquidity floors and Micro recheck boundaries were not lowered.
- Added regression tests for ordinary 4H bearish structure, genuine 15m crash conditions, missing data, explicit BTC hard-crash context, the zero sentinel, valid fresh exact books, stale/untrusted books, numeric diagnostics, heartbeat visibility, revision lineage, Spot LONG_ONLY, no Futures and `hard_gate_bypass=false`.
- Offline verification artifacts: `results/V702_A43_VALIDATE_ONLY.log`, `results/V702_A43_PY_COMPILE.txt`, focused/full pytest logs and `results/V702_A43_VALIDATION_SUMMARY.json`. These do not claim live MEXC orders, live Telegram delivery, native stop verification, deployment, or profitability. Unattended live trading remains NO-GO pending controlled integration verification.

---

# A38 — 30-minute operator digest, HTF evidence and shadow consistency closure (2026-10-16)

- Set the noncritical Telegram operator digest to 1800 seconds (30 minutes). The rolling `PIPELINE[WINDOW_15M]` analytics window stays at 900 seconds. Critical execution/order/protection/control/error notifications remain immediate; the software-SL watchdog behavior and missed-heartbeat limit are unchanged.
- Added bounded, telemetry-only records for HTF crash-guard evidence and a concise recent Builder-None record in the existing heartbeat without changing rejection decisions or fabricating candidate attribution.
- Fixed shadow spread/ATR recording to consume closed-bar-derived ATR context even when a nested candidate feature payload is incomplete; remains `SHADOW_ONLY`, with no quote/spread ceiling relaxation.
- Aligned realized knowledge-ledger same-bar TP/SL outcome classification with conservative SL-first. Earlier targets proven on earlier bars are retained; a target first touched in the same ambiguous OHLC candle is not counted as reached.
- Kept all existing entry, HTF, history, score, liquidity, structure, fee/net-cost, denylist, Spot LONG_ONLY, position sizing, order, stop and protection guards unchanged.
- Package scope is the current canonical runtime, required guardrails/modules, tests, current validation artifacts and current audit; historical audit snapshots/results are omitted from the GitHub upload bundle. No secrets, live credentials, live MEXC order, actual Telegram delivery, Docker/Railway deployment or profitability are claimed.

---

# A37 — canonical production audit closure (2026-10-16)

- Fixed the digest blocker formatter to prefer structured symbol/root/stage/reason records; section headings no longer leak into a block reason when log sections are concatenated without whitespace.
- Fixed the elite-quality helper exception path so a malformed profile falls back to the highest configured family score floor (minimum 80 by default), not the weaker general 70 floor; added an exception-path regression. Score-block context also records `score_floor_used`, canonical floor and floor source without changing final gate authority.
- Enforced conservative SL-first handling when one closed candle touches both a target and stop in shadow outcome attribution.
- Completed shadow-only spread/ATR diagnostics from raw ATR and price when the precomputed ATR percentage is absent; no spread ceiling or quote band was changed.
- Added a window-level entry-root summary with counts/confidence/age and explicit cycle/window funnel scopes while preserving the original heartbeat/digest observer identities.
- Added bounded Telegram HTML repair; added reject-only short-history repeat diagnostics with explicit `SHORT_HISTORY_UNVERIFIED_NOT_PROVEN_NEW_LISTING`; no short 4H history can become live-valid by this label.
- Added heartbeat-freshness-only Docker health check and `.dockerignore`, pinned the direct aiohttp dependency, and organized root audit reports under `docs/audits/`.
- Retained Spot LONG_ONLY, no futures/shorts, the >=70 live floor, all volume/depth/spread/fee/net-cost/HTF/structure/fake-break gates, denylist, position/ticket caps, KillSwitch, TruthSeal, PreSendGate, order/stop/protection controls, and `hard_gate_bypass=false`.
- Offline tests and validate-only do not establish live MEXC fills, real Telegram delivery, native stop verification, Docker/Railway deployment, or positive profitability. The lockfile pins direct dependencies only; complete transitive hash locking remains open.

---

# A35 — HTF projection / Builder parity closure (2026-10-16)

- The canonical score projection now replays the closed 1H `HTFGrader` result instead of inferring `htf_pass` from a numeric strength alone.
- Missing 1H data, zero/invalid HTF evidence, and HTF reject states that may still be handled by the established resolver/bridge/recovery path remain incomplete projection results. An incomplete projection cannot create a canonical score hard-block and preserves original selector ranking; the Builder and downstream live gates remain authoritative.
- Added A35 terminal release contract and regressions for stale snapshot HTF values, failed HTF grade, missing 1H evidence, exact-route hard-block refusal on incomplete projection, and unchanged SPOT LONG_ONLY/hard risk floors.
- No change to score, liquidity, spread, fee, position sizing, forbidden assets, queue/Telegram authorization, order placement, stop-loss, or protection thresholds. `hard_gate_bypass=false`.
- Live MEXC orders/fills, real Telegram delivery, production stop capability, deployment and profitability remain unverified offline.

See `docs/audits/FINAL_PRODUCTION_AUDIT_A35_CANONICAL_AR.md`.

---

# A33 — align adaptive local 1H history and prequal diagnostics (2026-10-15)

- Fixed a real policy mismatch: A32 admits valid 50+ closed local 4H history, but both scan precheck and Builder snapshot validation still required 240 local 1H rows. Both now admit 210 genuine closed 1H rows only if local 4H independently passes its own integrity/minimum; the normal 240-row fetch target remains unchanged.
- Added timestamp-aware 1H validation: strictly ordered unique candle-open timestamps, hourly boundaries, latest closed candle freshness, no future/stale tail, and no gaps. No candle is padded or synthesized.
- Extended the bounded HTF proxy to handle valid short 1H history as well as A32 short 4H history. Both timeframes cap confidence; existing usable HTF evidence and credible bearish/crash evidence take precedence. BTC macro checks are untouched.
- Corrected entry-root reporting to use recent prequal rejection reasons only when the active live cycle has zero selected candidates. This is diagnostics-only and never alters a gate.
- Added A33 terminal validation and tests for 214/209-row boundaries, snapshot/scanner parity, timestamp gaps, HTF crash precedence, canonical identity and root diagnostics.
- Preserved Spot LONG_ONLY/no-Futures, forbidden-asset list, score/volume/depth/fee/spread/net-profit floors, max-two positions, and order/SL/protection controls. `hard_gate_bypass=false`.

See `docs/audits/FINAL_PRODUCTION_AUDIT_A33_FINAL_AR.md`. Offline checks do not verify a live MEXC order, Telegram delivery, exchange-native stop behavior in production, deployment or profitability.

---

# A32 — adaptive local 4H admission, bounded HTF proxy and truthful spread diagnostics (2026-10-15)

- Replaced the hard 210-row local-4H admission gate with a **50 closed, consecutive candle minimum** for local symbols; the full-history target remains 210 rows or more whenever the exchange can provide them.
- Added a confidence-capped 4H HTF proxy for 50–209 local candles when the inherited HTF evidence is unavailable/invalid. The proxy uses closed-bar EMA20/EMA50 on 4H and independent 1H EMA50/EMA200 alignment; it does not claim that short history equals full EMA200 warm-up. Valid raw HTF evidence and credible bearish/crash evidence retain precedence.
- Timestamped local 4H rows must be ordered, unique, on candle boundaries, continuous, current through the last closed bar, valid and numerous enough. No candle is fabricated. BTC macro and 1H EMA200 minimums remain independently strict.
- Corrected spread diagnostic operators so pass reasons print `<=ceil` and actual over-cap rejects print `>ceil`. Existing per-tier ceilings and elite-only bounded rules are unchanged.
- Preserved Spot LONG_ONLY/no-Futures, 70 score floor, core quote-volume floor, MICRO depth, fee coverage, denylist, position/ticket caps, stop/protection and final execution authority; `hard_gate_bypass=false`.
- Offline evidence: **235/235 full tests passed**, A32 behavioral tests **5/5 passed**, `--validate-only` reports `pass=true` and `live_threads=[]`, and `py_compile` passes. Live MEXC fills, actual Telegram delivery, native stop protection, deployment and profitability remain unverified.

---

# A31 — bounded short-history revalidation and 4H paging closure (2026-10-15)

- Corrected an invalid inference in the inherited A29/A30 reject-only cache: contiguous but short closed 4H rows prove only that the received subset is internally continuous, not that the symbol was newly listed or the OHLCV endpoint is complete.
- Replaced the next-4H-boundary-only delay with a bounded negative-cache TTL (300 seconds by default; clamped to 60–900 seconds, and the next 4H boundary can invalidate earlier). Cache entries remain reject-only and the normal fetch path resumes on expiry. General API errors/timeouts are not cached as short history.
- Increased bounded 4H recovery paging from three to four extra pages and set the recovery-page timeout to two seconds. Added regression coverage for exchanges returning no more than 50 rows per response while retaining the 210-contiguous-closed-row requirement and never fabricating candles.
- Added `A31_HISTORY_RECHECK` diagnostics and made validation logs report the active A31 revision. Added checks for TTL range, page budget, timeout, Spot LONG_ONLY, score, liquidity/depth/fee floors, denylist and no-bypass invariants.
- This is a data-throughput/revalidation fix only. No HTF, liquidity, score, fee/net-economics, structure, exposure, stop/protection or final execution gate was relaxed. Live MEXC execution, Telegram delivery, exchange-native stop verification, deployment and profitability remain unverified offline.

---

# A29 — bounded adaptive rejection relief and data-funnel closure (2026-10-14)

- Added a bounded near-miss rescue for the plain `PULLBACK` family only: exactly one soft technical metric may be slightly under its floor, while the setup/composite quality, local closed-bar evidence, macro regime, known HTF context, chase ceiling, and at least three independent supporting metrics remain strong. A relief cannot be spent across stages to rescue a different second metric.
- Added a 65.0–69.9 final-score shadow band for analysis only. It cannot pass the live-score floor, selection, opportunity queue, Telegram opportunity sender, or execution.
- Added a reject-only short 4H history cache for genuinely contiguous, young listings; cache data expires at the next 4H boundary, required row count stays at 210, and data gaps/API failures are not hidden or padded.
- Added truthful `[V702-A29-VALIDATION]` pass/fail logging and regression coverage for relief boundaries, confirmed closed bars, cross-stage reuse rejection, shadow-only scores, history-cache expiry, and safety invariants. Closed-bar confirmation counts now derive only from the verified frame or a trusted same-snapshot validation marker; stale feature flags alone cannot count as confirmation.
- Final re-audit hardens freshness and identity of closed 5m evidence: stale/future frames are rejected, and a previously validated evidence marker is accepted only when its SHA-256 fingerprint matches the exact four-bar OHLCV snapshot.
- Final re-audit extends the bounded 4H cache only to contiguous closed short history after `short_history` or a multi-page `recovery_page_added_no_rows` diagnosis; timeouts/API failures, gaps, and synthetic rows are not cached. Cache expires at the next 4H boundary and is size-bounded.
- Final offline verification: full suite **216 passed**; focused A29/revision/context suite **17 passed**; `py_compile` passed; `--validate-only` returned `pass=true`, `live_threads=[]`, and `hard_gate_bypass=false`.
- Preserved Spot LONG_ONLY/no-Futures, forbidden bases AERO/BNB/CAKE/ETHFI/PUMP, live score >=70, core quote volume >=3M USDT, MICRO depth >=1.90, fee/net-cost controls, 2-position cap, 75 USDT entry cap, stop/protection and final execution authority. No live exchange, Telegram delivery, native stop, deployment or profitability verification is claimed.

---

# A28 — candidate attribution and Telegram funnel coherence (2026-10-14)

- Builder terminal reasons now recover from the bounded pipeline event ledger only for the exact candidate key, same runtime cycle, and fresh builder-call time window. The strict no-global/same-symbol fallback rule remains.
- Telegram funnel telemetry now counts `TELEGRAM_ENQUEUED` only for a canonical opportunity headline after a same-candidate/same-cycle `QUEUED` event exists. Diagnostic/control messages and unknown enqueue results do not inflate candidate progression.
- Fixed A24's synthetic monotonic-clock fixtures to use a positive deterministic clock value; live no-send policy, score floor, and risk gates are unchanged.
- Added regressions for exact score-block recovery, cross-candidate isolation, queue-gated Telegram attribution, and deterministic fresh-process timing.
- Current validator: `--validate-only` pass=true, exit 0; A23/A24/A26 terminal reports pass; `live_threads=[]`; `hard_gate_bypass=false`. Full results are recorded in `results/V702_A28_*`.
- No gate was relaxed. Real MEXC orders/fills, actual Telegram delivery, native stop semantics, Docker/Railway deployment, and profitability were not verified.

---

# A27 — deterministic starvation-clock validation (2026-10-14)

- Fixed the recurrence visible in the new Railway logs: `no_send_age_uses_freshest_source` compared two independent real-clock reads with a tolerance of 1 microsecond, so OS scheduling delay could make A23/A24 terminal validation fail while A26 itself passed.
- The terminal probe now freezes `WALL_NOW` and `MONO_NOW` to the same captured values during its synthetic assertion and restores both original providers in `finally`, including on exceptions. The production age calculation, freshest-source/min-age policy, live score floor, and eligibility gates were not altered.
- Promoted the package audit revision append-only to A27; A21/A22/A23/A24/A25/A26 lineage remains intact. The log now reports `[V702-A27-VALIDATION]` as the active validator result.
- Added repeatability regression coverage that runs the A24 terminal probe three times and verifies both clock providers are restored after each run.
- Offline validation: `--validate-only` pass=true; `base_ok=true`; A23, A24 and A26 terminal checks pass; `live_threads=[]`; `hard_gate_bypass=false`. Full suite and focused results are in `results/V702_A27_*`.
- No validator bypass, risk relaxation, network call, live order, Telegram delivery, Railway redeploy, or profitability claim was made.

---

# A26 — monotonic validation revision compatibility (2026-10-14)

- Fixed the actual `config_invalid` blocker: superseded A21/A22 checks compared the active package revision for exact equality with an older revision, causing A25 and later monotonic releases to fail their canonical validator.
- Changed historical revision contracts to require prefix-preserving lineage while keeping their substantive policy checks active. No validator bypass, gate skip, risk relaxation, or retry-on-failure was introduced.
- Added the A26 terminal self-test: revision-chain coherence, A21/A22 contract validity, Spot LONG_ONLY/no-Futures invariants, live score floor (>=70), core quote-volume floor (>=3M USDT), two-slot/75 USDT caps, forbidden-asset list, no-bypass status, and startup validation-order contract.
- Improved terminal failure diagnostics to include nested failed checks and revisions, and to separate clearly labelled historical/superseded reports from active blockers.
- `python main.py --validate-only`: PASS, exit 0, `pass=true`; A23, A24 and A26 terminal checks pass. Full test suite and focused regressions recorded in `results/V702_A26_*`.
- Offline verification only. No real MEXC order, live Telegram delivery, exchange-native stop verification, Docker build, Railway redeployment or profitability verification was performed.

---

# A25 — startup validation order and failure-truth closure (2026-10-14)

- Moved operational `_v699_arm_live_epoch()` out of the module entrypoint and into `main()` after canonical `validate_config()` returns success. Failed config stays fail-closed; epoch-arm exceptions abort startup.
- Replaced stale-only startup error details with bounded active terminal diagnostics covering A23/A24 reports and failed upstream R23–R40/V699 validation reports, including failed checks, error, revision, and superseded/historical labels where present.
- Added `[V702-A25-VALIDATION]` records separating `base_ok`, A23/A24 outcomes, and upstream failure summaries.
- Updated the source fingerprint boot line to show both legacy `validator_revision` and active `package_revision`.
- Added A25 startup-order regression tests. `py_compile` passed and the 3 focused A25 tests passed. The full `--validate-only` run did not complete within the audit tool time limit; no live exchange, Telegram, Docker or Railway deployment test was performed.
- No trading or economic gate was relaxed, and no failed validator is ignored or retried to force startup.

---

# A24 — truthful starvation telemetry, exact attribution and canonical release closure (2026-10-14)

- Replaced maximum-of-multiple-counters starvation timing with an explicit source-age ledger and conservative minimum elapsed age; no-send eligibility now exposes its reason and source ages. Relief remains above the hard global floor and does not admit scores below 70.
- Added an explicit `SCORE_BLOCK` pipeline stage and separated scorer, route/pre-exec and actual Builder blocks in the bounded Telegram digest and counters.
- Removed stale/global same-symbol fallback when attributing a Builder terminal rejection; the exact candidate key, current cycle and timestamp must match or the cause remains unattributed.
- Replaced brittle A23 source-text self-checks with behavioral tests proving local-history rejection prevents candidate-map commit and valid history commits exactly once; Builder-side validation remains active.
- Added regression coverage for relief boundaries, no-send clock consistency, telemetry category separation, exact attribution, Spot LONG_ONLY, forbidden assets, the score/liquidity floor and the frozen wrapper chain.
- Lowered `MIN_PAPER_SCORE` to 60 for paper-only observation; kept live score >=70 and every trading/economic/protection hard gate intact. No automated live-policy learning was added.
- Froze the `validate_config` wrapper chain at A24 rather than performing a risky wholesale merge of historical wrappers; published the A24 audit, validation logs and checksums.
- Offline validation only: no real MEXC order, live Telegram delivery, native stop verification, Docker/Railway deployment or profitability test was performed.

---

## A23 — Local-history pre-rank admission closure (2026-10-14)

- Added a canonical scan-stage precheck that uses the same local OHLCV row requirements as the mandatory MSE snapshot validator before a candidate is admitted to the market-data map.
- Eliminates wasted discovery/ranking/selected-builder cycles for symbols that already fail local-history requirements, including 4H contexts such as 75 rows when 210 are required.
- Retained the builder-side snapshot validator, strict finite OHLCV validation, and fail-closed behavior; no synthetic rows or BTC-to-altcoin local-history substitution.
- Added bounded `A23_LOCAL_HISTORY` heartbeat telemetry with count and last rejection cause.
- Preserved all trading and risk gates; no score, HTF, structure, liquidity, fee, position, stop/protection, or execution gate was relaxed.
- Offline-only verification; no live MEXC order, live Telegram delivery, native stop verification, deployment, or profitability claim.

# A21 — live-pilot release and confirmed TIA submit blocker closure (2026-10-13)

- Closed the observed `submit_failed:a19_diagnostic_only_new_live_entries` cause by changing the A19 diagnostic hold from hidden default-on to explicit opt-in. The absent setting now permits the existing user-requested live-pilot authorization path to run.
- Kept `UNIFIED_A19_DIAGNOSTIC_ONLY=1` as an immediate operator hold and preserved `UNIFIED_LIVE_PILOT_ENABLE=0` as the emergency off switch.
- Added a final A21 terminal self-test and regression coverage showing the no-env default can reach the mocked canonical Spot order path only after credentials, hard invariants, and portfolio authorization pass.
- Preserved score >=70, core quote volume >=3M USDT, Spot LONG_ONLY, futures/short off, forbidden bases AERO/BNB/CAKE/ETHFI/PUMP, max 2 concurrent positions, max 75 USDT entry, portfolio drawdown guard, stop/protection, spread/fee/net economics, and `hard_gate_bypass=false`. No global quality/risk gate was relaxed to inflate opportunity count.
- TIA is not replayed as a stale order; only a fresh future signal can be evaluated by the canonical pipeline. The offline mock test does not prove live MEXC acceptance/fill, Telegram delivery, native stop, deployment correctness, or profitability.

---

# A20 — strategy/timeframe edge logs and database discoverability (2026-10-13)

- Added a 15-minute `[V702-KNOWLEDGE-DB]` report with the active `SCALPER_DB` path, file size, total/finalized/active records and completed shadow entries.
- Added `[V702-KNOWLEDGE-FAMILY-TF]` logs for family/style/timeframe groups, including sample count, first-touch win rate and expectancy, modeled realized expectancy, TP/SL counts, and sample-qualification status.
- Extended A9 strategy logs with timeframe, resolved outcomes, net-positive rate, average/median net R, net profit factor, maximum drawdown, and sample-quality labels.
- Added the exact SQLite/report paths to A9's JSON report and logs. Knowledge JSON export defaults beside the selected database to support persistent volume layouts.
- Preserved A19 diagnostic-only default, SPOT LONG_ONLY, all blacklists, entry score/liquidity/HTF/structure/fee gates, live position limits and protection logic. New reports are research/observability only; no live execution authority was added.
- Added regression tests for path reporting, family/timeframe aggregation, JSON report artifacts and unchanged hard gates.

# A19 — exact candidate attribution and diagnostic-only live-entry hold (2026-10-13)

- Added a stable 40-character CandidateRef that follows the same semantic payload as the knowledge-outcome ledger. Shadow/live comparison now requires exact CandidateRef, matching symbol/family, a fresh route record, and an explicit blocking stage; same-symbol proximity is no longer interpreted as a missed candidate.
- Made MICRO handoff failures observable by specific evidence reason (for example, missing spread/book proof), retaining candidate reference and snapshot context. The heartbeat exposes the latest MICRO diagnosis even when no shadow event exists.
- Added an opt-out-by-explicit-setting diagnostic hold at the final new-live-entry submission boundary. `UNIFIED_A19_DIAGNOSTIC_ONLY=1` (default) blocks only new real live BUY submissions; paper flow and existing-position management/protection/exit flows are left intact. Operator opt-in is required with `UNIFIED_A19_DIAGNOSTIC_ONLY=0` after review; no automatic timer re-enables live entries.
- Added regression coverage for identity parity, reject-root observability, exact shadow attribution, live hold scope, paper bypass, and terminal validation.
- No strategy-quality or risk gate was relaxed: score floor 70, 3M USDT core liquidity, MICRO depth 1.90, Spot LONG_ONLY, Futures/short disabled, forbidden-asset policy, max two concurrent positions, 75 USDT entry cap, and stop/protection/execution gates remain enforced.
- Live exchange execution, Telegram delivery, exchange-native stop protection, deployment, and profitability remain unverified by offline tests.

---

# A17 — canonical macro-path and policy-parity closure (2026-10-13)

- Reused successful shared BTC 4H macro and BTC 15m/4H severity calculations through content-validated, bounded caches (8 macro frames; 16 severity pairs). Invalid/error results are never cached.
- Quarantined missing/invalid 4H macro context before strategy-engine fan-out; still fail-closed, no candidate, score, policy, or execution bypass. Added bounded A17 heartbeat telemetry for seen/pass/blocked counts and cache hits/misses.
- Corrected the redundant PULLBACK Elite chase ceiling from 0.75 to the canonical 0.90 ATR; regression confirms 0.901 is rejected.
- Required unique, monotonic timestamp candle indices for scan cooldown identity; normalized known closed-candle timestamps to UTC; malformed/numeric/unordered indices remain unverifiable.
- Preserved score >=70, core volume >=3M USDT, MICRO depth >=1.90, HTF, structure/fake-break, spread/fees/net costs, denylist, Spot LONG_ONLY, two-position/75-USDT limits, SL/protection and single execution authority.
- Offline: `--validate-only` pass=true, `live_threads=[]`; live MEXC/Telegram/native protection/deployment/profitability remain unverified.

---

# A16 — Bounded Pullback Recall and Candle-Scoped Cooldown (2026-10-12)

- Aligned only the secondary PULLBACK Elite thresholds to bounded primary-policy values: score 70, HTF 50, volume ratio 0.85, RS 2 points, structure 55, retest 45, setup quality 72, maximum chase 0.75 ATR.
- Changed `symbol_scan` cooldown to track the candidate strategy and last closed 5-minute candle, preventing same-symbol cross-strategy scan starvation while retaining same-strategy-mode/same-candle deduplication and fail-closed behavior without a verifiable candle key.
- Kept the original Builder observer as a one-call delegate and preserved its terminal outcome contract. No new queue, Telegram, or execution authority.
- Preserved global score >=70, core quote volume >=3M USDT, MICRO exact-book depth >=1.90, HTF/structure/fake-break, spread/fee/net-economics, Spot LONG_ONLY, denylist, max 2 concurrent positions, max 75 USDT per ticket, SL/protection, and hard_gate_bypass=false.
- Offline evidence does not establish live MEXC fills/protection, Telegram delivery, deployment, or profitability. See `docs/audits/FINAL_PRODUCTION_AUDIT_A16_FINAL_AR.md`.

---

# A14 — Selective Secondary Quality-Floor Alignment (2026-10-12)

- Aligned the secondary Elite score threshold with the existing global score floor at **70** across configured strategy families. Scores below 70 remain blocked by the global policy and by the Elite context check.
- Reduced only the secondary Elite HTF context floors to bounded family-specific values: default 70, Pullback/Local Strength Reversal 72, MTF Pullback and breakout/Local Strength Breakout 75, Momentum 74. Valid HTF data and primary family/strategy HTF policy are unchanged.
- Preserved strong-factor checks (volume, relative strength, structure, retest, setup quality and chase), fake-break rejection, current regime/local confirmation, quote-volume and order-book quality, spread, fees/net economics, position sizing, denylist, Spot LONG_ONLY, two-position limit, 75 USDT ticket, stops/protection, PreSend and the single execution authority. `hard_gate_bypass=false`.
- Purpose: remove a stricter secondary admission floor that could reject otherwise-qualified 70–75 score candidates. It does **not** admit the 52–65 scores shown in the supplied logs, and does not guarantee more fills or profit.
- Added A14 self-test/CLI validation and offline regressions for floor alignment, below-70 rejection, cross-factor HTF/volume checks, projection parity and unchanged safety invariants.
- Offline checks do not establish live MEXC order acceptance, actual Telegram sends, exchange-native stop protection, deployment or profitability. See `docs/audits/FINAL_PRODUCTION_AUDIT_A14_FINAL_AR.md`.

---

# A13 — Fresh Liquidity Core, Bounded 4H Recovery, and MICRO Depth Recheck (2026-10-12)

- Reconcile core candidates against a current bounded ticker snapshot before deep OHLCV, requiring active SPOT/USDT, a valid last price, and the existing 3M USDT quote-volume floor. Empty V650 slots and V646 rotation can no longer refill from unverified original TOP-500 ordering.
- If 4H OHLCV is truncated, make at most three timestamp-based recovery page calls, with a four-second per-recovery-page timeout. Merge by candle timestamp, reject gaps/stale history, and never fabricate rows. The local 4H history floor remains at least 210 rows.
- Defer only cached MICRO depth ratios from 1.50 to <1.90 when a valid book exists, to the exact route-book refresh. The final exact-book confirmation still requires depth >=1.90, so this is a recheck, not a gate bypass. Route `depth_ratio` now reflects the captured exact book.
- Reduce successful MICRO scan cooldown from 600s to 300s; failed-data retry remains 60s. Selection stays bounded.
- Added A13 regressions and terminal validation for stale-volume core exclusion, bounded recovery, short-history fail-closed behavior, MICRO depth deferral, unchanged score/HTF/structure/economic/protection policy, Spot LONG_ONLY, and the denylist.
- No score threshold, core liquidity floor, final order-book floor, fee/economic gate, HTF/structure gate, order authority, SL/protection rule, or position limit was relaxed. Live MEXC execution, Telegram delivery, exchange-native stop behavior, deployment, and profitability remain unverified offline. See `docs/audits/FINAL_PRODUCTION_AUDIT_A13_FINAL_AR.md`.

---

# A12 — Exact Selection/Builder Score Parity + MICRO Retry Closure (2026-10-12)

- Fixed the selector’s false choke: projected canonical score can now hard-block a candidate or influence its rank only when the projection is complete, fresh (45-second bound), and bound to the same candidate object, candle, and cycle. Incomplete, stale, or mismatched projections retain the canonical arbiter’s original rank and defer the actual decision to Builder.
- Made the early projection floor match Builder’s actual ordered floor stack: regime adjustment, family/strategy policy, learned/session offsets, bounded adaptive/V45 rescue, Elite LIVE floor, and eligible starvation score relief. This avoids rejecting a candidate with a projection floor that does not match the live Builder decision. Existing global live floor remains at least 70; no general score relaxation was introduced.
- Fixed MICRO recall starvation after transient market-data errors. A failed/timeout/invalid fetch now becomes eligible for retry after a bounded 60-second backoff instead of inheriting the full 600-second successful-scan rotation TTL; a successful scan still keeps the full 600-second TTL. The sample remains stratified/bounded.
- Added A12 deterministic regressions and a terminal self-test for exact low-score rejection, stale/incomplete rank preservation, complete passing projection ordering, bounded starvation-relief floor parity, and failed-vs-successful MICRO scan cooldown.
- Preserved Spot LONG_ONLY, futures disabled, the denylist, maximum two concurrent trades, maximum 75 USDT entry notional, the 3M USDT core quote-volume floor, fee/economic checks, HTF/local confirmation, structure, book/spread/depth, stop geometry, native-stop verification, single order authority, and hard-gate-bypass disabled.
- Offline code validation does not prove a live exchange will create a trade or that profitability improves. MEXC orders, Telegram delivery, exchange-native stop protection, Docker/Railway deployment, and net profitability remain unverified. See `docs/audits/FINAL_PRODUCTION_AUDIT_A12_FINAL_AR.md`.

---

# A11 — Shared BTC Macro-Context Binding Closure (2026-10-12)

- Fixed the actual data-path mismatch surfaced by the post-deployment digest: `BTC/USDT` candidates previously bound `df_btc_4h` to their candidate-local 220-row scan frame, despite the dedicated shared BTC fetch recovering 260 rows.
- All macro BTC frames (`df_btc_5m`, `df_btc_15m`, `df_btc_1h`, `df_btc_4h`) now consistently bind to the dedicated shared context fetch for every symbol; context age is measured from that shared fetch. Candidate-local `df_4h` remains unchanged for symbol-level calculations.
- Added regression checks to prevent reintroducing the local-frame shadowing and to ensure the runtime package audit revision identifies A11.
- Kept the strict 240-closed-bar macro contract and the local 210-row 4H snapshot floor. A symbol with only 63 local 4H rows (such as the `XDP/USDT` example in the digest) remains correctly rejected; no data requirement is relaxed or fabricated.
- No score threshold, liquidity/depth/spread limit, HTF/structure requirement, fee check, orderbook gate, denylist, position cap, Spot LONG_ONLY policy, stop/protection rule, or execution gate was relaxed.
- Validation status is recorded in `results/V702_A11_FINAL_TESTS.txt`. Live MEXC, Telegram delivery, native stop, Docker, and Railway deployment remain unverified by this offline audit.

---

# Final production closure — A10 (2026-10-11)

- Aligned the active BTC 4H macro snapshot resolver and standalone bearish-severity helper to the configured 240-row operational context minimum; 239 rows fail closed and the 240-row boundary is regression-tested.
- Added timestamped last-failed snapshot diagnostics (reason and BTC 4H row count), passed exact macro-context failure metadata into PREQUAL telemetry, and surfaced the latest failed snapshot as a bounded, explicitly non-global heartbeat label.
- Made the current rendered `ENTRY_STATUS=BLOCKED:...` take precedence over stale route/status cache in `ENTRY_BLOCK_ROOT`; generic `NO_LIVE_READY` no longer inherits an old specific blocker.
- Corrected top-level canonical runtime metadata so the A9 component bootstrap cannot downgrade package identity from A10 to A9.
- Added final `--validate-only` checks and regressions; **117/117 pytest tests pass**, Python compilation passes, and `--validate-only` exits 0 with A9 14/14 and A10 15/15.
- Trading gates and order authority are unchanged. No real MEXC orders, native-stop verification, Telegram delivery, Docker/Railway deployment, or profitability claim was performed.

---

## 2026-10-11 — A10 strategy-aware HTF policy closure

- Replaced the one-size-fits-all HTF alignment treatment with an explicit family policy: strict alignment remains for breakout/momentum/continuation and MTF/swing pullbacks; the existing 15m `PULLBACK` lane gets only a bounded 45/100 context floor; local-first reversal/reclaim families use HTF direction as context while retaining a bounded 35/100 data-strength minimum.
- Added local-confirmation requirements to contextual admissions. `MEAN_REVERSION` is eligible in BULLISH/NEUTRAL only with explicit local bullish/recovery/neutral state; under BEARISH macro it requires `LOCAL_RECOVERY` and non-crash severity. Missing/unknown HTF data, weak context, unsupported family/regime combinations and missing local proof fail closed.
- Added a terminal A10 validator to `--validate-only`, covering strategy floors, local confirmation, BEARISH recovery, Spot LONG_ONLY, two concurrent slots, 75 USDT maximum/fixed ticket, forbidden bases, Shadow-only order authority and hard-gate-bypass disabled.
- Regression coverage checks both permitted and denied paths. The A9 matrix/validators remain as historical component checks, while the package-level canonical revision advances to A10.
- No liquidity, spread, depth, score, fee/economics, structure, sizing, drawdown, order, stop-protection or execution-authority gate is bypassed. Shadow strategies remain non-executing. Live MEXC/Telegram/protection are not claimed as tested by offline checks.

---

## 2026-10-11 — A9 Production Debugging Final Closure R1

- Preserved the original MEXC order-book capture timestamp when a fresh cached book is reused; last-check time is tracked separately so reuse cannot make stale data appear fresh.
- Classified invalid, future, and stale market-fact timestamps before diagnosing snapshot transfer; future order-book/spread timestamps fail closed.
- Split MEXC/API failures, transport timeouts, worker-task exceptions, invalid responses, budget deferrals, skipped scans, and missing candidate handoff into distinct telemetry causes.
- Added explicit expected macro-policy block versus registry-conflict attribution. The canonical MEAN_REVERSION allowlist remains NEUTRAL/BEARISH; no macro/trend gate was weakened.
- Clarified per-cycle versus historical/cost-adjusted Shadow telemetry; A9 research engines remain non-executing.
- Verification: 11 focused A9 regressions passed; full pytest 107/107 passed; static compilation passed; `--validate-only` exited 0 with `pass=true`, A9 checks 14/14, regime matrix 21 modes/63 cells/0 mismatches, `live_threads=[]`.
- Preserved Spot LONG_ONLY, $75 USDT entry, two-trade cap, denylist, execution protection gates, and the no-Shadow-execution policy. Real MEXC orders, live protection, Telegram delivery, deployment, and profitability were not verified.

---

## 2026-10-11 — R40-A8 final production closure

- Aligned early route projection rejection with the canonical Builder effective score floor, but only for a complete, fresh, same-candidate/cycle/candle projection; incomplete projections still defer to Builder.
- Aligned mandatory local 4H snapshot warm-up with the consumer's 210-candle floor and added read-only per-frame failure diagnostics. Invalid market data remains fail-closed and is never synthesized.
- Added live-epoch, bounded, per-stage MICRO order-book rejection reasons and last measured context; strict depth/spread/volume/chase/structure and fee gates remain unchanged.
- Reduced blocker-root freshness to 300 seconds and required a current timestamp for the fallback entry-status root, preventing stale SCORE telemetry from masking present blockers.
- Added A8 terminal validation and refreshed release manifest, source hash, tests, validation log and SHA-256 sums.
- Verification: A8 offline pytest and `--validate-only` evidence in `results/V702_A8_FINAL_TESTS.txt` and `results/V702_A8_FINAL_VALIDATE_ONLY_LOG.txt`. Real MEXC/Telegram/Docker/Railway and profitability remain unverified; no live order was sent by validation.

---

# R40-A3 — Pipeline truth, Builder attribution and Telegram noise (2026-10-10)

- Reduced the noncritical compacted operator digest cadence from every 5 minutes to every 15 minutes. `/digest` remains on-demand; execution/order/protection/control/error notices remain immediate.
- Added an explicitly scoped `PIPELINE[WINDOW_15M]` line alongside `PIPELINE[CYCLE]`, with unique candidate-stage counts, deduplicated rejection counts/reasons and a buffer-truncation indicator. This prevents comparisons between a multi-minute rejection window and one scanner cycle from being misread.
- Made Builder-returned-`None` diagnostics candidate-scoped and freshness-bound. Stale global/same-symbol hints are no longer promoted as the exact cause; no fresh blocker is labeled unattributed instead of fabricated.
- Added offline regressions and a fail-closed `--validate-only` contract for digest cadence, window-scope accounting, candidate-attributed Builder reasons, digest length bounds, and unchanged hard-gate state.
- No entry policy/quality gate, Spot LONG_ONLY restriction, forbidden-asset list, economic viability check, order/stop protection logic, or risk limit was relaxed. Live MEXC order, real Telegram delivery, and redeployment remain unverified.

---

# R40-A2 — Correct MICRO route order-book handoff argument contract (2026-10-10)

- Fixed a production-path TypeError: the selected-route MICRO branch called `_v45_orderbook_confirmation` with two arguments (`candidate, md`) even though the helper requires `(orderbook, opp, tier)`. The broad route exception handler converted that mismatch into a fail-closed `route_orderbook_unverifiable` rejection.
- The corrected call passes the exact order book fetched for the selected symbol, a normalized context derived from the same route snapshot/candidate features, and the candidate's resolved liquidity tier. Depth is deliberately recomputed inside the helper from that exact book instead of trusting a potentially stale pre-route depth ratio.
- Added a release regression contract to assert the three-argument handoff and correct order-book source. MICRO still fails closed when the actual order book/context is missing or invalid; no gate was relaxed.
- Maintains A1's bounded/redacted diagnostic error token and honest runtime-log reconciliation. Public runtime identity remains `4.5.99-V702-R40-SMALL-NET-PROFIT-CANONICAL`; package audit revision now ends in `A2-ORDERBOOK-HANDOFF`.
- Final offline verification completed: 60/60 tests passed across the five test files; actual MEXC entry, native stop protection, live Telegram delivery and deployment remain unverified.

---

# R40-A1 — Final runtime-log reconciliation and route-error observability (2026-10-10)

- Reconciled the supplied R40 operator digests against the actual pipeline: discovery/handoff-precheck is not equivalent to queue/send/order execution, and shadow TP/SL/MFE/MAE events are not live P&L.
- Added `_v703_route_orderbook_error_token` to expose a short sanitized error detail in MICRO route rejection attribution while redacting URLs and common credential assignments; full fail-closed orderbook requirements remain unchanged.
- Added a regression test for bounded/redacted error attribution; final offline total is 59 tests across the five test files.
- No entry-quality, cost, liquidity, structure, score, stop-loss, exposure, drawdown, Spot LONG_ONLY, execution, or forbidden-asset gate was relaxed.

# R40 — small-net-profit cost-aware target model (2026-10-10)

- Added an explicit R40 mode that derives TP1 target RR from round-trip commissions, measured/fallback spread, two-sided slippage, a 0.10% minimum modeled net TP1 profit, existing 2.5x fee coverage, and a bounded safety margin.
- Fee-rescue logic can move TP1/TP2 targets only within configured R limits and does not modify stop-loss geometry. Exit distribution updated to TP1/TP2/runner = 60%/30%/10%; legacy fee thresholds remain unchanged for callers outside R40 mode.
- Added bounded small-net target compression for SCALP/SCALPING/INTRADAY/DAY styles: applies only after economics pass and only when at least 0.15R TP1 distance is saved; rechecks net cost, family-native ATR distance and S/R ceilings. If family/S/R constraints reject compression, the original viable targets are retained. Swing profiles are not compressed and SL never changes.
- Counterfactual shadow outcomes now deduct round-trip commission, estimated spread, and two-sided slippage, aligning study accounting with the small-net model.
- BTC shared context now requests 260 4H candles and requires 240 closed candles. Unknown macro context remains fail-closed rather than being treated as neutral.
- Public package/runtime identity is now R40. Historical R38 terminal-validator labels are retained only as compatibility identifiers.
- Added 10 targeted small-net regression tests and updated release/manifest contracts. These changes do not bypass fake-break, structure, liquidity, score, stop-loss, exposure, drawdown or Spot LONG_ONLY hard gates.
- No real MEXC order, exchange stop verification, live Telegram send, or production deployment was performed during this audit.

---

## R39-R3 — User-requested Live Pilot + truthful entry status (2026-10-10)

- Enabled the live-pilot authorization setting because the operator explicitly asked to execute real Spot entries for a controlled observation period. Actual entry authorization remains conditional on both MEXC credentials and every existing hard invariant.
- Added `UNIFIED_LIVE_PILOT_ENABLE=0` as the highest-precedence off switch; it forces `MONITOR_ONLY_NO_NEW_BUYS` even when the legacy opt-in token is present. It blocks new buys; it does not liquidate open positions.
- Corrected heartbeat truth so monitor-only is reported as `ENTRY_STATUS=BLOCKED:MONITOR_ONLY` rather than `BLOCKED:NONE`; no starvations or execution status are inferred from unrelated counters.
- Added package revision/entry policy to startup messaging and `--validate-only` metadata, retaining the canonical runtime identity `4.5.99-V702-R38-FINAL-CANONICAL`.
- Added offline mocked-exchange test proving authorized flow can reach the canonical OrderExecutor handoff without using real exchange APIs. No real MEXC entry or stop was submitted or verified by this audit.
- No score, liquidity, fee, spread, fake-break, structure, stop, exposure or forbidden-asset gate was lowered. Spot Long Only, max two concurrent entries and maximum 75 USDT notional per entry remain.
- Final local verification: `--validate-only` reports `pass: true`; 48/48 offline unit tests pass. Docker build, Railway redeployment, real Telegram delivery, and exchange-native stop protection remain unverified.

# CHANGELOG — UNIFIED SCALPER V702

**Current release family:** `4.5.99-V702-R40-SMALL-NET-PROFIT-CANONICAL`  
**Current audit amendment:** `R40-A7-BOUNDED-MICRO-HANDOFF-TELEGRAM-AUTH-ROOT-DIAGNOSTICS-2026-10-11`  
**Date:** 2026-10-11

This file consolidates the major release notes preserved in the supplied archive. The historical R33–R37 entries describe the earlier release artifacts; their old test counts are not added to the current audit's test count and were not rerun as separate historical releases.

## R40-A7 — Bounded MICRO handoff, Telegram sender authorization and final validator closure (2026-10-11)

- Added an evidence-gated MICRO-to-Builder handoff only for 1,000,000 to below 3,000,000 USDT 24h quote volume and an allowlist of Long families. Requires score >=70 and the strategy-specific floor, known below-ceiling spread, passing MICRO order-book confirmation, fresh facts where timestamps exist, and fee viability. It grants continuation to downstream checks, not execution permission.
- Reused the proof at prequalification, canonical JIT policy checks, and both Builder policy paths. Missing/invalid book or failed economics remains fail-closed; no synthetic micro-contract fallback is added.
- Hardened Telegram command sender authorization: private owner or explicitly allowlisted sender; group/supergroup commands require `TELEGRAM_ALLOWED_USER_IDS`; bot senders are denied.
- Added concise entry-block root/age and MICRO handoff counters to heartbeat; retained macro-regime policy while exposing its rejection diagnostics. Shadow/live-gap telemetry is observational only.
- Moved the A7 terminal layer before the `--validate-only` guard and included the A7 validation report in the final CLI JSON and overall exit decision. This closes the previous gap where the command could exit before loading A7.
- Consolidated dependency installation through `requirements.txt` including `requirements-lock.txt`; the latter remains a direct-dependency constraints file, not a complete transitive/hash lock.
- Kept the 3M core liquidity floor, score floor >=70, Spot LONG_ONLY, Futures-disabled contract, forbidden bases, max two positions, max 75 USDT per entry, hard-gate bypass off, HTF/structure/economic checks, SL, PreSend, execution and protection intact.
- Explicitly rejected the proposed generic score-68 pilot fallback, blanket neutral macro bypass, and micro-contract creation when book confirmation fails. None is justified by the supplied logs and each risks admitting low-quality or unprotected entries.
- Final offline verification passed: `pytest -q` reports 79 passed, syntax compilation passed, and A7-aware `--validate-only` exited 0 with all 10 A7 checks true and `hard_gate_bypass=false`. Results are recorded in `results/V702_A7_FINAL_TESTS.txt`, `results/V702_A7_FINAL_VALIDATE_ONLY_LOG.txt`, and `results/V702_FINAL_VALIDATE_ONLY_LOG.txt`. No live exchange order, live Telegram message, exchange-native SL, Docker build or Railway deployment was performed.

---

## R40-A6 — Complete-projection handoff and MICRO sampling correction (2026-10-11)

- Fixed a false-negative route condition: a projected score below the floor no longer blocks before Builder when the projection's parity status is incomplete, stale or inconsistent with the exact candidate/cycle. A complete, fresh, same-candidate low projection remains an early rejection; all Builder and later gates remain authoritative.
- Fixed the MICRO warm-pool slice so the configured warm-pool multiplier actually broadens the sample; a stratified deterministic selection spreads the bounded scan across eligible symbols rather than always selecting the first `budget` rows.
- Added concise reasons for zero MICRO selections and counters for incomplete score projections deferred to Builder.
- No score/liquidity/family/HTF/structure/economic/protection threshold changed; Spot LONG_ONLY, forbidden bases and hard-gate bypass protections remain unchanged.
- Validation: 67 offline tests passed; `--validate-only` pass=true; no live exchange, Telegram send, Docker or Railway deployment was performed.

## R33 — Production audit and telemetry closure

- Retained the single Spot / Long Only operating contract and hard-gate execution architecture.
- Improved the distinction between intended policy rejection and errors in the candidate funnel.
- Preserved earlier reports and SHA-256 lists as historical provenance rather than treating them as proof of the current source.

## R34 — Liquidity, score and handoff consistency

- Reconciled candidate-universe liquidity floors with score and handoff checks.
- Tightened observability around whether a candidate was discovered, qualified, selected, passed onward, or rejected.
- Kept hard-gate bypass disabled; no rejection threshold was lowered merely to increase trade count.

## R35 — Strategy and structural-contract hardening

- Preserved native strategy-family entry and exit policies and structural invalidation.
- Improved candidate structure, branch identity and closed-candle constraints described in the archived R35 audit.
- Historical R35 validation figures are intentionally not included in the final audit's executed-test count.

## R36 — HTF, policy and lifecycle hardening

- Improved higher-timeframe evidence handling, closed-bar context, policy alignment and runtime observability.
- Retained the hard entry, balance, exposure, fee, stop and execution gates.
- Historical R36 test reports remain archived and are not represented as newly rerun tests for this amendment.

## R37 — Canonical runtime and operational truth

- Canonical runtime identity: `4.5.99-V702-R37-FINAL-CANONICAL`.
- Reconciled runtime strategy registry reporting with the final 18 registered / enabled engines and 23 strategy contracts.
- Preserved Spot Long Only, maximum two concurrent trades, base live-score floor 70, core quote-volume floor 3,000,000 USDT, and the hard forbidden-asset set `AERO`, `BNB`, `CAKE`, `ETHFI`, `PUMP`.
- Improved HTF missing-data semantics and the observability of selected-to-builder policy rejections.

## S/R-aware target patch

- Target planning uses confirmed, closed 15-minute resistance pivots clustered with ATR; TP1 and TP2 are capped before relevant resistance when the geometry remains valid.
- TP3 remains strategy-native; final target geometry is recomputed after the final stop-loss bound.
- A fee-target rescue must not undo the structural TP1/TP2 cap. Invalid or uneconomic final geometry is rejected; unavailable S/R inputs use the explicitly tested canonical RR fallback.
- S/R does not widen the stop loss and does not bypass downstream risk, fee, liquidity, spread, balance, blacklist or execution checks.

## Post-audit amendment — 2026-10-09

- **Fixed and behavior-tested:** normalized forbidden-asset detection for common alternate exchange symbol encodings: slash, underscore, dash, pipe, colon, dot, CCXT contract-suffix forms, lowercase symbols, and compact market IDs such as `AEROUSDT`. Hard-deny assets remain blocked even if the runtime's public alias has not yet been bound during early initialization.
- **Fixed and tested:** changed the Pandas daily-frequency alias from `freq="1d"` to `freq="1D"` in the historical date-index self-test.
- **Canonical file contract:** synchronized `main.py` and `main_combined_V702_FINAL.py` byte-for-byte.
- **Dependency reproducibility improvement:** pinned direct dependency versions in `requirements.txt` and `requirements-lock.txt`. A complete transitive, hash-verified lock remains deferred because the package index could not be reached from the audit environment; `LOCKFILE_NOTES.md` records this limitation.
- **Rollback:** retained byte-for-byte baseline copies of the incoming canonical main files under `rollback/`; the uploaded original ZIP is not overwritten.

## Unchanged hard contracts

- Spot, Long Only; Futures disabled.
- Maximum two concurrent trades.
- Live score floor 70; no production score, liquidity, spread, HTF, fee or risk gate was relaxed by this audit amendment.
- Hard deny: `AERO`, `BNB`, `CAKE`, `ETHFI`, `PUMP`.
- Telegram notification is not an execution authority; a candidate does not reach Queue/Telegram/Execution merely because it was discovered or ranked.


## 2026-10-09 — Canonical post-audit consolidation

- Added offline S/R target handoff coverage for PreSend, fee viability, target precision, resistance caps, TradeState parity, capture-only order submission, and in-memory Telegram queue serialization.
- Added `V702PipelineMetrics` for active-cycle unique candidate-stage counts, epoch-scoped totals, cycle/epoch top rejection lists, and explicit native-stop/protection-failure states.
- Reset cycle-scoped rejection causes on cycle rollover while preserving epoch totals.
- Hardened release validation metadata so historical predecessor-validation status is retained but cannot veto the current release-chain contracts.
- Removed duplicate historical executables and stale reports from the canonical package; kept one rollback baseline.
- Kept hard trading gates, Spot LONG_ONLY, Futures-disabled mode, and the hard forbidden-asset set unchanged.
- Live exchange, live Telegram, Docker build, and profitability validation remain out of scope for this offline audit.

### Final package consolidation — 2026-10-09

- Supersedes prior packaging notes above that described synchronized duplicate executables: the deliverable contains only `main.py` as the canonical runtime and one incoming `ROLLBACK__main.py.baseline`. This is deliberate to remove duplicate deployable code.
- Added and tested management-only post-fill target recovery for the case where actual fill drift consumes the configured S/R buffer; it never targets above the identified physical resistance and cannot authorize a new entry.
- Added an eighth offline S/R integration test; all 14 release/integration unittest cases must pass before package generation.
- The manifest SHA-256 identifies the delivered `main.py` bytes. Historical executable duplicates and transient SQLite `-wal`/`-shm` sidecars are excluded from the deliverable.


## R38 — Final canonical production audit seal (2026-10-09)

- Promoted the active public runtime identity and release tag to `4.5.99-V702-R38-FINAL-CANONICAL` / `UNIFIED-SCALPER-V702-R38-FINAL-CANONICAL-PRODUCTION-AUDITED`; the earlier R37 contract remains as predecessor evidence.
- Added a terminal validator with 25 explicit checks for the active identity, all registered pipeline-stage observers, digest instrumentation, target-planner wiring, Spot LONG_ONLY, disabled Futures, fail-closed forbidden assets, hard-gate bypass disabled, and the preserved score/liquidity/trade-count bounds.
- Reclassified failed R33/R34 checks as explicitly historical/superseded warnings. They remain visible for forensics but cannot masquerade as the active release result.
- Fixed the test harness to reuse already-produced import-time terminal validation results; unit tests no longer start a nested runtime, rerun the expensive full-source AST validators, or overwrite the archived CLI validation evidence.
- Renamed shadow outcome telemetry as `shadow_alerts` / `shadow_entries` / `shadow_TP*` / `shadow_SL` so shadow labels cannot be misread as live trades.
- No entry threshold, liquidity/HTF/structure/fee/spread gate, stop requirement, trade cap, or forbidden asset rule was relaxed for the purpose of increasing trade count.
- The existing portfolio equity drawdown halt remains retired rather than being silently assigned a new threshold; the daily realized-loss circuit breaker remains at `-2.0R` with loss-streak cooldown. This is an explicit deployment risk limitation, not evidence of a portfolio equity drawdown stop.


## R38 packaging amendment — Railway aiohttp resolver fix (2026-10-09)

- Responded to the supplied Railway build log: the new deploy failed at pip install with `ResolutionImpossible` and a conflict involving `ccxt 4.5.81` / `aiohttp`; Railway still showed the prior deployment as ACTIVE.
- Replaced the exact `aiohttp==3.13.3` requirement in both requirement files with `aiohttp>=3.14.3,<3.15`, the compatible range used by the current CCXT Python dependency configuration. This avoids an unnecessarily strict patch pin without changing `main.py` or any trading gate.
- Updated the release-contract test to enforce the compatibility range and prevent regression to the old exact pin.
- Added `RAILWAY_BUILD_FIX.md` with repository-root deployment instructions. The actual Railway rebuild remains pending and is not represented as passed.


## R38-BUILD-FIX-2 — pipeline / protection telemetry truth closure (2026-10-09)

- Corrected the operator pipeline columns to reflect the actual order: Discovery → local ranking → PREQUAL seen → PREQUAL pass/reject → selection → Builder → score/PreSend → queue/Telegram → execution/order/state/protection.
- Exposed `PREQUAL_REJECT` in the cycle line; `D/P/PASS/R` no longer presents a misleading stage order or hides why `PASS` is zero.
- Records PREQUAL entry before invoking the gate and accounts for gate exceptions as rejected observations before re-raising to the existing fail-closed handler.
- Records unexpected native stop-placement exceptions as `NATIVE_SL_UNVERIFIED` and re-raises them. This does not claim the trade is protected or suppress ambiguous exchange outcomes.
- Added four terminal-contract checks and three offline regressions for digest ordering, PREQUAL exception accounting, and Native SL exception telemetry.
- No scoring, liquidity, HTF, structure, fee, stop, blacklist, trade-cap or execution-authority gate was relaxed. The external Railway rebuild remains unverified.


## R38-BUILD-FIX-3 — selected-route truth and tier fail-closed closure (2026-10-10)

- Added candidate-scoped `PREEXEC_PASS`, `PREEXEC_BLOCK`, and `ROUTE_DEFERRED` events. Current-cycle selected-route failures now surface their actual freshness, handoff, policy/structure, orderbook, or projected-score reason in the same pipeline ledger rather than leaving `SEL=1` with no explanation. Execution-budget exhaustion is recorded as a deferral, not mislabeled as a policy failure.
- Added `BUILDER_RETURNED_NONE` and `BUILDER_EXCEPTION` telemetry. A `None` return records current queue/send/live-ready totals and per-call deltas; it is not automatically called a failure because it may follow an expected veto or a valid queued/send path. Builder exceptions remain visible and re-raised.
- Removed synthetic candidate IDs from `record_current`. Non-candidate Telegram messages are counted in separate unattributed telemetry and cannot inflate candidate-funnel `TG_ENQ` beyond its true candidate context.
- Normalized explicit liquidity tier labels and made unknown/invalid labels fail closed as `liquidity.tier_unverifiable`; case variants such as `below` are treated as `BELOW`, not as tradeable.
- Added terminal contracts and offline regressions for all of the above. Current runtime identity remains `4.5.99-V702-R38-FINAL-CANONICAL`; the package audit amendment is dated 2026-10-10.
- Kept HTF family policy and bounded recovery, bounded MID-tier rescue, the $3,000,000 minimum universe quote-volume floor, score floor, spread/fee viability, fake-break rejection, stop-protection and exposure safeguards, Spot LONG_ONLY/Futures-disabled mode, and the forbidden set unchanged. No new live-gate relief was enabled. Existing Knowledge Shadow tracks emitted alerts; it is not a complete counterfactual outcome study for candidates rejected before later gates.
- Validation is offline only: no live MEXC order, actual Telegram delivery, Railway deployment, or counterfactual profitability claim is made.

## 2026-10-10 — V702 R39 final canonical production guardrails

- Added a central fail-closed guard around the canonical new-entry submit boundary. Default mode is `MONITOR_ONLY_NO_NEW_BUYS`; existing-position lifecycle/exit management is not disabled by flipping the old global runtime mode.
- Added a persistent portfolio peak-to-current equity drawdown guard with a 5.0% default threshold, sticky halt latch, fail-closed account valuation, and explicit reasoned manual-reset pathway. It blocks new entries only; it does not liquidate an open position.
- Added a bounded PREQUAL-only counterfactual shadow for baseline passes and HTF/MID-tier-related rejects. Outcomes are tracked from closed 1-minute bars, configured fee assumptions, and 0.10% per-side modeled slippage; same-bar SL/TP ambiguity stays explicitly unresolved. It does not alter live admission rules.
- Added an explicit `entry_policy=` marker to the pipeline digest and fixed blocked-entry reason attribution so a stale prior execution error cannot explain a monitor-only rejection.
- Preserved Spot LONG_ONLY, the AERO/BNB/CAKE/ETHFI/PUMP forbidden-base list, score/liquidity/fee/stop gates, existing R38 terminal validator identity and its 32 checks, and no hard-gate bypass.
- Added R39 regression tests, including a synthetic async Builder route that reaches the queue and is stopped at the monitor-only submit boundary without an order wire.
- **Not claimed:** live MEXC entry or native stop validation, actual Telegram delivery, Railway/Docker build success, full real-market Builder execution, or profitability. Live-entry opt-in remains disabled by default.


## R39-R1 — Telegram digest symbol-attribution fix (2026-10-10)

- Fixed digest-only extraction/rendering for Spot pairs containing parentheses or Unicode (for example `GOLD(PAXG)/USDT` and `龙虾/USDT`).
- Missing symbol attribution is now shown as `UNATTRIBUTED` with a unique internal dedupe key, rather than fabricating `UNKNOWN/USDT`; symbols are HTML-escaped for Telegram-safe display.
- Extended `--validate-only` so it fails if this diagnostic patch is not installed; added regression coverage for discovery, selected-route, builder-block and knowledge-shadow labels.
- Display/telemetry only: no score, HTF, liquidity, fee, structure, blacklist, stop, trade-cap, entry-policy, or order-submission rule changed. Runtime identity remains `4.5.99-V702-R38-FINAL-CANONICAL`.


## R39-R2 — executable HTF/MID counterfactual study (2026-10-10)

- Corrected the R39-R1 packaging gap: the planned cohort study module was absent from that archive. `v702_counterfactual_shadow.py` is now integrated and required by the terminal validator.
- Added persisted lanes `BASELINE_PASS`, `CURRENT_HTF_RELIEF_PASS`, `HTF_RELIEF`, and `MID_TIER_COUNTERFACTUAL`, with candidate de-duplication, row bounds, closed 5-minute candles, TP1/SL tracking, modeled fees/slippage, and conservative stop-first handling when both target and stop occur in one candle.
- Added periodic JSON/Markdown reports and the `[V702-CF-SHADOW]` runtime marker. The study is read-only and starts at PREQUAL; it does not prove downstream Builder eligibility.
- Kept live thresholds, forbidden-asset policy, Spot LONG_ONLY, `MONITOR_ONLY_NO_NEW_BUYS`, and all execution guardrails unchanged. No performance conclusion is made before real samples are collected.
- Added source-wiring, no-order-API, schema, dedupe, outcome, cost, report and conservative-ambiguity tests.


## R39-R3 — user-requested live pilot authorization + truthful entry status (2026-10-10)

- Changed the central entry mode so the user's explicit request enables the live-pilot path when production MEXC credentials and every pre-existing hard invariant are present. No exchange credentials are embedded.
- Added hard operator override `UNIFIED_LIVE_PILOT_ENABLE=0`; it blocks new live buys even if the older opt-in token remains configured. Existing-position management and emergency/protection logic are not disabled by this override.
- Retained Spot LONG_ONLY, futures/short prohibition, forbidden bases (AERO/BNB/CAKE/ETHFI/PUMP), 70-point score floor, 3M USDT core liquidity floor, fee/spread/structure/stop checks, 5% sticky account drawdown latch, position-manager requirement, two-trade cap and 75 USDT per-entry cap. No gate was lowered to fabricate an order.
- Corrected heartbeat entry status so `ENTRY_STATUS=BLOCKED:MONITOR_ONLY` explicitly reflects the entry policy. The prior `BLOCKED:NONE` could misleadingly look like no block despite monitor-only mode; starvation roots and entry authorization now have separate labels.
- Added offline regressions for configured live-pilot mode, credentials/invariant conjunction, forced-off precedence, and monitor-only Builder control flow.
- The runtime banner and validation identity continue to identify R38 as the canonical executable lineage; R39-R3 is a packaging/guardrail amendment. Live exchange orders, live stop verification, Telegram delivery and real-market profitability are not verified in this environment.


## 2026-10-11 — R40-A4 PREQUAL rejection truth closure

- Fixed a digest observability mismatch where `PRE_REJ` stage counts could be positive while the separate low-level `rejects/top` fields read zero/empty.
- Renamed low-level metrics to `record_rejects` / `record_top` and added candidate+reason deduplicated `prequal_top` from canonical `PREQUAL_REJECT` stage events.
- Added A4 `--validate-only` self-check and regression coverage. No trading gate, score floor, liquidity floor, stop, size, live authorization or execution route changed.
- Public runtime identity remains `4.5.99-V702-R40-SMALL-NET-PROFIT-CANONICAL`; audit revision advances to A4.


## 2026-10-11 — R40-A5 PREQUAL/PREEXEC rejection truth closure

- Extended the A4 digest repair after final pipeline review showed `PX_BLK` counts had no corresponding reason summary.
- Added candidate+reason-deduplicated `preexec_top` from selected-route `PREEXEC_BLOCK` events, including policy, freshness, canonical structure and orderbook reasons after route-prefix normalization.
- Terminal validation now requires visibility of both PREQUAL and PREEXEC reasons. No entry gate, score, liquidity, fee, stop/protection, position-size or execution policy changed.
- Public runtime identity remains `4.5.99-V702-R40-SMALL-NET-PROFIT-CANONICAL`; package audit revision advances to A5.


## R40-A9 — Intraday micro-scalping and VWAP/relative-strength shadow experiments (2026-10-11)

- Added `v702_intraday_shadow.py` as a separate research-only subsystem with four independently labeled lanes: `MICRO_MOMENTUM_1M`, `MICRO_SWEEP_RECLAIM_1M`, `MICRO_PULLBACK_RECLAIM_1M`, and `VWAP_RECLAIM_RS_5M`.
- 1m/5m experiments do not require a bullish 1H/4H trend for each signal; they use local closed-candle structure plus a narrow BTC 15m shock pause. Missing, invalid, or excluded symbols fail closed for the study.
- Added bounded rotating 1m market-data sampling (24 symbols/cycle, split between core-liquidity and micro-liquidity pools), timeout-bounded fetches, SQLite deduplication/outcome tracking and 15-minute JSON/Markdown reports. The research lane never feeds the live order queue and can never submit orders.
- Added UTC-session VWAP reclaim with relative-strength confirmation versus BTC using closed 5m/15m bars. Fixed the return calculation to use its newest closed candle, since the frame passed to it already excludes the potentially open candle.
- Shadow economics deduct two-sided taker fees, measured-or-fallback spread and two-sided slippage. Cost-aware target geometry is explicitly labeled as simulated and capped; ambiguous same-bar stop/target events resolve pessimistically to SL first. No performance claim is made before samples resolve.
- Preserved the canonical denylist, Spot LONG_ONLY, Futures/short prohibition, score/liquidity/orderbook/fees/structure/stop/protection/entry-policy gates, position cap and order execution logic. No live threshold is relaxed. A8 remains in the package as historical lineage; A9 is the current package audit revision.
- Added runtime `--validate-only` contract, Docker packaging, schema/no-order-API and signal/outcome/cost regressions. Offline tests and source validation must pass before release; no live MEXC order, real Telegram delivery, native-stop confirmation or deployment is implied by this change.

### A10 post-deployment closure — BTC 4H history coverage (2026-10-11)
- Production digest showed `MACRO_HISTORY_INSUFFICIENT:n4h=220` despite a configured 260-candle request. The BTC 4H fetch now pins an explicit UTC `since` range and performs up to three bounded recovery pages to fill a truncated edge or missing interval; diagnostics record raw rows, merged rows, closed-row availability, timestamp range, and recovery status.
- Corrected the closed-candle off-by-one: because macro and bearish severity calculations intentionally read `iloc[-2]`, at least 241 total rows are required to guarantee 240 closed-candle observations. Missing history still blocks safely; score, liquidity, spread, structural, policy, orderbook, execution, and protection gates are unchanged.
- This closes a data-coverage/telemetry defect only. It does not declare live execution or profitability verified.


## 2026-10-12 — R40-A15 canonical live-entry authorization parity closure

- Closed a confirmed policy contradiction: central mode resolution could authorize `USER_REQUESTED_LIVE_PILOT` when MEXC credentials and all hard invariants passed, while the final `V702PortfolioDrawdownGuard.authorize_entry` helper unconditionally required `UNIFIED_ALLOW_LIVE_TRADING=I_ACCEPT_LIVE_RISK`.
- The final authorizer now calls `_V702_R39_REFRESH_ENTRY_MODE` as the single source of entry authority. Configured Pilot permission and the legacy explicit token are alternative authorization routes rather than duplicate mandatory gates.
- Preserved absolute precedence of `UNIFIED_LIVE_PILOT_ENABLE=0`, MEXC credentials, Spot LONG_ONLY/Futures-off invariants, forbidden bases, portfolio drawdown valuation/latch, score/liquidity/spread/fee/structure/stop/protection/cap checks, and `hard_gate_bypass=false`.
- Added a terminal A15 release self-test plus local fake-exchange regressions that exercise the real final authorization helper without network access. An enabled Pilot without the legacy token now passes this specific gate when all required invariants are satisfied; emergency-off still blocks.
- Validation: 144 offline pytest tests passed; compilation and `--validate-only` passed; no live MEXC orders or Telegram messages were sent. The attached production transaction event was not included, so the exact rejection stage of the historical single opportunity cannot be proven from this archive alone.


## 2026-10-13 — R40-A18 universe freshness and non-destructive validation

- Aligned the ranked TOP-500 Spot/USDT universe refresh cadence from 900 seconds to 300 seconds, matching the 5-minute scan cycle. Existing V699 bounded deep-scan widths (130/150/170), the >=3,000,000 USDT core-volume threshold, per-cycle candidate/market-data bounds and all downstream quality gates are preserved. This improves market-list freshness without manufacturing extra eligible signals or multiplying OHLCV work across the 500-symbol source.
- Made `--validate-only` use a disposable, auto-cleaned SQLite directory by default. A deliberate non-empty `SCALPER_DB` override is still honored. Pytest-only imports are also isolated so import-time schema initialization cannot mutate the shipped reference database during offline tests; normal `python main.py` runtime DB behavior remains unchanged.
- Sanitized the packaged reference SQLite database after confirming the only stored row was the shadow study's `schema_version=1` bootstrap marker. That marker is recreated by the module's normal schema initializer; it is not trading/event/sample data. The final bundled DB has valid schema and zero rows in every application table.
- Added A18 terminal self-tests and regressions for refresh cadence, DB isolation, score/liquidity/depth floors, Spot LONG_ONLY, forbidden bases, two-trade cap, 75-USDT ticket cap and `hard_gate_bypass=false`.
- **Unchanged:** score floor >=70, core volume >=3M USDT, MICRO depth >=1.90, HTF/local confirmation, structure/fake-break, spread/fees/net economics, stops/protection, Telegram/order lifecycle, entry authorization and execution authority. No live order, real Telegram delivery, live native-stop confirmation or profitability is claimed.


## A22 — Pre-reprice TP1 starvation and rejection observability (2026-10-13)

- Fixed premature TP1-floor rejection on provisional entry/SL/TP geometry. It now records a diagnostic warning and allows the canonical repricing/target path to compute final geometry. The final SR-aware TP1 floor remains hard and includes explicit shortfall/resistance diagnostics.
- Added bounded prequalification rejection context counts for HTF, structure, liquidity, and other blockers without modifying accept/reject decisions.
- Widened the HTF-relief counterfactual capture to 5 points for shadow-only measurement; no live HTF floor changed.
- Added `.gitignore` rules for API secrets, runtime databases, caches, and generated results. Excluded `unified_scalper.db` from this release.
- Preserved Spot LONG_ONLY, score floor >=70, core quote-volume floor >=3M USDT, forbidden assets, ticket/trade caps, execution authority, and all SL/economic/protection gates.


## 2026-10-14 — R40-A30 reject-only history prefetch throughput closure

- Closed a scan inefficiency found during the A29 re-audit: when a valid A29 cache entry already proved that a symbol has fewer than the required 210 contiguous closed 4H candles, the scanner still launched 1H, 15M and 5M OHLCV reads in parallel before A23 rejected it.
- The scanner now checks the verified, time-bounded reject-only cache before launching those requests and skips those three redundant reads for that symbol only. Cache miss, expiry, malformed cache data, or helper error falls back to the original fetch path. The A23 rejection is still counted with an explicit reason, and `/digest` exposes cache skips and saved read counts.
- Kept the minimum 210 contiguous closed 4H rows, no synthetic history, Spot LONG_ONLY, Futures/short prohibition, forbidden bases, live score floor >=70, core quote-volume floor >=3M USDT, MICRO depth >=1.90, TP1 fee coverage >=2.5x, spread/liquidity/structure/HTF policies, order sizing, two-position cap, stops/protection and single execution authority unchanged.
- Added A30 regressions for exact cache validity, boundary expiry, preserved rejection, three-read savings, scanner integration ordering and terminal identity. No external API, Telegram send, real order, or profitability claim is implied.

## 2026-10-15 — A33 Final Audit Hotfix HF1

- Made the A33 local 1H history terminal self-test deterministic with an injected fixed clock and a fixture that ends on the latest closed candle; gap rejection is tested independently of wall-clock minute/second.
- Replaced blind summary-reason truncation with boundary-aware, collision-resistant compact tokens while preserving detailed event reasons.
- Corrected A30 cache-only heartbeat text so an absent prior skip is represented as `none_yet`, not `unknown`; kept the stats writer/reader on the same keys.
- Demoted explicitly historical/superseded R33/R34 validation notices from WARNING to DEBUG to avoid misleading normal startup output.
- Split unmatched Shadow observations from verified same-candidate live-gap telemetry so an unmatched candidate cannot overwrite a prior verified gap alert.
- Updated release-contract tests to use current HF1 validate-only evidence and the active monotonic runtime revision instead of an obsolete log/revision literal.
- Re-ran full pytest in two modes (247/247 in each), five isolated timed groups (247/247 combined), focused regressions (33/33), Python compilation, and `python main.py --validate-only` (pass=true; A33 14/14; hard_gate_bypass=false). Raw logs are packaged under `results/`.
- No live trading gate was relaxed. Real MEXC fills, real Telegram delivery, exchange-native stop behavior in production, deployment builds, and profitability remain unverified.
- Remaining partial/technical debt is documented in `docs/audits/FINAL_PRODUCTION_AUDIT_A33_HOTFIX_HF1_AR.md`, especially exclusive candidate terminal attribution, a shared starvation/root snapshot, hard PRESEND/QUEUE shadow-gap eligibility, dynamic spread policy (shadow-only research), and gradual decomposition of `main.py`/validators.

## A34 HF2 — Current-log closure (2026-10-15)

- Added an allowlist-first guard for per-candidate micro-handoff telemetry. Disallowed lanes only increment aggregate diagnostic counters.
- Kept short-history cache skipping reject-only and made its saved-read accounting explicit; optimization accounting failure falls through to the ordinary fetch.
- Set bounded A31 short-history recheck TTL to 420 seconds, still invalidating sooner at the next 4H boundary; closed-history floors remain unchanged.
- Required exact CandidateRef plus recent PRESEND/QUEUE/SENT evidence before a Shadow/live gap can be marked as a verified match.
- Added shadow-only observation of candidates rejected by the fixed spread ceiling, including ATR/spread ratio and depth/volume context where available. The live spread ceiling and returned decision are unchanged.
- Added a conditional policy-starvation note and an Operator Digest legend to clarify classifier scope and aggregate-counter semantics.
- Extended the A34 terminal self-test and regression tests. Real MEXC orders/fills, exchange-native stop behavior, real Telegram delivery, deployment builds and profitability remain unverified.

### A34 HF2 — final offline verification record (2026-10-16)
- Final current-source pytest: **257/257 passed** with default plugin loading (42.07s pytest time; 45.65s wall; 75s timeout; exit 0) and **257/257 passed** with external plugin autoload disabled (41.26s pytest time; 42.86s wall; 75s timeout; exit 0).
- Independent timed groups also passed **257/257**: A7–A10 38/38, A11–A17 38/38, A18–A24 39/39, A25/A26/A29–A34 54/54, and cross-module/release contracts 88/88. Every group had an explicit timeout and exit code 0.
- `py_compile` passed (5.87s, exit 0). The current `--validate-only` passed with top-level `pass=true`, A34 validation PASS, `hard_gate_bypass=false`, and `live_threads=[]`, exit 0. Logs and exit records are in `results/final_hf2/`.
- Timeout diagnosis: no individual test call exceeded the timeout; the slowest test call was 6.03s. A25 AST work occurs during test-module collection/import; its isolated probe completed under the 30s subprocess limit. Earlier command-wrapper interruptions were not counted as successes and the full suite/group 4 were re-run with recorded exit status.
- This is local validation, not live certification. No live MEXC order/fill, exchange-native stop/cancel test, production Telegram delivery, Docker/Railway deployment, or profitability result was produced.

## A36 — Strategy-aware scalp HTF relief and local evidence closure (2026-10-16)

- Added the bounded A36 policy at the end of `main.py`, connected through the active A29 HTF-relief, Pullback-quality and soft-HTF wrappers. Existing engines and execution authority are retained; no engine was removed.
- Added a bounded, family-aware higher-timeframe context relief for SCALP/SCALPING/INTRADAY/DAY styles in `PULLBACK`, `MTF_PULLBACK`, `COMPRESSION_EXPANSION`, `MOMENTUM_EXPANSION`, and `LOCAL_STRENGTH_BREAKOUT` only.
- Requires a known context-safe HTF state and minimum strength (35/100 generally; 40/100 for MTF_PULLBACK), BULLISH/NEUTRAL macro context, no crash/extreme/stressed condition, fresh verified closed 5m evidence, and fresh ordered closed 15m history (at least 24 rows and two independent local confirmations).
- Compression/momentum relief additionally requires volume ratio >= 1.10; local-strength breakout additionally requires a BOS confirmation.
- Added a second, stronger-only pullback near-miss lane for HTF-only quality failures: setup >= 82, composite quality >= 84, at least four closed 5m confirmations, at least two 15m confirmations, independent volume/relative-strength/structure/retest support and chase <= 0.75 ATR.
- Kept A29's existing relief first and retained A35 HTF projection/Builder parity. A36 failure diagnostics are attached without masking the established rejection reason.
- Preserved live score floor >= 70, fee/net-profit economics, spread ceilings, order-book integrity and depth floors, fake-break safeguards, stop/protection logic, Spot LONG_ONLY, Futures/short disabled, denylist, maximum two concurrent trades, <= 75 USDT ticket cap, and `hard_gate_bypass=false`.
- Verified the effective JIT/Builder authority: `_v542_exact_policy_precheck` is rebound to `_v692_builder_precheck`, which reuses the canonical verdict when facts are unchanged and calls `_v702_public_prequal` when facts change. Removed attempted hooks from the shadowed legacy precheck body so no duplicate dead policy code remains; the canonical base prequalification and downstream tier/Micro/order-book guards remain in force.
- Added focused A36 regressions for strategy/family eligibility, closed-bar 5m/15m evidence, strict Pullback-only near-miss handling, active Builder/canonical-prequal ownership, and hard-gate preservation; updated append-only revision compatibility tests. Current live MEXC order execution, real Telegram delivery, native exchange stop behavior and profitability are not verified by this offline patch.

### A36 — final offline verification record (2026-10-16)
- Full pytest: **259/259 passed** in 46.95s; exit 0.
- Focused regression set: **32/32 passed** in 28.63s; exit 0.
- `py_compile`: PASS for canonical runtime, guardrails, shadow modules and tests.
- `python main.py --validate-only`: PASS; JSON `pass=true`, A36 validation PASS, `live_threads=[]`, `hard_gate_bypass=false`, exit 0.
- No real MEXC orders, Telegram delivery, live stop verification, deployment build or profitability test was performed.


## A36 — final post-audit closure (2026-10-16)

- Fixed scalp-only HTF relief eligibility so a missing `strategy_style` remains `UNKNOWN`; relief now needs an explicit scalp style or explicit scalp mode.
- Corrected the 15m local-history boundary to require 24 closed candles after excluding the in-progress candle; duplicate timestamps now fail closed.
- Kept score >=70, SPOT LONG_ONLY, Futures/short disabled, denylist, two-trade/75-USDT caps, fees/net economics, spread/depth/book checks, fake-break, stop/protection, and execution authority unchanged.
- Re-ran all 262 tests successfully in the full suite and in four bounded independent groups; focused regressions 35/35, `py_compile` PASS, and `--validate-only` PASS with `live_threads=[]` and `hard_gate_bypass=false`.
- Offline-only verification. No real MEXC order, Telegram delivery, production deployment, or profitability test was performed.


## A37 — Production audit closure (2026-10-16)

- Structured compacted blocker records now preserve the symbol/root/stage/reason independently of section headings; scorer, route and builder lists share the same formatter.
- Same-closed-bar TP+SL is resolved as SL-first in the Knowledge Edge ledger, matching both shadow lanes.
- Spread/ATR shadow telemetry derives ATR percent from raw ATR and price where possible, while the fixed live spread ceilings remain unchanged.
- Added explicit score-floor-used/canonical metadata to score rejects, unique-symbol/boundary short-history classification, and cycle/window-scoped blocker/funnel telemetry.
- Added bounded Telegram HTML repair, heartbeat-freshness healthcheck, Docker healthcheck and `.dockerignore`.
- Pinned direct aiohttp dependency exactly; transitive hash locking remains explicitly unclaimed pending a reproducible resolver/index run.

## 2026-10-17 — A38 production remediation hardening (NO-GO remains)

- Added durable SQLite entry execution intents written before BUY submission; unresolved/unknown execution blocks subsequent entries and is not silently cleared on startup.
- Fixed critical post-fill adoption hazards: confirmed fill drift no longer returns before state/protection handling; invalid post-fill target geometry creates a managed target-pending state; actual reported fills are not clipped to requested quantity; net sellable amount accounts for base-asset fees.
- Prevented Maker partial/unknown outcomes from triggering a duplicate full-size Market fallback; added terminal reconciliation for Market fills and zero-quantity pending trade states for unknown execution outcomes.
- Made trade snapshot/finalized-ID persistence failures explicit and entry-blocking; added intent/protection state updates and conservative recovery path.
- Hardened stop replacement around unverifiable cancellation; native stop coverage requires a valid amount; software SL may represent breakeven/profit-lock states; added final KillSwitch checks directly before LIMIT/MARKET buy sends.
- Added real ATR/relative-strength helpers for referenced engines; timestamps are unit-normalized and future data is rejected; fixed HTF/context initialization and tier recovery references.
- Improved starvation attribution, price-sensitive rejection dedup, alternate-candidate attribution, ring-buffer drop accounting, Telegram API ACK validation, chunk callback semantics, and retry scheduling.
- Added test_v702_production_audit_fixes.py and an Arabic remediation report. Offline regressions do not substitute for live MEXC/Telegram, Docker/Railway, restart/leader-election, or profitability tests. Production status remains NO-GO for unattended live trading.


## V702 A39 — 2026-10-17 — Free-balance recovery and pending-order coherence

- Fixed the prequal deadlock where `balance.entries_blocked` could prevent every candidate from reaching the Sizing path that normally refreshes and recovers a temporary balance latch.
- Added a bounded 30-second recovery worker that refreshes the exchange balance only while one of the known soft balance latches is active.
- Canonicalized USDT parsing across `free`, `used`, and `total`; sizing consumes `free.USDT` only, and never falls back to `total` when spendable balance data is missing.
- Prevented a successful balance fetch from clearing unresolved execution intents, unknown submissions/fills, or unresolved protection/order states.
- Kept the 75 USDT per-entry ceiling, 3 USDT account reserve, cost-aware preflight, maximum two concurrent trades, Spot Long-Only policy, and all hard quality/economic/protection gates unchanged.
- Added regression tests for the requested scenario: 75 USDT free while 75 USDT is already used/locked by another order. Local tests do not certify live MEXC execution or profitability.


## V702 A40 — 2026-10-17 — Live entry-block root-cause and order-reconciliation diagnostics

- Exposed the actual `LIVE_ENTRIES_BLOCKED` active/reason/location/age in the existing canonical heartbeat and operator digest. `balance.entries_blocked` is no longer the only visible explanation for the zero-pass funnel.
- Added the age and latest values of the real balance snapshot plus A39 recovery success/block/error/skipped-nonbalance/task-error counters. The A39 recovery worker now counts and records intentional skips for non-balance latches rather than looking silent.
- Recorded the startup unresolved execution-intent reconciliation result even when the result is zero; errors remain explicit and fail-closed.
- Added a bounded, read-only diagnostic worker while an entry block is active. It samples unresolved durable intents and exchange open orders every 90 seconds, reports real/error/unsupported status, and never clears a latch, cancels an order, or places a trade.
- Added the A40 self-test to `--validate-only` and updated canonical release contracts. SPOT Long-Only, forbidden assets, the 75 USDT per-entry cap, reserve, concurrent-trade cap, fees, liquidity/HTF/score gates, and order-protection gates remain unchanged.
- This is observability and reconciliation evidence only: no live MEXC, Telegram, native-stop, deployment, or profitability claim is made. Unattended live production remains NO-GO until controlled live verification.


## V702 A41 — 2026-10-17 — Durable execution-intent reconciliation and verified startup recovery

- Added a bounded 60-second reconciler for the specific startup execution-intent latch; it re-reads durable unresolved intents, performs exact venue-order reconciliation, records auditable outcomes, and never cancels or submits orders.
- Allows deterministic `NO_FILL_TERMINAL` resolution only with a venue-confirmed terminal canceled/expired/rejected status, an explicitly present zero fill amount, no positive historical fill evidence, exact order/symbol/side identity and no linked active trade.
- Classifies any partial/full fill as `FILLED_REQUIRES_POSITION_PROTECTION`; it remains unresolved until normal trade adoption and protection handling settle the exposure. Unknown IDs, ambiguous client IDs, stale/error/unsupported snapshots, mismatches, open orders, unknown BUY orders, unprotected trades or changed block roots remain blocked.
- Narrowly permits clearing only the original startup intent block after durable DB count reaches zero and fresh real free-balance plus open-order snapshots prove that any remaining open orders are known protective/target SELL orders on actively protected trades; the exact block source/reason is checked again when applying the clear.
- Added exact-identity, zero-fill, partial/full-fill, historical-fill-evidence, ambiguous/missing-ID, order mismatch, unknown BUY, verified clear, fail-closed, and worker-cycle regression coverage. Added `A41_INTENT_RECON` heartbeat counters and pending-intent summary.
- Preserved Spot LONG_ONLY, Futures/short prohibition, denylist, score/liquidity/fee/spread/depth/economic checks, position/sizing ceilings, stop and protection policies, emergency off switch, and `hard_gate_bypass=false`.
- Local/offline closure only. Live MEXC order state, native protection, Telegram delivery, Docker/Railway deployment and profitability remain unverified.
- Final offline verification: full pytest **314/314 passed** (25.75 s); focused A39/A40/A41 plus release-compatibility set **68/68 passed** (13.59 s); `py_compile` exit 0; `python main.py --validate-only` exit 0 with A41 self-test **14/14**, `hard_gate_bypass=false`, and `live_threads=[]`. Evidence is under `results/V702_A41_*`.


## V702 A42 — 2026-10-18 — Boot self-test database isolation and mock-intent quarantine

- Root-cause traced the A41 `MOCK-*` unresolved-intent rows to the V517 unknown-outcome self-test: it used a mock exchange while durable intent writes still pointed at the configured `DB_PATH`.
- The V517 unknown-outcome self-test now runs only on a disposable SQLite database while the internal self-test guard is active and the live runtime is unarmed; the original DB path is restored and the temporary DB/WAL/SHM files are removed.
- Explicit known test fixtures are quarantined from live unresolved-intent reconciliation without deleting or changing their DB rows. A `TEST/USDT` symbol alone is insufficient. The direct reconciler refuses to query the real exchange for a known test fixture.
- Added bounded `A42_INTENT_QUARANTINE` and `A42_SELFTEST_DB` telemetry and regression tests for DB isolation, source markers, no-delete behavior, and preservation of Spot LONG_ONLY/hard gates.
- Real or ambiguous execution intents remain fail-closed; no orders are placed/canceled and no latch is cleared solely because a mock row was recognized. Offline validation does not prove the user's live database has been cleaned, live MEXC reconciliation, Telegram delivery, deployment, or profitability. Unattended live operation remains NO-GO pending controlled live verification.

## V702 A47 — 2026-10-18 — Coverage, policy reuse and attribution closure

- Added bounded configurable event-ring retention (default 20,000) and split event eviction rate from actual telemetry-window coverage.
- Standardized the operator digest interval to 1,800 seconds across defaults, validation, fallback paths, and active manifest metadata.
- Added explicit preflight-vs-arbiter prequal attribution and bounded duplicate reason counting by candidate/stage/reason per cycle or epoch.
- Made strategy allowed-regime metadata explicit before bootstrap, conservatively inheriting existing policy and failing closed to NEUTRAL when no valid definition exists.
- Blocked stale or cross-cycle prequal snapshot reuse from overriding the current family macro-policy rejection; requires a fresh matching cycle and fingerprints.
- Aligned active revision identity, source hashes, tests, validation evidence and manifest records with A47; historical missing A36 logs are not fabricated.
- Safety decision: the proposed V518 live bridge expansion into BEARISH_NORMAL remains disabled for live entries. Existing macro/family gates, score floor, Spot LONG_ONLY and fail-closed safety controls remain enforced.
- Validation artifacts are packaged under `results/V702_A47_*`; offline success does not certify live MEXC execution, native stop protection, opportunity Telegram delivery or profitability.

## A52 validation status (2026-10-21)
- `python -m compileall -q .`: PASS.
- `pytest -q test_v702_production_audit_fixes.py`: 23 passed.
- Full-suite/long-running checks were not accepted as clean because they did not complete reliably in this environment.
- No live exchange order, live Telegram delivery, or Docker image build was tested. Release remains NO-GO for unsupervised live trading.


# V702 A55 — Shadow PreSend, post-Builder evidence, and fail-closed EdgeGate (2026-11-04)

- Added balance-independent, read-only Shadow PreSend using fresh order-book depth, VWAP, spread, venue taker fees, estimated market friction, slippage limits, round-trip cost floor, and existing TP/fee/net-economics constraints. Missing fee/book evidence blocks Edge eligibility.
- Paper outcomes now wait for a future closed 1m candle to touch the planned entry; after Builder, the exact Paper record is annotated with Shadow eligibility, final geometry, measured round-trip cost, and separate market versus account execution readiness.
- Edge learning now consumes only current A55 Builder+Shadow eligible Paper outcomes; it requires 100+ resolved observations, net partial-exit R, positive 90% lower confidence bound, positive chronological halves, and BH FDR q=0.10. The live gate requires the exact family/style/timeframe/HTF recipe and still rechecks all existing live controls.
- Updated score buckets and bounded Paper capacity to 120. Kept the true TP exit split at 60/30/10.
- Real BUY requires both `UNIFIED_LIVE_PILOT_ENABLE=1` and `UNIFIED_A55_LIVE_ARM=1`; release examples keep both OFF. Scan/Paper can continue with zero USDT.
- A53 and A54 ZIP archives remain unchanged. This release is offline validated only; live MEXC/Telegram/deployment/profitability are not claimed.


# A58.1 — Canonical runtime/build closure (2026-11-13)

- Added one shared hard-forbidden asset policy module and reused it in runtime prefetch/handoff guards, both shadow systems, and production guardrails. CAKE remains forbidden; older V609 fee-rescue comments and fixtures are historical regression context only.
- Added one process-wide SQLite writer lock shared by KnowledgeOutcomeLedger, portfolio drawdown guard, ExpansionShadow and both V702 shadow modules. Shadow DB reads/writes and the PortfolioDrawdown DB path are offloaded from the asyncio event loop. Counterfactual shadow submissions use a bounded task queue; backpressure drops observational samples instead of stalling canonical scan/decision flow.
- Kept the final live score floor at 70; the floor policy remains the single live-floor authority. Paper/shadow sub-threshold research cannot authorize a live queue item.
- Replaced the broken Docker hash-gate default with an explicit two-path contract: Railway's default build installs pinned direct dependencies from requirements.in; CI resolves a Python 3.12 Linux/amd64 transitive SHA-256 lock and builds with STRICT_HASH_LOCK=1. CI publishes the resolved lock artifact. No fake hashes are stored in the repository.
- Pinned the image builder's pip version, updated the hidden GitHub Actions workflow, and documented the need to push `.github/workflows/` with Git.
- Documented Railway's root-owned volume requirement (`RAILWAY_RUN_UID=0`), `Always` restart policy and the distinction between Docker HEALTHCHECK and Railway's deployment-only healthcheck.
- Added regression contracts for shared policy/lock identity, shared database initialization, event-loop offloading, Docker dependency modes and the immutable 70-point live floor.
- No strategy, candidate ranking, score computation, admission threshold, order sizing or execution gate was intentionally relaxed. Full live exchange/Telegram behavior remains unverified; unattended live trading remains NO-GO.
- Final local verification on Python 3.13.5: `compileall` PASS; `--validate-only` exit 0 with `bot_started=false` and `live_threads=[]`; full pytest **435 passed, 1 skipped, 0 failed** with a clean process exit. Docker/Python 3.12 target build and all live MEXC/Telegram checks remain unrun.


## Historical `main.py` header archive

The following legacy version narrative was moved out of the executable header to keep startup source navigation focused. Its comments are preserved verbatim as historical context; they do not describe a separate active entry authority.

```text
# FINAL PATCH — V702 R37 S/R-AWARE TARGETS (2026-10-09)
# Re-anchor RR targets after final SL bounds; cap TP1/TP2 before confirmed closed-15m
# resistance; preserve canonical fee/RR, FamilyPolicy, RiskCoherence and PreSend gates.
# Fee-target rescue is not permitted to erase an S/R target ceiling.
# v4.5.99-V606 FINAL CURRENT-CYCLE RESCUE ESCALATION / STARVATION TRUTH:
#   * Closes the L1->L2 same-cycle rescue escalation gap when the current
#     zero-winner cycle has a prequalified candidate at the existing L2 floor.
#   * Heartbeat now prefers truthful current-cycle GLOBAL diagnostics over a
#     stale historical NO_OPP label: SCORE/SELECTION/POLICY/MSE-RANK starvation.
#   * No score floor is lowered, no hard gate is bypassed, and no order path is
#     introduced. Canonical SignalBuilder remains the final authority.
#
# v4.5.99-V605 FINAL CURRENT-CYCLE GLOBAL RESCUE / STARVATION CLOSURE:
#   * Global rescue now evaluates the CURRENT prepared/prequalified cycle
#     before V45GlobalFunnelState.note_cycle() records it.
#   * A fresh zero-winner cycle can therefore activate the existing bounded
#     L1/L2 rescue ladder from its own top candidate instead of waiting for
#     historical window evidence.
#   * Hard global floor, canonical gates, risk, liquidity, SL/TP, execution,
#     LONG_ONLY/SPOT and fail-closed behavior are unchanged.
#
# v4.5.99-V604 FINAL FEE-RESCUE COHERENCE / STARVATION FORENSICS:
#   * Audits the exact fee-rescue path with the FINAL candidate geometry and
#     records whether rescue succeeded, failed, was applied, or was hard-rejected.
#   * Adds an offline XMR-like regression proving the observed 489/484.013857/
#     493.733352/498.466704 geometry can be rescued without lowering any fee gate.
#   * Keeps MIN_NET_RR_TP1, MIN_TP1_TO_FEE_RATIO and MIN_NET_RR_OVERALL hard.
#   * No entry, risk, SL/TP, Balance/TruthSeal, Exposure, Liquidity, Execution,
#     LONG_ONLY/SPOT, or fail-closed authority is relaxed.
#
# v4.5.99 FINAL ALL-IN-ONE RECALL / UNIVERSE-TOTAL-TIMEOUT / FORBIDDEN-ALERT-DEDUPE:
#   * Adds a bounded total read-only market-data budget per symbol so sequential
#     4TF+ticker reads cannot stretch one symbol into a multi-minute scanner stall.
#   * Adds a bounded timeout around dynamic-universe fetch_tickers so boot/refresh
#     cannot hang independently of the per-symbol scanner timeout.
#   * Deduplicates forbidden-coin operator alerts by symbol/reason/stage with TTL;
#     the scan still skips the forbidden asset and V587 remains final authority.
#   * No entry gate, risk rule, SL/TP rule, execution authority, or LONG_ONLY SPOT
#     invariant is relaxed.
#
# v4.5.98 FINAL ALL-IN-ONE RECALL / SCAN-TIMEOUT / FORBIDDEN-PRESCAN CLOSURE:
#   * Adds bounded read-only market-data timeouts so one stalled exchange read
#     cannot freeze the scanner and age otherwise-valid candidates.
#   * Prunes forbidden assets before expensive scanner reads; V587 execution
#     enforcement remains the final authority and no trading gate is bypassed.
# v4.5.97 FINAL ALL-IN-ONE RECALL / STARVATION / CYCLE-ACCOUNTING CLOSURE:
#   * Extends V596 with a bounded EMPTY-MSE legacy recall lane so a real
#     NO_OPP cycle can still test a small number of legacy-router opportunities.
#   * Resets per-cycle global counters before every GlobalOpportunityBrain run,
#     preventing stale prior-cycle telemetry from triggering recovery after a
#     brain failure or early return.
#   * Bridge attempt timestamps are armed before builder execution, preventing
#     repeated deterministic re-attempts inside the cooldown interval.
#   * Forbidden symbols are pruned before legacy recovery work; final V587
#     executor enforcement remains authoritative.
#   * Heartbeat exposes distinct MSE-RANK and LEGACY-BRIDGE outcomes.
#   * Final boot telemetry exception is observable instead of silently dropped.
#   * LONG_ONLY SPOT, fail-closed behavior, all hard gates, execution authority,
#     Balance/TruthSeal/Exposure/Liquidity/PreSend/SL/exit invariants unchanged.
# v4.5.96 FINAL MSE RANK-STARVATION / LEGACY-RECALL / OBSERVABILITY CLOSURE:
#   * Closes the observed live funnel where MSE generated/hard-valid candidates
#     but ranked zero (G/V > 0, R/W = 0), with exact rank-reject diagnostics.
#   * Adds a bounded legacy-router recovery bridge ONLY for a technically empty
#     MSE/global cycle; every recovered symbol still goes through SignalBuilder.
#   * Adds heartbeat visibility for MSE rank starvation and the recovery bridge.
#   * Makes boot-finalization exceptions observable instead of silently disappearing.
#   * No HTF, liquidity, structure, fee, score, Balance/TruthSeal, Exposure,
#     PreSend, SL, execution ambiguity, LONG_ONLY SPOT, or exit authority is bypassed.
#
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# v4.5.99-V673 FINAL — CANONICAL DATA/STRUCTURE/ACCOUNTING COHERENCE CLOSURE.
#   * Repairs missing PB/MTF quality facts at the exact V654/V671 recovery
#     boundary from the same prepared snapshot; no new market-data fetch.
#   * Reuses existing canonical HTF recovery, structure formula, retest calculator,
#     closed-bar RS calculator, volume derivation and final entry-vs-zone chase.
#   * Re-runs the same V587 hard quality contract; missing facts remain reject.
#   * Fully wires canonical snapshot/structure/economic/watchdog/lifecycle/scheduler facts into existing authorities.
#   * Adds truthful heartbeat correlation of execution attempts vs builder/pre-send/
#     queue/send and exact current-cycle watchdog-rejection count.
#   * No fee/RR/SL/risk/HTF/liquidity/structure/score hard floor is relaxed.

# v4.5.99-V669-R4 FINAL — integrated hardening/recalibration build.
# Changes: 75-USDT ticket cap/request, 2 slots, 3-USDT reserve, 12% peak-equity
# entry halt, 0.40% minimum SL, 1500s score-starvation evidence, paper score 64,
# news blackout enabled, combined >=62 score-floor invariant, invalid-symbol
# blacklist fail-closed, and final V612 boot-policy validation.

# v4.5.99-V609 FINAL — FEE-RESCUE EXECUTION CLOSURE / CAKE ROOT-CAUSE PATCH:
#   * Closes the observed live gap where a PULLBACK candidate reached PreSend with
#     valid geometry and score but was still rejected as fee_unviable even though
#     the existing bounded V420/V551 target rescue could prove the same trade
#     economically viable without lowering any fee threshold.
#   * Adds one final, fail-closed retry of the EXISTING fee-target rescue only when
#     SizingEngine returns fee_unviable. No new execution path and no fee-floor
#     relaxation are introduced.
#   * Reuses the exact final entry/SL/TP/notional/strategy score supplied to the
#     sizing call, re-runs the ORIGINAL hard fee gate, and hands rescued TP1/TP2/TP3
#     back through the already-existing PreSendGate ordering/Exposure/Liquidity
#     authorities.
#   * Adds exact fee-rescue outcome telemetry, including why rescue was rejected,
#     preventing future silent CAKE-like failures.
#   * Adds a deterministic CAKE regression using the exact logged geometry:
#     1.864 / 1.857314 / 1.870597 / 1.877193 / 1.896983 at score 68.1.
#   * Keeps MIN_NET_RR_TP1=0.8, MIN_TP1_TO_FEE_RATIO=2.5 and
#     MIN_NET_RR_OVERALL=1.2 hard; LONG_ONLY/SPOT, Balance/TruthSeal, Exposure,
#     Liquidity, Structure, PreSend, SL/TP, Execution and fail-closed authority
#     are unchanged.

# v4.5.95 FINAL HEARTBEAT-WRAPPER / WATCHDOG-STARVATION / BOOT-CLOSURE:
#   * Fixes the exact production error shown in Railway:
#       _v584_install_telemetry.<locals>._emit() missing 1 required positional argument: 'cls'
#     The wrapper is installed as a staticmethod, so it MUST have zero positional
#     receiver arguments. The previous `cls` signature made every heartbeat call
#     fail before the function body executed, which then triggered the watchdog
#     and masked otherwise healthy LIVE operation.
#   * Adds a deterministic V595 regression self-test that actually invokes the
#     installed heartbeat wrapper, not just source-checking its signature. This
#     specifically prevents recurrence of staticmethod/classmethod mismatches.
#   * Keeps heartbeat telemetry non-blocking: instrumentation failure is logged
#     and never changes trading decisions or opens a fall-open path.
#   * Removes the final silent `except: pass` around boot telemetry finalization
#     and logs the exception instead, preserving non-blocking behavior while
#     making future lifecycle regressions visible.
#   * Removes the accidental historical comment tail after the executable main()
#     call so the canonical file ends at the actual runtime entry point.
#   * All entry strategy, opportunity routing, scoring, HTF, liquidity, structure,
#     Balance/TruthSeal, Exposure, PreSend, SL/TP, execution authority and
#     LONG_ONLY SPOT invariants remain unchanged.
#
# v4.5.93 FINAL RUNTIME-LIFECYCLE / EXCEPTION-OBSERVABILITY / SELF-TEST CLOSURE:
#   * Fixes the actual production boot blocker shown in the supplied Railway log:
#     the V525 protected-entry/TradingView self-test used stale grade examples
#     that no longer matched the active v4.5.87 opportunity-grade implementation.
#     The production grader is unchanged; the self-test is now aligned with the
#     canonical grader boundaries so validate_config() can prove the real policy.
#   * Replaces both runtime asyncio.get_event_loop() lookups with
#     asyncio.get_running_loop() in active async contexts, removing the Python
#     DeprecationWarning and preventing accidental creation/retrieval of a
#     non-running loop. Signal-handler installation remains fail-closed.
#   * Adds source-level regression checks for the deprecated loop API so the same
#     warning cannot silently return in a later patch.
#   * Fixes signal lifecycle correctly: SIGINT/SIGTERM handlers are installed
#     inside run_bot() on the running loop, not synchronously before asyncio.run().
#   * Adds bounded exception-observability telemetry in critical execution/SL/PM
#     paths where nonfatal instrumentation exceptions were previously silent;
#     trading decisions and fail-closed behavior are unchanged.
#   * Adds V593 runtime-lifecycle regression validation to the mandatory boot chain.
#   * Re-runs the existing V591 strategy/policy/profile/closed-bar parity audit
#   * Canonical runtime version: v4.5.95; the runtime identity is validated by V594/V595.
#     unchanged; LONG_ONLY SPOT, execution authority, safety gates, SL/TP,
#     Balance/TruthSeal, Exposure, Liquidity, PreSend and all existing strategy
#     gates remain unchanged.

# v4.5.92 FINAL BOOT-VALIDATION / ASYNCIO / SELF-TEST CLOSURE BUILD:
# v4.5.91 FINAL ALL-STRATEGY PARITY / INVARIANT CLOSURE BUILD:
#   * Final release marker is synchronized with SCRIPT_VERSION below.
#   * Includes v4.5.90 canonical-context policy closure and closed-bar DUAL entry parity.
#   * Includes v4.5.89 non-finite quality protection and corrected raw-GEN funnel accounting.
#   * Includes v4.5.91 cross-layer strategy/family/policy/profile/closed-bar invariant audit.
#   * No strategy, safety gate, execution authority, risk rule, or LONG_ONLY/SPOT invariant is removed.
#
# v4.5.86 FINAL ROOT-CAUSE / SIGNAL-STATUS / CLOSED-BAR-COHERENCE BUILD:
#   * Canonical BUY alerts are PENDING until final gates complete.
#   * Negative RS no longer earns long-quality points.
#   * Bearish severity uses the last CLOSED 15m candle.
#   * Starvation alerts expose fresh exact builder blockers.
# v4.5.80 FINAL PULLBACK-ALL-COHERENCE BUILD: retains the complete
# complete v4.5.78/v4.5.79 codebase and applies the full bounded PULLBACK
# coherence closure: (1) shallow_pullback is supporting evidence only, never
# standalone confirmation; (2) PULLBACK/MTF_PULLBACK structural SL prefers a
# confirmed closed-bar swing-low/pullback invalidation with bounded ATR buffers;
# (3) adaptive repricing re-applies structural SL from the FINAL entry; (4) final
# PULLBACK entry remains anchored to its validated zone with a bounded ATR
# envelope and final chase check; (5) the existing single JIT transient-spread
# recheck remains the only spread rescue and tier spread stays a hard gate.
# Existing TP/SL, Exit Authority, Recovery, Global Funnel and 80-USDT sizing/cap
# behavior remain intact. No execution safety gate is bypassed and no strategy
# section is removed.
"""
================================================================================
    UNIFIED SCALPER v4.5.18-COMPREHENSIVE-FINAL-OPPORTUNITY-BRAIN-GLOBAL-CANONICAL-COHERENCE
  Long-Only Spot | MEXC | Composite Score Engine | Fail-Closed
================================================================================

  v4.5.2 OPPORTUNITY-BRAIN GLOBAL ARBITRATION / GLOBAL FUNNEL REPAIR
    * Global-score preservation, market-wide funnel telemetry, bounded rescue
      retries, universe quote-volume fallback, and starvation-alert gating.
    * LONG_ONLY SPOT / Fail-Closed / SL & execution invariants preserved.

  v4.5.3 GLOBAL<->CANONICAL COHERENCE REPAIR (bounded, additive, fail-closed):
    * Canonical prequalification BEFORE global winner declaration (no new
      fetch; reuses the same MSE snapshot facts the canonical funnel knows).
    * Correct funnel telemetry semantics: global_selected is no longer
      reported as execution-queued; new GEN/PRE/RANK/SEL/CANON/SEND chain.
    * Per-winner canonical rejection attribution ([GLOBAL->CANON] reason=*)
      with aggregate counters (htf/liquidity/score/structure/pre_send/
      balance/execution/other).
    * Bounded adaptive canonical score floor (70->68->66->64->62, TTL-based,
      auto-revert on successful send; armed ONLY when the real bottleneck is
      score_below_threshold — never under crash/kill/balance/watchdog and
      never when liquidity/HTF/structure is the dominant reject reason).
    * Execution-aware TOP-500 source universe (tier!=BELOW + bounded spread filter
      from already-fetched tickers) with a single bounded expansion 120->150
      only when execution-eligible universe < 100; degraded universe allowed.
    * Cycle telemetry disambiguation: window_cycles vs cumulative_cycles,
      process_start_ts, last_successful_global_cycle_ts (minimal SQLite
      persistence; a lost counter NEVER opens trading).
    * Starvation classifier modes: NONE/NO_OPP/HTF/LIQUIDITY/STRUCTURE/
      SCORE/EXECUTION/SYSTEM; Near-Miss accepts only score-gap candidates
      that already passed hard eligibility.
    * T1..T16 acceptance self-tests (env UNIFIED_V453_SELF_TEST=1).
    * INVARIANTS UNCHANGED: LONG_ONLY, MEXC SPOT, no futures/leverage/shorts,
      KillSwitch, TruthSeal, BalanceReconciler, ExposureProtection,
      DailyCircuitBreaker, FailedSendCB, ExchangeWatchdog, LiquidityDepth,
      Precision, SL verification chain, PreSendGate, TP1/TP2/Runner geometry,
      risk model. Global winner still CANNOT bypass any hard gate; canonical
      SignalBuilder remains the only execution authority.

  v4.5.4 GLOBAL<->CANONICAL COHERENCE — FINAL REPAIR + TELEMETRY/UNIVERSE PATCH (bounded, fail-closed):
    * Canonical prequalification now runs BEFORE global arbitration: the
      arbiter ranks ONLY prequalified candidates (MSE candidates -> canonical
      prequalification -> global arbitration -> final winners -> canonical
      execution -> queue -> send). No post-arbitration correction remains.
    * Real adaptive-floor TTL: every relief step (70->68->66->64->62) carries
      an expiry (V453_SCORE_FLOOR_TTL_SEC) and walks back toward the base ONE
      step at a time; send recovery preserved; floor bounded [62..base].
    * Windowed starvation classification: the bottleneck is computed from
      in-window funnel deltas (generated/ranked/selected/canonical/queued/
      sent + reject-category deltas) with explicit priority
      SYSTEM > HTF/LIQUIDITY/STRUCTURE > SCORE > EXECUTION.
    * Stronger T1..T16 behavioral self-tests (real lifecycle, real hazards,
      real funnel semantics) — no new test framework.
    * Version telemetry fix: runtime heartbeat/startup logs report v4.5.4.
    * Cached orderbook/depth reuse verification inside prequalification:
      NO new fetch; absence is never an allow; the canonical pre-send
      LiquidityDepth gate remains the final authority.
    * INVARIANTS UNCHANGED: LONG_ONLY, MEXC SPOT, no futures/leverage/shorts,
      KillSwitch / TruthSeal / BalanceReconciler / ExposureProtection /
      DailyCircuitBreaker / FailedSendCB / ExchangeWatchdog / LiquidityDepth /
      Precision / SL verification / PreSendGate all intact; a global winner
      still CANNOT bypass any canonical hard gate.

  v4.4.x-FINAL-HARDENED-ADAPTIVE-EXPECTANCY-COMPLETION:
    1. Global bounded ranking across ALL valid strategy candidates.
    2. Canonical MarketContext + MarketPhase detection in the live MSE snapshot.
    3. Canonical RS-vs-BTC features (5m/15m/1h + persistence).
    4. LOCAL_STRENGTH_BREAKOUT with real breakout/RS/volume/chase confluence.
    5. COMPRESSION_EXPANSION with real range break + hard RR/chase validation.
    6. SWING_PULLBACK with bounded strategy-specific ExitProfile.
    7. EXTREME_FLUSH_REVERSAL with sweep/reclaim/HL/RS confluence.
    8. Strategy-aware FamilyPolicy (macro x local x phase x severity x style).
    9. Shadow A/B telemetry: legacy winner vs V4.3 winner + score delta.
   10. Stronger self-tests and end-to-end acceptance cases.
   11. NO changes to safety invariants (CrashGuard / TruthSeal / SL chain).
   12. Long-only SPOT preserved; no shorts / futures / leverage.

  v4.2.6-MTF-PULLBACK — integrates a bounded multi-timeframe long strategy:
    1D bullish trend -> 4H bullish confirmation -> 15m pullback zone ->
    5m bullish/recovery confirmation. It is additive only; all existing
    safety, sizing, SL, exposure, circuit-breaker and execution gates remain.
  v4.2.7-RECALL-COHERENCE — surgical opportunity-coverage fixes:
    (A) LOCAL_BULLISH Bearish-Recovery branch enabled with stronger local gates.
    (B) NFM/G starvation ratio now uses the SAME sliding window for numerator
        and denominator; independent watchdog cadence retained.
    (C) HTF grading and MSE entry/ATR geometry use CLOSED candles consistently.
    (D) BEARISH countertrend routing allowed only after concrete closed-bar
        LIQUIDITY_SWEEP or MEAN_REVERSION prefilter; crash remains absolute.
    (E) Bearish sweep/mean-reversion HTF floor bypass is bounded to those
        families only; structural confirmation/tier gates remain active.
    (F) Pullback near-miss telemetry widened beyond the actual entry envelope.
    (G) No futures/funding/OI dependency added; spot LONG_ONLY invariants are
        preserved.

  v4.1.1-LIVE-READINESS — final safety/recall corrections over v4.0.11/v4.1.0:
    (R1) BalanceReconciler.fetch now uses coroutine-factory + retry_safe=True
         so transient network errors get one real retry (previously it awaited
         a raw coroutine that could not be retried).
    (R2) SL_POST_CREATE_VERIFY_TOLERANCE_PCT raised 0.15→0.30 to accommodate
         MEXC spot tick rounding/normalization; settle window bumped 0.4→0.6s.
         Still comfortably below any legitimate SL deviation. Safety unchanged.
    (R3) RUNNER_MAX_HOLD_HOURS lowered 24→12 to tighten the runner envelope
         (RUNNER_EXEMPT_FROM_TIME_EXIT stays True — asymmetric upside kept,
         but the hard cap is now realistic for scalping). Comment in the
         changelog aligned with actual behaviour (envelope, not time-exit).
    (R4) SIGNAL_DEDUP_TTL_SEC raised 180→330 so it is >= TF_ENTRY (5m) * 1.1
         and dedup can NEVER underrun the entry candle; the max() clamp at
         the call site becomes a no-op safety net rather than a corrector.
    (R5) MAX_SL_PCT raised 1.5→1.8 (conservative). ATR-based SL on high-vol
         majors was routinely tripping max_sl_pct_exceeded on legitimate
         setups; RISK_COHERENCE_MAX_SL_PCT (4.5) still bounds the ceiling.
    (R6) emergency_close: if market_sell RAISES after a verified SL cancel,
         we now explicitly declare STOPLESS_EXPOSURE and escalate
         LIVE_ENTRIES_BLOCKED so no new entry is issued while the residual
         is unprotected. No new layer, no new strategy; a two-branch guard
         in the existing except block.

  v4.0.10-LIVE-READINESS — surgical production hardening over v4.0.9:
    heartbeat final exchange re-check; runner 24h hard cap; atomic candidate
    SL mutations; cancellation status hardening; starvation suppression vs
    blindness split with UTC daily reset; entry-only equity drawdown halt;
    TruthSeal retry wiring. Long-only / fail-closed / exit invariants preserved.

  v4.0.9-DEEPSEEK-HARDEN — SURGICAL LIVE-READINESS PATCHES (additive over
  v4.0.8-STARV-FIX; minimal-diff, fail-closed; no new layers, no new
  strategies, no threshold changes to sizing/risk/SL invariants).

    DS-1  (BLOCKER) — POST-CREATE SL VERIFICATION on MEXC spot.
              place_sl now fetches the order back right after create_order
              and treats the SL as live ONLY when status is open-ish AND the
              returned stop/trigger price matches within
              SL_POST_CREATE_VERIFY_TOLERANCE_PCT. Any failure → software SL
              fallback + retry. Toggle: SL_POST_CREATE_VERIFY_ENABLE.

    DS-2  (BLOCKER) — UNIFIED SYMBOL LOCK on SL mutations in PositionManager
              (TP1 BE-move, TP2 partial replace, staircase, trailing) using
              HandoffOwnership.lock_for — the same lock as build_and_route.

    DS-3  (BLOCKER) — TIME-BASED EXIT covers `runner` state (was excluded
              from open_states). Toggle: RUNNER_EXEMPT_FROM_TIME_EXIT
              (default False → runner IS time-exited).

    DS-4  (BLOCKER) — DYNAMIC REENTRY COOLDOWN by exit reason.
              REENTRY_COOLDOWN_BY_REASON maps exit_reason → seconds;
              _finalize_and_record_r writes (armed_ts, cd_sec) and the gate
              reads the pair (backward-compatible with legacy floats).
              Toggle: REENTRY_COOLDOWN_DYNAMIC_ENABLE.

    DS-5  (TWEAK)   — EXECUTION_COOLDOWN check relocated BEFORE
              PreSendGate.evaluate (was after the gate → wasted sizing work).

    DS-6  (TWEAK)   — SHARED ORDERBOOK: PreSendGate.evaluate accepts
              cached_ob and forwards it to LiquidityDepth.check, halving
              fetch_order_book calls per signal.

  v4.0.8-STARV-FIX — STARVATION-KILLER SURGICAL PATCHES (additive over v4.0.7-MSE,
  minimal-diff, fail-closed; no new layers, no new strategies, no threshold
  changes to sizing/risk/SL invariants). Goal: raise E/Q/S in the funnel
  without loosening any risk or long-only invariant. Every change is bounded
  and revertible via CONFIG toggles.

    STARV-A — SYMBOL_SCAN COOLDOWN RELOCATED (pre-gate  → post-microstruct).
              Previous placement armed cooldown at the TOP of build_and_route
              *before* any analysis, which suppressed re-evaluation of a symbol
              for the entire SYMBOL_COOLDOWN_SEC window even when the symbol
              never reached a scoring/executable state. Now the cooldown is
              armed ONLY after the symbol clears microstructure (i.e. it
              actually consumed pipeline work). REENTRY_COOLDOWN is unchanged
              (still applied at the top) because it protects against re-entering
              a JUST-CLOSED position — a genuine risk gate, not a scan throttle.
              New CONFIG toggle: SYMBOL_COOLDOWN_MODE = "post_microstruct"
              (default) | "pre_gate" (legacy v4.0.7 behavior) | "candle_dedup"
              (relies only on candle_ts dedup — most permissive). Default
              lowered to 180s from 600s to reduce residual starvation.

    STARV-B — SIGNALS_GENERATED counted AFTER cooldown pre-gates so telemetry
              G/E/Q/S ratios reflect ONLY symbols that actually entered the
              analysis pipeline. Cooldown-suppressed symbols are tracked in
              a separate counter (signals_scanned_cooldown_skipped) instead
              of inflating G. Prevents "blindness" false-positive in
              StarvationGuard.

    STARV-C — OPPORTUNITY ROUTER RECALL WIDENED — softer PULLBACK detector +
              new TREND_CONTINUATION_SOFT tail-detector (bounded).
              (a) detect_pullback now also matches a controlled retracement
                  toward EMA20 (previously only EMA50), and a mild negative
                  distance (up to -0.5 * ATR below EMA) is allowed when RSI
                  is in the bullish recovery band. Prior close/current
                  higher-low pattern gives an alternate anchor.
              (b) detect_trend_continuation_soft (new, LOWEST priority)
                  catches healthy uptrends where price>EMA20>EMA50 on 15m
                  and last CLOSED 5m bar is a bullish body — this closes
                  the no_family_matched gap during established trends.
                  It maps to family="TREND_CONTINUATION" which is subject
                  to the SAME BOS/reclaim hard-gate as BREAKOUT_RETEST/
                  CONTINUATION downstream, so recall widens WITHOUT
                  relaxing structural rigor. New CONFIG toggle:
                  ROUTER_ENABLE_TREND_CONTINUATION_SOFT = True.

    STARV-D — PULLBACK MICRO-UPTREND GATE SOFTENED. In addition to the
              existing (bos_confirmed | reclaim | bullish_close) triad, a
              higher-low pattern on the last 3 CLOSED 5m bars is now
              accepted as micro-uptrend evidence. Structural strength is
              still required — score gate downstream is untouched.
              New CONFIG toggle: PULLBACK_ACCEPT_HIGHER_LOW = True.

    STARV-E — SCORE-INPUT OBSERVABILITY. When CompositeScorer rejects on
              insufficient data, the missing fields are now recorded in a
              rolling window (STATS["score_input_missing_top"]) so top
              feed instability is visible in heartbeat/telemetry without
              changing the fail-closed contract. Optional soft mode via
              CONFIG.SCORE_INPUT_SOFT_MODE (default False = fail-closed):
              when True AND only ONE non-critical field is missing (RS or
              spread), a small penalty is applied and scoring proceeds.
              Critical fields (structure_confidence, orderbook_imbalance,
              momentum_score_val, retest_quality_score, volume_ratio) still
              force C_REJECT. Default keeps legacy hard-fail behavior.

  v4.0.6 EXECUTION-COHERENCE FIXES (additive over v4.0.5, minimal-diff,
  fail-closed; no new layers, no new strategies, no score-threshold changes):
    FIX A — AdaptiveRepricing.maybe_reprice now uses CANONICAL TP1_RR when
            recomputing new_tp1. `ADAPTIVE_REPRICE_MIN_TP1_RR` is preserved
            as a soft alias only (falls back to TP1_RR if absent). Prevents
            TP1 policy from drifting between repricing and fee-viability.
    FIX B — Post-fill level recalibration. After a real `create_market_buy`
            fill, TradeState levels (effective_entry, original_sl, current_sl,
            tp1, tp2, tp3) are rebuilt from `fill_px` instead of
            `planned_entry`. If drift > FILL_DRIFT_ABORT_PCT the trade is
            emergency-closed at once (clean unwind).
    FIX C — Exposure headroom now uses REMAINING notional
            (remaining_position * effective_entry) rather than the frozen
            original notional. Prevents runners / post-TP1 legs from
            over-reserving headroom against new entries. Applied in
            SizingEngine.decide AND ExposureProtection.check.
    FIX D — emergency_close: unverified SL cancel is now an EXPLICIT declared
            state (sl_health_state="CANCEL_UNVERIFIED"). No new SL re-place
            before verification; no silent "assumed cancelled" flip. Central
            finalization path unchanged.
    FIX E — Staircase / trailing commit order. `candidate_sl` is computed
            first; `trade.current_sl` and `trade.staircase_level_hit` are
            promoted ONLY after cancel+replace succeeds. Prevents desync
            when cancel is unverified or replace fails.
    FIX F — BalanceReconciler entry-block vs system-block split. Balance
            failures now set `LIVE_ENTRIES_BLOCKED` (soft) instead of
            escalating to LIVE_BLOCKED. `is_live_runnable()` still allows
            managing open positions; only NEW entries are gated. Hard BLOCK
            (fetch failed AND cache expired) still hard-escalates.
    FIX G — Dead config keys removed. Nine previously-unread keys
            (MIN_ATR_PERCENT, MAX_IMPULSE_CANDLE_ATR, VOLUME_MIN_RATIO,
            VOLUME_HARDCUT_RATIO, VOLUME_CONFIRM_MULT, HTF_STRENGTH_FLOOR,
            MR_RSI_LOW, MR_RSI_HIGH, CONFIRM_RSI_MIN_RECOVERY) removed from
            CONFIG so no filter is falsely implied.

  v4.0.5 TUNING & DESYNC FIXES (additive over v4.0.4, minimal-diff):
    FIX #1 — Lower MIN_LIVE_SCORE 78→70 and SIGNAL_CLASS_B_MIN 65→62.
             Reason : live funnel starving on score_below_threshold.
             Effect : more A/B setups reach PreSendGate; paper mode
                      unchanged for LIVE; MIN_PAPER_SCORE=60 for paper-only sampling.
    FIX #2 — AdaptiveRepricing now runs BEFORE PreSendGate.
             Reason : gate sized against planned entry while repricing
                      then mutated entry/sl/tp under it (desync).
             Effect : gate sizing / risk-coherence / caps evaluated on
                      the FINAL levels that will actually be submitted.
    FIX #3 — StarvationGuard Q→S uses DELTA counters (per-minute), not
             cumulative totals.
             Reason : `queued>0 and sent==0` never re-fires after the
                      first successful send in the process lifetime.
             Effect : starvation detection remains functional after
                      any number of successful sends.
    FIX #4 — Recovery path re-checks KillSwitch before AND after truth-
             seal retry; blocked kill switch cannot be un-blocked by a
             successful truth-seal (fail-closed).
    FIX #5 — fake_break_filter loosened: requires MAJORITY of recent
             closes below tolerance floor instead of ANY single close.
             Effect : catches genuine breakout/retest failure, no
                      longer rejects healthy pullbacks near the high.
             Also   : FAKE_BREAK_TOLERANCE_PCT 0.0005 → 0.0025.
    FIX #6 — BTCContext uses ~2h window (8×15m) with softer thresholds
             (WEAK ≤ -3%, CRASH ≤ -6% instead of -2% / -5%).
             Effect : fewer spurious WEAK/CRASH flips on normal noise.
    FIX #7 — Removed duplicate _finalize_and_record_r calls at every
             call-site immediately following emergency_close.
             Reason : emergency_close is the central finalization path
                      since v4.0.4 PATCH S; idempotency kept it safe
                      but the single-terminator contract is cleaner.
    FIX #8 — CompositeScorer spread scoring uses CONFIG["SCORE_SPREAD_
             CEIL_PCT"] (was hardcoded 0.15 literal).
             Effect : single source of truth for the spread ceiling.

  v4.0.4 HARDENING PATCHES (additive over v4.0.3, minimal-diff):
    PATCH Q  (CRITICAL) — safe_api_call: REAL single retry for transient
                          network errors via opt-in coroutine-factory API
                          (retry_safe=True). Legacy raw-coroutine callers
                          unchanged. Order-placement calls NEVER retry
                          (no duplicate-execution hazard).
    PATCH R  (CRITICAL) — PositionManager.tick: short-circuit after
                          SLHealthAuditor.verify() and SoftwareSLFallback.check()
                          when the trade has been finalized / popped /
                          drained. Prevents stale TP/staircase/trailing/
                          time-exit logic from acting on closed trades.
    PATCH S  (CRITICAL) — emergency_close: unified accounting. After
                          cancel-SL + market-sell (or short-circuit when
                          qty<=0) the method now routes through
                          _finalize_and_record_r() itself, so R is recorded
                          in DailyCircuitBreaker and the trade is popped
                          from ACTIVE_TRADES in the SAME path. Idempotency
                          via _FINALIZED_TRADE_IDS keeps existing callers
                          that also call the finalizer safe (no double R).

  v4.0.2 HARDENING PATCHES (additive over v4.0.1):
    PATCH A — TP2 runner math fix + SL quantity re-sync after every partial fill
    PATCH B — SoftwareSL hardening: heartbeat, hard-timeout, activation counter,
              rolling-window escalation to LIVE_BLOCKED
    PATCH C — Granular send-fail taxonomy (balance / timeout / depth / drift /
              exchange_reject / unknown) + record_rejection wiring
    PATCH D — WithdrawalIsolation HARD_BLOCK default,
              BalanceReconciler CACHE-state gate for new entries + TTL=45s live,
              Precision/step/min-notional normalization pre-submit,
              Consistency interval 180s + starvation escalation to LIVE_BLOCKED,
              Indicators tagged-rejection (no silent None swallowing)
    PATCH E — (additive, observability-only, no invariant touched)
              E.1 Heartbeat top_rejects (log + Telegram)
              E.2 StarvationGuard blind-spot detection (G→E blindness alert,
                  Q→S starvation kept as existing LIVE_BLOCKED escalation,
                  stage stagnation tracker)
              E.3 Per-stage rejection counters (funnel diagnostics)
              E.4 Regime hysteresis: separate enter/exit thresholds + dwell time
              E.5 Score/regime interaction kept clean (no duplicate blocking)
              E.6 Telemetry snapshot extended with funnel ratios + regime/starvation
              E.7 All PATCH E code is additive; no removal, no refactor

  v4.0.3 HARDENING PATCHES (additive over v4.0.2, minimal-diff, fail-closed):
    PATCH F  (CRITICAL) — emergency_close now cancels SL BEFORE market-sell
                          (kills orphan SL + double-sell hazard).
    PATCH G  (CRITICAL) — Centralized _finalize_and_record_r: every exit path
                          (TP2-full, SL_HIT via SLHealth, emergency_close,
                          time_based_exit) contributes weighted R to
                          DailyCircuitBreaker AND pops ACTIVE_TRADES.
                          Fixes: (a) DailyCircuitBreaker never saw SL losses,
                                 (b) ghost trades stuck in ACTIVE_TRADES.
    PATCH H  (CRITICAL) — tp3 recomputed after Adaptive Repricing (was stale).
    PATCH I  (CRITICAL) — fee_viability_ok uses REAL exit weights
                          (TP1_EXIT_PCT / TP2_EXIT_PCT / RUNNER_KEEP) instead
                          of the hardcoded 50/50 blend.
    PATCH J  (HIGH)     — SLHealthAuditor recognises 'closed'/'filled' SL
                          (SL_HIT path) → finalize the trade, do NOT try to
                          replace SL on an already-closed position.
    PATCH K  (MED)      — move_to_break_even offsets by roundtrip fees so BE
                          truly breaks even (was placing SL exactly at entry).
    PATCH L  (MED)      — maybe_activate_runner only runs after tp2_hit (was
                          being invoked on every tick, could mis-flag runner).
    PATCH M  (MED)      — safe_api_call: single retry for transient network
                          errors only (timeout / reset / connection reset).
    PATCH N  (MED)      — Diagnostic counters for missing score inputs
                          (volume_ratio, structure, retest_q, ob_imbalance,
                          momentum, rs, spread) — no silent swallowing.
    PATCH O  (LOW)      — Oversell guard: if total_sold_qty exceeds original
                          size by > 0.5%, emergency_close the residual & log.
    PATCH P  (LOW)      — build_and_route reuses one orderbook fetch for both
                          score-imbalance and pre-send depth check (halves
                          fetch_order_book calls per signal).

  v4.1.1 final corrections:
    (F1) CACHE state explicitly raises LIVE_ENTRIES_BLOCKED in the canonical
         reconciler; existing position management remains allowed.
    (F2) Emergency close now FAILS CLOSED when SL cancellation is unverified:
         it does not market-sell into ambiguous SL ownership, preventing a
         potential double-sell. The residual remains owned and entries block.
    (F3) SL health-state enum now includes every runtime safety state used by
         the implementation.
    (F4) Family tier-aware spread ceiling is enforced as a real hard gate;
         global spread scoring cannot override tier policy.
    (F5) Optional D1 bias is fetched only after a candidate exists and is
         additive by default; optional hard block remains explicit.
    (F6) HTF repeat backoff is now real bounded telemetry/state bookkeeping;
         it never converts an HTF rejection into an entry.

  Merged from:
    1) htf_pullback_scalper_v3-5-1_FINAL.py    (Backbone: HTF families, funnel)
    2) hybrid_crypto_scalper_FINAL_v3_5.py     (Composite score, safety layer)
    3) scalp_strategy_pack_v1_9_24_P33.py      (Boot orchestrator, micro-struct)

  ARCHITECTURE (8 LAYERS):
    L1  Boot & Truth Model
    L2  Safety & Reconciliation
    L3  Regime & Context
    L4  Opportunity Engine
    L5  Composite Scoring
    L6  Execution Funnel
    L7  Exit Management
    L8  Telemetry & Recovery

  INVARIANTS (NON-NEGOTIABLE):
    * LONG_ONLY spot execution (no shorts, no futures, no leverage)
    * fail-closed everywhere (any uncertainty => reject/block)
    * single truth source (balance/state/live-gating)
    * single execution decision path (ExecutionFunnel only)
    * no silent fall-open, no hardcoded secrets
    * Exit-pct invariant: TP1+TP2 == 1.0 (runner OFF) or TP1+TP2+RUNNER_KEEP == 1.0 (runner ON)
    *              (SystemExit @ boot if violated in LIVE)
    * SL must always exist for live trades (emergency_close if MISSING)
    * SL cancel MUST be verified before id-clear
    * telemetry MUST be non-blocking (never blocks execution loop)

  ========================================================================
  v4.4-ADAPTIVE-EXPECTANCY-MULTI-OPPORTUNITY — G->E RECALL & OBSERVABILITY LAYER (2026-08-10)
  ========================================================================
  ADDED (all additive, flag-gated, bounded, revertible):
    1. VWAP anchor as 3rd pullback anchor (Indicators.vwap) + relaxed-mode
       pullback distance widening (bounded, auto-reverting with TTL).
    2. PULLBACK micro-uptrend gate: 5th OR-alternative 'ema20_slope_up'
       over the last N CLOSED 5m bars + fully detailed rejection ctx.
    3. family_regime_disallowed / family_htf_strength_below_floor /
       family_tier_below_floor / below_tier / score_below_threshold now
       emit EXPLAINABLE ctx (family, regime, allowed_regimes, floors,
       tier, zones).
    4. no_family_matched ctx: closest_detector + dist_atr_ema20/ema50/vwap
       + rsi_5m + regime/tier/htf_strength/volume_ratio/btc_context.
    5. Per-family preferred_zones + volume_floor_ratio policy applied as
       a bounded SOFT score penalty (never a standalone reject).
    6. V420FunnelWatchdog: ratio-based nfm trigger + heartbeat now shows
       nfm_ratio / nfm_delta / relaxed TTL / watchdog state.
    7. V422NearMiss aggregated stats (closest detector, mean ATR distances,
       per-detector reject rates, top rejected families, TOD buckets).
    8. V422StarvationAlerter: independent task watching last_send_ts and
       emitting a bottleneck snapshot (does not rely on HB cadence).
    9. PreSendGate defense-in-depth: re-asserts FINAL-level ordering on
       the repriced levels (ordering itself was already correct).
    10. SizingEngine: canonical net-RR floor + risk-capture coherence +
        structured exception counters (fail-closed in LIVE).
    11. PositionManager.tick: structured per-exception counters (kept the
        existing short-circuit guards after finalization/drain intact).
    12. Composite-aware router winner selection WITHIN each priority class
        (single winner per symbol tick preserved).
  PRESERVED BYTE-EQUIVALENT BEHAVIOR:
    * LONG_ONLY spot only - no shorts, no futures, no leverage paths.
    * ALL hard safety gates: SL chain, BalanceReconciler REAL->CACHE->BLOCK,
      TruthSeal mandatory direct fetch, ExposureProtection,
      DailyCircuitBreaker, KillSwitch, ExchangeWatchdog,
      EquityDrawdownHalt, FailedSendCB.
    * BOS hard gate for BREAKOUT_RETEST / BREAKOUT_CONTINUATION untouched.
    * No silent fall-open anywhere; every softening is bounded +
      flag-gated + auto-reverting (RELAXED_MODE TTL) and NEVER touches
      SL/TP/exposure math.
  REMAINS FAIL-CLOSED:
    * SL placement/verification/cancel (verified-cancel-before-id-clear).
    * Balance truth (config balance is NEVER live truth).
    * Data sufficiency (missing/NaN inputs => reject, never pass).
    * emergency_close (cancel->sell order, unified finalizer, no ghosts).
  ========================================================================

================================================================================

  v4.5.5-GLOBAL-CANONICAL-COHERENCE — SURGICAL RECALL + STARVATION REPAIR
    * Candidate freshness clock-domain fix: Unix wall timestamps use WALL_NOW;
      missing/invalid timestamps remain fail-closed as freshness.unverifiable.
    * Bounded NEUTRAL-only HTF floor override (45.0) without bypassing family,
      availability, structure, or other hard policy gates.
    * MID-aware LOCAL_STRENGTH_BREAKOUT / COMPRESSION_EXPANSION tier floors;
      BREAKOUT_RETEST / BREAKOUT_CONTINUATION remain LARGE.
    * Liquidity universe minimum quote volume raised to 3M USDT; no below-MID
      fill-in is permitted when fewer than Top-120 qualify.
    * Starvation classifier gains telemetry-only SCAN_STALE mode; 12-minute
      window and explicit windowed funnel deltas prevent rollover false alarms.
    * Added detailed funnel/rejection telemetry and offline v4.5.5 self-tests.
    * Final surgical closure: heartbeat PRE now equals true prequalification;
      canonical reject is explicit; window deltas are separated from cumulative
      counters; persisted cycle timestamps use explicit wall/monotonic domains;
      duplicate funnel-window configuration removed; safety/telemetry self-tests
      strengthened without changing execution authority.

  v4.5.7-POLICY-RECALL-DEADLOCK-FIX — BOUNDED FAMILY RECOVERY + HTF RELIEF
  v4.5.10-HIGH-RECALL-DIVERSITY-LOW-TARGET — SURGICAL OPPORTUNITY COVERAGE + DIVERSITY
    * Promotes RELATIVE_STRENGTH_LEADER and VOLATILITY_BURST into the live
      MSE path (their old per-strategy SHADOW flags were telemetry-only).
    * Adds MICRO_TREND_CONTINUATION as a bounded closed-bar MSE candidate.
    * Low-target exit profiles: TP1~0.9R / TP2~1.8R, still subject to fee,
      SL, RR, sizing, PreSend and execution hard gates.
    * Applies smaller risk factors (0.60/0.65) to high-recall candidates.
    * Gives the global arbiter a tiny bounded bonus and a 0.51 floor only for
      the high-recall lane; never below the existing global hard floor.
    * Existing OrderBook confirmation, Balance/Exposure/SL/TruthSeal and
      LONG_ONLY SPOT execution authority are unchanged.
    * FamilyPolicyLayer now exposes exact mismatch attribution (macro/local/
      phase/severity/style) without changing canonical authority.
    * Bounded NEUTRAL + LOCAL_BULLISH recovery is allowed only for
      PULLBACK / LOCAL_STRENGTH_BREAKOUT / COMPRESSION_EXPANSION /
      CONTINUATION_RECLAIM / TREND_CONTINUATION, only after repeated
      windowed policy starvation evidence and strong closed-bar confirmation.
    * Family-specific HTF relief is capped at 5 points, NEUTRAL-only,
      LOCAL_BULLISH-only, TTL<=1800s, auto-reverting, and never active under
      hard/system hazards or liquidity/structure/score bottlenecks.
    * Added hourly telemetry-only GLOBAL-TRACE and clearer STARV/ACCOUNTING
      heartbeat semantics.
    * Pullback forensic counters remain telemetry-only; no new strategy or
      execution path was added.
    * LONG_ONLY/SPOT, SL/TP, risk, balance, liquidity, structure, execution,
      and all fail-closed hard gates remain unchanged.
v4.5.13-RECALL-COVERAGE-HTF-RECOVERY-ADAPTIVE-FUNNEL
    * Bounded same-symbol HTF recovery cache (TTL + candidate freshness).
    * Adaptive local retention: 3 -> at most 5 distinct strategy candidates.
    * Recovery evidence continuity across NEUTRAL -> BULLISH without new relief.
    * Policy telemetry split into macro/local/phase/severity/style + HTF quality.
    * Full window funnel heartbeat: GEN -> HARD_VALID -> RAW_RANK -> POOL ->
      PRE -> SEL -> Q -> S.
    * T41..T44 acceptance tests; no hard execution gate is relaxed.

  v4.5.10-DIVERSITY-LOW-TARGET-CLOSURE
    * Low-target ExitProfile is now the canonical source for the high-recall lane
      after Adaptive Repricing; no reversion to global TP1/TP2/TP3 values.
    * RELATIVE_STRENGTH_LEADER / VOLATILITY_BURST require their explicit LIVE
      enable flags in addition to the base engine enable flags.
    * Global arbitration adds bounded strategy/family diversity preference and
      a configurable maximum of one winner per high-recall family by default.
    * High-recall funnel telemetry is exposed as GEN/PRE/SEL/Q/S in heartbeat.
    * No hard safety or execution gate is bypassed.

v4.5.12-ROOT-CAUSE-SNAPSHOT-COHERENCE-STARVATION-FINAL
    * ROOT FIX: canonical prequalification reuses the exact enriched
      GlobalOpportunityBrain snapshot used by MSE candidate generation instead
      of rebuilding raw market_data_map snapshots. This removes regime/local/
      phase/HTF coherence drift and false policy/HTF starvation caused by
      mismatched snapshot domains.
    * STARVATION FIX: aggregate the two equivalent policy-rejection labels
      `family_regime_disallowed.macro` + `htf.family_regime_disallowed` before
      deciding policy starvation. `htf.unavailable` remains separate and
      fail-closed.
    * Bounded recovery evidence is now 2 complete windows / 30 minutes
      no-send / 35% aggregated policy-mismatch share. Recovery remains
      NEUTRAL + LOCAL_BULLISH + NORMAL + allow-listed family + closed-bar
      confirmation only, with the same downstream hard gates.
    * MTF_PULLBACK is included in the existing bounded recovery allow-list;
      its own recovery validator remains mandatory.
    * Candidate-vs-snapshot context-drift telemetry added for future audits.
    * No relaxation of liquidity, spread, structure, score hard floors,
      Balance/TruthSeal/Exposure/SL/PreSend/Execution gates.
    * LONG_ONLY SPOT / fail-closed invariants preserved.

v4.5.5-PQX — PREQUALIFICATION EXCEPTION OBSERVABILITY REPAIR
    * Unexpected exceptions inside canonical prequalification are no longer
      silently discarded by the global arbitration loop. They are recorded as
      dedicated exception.* reasons with bounded history and compact context.
    * Exception rejects are attributed to the OTHER telemetry bucket instead of
      being mislabeled as normal HTF/STRUCTURE bottlenecks.
    * Heartbeat/starvation diagnostics expose prequal exception deltas, OTHER
      rejects, and top canonical-prequalification reasons.
    * Final closure: canonical prequalification now calls the tier-aware spread
      gate with its canonical argument order (spread_pct, tier), removing a
      hidden ValueError path that previously looked like silent prequal starvation.
    * NO hard gate, score floor, HTF threshold, liquidity threshold, SL/TP rule,
      sizing rule, or execution authority is relaxed or bypassed by this patch.
================================================================================
"""

# v4.5.83 FINAL ALL-STRATEGY-COVERAGE / CANONICAL-FEASIBILITY CLOSURE
#   * Discovery fairness: bounded per-family quota + two-pass family-diverse
#     scheduling so early PULLBACK candidates cannot consume the full cycle cap.
#   * Canonical score feasibility: V570 no longer treats engine_score as if it
#     were the final SignalBuilder score; it rejects only when the bounded
#     maximum canonical adjustment still cannot reach the canonical floor.
#   * Adds explicit bounded telemetry for family coverage and parity-feasibility
#     rejections. The final SignalBuilder score gate remains authoritative.
#   * No HTF, liquidity, structure, PreSend, Balance, TruthSeal, SL, exposure,
#     execution, LONG_ONLY/SPOT or exit safety gate is weakened or bypassed.
#
# v4.5.82 FINAL ALL-STRATEGY-DISCOVERY / SCORE-PARITY CLOSURE
#   * Discovery notifications are deduplicated by SYMBOL+FAMILY instead of
#     SYMBOL only, so PULLBACK can no longer suppress other strategy families
#     for the same symbol.
#   * Discovery cycle cap is truly global across engine invocations, preventing
#     each individual MSE engine from resetting the per-cycle notifier budget.
#   * V570 global->canonical score parity now derives the same strategy-aware
#     canonical base floor used by SignalBuilder (regime + family/mode policy
#     + strategy offset/memory), then applies the existing bounded adaptive
#     relief. This removes SELECTED->SCORE policy drift without lowering any
#     safety floor or creating a new execution authority.
#   * No strategy detector, HTF, liquidity, structure, PreSend, Balance,
#     TruthSeal, SL, exposure, execution, LONG_ONLY or exit invariant is
#     weakened or bypassed.
#
# v4.5.81 FINAL PULLBACK-FULL-COHERENCE CLOSURE
#   * Finalizes bounded entry-zone coherence on both sides of the validated zone.
#   * Restricts structural swing-low selection to a recent, zone-relative invalidation area.
#   * Requires the final PULLBACK SL to remain below the validated pullback zone.
#   * Keeps all existing HTF/liquidity/score/PreSend/execution/safety gates unchanged.
#
# v4.5.80 FINAL PULLBACK-ALL-COHERENCE CLOSURE
#   * Makes shallow_pullback support-only across every active PULLBACK structural gate.
#   * Uses confirmed closed-bar swing lows for structural SL with bounded ATR/% safety.
#   * Re-applies structural SL after adaptive repricing using the final entry.
#   * Adds a final zone/chase coherence assertion so repricing cannot turn a pullback
#     into a late chase entry.
#   * Keeps the existing single JIT transient-spread recheck; tier spread remains hard.
#   * TP1/TP2/TP3 geometry, 80-USDT sizing/cap, balance, exposure, PreSend, execution,
#     Software-SL, LONG_ONLY SPOT and all fail-closed authorities remain unchanged.
#
# v4.5.76 FINAL EXIT-POLICY / LEGACY-DRIFT / SAFETY-RECONCILIATION CLOSURE
#   * Canonicalizes legacy SL-failure flags so no older CONFIG key can disable
#     automatic Software-SL protection for a live trade.
#   * TARGET_ONLY remains a target-order management policy only; Software-SL
#     remains mandatory for live protection.
#   * Safety-hazard MARKET SELL remains OFF by default and, even when explicitly
#     enabled, is single-attempt per trade with a hard anti-repeat latch.
#     Ambiguous/unknown safety outcomes block NEW entries instead of repeating
#     a potentially duplicate MARKET SELL.
#   * Exit classification is preserved across normal TP/SL and safety paths;
#     protection failures never masquerade as SL_HIT.
#   * No entry strategy, score, HTF, liquidity, sizing, or LONG_ONLY SPOT
#     invariant is changed.
#
# v4.5.74 FINAL TP-SL STRICT / TARGET-ONLY-SL / SAFETY-CLOSURE
#   * TARGET_ONLY no longer disables automatic Software-SL protection; target
#     limit orders and automatic SL protection coexist.
#   * Manual/target-only SL-failure policy always attempts to arm software SL;
#     if arming fails, NEW entries remain blocked fail-closed.
#   * Emergency/Safety-Hazard MARKET SELL is disabled by default; only an
#     explicitly enabled operator safety override can authorize it.
#   * Software-SL supports a bounded decisive-breach fast path in addition to
#     the normal spaced multi-tick confirmation, without weakening the model SL.
#   * Exit reason separation is enforced so protection failure is never labeled
#     as SL_HIT and price-independent exits cannot masquerade as normal exits.
#   * Restart/reconciliation remains exchange-first and target completion latches
#     are preserved; no blind TP recreation after restart or ambiguous state.
#   * Normal automated exits remain strictly TP1 / TP2 / confirmed Software-SL.
#
# v4.5.73 FINAL EXIT-AUTHORITY / SAFETY-SEPARATION / RESTART-EXIT-CLOSURE
#   * Keeps normal automatic SELLs strictly within TP1/TP2/confirmed-SL paths.
#   * Safety-hazard MARKET SELLs are separately tagged, counted, and never
#     conflated with TP/SL exits in telemetry/accounting.
#   * Time-exit, monitor-stale, and software-SL hard-timeout remain non-SELL
#     controls; they block new entries / preserve protection instead of creating
#     a price-independent MARKET SELL.
#   * Recovered trades reconcile persisted TP/SL order IDs with exchange open /
#     terminal state before rearming protection; no blind target recreation is
#     allowed after restart.
#   * Recovered spot balance is checked against persisted remaining_position;
#     insufficient/ambiguous balance blocks NEW entries and target recreation.
#   * Completed TP stages are latched explicitly so a later tick/restart cannot
#     recreate or repeat an already-executed target.
#   * No changes to entry strategy, risk, HTF, liquidity, Balance/TruthSeal,
#     LONG_ONLY SPOT or the canonical TP/SL geometry.
#
# v4.5.72 FINAL EXIT-AUTHORITY / TP-SL-RECONCILIATION-CLOSURE
#   * Every live MARKET SELL passes through one final authorized-submit gateway
#     immediately before the exchange call; no direct SELL call-site bypass remains.
#   * TP1/TP2 partial exits have an in-flight guard to prevent concurrent duplicate
#     MARKET SELL submissions for the same stage.
#   * TP exits require the current observed price to have reached the target;
#     software-SL exits require a proven current-price breach of active model SL.
#   * Partial/ambiguous fills remain exchange-reconciled and cannot be blindly retried.
#   * Monitor-stale, hard-timeout, fill-drift, and time-exit remain non-market-SELL
#     paths by default. Only narrowly allow-listed safety hazards may emergency-sell.
#   * No changes to entry strategy, risk/HTF/liquidity/Balance/TruthSeal, or
#     LONG_ONLY SPOT invariants.
#
# v4.5.71 FINAL EXIT-AUTHORITY / TP-SL-ONLY CLOSURE
#   * Central exit authority: normal market SELLs are permitted only for TP1,
#     TP2, or a confirmed SOFTWARE_SL breach; explicit safety-hazard exits
#     remain separately allow-listed and auditable.
#   * Post-entry protection/failover SELLs are blocked before any SL mutation
#     during the bounded stabilization window, eliminating BUY->SELL races.
#   * Monitor-stale, software-SL hard-timeout, and time-based exits no longer
#     issue automatic market SELLs by default; they block NEW entries and keep
#     the position under its existing protection model until TP/SL conditions.
#   * Large fill drift no longer performs an immediate emergency SELL after a
#     successful BUY; the actual fill is kept authoritative and SL/TP geometry
#     is recalibrated from the real fill so the trade can exit normally at SL/TP.
#   * Software-SL breach confirmation is canonicalized to 3 spaced ticks;
#     duplicate legacy config cannot override the v4.5.70 safety setting.
#   * TP execution paths are explicitly audited before the first exchange SELL;
#     unknown/incorrect SELL reasons fail closed.
#   * No change to entry strategy, risk sizing, HTF, liquidity, Balance/TruthSeal,
#     LONG_ONLY SPOT, or the existing native-SL/software-SL safety model.
#
# v4.5.70 FINAL POST-BUY AUTO-SELL / PROTECTION LOOP CLOSURE
#   * MEXC Spot native stop creation is no longer trusted from generic CCXT
#     capability flags; software AUTO-SL is the default protection mode.
#   * Protection-related market SELLs are blocked during a bounded post-fill
#     stabilization window, preventing BUY->SELL-in-seconds races.
#   * Software-SL breaches require multiple spaced PM confirmations after the
#     stabilization window; one stale/duplicate tick cannot trigger a SELL.
#   * A monotonic fill timestamp is captured for deterministic age gating.
#   * A central emergency-close audit covers protection/failover reasons only;
#     unrelated hard emergency paths remain unchanged.
#
# v4.5.66 FINAL ROOT-CAUSE CALLSITE / RECOVERY COHERENCE
#   * Critical call-site closure: every _v520_fake_break_gate invocation now
#     passes family/zone/ATR by keyword. The previous positional calls placed
#     zone and ATR into strategy_mode/zone_ref, leaving atr_value unset and
#     could systematically distort pullback/fake-break decisions.
#   * V549 recovery fallback defaults now match the active V565 recovery policy,
#     eliminating hidden legacy fallback drift if an environment key is absent.
#   * Discovery noise control is now actually wired: blocked Discovery alerts
#     are emitted only when a bounded V565 recovery lane is plausible.
#   * Structural quarantine is also armed for microstructure/fake-break
#     canonical rejects, not only the final live-builder fake-break path.
#   * Pullback review receives optional structural evidence when supplied,
#     without changing live hard gates.
#
# v4.5.68 FINAL RESTART / PROTECTION RECONCILIATION
#   * Re-validates recovered ACTIVE_TRADES before NEW-entry scanning.
#   * Idempotently re-arms persisted SOFTWARE_SL protection after process restart.
#   * Never clears a persisted native SL id merely because the exchange response
#     is ambiguous; ambiguous native protection blocks NEW entries fail-closed.
#   * If no persisted native stop exists, software AUTO-SL is restored without
#     submitting a SELL and without duplicate failover alerts.
#
# v4.5.67 FINAL PULLBACK-RECOVERY ROBUSTNESS / SCALE-CONSISTENCY
#   * Fixes a critical threshold-scale edge case: StrategyCandidate.engine_score
#     is stored as 0..1, while the V565 structural recovery thresholds are 0..100.
#     Recovery now normalizes the object path through the canonical candidate
#     context builder, preventing the rescue lane from being silently disabled.
#   * Keeps the structural recovery lane narrow and PULLBACK-only; no breakout
#     family gets this bypass.
#   * Preserves all v4.5.65 gates and v4.5.64 automatic SL behavior.
#
# v4.5.65 FINAL PULLBACK-GATE COHERENCE / RECALL / STARVATION HARDENING
#   * Pullback fake-break detection is pullback-aware: a shallow controlled
#     retracement is not classified as a fake breakout solely because the last
#     closed 5m candle is bearish.
#   * PULLBACK microstructure parity shares the same confirmed evidence instead
#     of double-gating on two equivalent tests.
#   * EMA20 slope window is widened from the short 5-bar view to a bounded
#     8-bar closed-candle view, reducing false negatives during pullbacks.
#   * V549 pullback recovery volume floor is lowered to 0.60 only for elite
#     candidates with stronger compensating HTF/engine evidence.
#   * Starvation classifier uses structural-pressure attribution first so
#     `mode=SCORE` cannot hide a dominant STRUCTURE bottleneck.
#   * Adds a narrow structural recovery lane for exceptional PULLBACK setups
#     only. Breakout hard gates remain hard and canonical SignalBuilder remains
#     the sole execution authority.
#   * Review score uses pullback-aware shallow-retracement evidence and
#     progressive RS penalties instead of repeated full penalties.
#   * ATR/chase calculations fail closed when ATR is invalid; they never turn an
#     invalid ATR into a misleading 0.00-ATR chase.
#   * Same-symbol structural quarantine reduces repetitive rejected rescans and
#     Telegram discovery noise without changing live safety gates.
#   * Discovery telemetry is suppressed unless a bounded live-recovery path is
#     plausible.
#   * All Balance/TruthSeal/Exposure/PreSend/SL/Execution/Watchdog/KillSwitch
#     and LONG_ONLY SPOT hard authorities remain unchanged.
#
# v4.5.64 FINAL SL-FAILOVER IDEMPOTENT / SOFTWARE-COHERENCE
#   * Same-trade SL failover is idempotent: repeated PM ticks cannot re-arm or
#     re-notify the same software protection state indefinitely.
#   * Once SOFTWARE_SL_AUTO is active, native SL cancel/replace loops are skipped.
#     BE, staircase, runner-lock and trailing update the software model locally.
#   * A software-protected position is never treated as stopless solely because
#     native SL has no order id.
#   * Failover notifications are state/cooldown limited and exposed in /sl.
#   * Actual software-SL breach still performs automatic reconciled SELL.
#   * Existing hard gates remain: KillSwitch, Balance, Exposure, Drawdown,
#     Watchdog, ambiguity, Precision, Liquidity, Structure, PreSend and
#     LONG_ONLY MEXC Spot authority.
#
# v4.5.63 FINAL LIVE-BLOCK / PROTECTION-COHERENCE / WATCHDOG REPAIR
#   * SOFTWARE_SL_ACTIVE is now a first-class protected state for NEW-entry
#     gating; a protected software stop must not be mislabeled stopless exposure.
#   * Removes the old hard LIVE_BLOCKED escalation on ordinary software-SL
#     activation bursts. Multiple software fallbacks are expected when native
#     MEXC Spot trigger support is unavailable; they remain protected by the
#     dedicated software watchdog.
#   * Watchdog records operational API failures by category. Native SL probe/
#     verification failures are excluded from the transport watchdog because
#     they are handled by the software-SL failover path and should not deadlock
#     the entire entry engine.
#   * Adds runtime LIVE_BLOCKED recovery for watchdog/software-protection
#     diagnostic blocks only after the underlying hazard is actually gone.
#   * Fixes heartbeat telemetry to report windowed watchdog error counts and
#     explicit reason/recovery state.
#   * Keeps all hard gates: KillSwitch, real-balance truth, exposure, drawdown,
#     precision, liquidity, structure, PreSend, SL breach exit, ambiguity and
#     LONG_ONLY MEXC Spot remain authoritative.
#
# v4.5.62 FINAL AUTO-SL HARDENED / NATIVE RECONCILE
#   * Hardens every native SL state-changing call to use a callable factory,
#     so synchronous exceptions and async exceptions both enter the same
#     fail-safe handling path.
#   * Native SL verification is multi-path: fetch_order + live open/recent
#     stop-order fallback; only a positively matched SELL trigger is CONFIRMED.
#   * If native SL is unavailable/unverified, the trade is automatically kept
#     open under SOFTWARE_SL_AUTO. A missing SL ID alone never sells.
#   * Software SL checks price continuously through the dedicated PositionManager
#     and auto-sells only on a real model-SL breach.
#   * Protection-monitor heartbeat uses the configured V560 threshold directly;
#     no hidden longer threshold can postpone the safety decision.
#   * Any verified native-SL cancel followed by replacement failure (TP1/TP2/
#     staircase/trailing/runner) immediately restores the prior SL level as the
#     software watchdog's model and arms automatic software protection.
#   * Ambiguous SELL outcomes are reconciled before duplicate SELL attempts.
#   * Telegram /cancel and anti-recreate controls from v4.5.61 remain intact.
#
# v4.5.61 FINAL TELEGRAM ORDER CONTROL / ANTI-RECREATE
#   * Adds authenticated Telegram command control using the configured
#     TELEGRAM_CHAT only.
#   * /cancel <SYMBOL> cancels OPEN LIMIT SELL target orders for that symbol
#     and permanently disables automatic target recreation for the live process.
#   * /cancel_all_targets cancels all OPEN LIMIT SELL target orders across the
#     account and disables their automatic recreation for this process.
#   * /orders shows current open orders so the operator can verify exact state.
#   * Target-only reconciliation no longer recreates a target after cancellation
#     when V561_TARGET_RECREATE_ON_CANCEL=False (default).
#   * Cancellation is exchange-state reconciled; ambiguous cancellation does
#     NOT trigger blind retries or new SELL orders.
#   * Optional /cancel_all <SYMBOL> exists for emergency cancellation of every
#     open order on a symbol, but is deliberately separate from target cancel.
#   * No entry, SL, exposure, balance, TruthSeal or strategy gate is weakened.
#
# v4.5.60 FINAL AUTO-SL HYBRID NATIVE->SOFTWARE
#   * Verified native exchange SL is preferred when explicitly supported.
#   * Native SL unavailable/unverified after a confirmed BUY does not trigger
#     an immediate SELL; an automatic software-SL watchdog is armed instead.
#   * Software SL performs an automatic reconciled market SELL only when the
#     actual price breaches the model SL.
#   * Missing SL ID / stop verification failure / transient stop API error is
#     not itself a price-breach event.
#   * Dedicated PositionManager runs at 0.50s by default and is independent
#     from the market scanner.
#   * Missed protection heartbeat blocks NEW entries first; persistent monitor
#     failure is a last-resort protection hazard and can emergency-close.
#   * Native SL retries reconcile exchange state before another state-changing
#     create, preventing blind duplicate stops after ambiguous responses.
#   * Dynamic TP geometry, fee/risk/precision gates and LONG_ONLY MEXC SPOT
#     authority remain intact.
#
# v4.5.59 FINAL DYNAMIC TARGETS / SL-FAIL / TARGET-ONLY / SL-MONITOR
#   * Post-fill SL failure NEVER forces an automatic market SELL in the default
#     TARGET_ONLY policy.
#   * SL monitoring alternatives: verified native exchange SL, software
#     ALERT_ONLY monitor, or manual TARGET_ONLY monitoring.
#   * ALERT_ONLY mode can warn on SL-near / SL-breach conditions but cannot
#     place a SELL or finalize the position.
#   * TARGET_ONLY remains first in PositionManager, before pending SL/TP
#     reconciliation and all automated exit mutations.
#   * Dynamic targets remain bounded by StrategyExitProfiles + quality score
#     + ATR volatility + family bias, with existing fee/risk gates authoritative.
#   * 40-USDT sizing and 50/30/20 exit weights are unchanged.
#
# v4.5.58 FINAL DYNAMIC TARGETS / SL-FAIL / TARGET-ONLY
#   * Exit targets are now dynamically derived from the existing StrategyExitProfiles
#     plus signal quality and volatility, while preserving family-specific envelopes.
#   * Quality tiers: B <70, A 70-84.99, A+ 85-94.99, Elite >=95; bounded RR scaling only.
#   * ATR% volatility trims/extends target reach within a strict bounded range.
#   * Family bias favors breakout/trend continuation and slightly shortens reversal targets.
#   * Dynamic targets are checked against the existing hard fee-viability gate; if the
#     adjusted geometry becomes uneconomic, the canonical profile is retained or the
#     existing bounded fee-rescue is used and rechecked.
#   * 40-USDT position sizing is unchanged; default exit weights remain 50/30/20.
#   * SL-failure TARGET_ONLY behavior remains: no automatic market SELL; LIMIT SELL
#     targets only; manual SL monitoring remains the operator responsibility.
#
# v4.5.58 FINAL DYNAMIC TARGETS / SL-FAIL / TARGET-ONLY CLOSURE
#   * ROOT closure completed: SL missing-ID and repeated-unverified paths now
#     enter TARGET_ONLY directly; no automatic market SELL is issued.
#   * Explicit operator policy: failed/unverified native SL never causes an
#     automatic market SELL when target-only mode is enabled.
#   * The already-filled spot position remains open and LIMIT SELL exits are
#     installed at TP1/TP2/TP3 using the actual-fill geometry.
#   * TARGET_ONLY takes precedence over SLHealthAuditor, SoftwareSLFallback,
#     market-TP, staircase, trailing and time-exit for that trade.
#   * Target-order outcomes are reconciled from the exchange; ambiguous states
#     are preserved and never blindly duplicated.
#   * Any later SL replacement failure may enter the same target-only state.
#   * Normal emergency_close remains available for unrelated hard hazards.
#
# v4.5.56 FINAL LIVE-EXECUTION / PROTECTION CLOSURE
#   * ROOT-CAUSE FIX: current telemetry showed FULL_LIVE_RUNNING but ZERO sends
#     because EquityDrawdownHalt was hard-blocking every new entry at
#     19.60% drawdown. The halt remains a real safety authority (not removed),
#     but an explicit operator-reset path is now available at boot without
#     changing the limit or silently clearing the protection.
#   * ROOT-CAUSE FIX: current MEXC spot CCXT capability reports do not certify
#     trigger/stop orders; the old ProductionCapabilityGate treated a merely
#     callable create_stop_market_order helper as sufficient. That could lead
#     to a BUY fill followed by unverifiable protection and an immediate
#     emergency SELL. Live MEXC spot now detects this honestly and uses a
#     dedicated SOFTWARE_SL_ONLY protection mode when server-side stop support
#     is not explicitly certified.
#   * PROTECTION FIX: a failed exchange-stop verification no longer forces an
#     immediate market SELL when the bounded software-SL fallback is healthy.
#     The filled trade stays active and is protected by the software SL
#     watchdog; an exit occurs only on an actual breach/timeout or unresolved
#     protection hazard.
#   * LATENCY FIX: PositionManager gets a dedicated 1-second (configurable)
#     management task so software-SL protection is independent of the long
#     market-scan cycle. A per-class async lock prevents overlapping ticks.
#   * FAIL-CLOSED: KillSwitch, Balance/TruthSeal, Exposure, PreSend, precision,
#     entry ambiguity, and all existing risk/SL geometry remain hard gates.
#     No futures, leverage, shorts, or blind network retries are introduced.
#
# v4.5.55 FINAL CLEANED SCORE / FEE / MTF RECALL
#   * Single active Global Opportunity score policy: 0.54 -> 0.52 -> 0.50;
#     0.50 is the hard arbitration floor. Global score remains 0..1.
#   * Canonical live execution score remains 0..100 with the existing
#     V453 bounded 70 -> 68 -> 66 -> 64 -> 62 recovery; no cross-scale stacking.
#   * One active Fee-Rescue implementation (V420FeeRescue.try_expand_targets)
#     services both PreSend and the V554 ranking probe; original fee gate remains hard.
#   * MTF_PULLBACK recall widened only at HTF/volume/TP1 geometry:
#     HTF 62->58, volume 0.85->0.80, TP1 ATR 0.80->0.75; MID tier and confirmations remain.
#   * Local per-symbol ranking retention 3->4, with existing elastic cap of 5.
#   * No changes to Long-Only Spot, Balance/TruthSeal, Exposure, Liquidity/Spread,
#     SL verification/fallback, PreSend, execution ambiguity handling, or exit invariants.
#
# v4.5.54 FINAL PREQUAL-COHERENCE / MSE FEE-RESCUE / STARVATION TELEMETRY CLOSURE
#   * Discovery PASS can now be reconciled against CompositeRanking drops;
#     strong PULLBACK candidates that are only economically blocked at the
#     preliminary fee check remain rankable when the existing bounded target-
#     expansion rescue proves the original fee gate can pass.
#   * Empty Global pools no longer retain prior-cycle ranked/top-score values,
#     eliminating false SCORE starvation labels.
#   * Exact MSE rank-reject reasons and pullback fake-break context are logged
#     for evidence-based tuning. No hard execution gate is bypassed.
#
# v4.5.53 FINAL PROTECTED-ENTRY / STOP-RECONCILIATION / LIVE-BLOCK RECOVERY
#   * Fixes the observed ADA failure chain: entry filled -> exchange SL verification failed ->
#     emergency protection exit -> unresolved/ambiguous residual could leave LIVE_ENTRIES_BLOCKED
#     active and suppress all later BUY attempts.
#   * Adds a bounded STOP verification path using open/recent orders before treating a
#     correctly-created MEXC stop as failed. It matches symbol/side/trigger/amount without
#     requiring `filled` on an open stop order.
#   * Adds explicit reconciliation of an ambiguous emergency market-sell before declaring
#     STOPLESS_EXPOSURE. If the sell is proven filled, the trade is finalized and the entry-only
#     block is cleared through a dedicated proof-based recovery function.
#   * Adds robust BUY fill-price reconciliation using trades VWAP and cost/filled, then a bounded
#     fetch_order refresh. This prevents false FILL_DRIFT_ABORTs caused by bad average/price fields.
#   * Enables bounded LIMIT-FIRST entry; the limit is never above the planned entry, has a short
#     timeout, and market fallback is allowed only when current ask remains inside a small drift
#     envelope. Ambiguous resting-order cancel still blocks.
#   * No Balance/TruthSeal/Exposure/PreSend/SL hard gate is bypassed. LONG_ONLY MEXC SPOT and
#     fail-closed semantics remain intact; ambiguous exchange state still blocks new entries.

# v4.5.42 EXECUTION-PARITY / DISCOVERY-LIVE COHERENCE — SURGICAL LIVE HANDOFF CLOSURE
#   * Adds a just-in-time canonical preflight for every globally selected preferred candidate,
#     reusing the SAME canonical prequalification function used by global arbitration before
#     entering the live builder. This closes the observed SELECTED -> EXEC_BLOCKED drift where
#     a candidate was selected from one context and rejected immediately by final policy/HTF/structure.
#   * Discovery Telegram remains KNOWLEDGE ONLY, but now exposes a truthful LIVE PREFLIGHT
#     result and exact blocker reason when the same live snapshot is already provably blocked.
#     A+/95+ discovery quality is never presented as equivalent to live eligibility.
#   * Adds bounded V542 telemetry: preflight pass/block counts, top reasons, last blocker,
#     and candidate/current-context diagnostics. Telemetry is non-authoritative.
#   * Corrects the existing family-aware fake-break configuration drift so the configured
#     PULLBACK/MTF_PULLBACK chase cap is actually used by the soft fake-break gate.
#   * NO HTF/score/risk/liquidity/SL/exposure safety floor is lowered. No new order path is added.
#     LONG_ONLY MEXC SPOT, PreSendGate, Balance/TruthSeal, SL verification, KillSwitch,
#     watchdog, circuit-breaker and fail-closed execution authority remain unchanged.
#
# v4.5.44 FINAL BOOT-VALIDATION / RECOVERY-SELFTEST COHERENCE
#   * Fixes a configuration-validation contradiction introduced by v4.5.43:
#     runtime balance recovery was intentionally bounded to 2 fresh-REAL retries,
#     but the legacy V531 self-test still required the old exact value of 1.
#     That mismatch caused validate_config() to return False and the process to
#     abort with `config_invalid` before the live loop could start.
#   * The self-test now validates the actual supported bounded range (1..2),
#     while V543 remains the feature that authorizes the second recovery attempt.
#   * No trading gate, risk rule, network-timeout semantics, or fail-closed
#     safety authority is relaxed.
#
# v4.5.45 FINAL LIVE-HANDOFF / JIT-PARITY STARVATION CLOSURE
#   * V542 JIT execution-parity remains diagnostic/reconciliation telemetry,
#     but is no longer an independent hard blocker before SignalBuilder.
#   * The canonical SignalBuilder remains the sole live-entry authority and
#     still re-runs freshness, family policy, HTF, microstructure, score,
#     PreSend, balance, exposure, liquidity, precision, SL and execution gates.
#   * This removes a duplicate policy gate that could reject selected candidates
#     before the canonical builder's V457/V518 recovery branches had a chance
#     to run. No hard safety gate is bypassed; the same canonical gate still
#     decides the live order.
#   * Adds explicit JIT-block / JIT-pass / builder-block telemetry to heartbeat
#     so G->E and selected->live handoff failures are distinguishable.
#   * Adds a per-cycle live-ready counter and explicit builder blocker ledger.
#   * No retry of ambiguous network execution, no balance-truth bypass, no SL
#     bypass, no reduction of MAX_CONCURRENT_TRADES, and no short/futures path.
#
# v4.5.47 FINAL HANDOFF / SCORE-LIQUIDITY / CYCLE-ACCOUNTING CLOSURE
#   * Fixes a second-order starvation issue found in live telemetry: bounded
#     pending candidates were appended only AFTER the generic execution reserve,
#     so a full reserve could consume the attempt pool before exceptional
#     high-quality Discovery PASS candidates were ever considered.
#   * Pending handoff candidates are now inserted BEFORE the generic reserve,
#     while finalists remain first. This preserves global ranking authority but
#     makes the bounded Discovery->Execution bridge operational when capacity
#     is actually unused.
#   * Adds cycle-local handoff accounting for SELECTED -> EXEC_TRY -> BUILDER ->
#     LIVE_READY -> QUEUED -> SENT and explicitly separates score/liquidity
#     starvation from execution-handoff starvation.
#   * Adds selected-vs-reserve-vs-pending attempt attribution, exact current-cycle
#     builder-block reason tracking, and cumulative-vs-cycle heartbeat fields.
#   * No score, HTF, liquidity, structure, PreSend, Balance, TruthSeal, SL,
#     exposure, execution or long-only safety gate is bypassed or removed.
#
# v4.5.48 FINAL ELITE-GLOBAL-RECOVERY / PULLBACK-STRUCTURE-CLOSURE
#   * Adds a bounded GLOBAL elite recovery lane when canonical prequalification
#     passes but normal global arbitration selects zero candidates. The lane is
#     restricted to the existing V540 elite-quality evidence plus a hard global
#     safety floor; it never bypasses canonical execution gates.
#   * Separates global-score starvation from canonical-score starvation in cycle
#     telemetry. `relaxed=ON` can now be true without falsely implying that the
#     Global Arbiter itself was relaxed.
#   * Extends the family-aware PULLBACK fake-break soft gate with two existing,
#     closed-bar structural confirmations: higher-low and EMA20 slope-up. These
#     are bounded alternatives to reclaim/bullish-close; chase cap remains hard
#     and applies unchanged. Breakout families remain hard-gated.
#   * Adds explicit no-selection diagnostics: top prepared global score, global
#     floor, elite candidates seen, elite rescue result, and top rejection reason.
#   * No changes to Balance/TruthSeal/Exposure/PreSend/SL/Execution, no network
#     order retries, no shorts/futures/leverage, LONG_ONLY MEXC SPOT preserved.
#
# v4.5.46 FINAL PENDING-HANDOFF / EXECUTION CLOSURE
#   * Preserves exceptional, fresh Discovery candidates that passed the same
#     canonical preflight but were not promoted by the global winner set.
#   * Pending candidates are NOT orders and never bypass Global selection,
#     Balance, TruthSeal, Exposure, Liquidity, PreSend, SL or Execution gates.
#   * They are considered only as a bounded reserve AFTER the normal finalists
#     and existing execution reserve, and only when live capacity remains.
#   * Candidate freshness is rechecked against WALL_NOW at handoff time.
#   * Adds cycle-scoped handoff telemetry so cumulative rejects cannot masquerade
#     as current-cycle execution failures.
#   * Discovery PASS remains KNOWLEDGE ONLY; handoff requires a current snapshot
#     and canonical builder revalidation before any order can be queued/sent.
#
# v4.5.43 FINAL EXECUTION-STARVATION-RECOVERY-HARDENED
#   * Reviews the proposed V542/LIVE-unblock changes against the actual v4.5.42
#     implementation and keeps only changes that improve recall without turning
#     safety gates into fall-open paths.
#   * V537 dual-confirmation remains a hard gate for the dedicated dual engine,
#     but gains a bounded HTF-quality recovery lane only after the original hard
#     RSI floors and strong-bearish-body guards pass. This changes candidate
#     generation for the dual lane only; it does NOT bypass canonical HTF,
#     structure, liquidity, PreSend, Balance, TruthSeal or SL gates.
#   * Balance-send recovery increases from one to two bounded SAME-candidate
#     retries, but ONLY after a fresh REAL balance reconciliation. CACHE/BLOCK
#     never re-submit, and network-timeout outcomes remain terminal/ambiguous.
#     Recovery uses bounded exponential backoff and never blindly retries an
#     exchange order whose acceptance is ambiguous.
#   * Adds per-reason execution-blocker burst telemetry/alert logging at a
#     bounded threshold without introducing a new execution authority.
#   * Explicitly does NOT implement: breakout structural bypass, network-timeout
#     tolerance, aggressive FailedSendCB=2 tightening, duplicate starvation
#     relief, or blind Near-Miss promotion. Existing V453/V456/V542 bounded
#     mechanisms already cover those areas; duplicating them would weaken the
#     fail-closed design or create policy drift.
#   * LONG_ONLY MEXC SPOT, TruthSeal, Balance, Exposure, KillSwitch, Watchdog,
#     circuit breakers, PreSendGate, LiquidityDepth, SL verification and all
#     existing execution authorities remain intact.
#
# v4.5.40 FINAL ELITE-LIVE SELECTIVE TUNING — FAMILY-AWARE / SPREAD-BOUNDED / DISCOVERY-CLOSURE
#   * Adds an elite-live selection lane for the strongest candidates without bypassing hard safety/execution gates.
#   * Extends existing V528 quality-spread relief with a stricter V540 elite lane instead of lowering global tier ceilings.
#   * Gives fake-break handling explicit family semantics, preserving hard rejection for breakout families while keeping PULLBACK non-hard.
#   * Adds a bounded elite ranking bonus and an optional LIVE-READY Telegram diagnostic for exceptional candidates.
#   * Tightens knowledge-only Discovery noise (reviewed score >=80, bounded 5/cycle) without changing live execution floors.
#   * Slows starvation-alert repetition to 15 minutes; detection logic remains unchanged.
#   * No score/risk/SL/HTF/liquidity hard floor is globally bypassed; all fail-closed execution invariants remain.
#
# v4.5.40 FINAL UNIVERSAL/ELITE-LIVE DUAL-CONFIRMATION — REPLAY / TRANSIENT-SPREAD / BLOCKER TELEMETRY
#   * Adds an opt-in offline replay harness for the same Dual A/B trigger logic.
#   * Adds one bounded fresh spread recheck before a transient tier-spread reject.
#   * Adds compact Top Execution Blocker telemetry to heartbeat.
#   * No score/risk/SL/HTF/liquidity hard floor is relaxed; all fail-closed gates remain.
#
# v4.5.41 ELITE QUALITY / EXECUTION-BLOCKER CLOSURE
#   * Elite qualification now requires the bounded reviewed-quality score in
#     addition to raw engine score, preventing false-Elite relief on candidates
#     whose raw score is high but volume/RS/chase quality is weak.
#   * PreSend failures now record the exact final gate message in the execution
#     blocker ledger, making E→Q starvation root causes directly observable.
#   * LIVE-READY Elite diagnostics expose both canonical and reviewed quality.
#   * No execution/risk/liquidity/SL/HTF hard gate is relaxed or bypassed.
#
# v4.5.25 PROTECTED-ENTRY CLOSURE
#   CRITICAL: do not treat an entry fill as a healthy LIVE trade until the
#   exchange SL is created and post-create verified. The previous version
#   ignored the place_sl() return value, allowing an unprotected fill to stay
#   active until the next PositionManager tick, where emergency_close could
#   market-sell slightly below the fill. This version makes protection
#   verification explicit and observable.
#   Also adds opportunity A+/A/B/C grading and TradingView MEXC chart links.
#
# v4.5.33 FINAL OPPORTUNITY REFILL / EXECUTION RECOVERY
# v4.5.34 FINAL LIVE-HANDOFF / RESERVE-REFILL / ROOT-CAUSE CLOSURE
#   * Preserves the primary global-selected set and adds a bounded execution
#     reserve of additional prequalified, quality-qualified distinct symbols.
#     When selected routes fail before Q/S, reserve candidates are promoted in
#     rank order. No HTF/liquidity/structure/score/PreSend hard gate is bypassed.
#   * Adds explicit LIVE-READY telemetry immediately after PreSendGate PASS and
#     before Q, separating score-qualified, live-ready, queued and sent states.
#   * Adds exact per-attempt blocker attribution from the current rejection record
#     so stale prior reasons cannot be misreported against a new attempt.
#   * Adds one bounded balance-truth refresh/re-evaluation for a PreSend balance
#     blocker; exchange orders are never blindly retried. Network-timeout entry
#     attempts remain explicitly non-retryable because acceptance is ambiguous.
#   * LONG_ONLY/SPOT, TruthSeal, Balance, Exposure, SL/TP, KillSwitch, Watchdog,
#     circuit-breaker and all fail-closed invariants remain unchanged.
#
#   * Keeps a bounded prequalified global pool (default 8) while MAX_CONCURRENT_TRADES
#     remains the hard live-position cap (default 3). If a selected candidate dies
#     before Q/S, the router advances to the next-best independent candidate instead
#     of leaving a live slot unused.
#   * Balance send failures trigger ONE fresh canonical balance reconciliation for
#     subsequent candidates; the rejected order is never blindly retried.
#   * Network timeout remains explicitly non-retryable because exchange acceptance
#     is ambiguous and duplicate buys are unsafe.
#   * Send-fail telemetry preserves the exact root cause and avoids double-counting.
#   * No relaxation of HTF, liquidity, structure, score, PreSend, balance truth,
#     SL/TP, exposure, KillSwitch, watchdog, or LONG_ONLY/SPOT invariants.
#
# v4.5.32 FINAL QUALITY / EXECUTION HARDENING
#   * Discovery noise closure: knowledge-only alerts now require a reviewed
#     quality score >= 65 by default and are capped at 8 per rolling cycle.
#     This does NOT change the live execution floor or any execution gate.
#   * Stablecoin closure: adds USDGO explicitly; PAXG remains non-stable and
#     eligible. Stablecoin filtering remains hard and fail-closed at MSE,
#     discovery, and canonical execution entry points.
#   * Discovery gate uses the reviewed score (not raw engine score) as the
#     quality gate, while preserving raw score visibility in notifications.
#   * Discovery self-tests validate the new reviewed-score floor, cycle cap,
#     and USDGO exclusion.
#   * No risk, sizing, SL, TP, balance-truth, TruthSeal, exposure, watchdog,
#     or LONG_ONLY/SPOT execution invariant is loosened.
#
# v4.5.35 FINAL EXECUTION-HANDOFF / REFILL / TELEMETRY CLOSURE
#   * Q is treated as a provisional pre-submit commit for refill decisions; a
#     same-attempt send failure no longer suppresses the next-best candidate.
#   * Deterministic balance send failure gets one bounded same-candidate retry
#     after fresh balance truth; the failed order is never blindly duplicated.
#   * Queue/candle scan throttles are rolled back on pre-acceptance send failure
#     so the bounded balance recovery can actually re-evaluate the same candle.
#   * Ambiguous network timeout remains terminal for the cycle; no alternate
#     entry is submitted until the normal reconciliation/safety machinery can
#     establish exchange state.
#   * Heartbeat exposes execution attempts, LIVE_READY, send failures,
#     ambiguous blocks, balance retries and alternate/refill promotions.
#   * MAX_CONCURRENT_TRADES, TruthSeal, Balance, Exposure, HTF, liquidity,
#     structure, PreSend, SL/TP, KillSwitch, watchdog and LONG_ONLY/SPOT remain
#     hard authorities and are not bypassed.
#

# V702 A58.1 — Final Production Audit Closure (2026-11-13)
#   * Replaced repeated/full-module AST materialization in selected startup
#     source-contract checks with streaming token scans and parsing of bounded
#     call snippets; kept the checks fail-closed and preserved trading logic.
#   * Removed the obsolete full-source AST cache helper. Validator temporary
#     allocations are collected after validation; Linux malloc_trim remains
#     best-effort and never controls startup correctness.
#   * Measured `main.py --validate-only` max RSS: 530,732 KiB in this audit
#     container (prior pre-optimization peak was about 1.22 GiB).
#   * Kept SPOT/LONG_ONLY, score floor 70, two-key live authorization, strategy
#     gates, execution-intent context, and protection/reconciliation controls.
#   * Removed seven superseded A55/A56/A57 standalone release metadata/report
#     files from the compact distribution; excluded the generated local SQLite
#     database. No runtime Python module or test file was removed. ZIP target: 97 files.
#   * Screenshot review: supplied Railway Deploy Logs contain internal MOCK
#     self-tests and no live exchange client; no `[V702-CRASH]` traceback is
#     visible. The precise Railway crash cause therefore remains unproven.
#   * Full pytest and package checks are recorded in A58_FINAL_AUDIT_REPORT_AR.md
#     and A58_RELEASE_MANIFEST.json. Live MEXC/Telegram, Docker target build,
#     Python 3.12/linux-amd64 runtime, and profitability remain unverified.
#   * Production decision remains NO_GO_UNATTENDED_LIVE.

# =============================================================================
```
