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
