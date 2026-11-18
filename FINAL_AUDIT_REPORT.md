# A77 Final Production Audit — Micro Outcome Telegram Closure (2026-11-17)

## Executive result

A77 extends the A76 monitor-only Micro lane so an opportunity alert is followed by a durable Telegram result notification and a per-strategy daily report. The release also fixes a digest-compaction defect that could hide the `SELECTED → BUILDER BLOCK` evidence line while its aggregate counter remained visible.

**Distribution:** 99 files exactly, no new files, no deleted files.  
**Runtime authority:** `MONITOR_ONLY_NO_NEW_BUYS`; `V702_INTRADAY_SHADOW_LIVE_ENABLE=False`; `NO_GO_UNATTENDED_LIVE`.  
**Research DB schema:** v4, additive tables only.

## A77 changes

1. **Outcome notifications:** when an alerted 1m Micro sample resolves, the same SQLite transaction that updates its sample inserts one uniquely keyed outcome record. The result outbox supports `TP1`, `SL`, `TIMEOUT` and `AMBIGUOUS_DATA_GAP`; `sample_id` is unique, pending items are retryable, and ambiguous data gaps are excluded from scored returns.
2. **Telegram result message:** includes symbol, strategy, signal ID, entry/stop/target, reference exit, observation bars, modeled cost, gross R and net modeled R/percent. The message explicitly says Shadow/monitor-only and does not claim an exchange fill or realized PnL. Same-candle TP/SL behavior remains conservative stop-first.
3. **Opportunity links:** initial Micro alerts and their outcome notices reuse the existing opportunity link formatter. It can include the MEXC Spot TradingView chart and a Telegram public-channel/bot link when the corresponding public URL or username is configured. A private numeric chat ID is not converted into a fabricated `t.me` permalink. A Telegram link is omitted if no public link identity has been configured; the opportunity is still delivered to the configured bot chat when Telegram credentials are present.
4. **Daily report:** a unique durable report is generated for the previous calendar day in the configured timezone (default `Africa/Cairo`) after 00:05 local time. It reports each of the five intraday Shadow strategies separately, including samples, resolved outcomes, TP1/SL/timeout/ambiguous counts and average modeled net R/percent. It is a research report, not a profit guarantee.
5. **Digest evidence preservation:** when the operator digest is compacted to fit Telegram limits, the three `SELECTED → SCORER/ROUTE/BUILDER BLOCK` headings and their evidence rows now receive explicit preservation priority. This repairs an existing discrepancy where `builder_blocks=1` could be shown while the Builder section itself was dropped.
6. **Configuration and diagnostics:** `.env.example` documents the outcome outbox, batch cap, daily report enable/timezone/time, while `/digest`/service reporting expose pending/queued states. `QUEUED` means accepted into the application's durable Telegram dispatcher outbox; it is not an external Telegram delivery acknowledgement.

## Root-cause / safety boundary

A77 does not change the A76 core/micro scan allocation, family regime policies, macro crash filters, spread or cost thresholds, risk limits, selector, order builder, exchange execution, or position management. The 1m Micro lane stays independent and read-only. Outcome TP/SL labels are simulated closed-candle observations, not live order outcomes. No MEXC order, Telegram network call, external delivery ACK, or profitability claim was tested.

A public Telegram link requires a configured `TELEGRAM_OPPORTUNITY_PUBLIC_URL`, `TELEGRAM_PUBLIC_URL`/`TELEGRAM_CHANNEL_URL`, `TELEGRAM_PUBLIC_CHAT_USERNAME`, an `@channel` alias, or a public bot/channel username. The private bot chat ID alone cannot yield a valid public permalink.

## Verification

- **All packaged test modules:** 58 modules from the exact clean-extracted final ZIP in twelve non-overlapping groups of five modules (last group three); 574 passed, 1 skipped, 0 failed. Group results: 32, 31, 26, 33, 44, 34, 50, 86 + 1 skipped, 35, 32, 40, and 131 passed respectively. The skip is `test_release_contracts.py:375`, which requires a historical A51 runtime log not present in this source package.
- **Focused Micro/digest tests:** 25 passed, 0 failed after the final digest-compaction repair.
- **Compilation:** compileall and explicit `py_compile` for all 73 packaged Python files.
- **ZIP verification:** exact 99/99 manifest inventory, 99 unique archive paths, CRC clean, 98/98 non-self SHA-256 entries match `A66_SHA256SUMS.txt` (the checksum file intentionally does not hash itself).
- **Clean-extract `--validate-only`:** pass, exit code 0; `bot_started=false`, `live_threads=[]`. No live exchange or Telegram integrations are started by this validation.

## Operational recommendation

Keep A77 in `MONITOR_ONLY_NO_NEW_BUYS`. Confirm the Telegram bot token/chat ID and, if a clickable Telegram public link is required inside every alert, configure a public channel/bot URL or username. A durable enqueue is not proof that Telegram delivered the message to the client; monitor delivery acknowledgements and pending outbox counts in runtime logs. Evaluate virtual Micro net outcomes over a meaningful sample before considering any change to live authority.

## A78 — supplied-log diagnosis and applied Micro corrections (2026-11-18)

### Supplied log findings

The supplied `Untitled (2).txt` was parsed by unique Signal ID to avoid counting repeated Telegram copies as independent observations. It contains 193 initial Micro alert blocks but **190 unique signal IDs**. Among those unique IDs, 134 were labelled economically viable under the old modeled-cost gate and 56 were explicitly labelled `TECHNICAL PATTERN ONLY — cost gate not met`; nevertheless, the latter were also sent as initial alerts.

There are **184 unique result IDs** in the supplied log: 49 TP, 104 SL and 31 TIMEOUT. Eight of the 190 initial IDs have no result notice in the captured text; two result IDs have no initial alert in this captured text (their initial message may predate the excerpt). Repeated result messages were deduplicated by ID. Among outcomes with an unambiguous TP/SL result, TP share was 49 / (49 + 104) = **32.0%**; this is a historical Shadow alert statistic, not an exchange win rate.

| Strategy | Unique initial alerts | Resolved IDs | TP | SL | Timeout | TP share among TP/SL | Average modeled net R | Average modeled net % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| MICRO_MOMENTUM_1M | 79 | 74 | 21 | 30 | 23 | 41.2% | -1.132R | -0.423% |
| MICRO_SWEEP_RECLAIM_1M | 69 | 68 | 22 | 40 | 6 | 35.5% | -2.000R | -0.456% |
| MICRO_PULLBACK_RECLAIM_1M | 42 | 40 | 6 | 32 | 2 | 15.8% | -2.912R | -0.696% |
| **Total** | **190** | **184** | **49** | **104** | **31** | **32.0%** | **-1.870R** | **-0.507%** |

The averages above are across resolved virtual samples; the summed percentages/R are not a compounded portfolio backtest. Multiple patterns can overlap on the same symbol and market move. Timeout is kept separate from TP and SL. The file also includes at least one TP that remained net-negative after modeled costs, demonstrating why price touching target is not enough to call the idea economically successful.

The clearest weaknesses are (1) the Pullback detector's 6 TP versus 32 SL, (2) alerts sent despite explicit failure of the old cost gate, and (3) the 1m signal lane's insufficient higher-timeframe confirmation. Several failures occurred within 1–4 bars, consistent with early one-minute false breaks/reclaims. Successful examples generally needed more bars to reach target. The log does not provide an independent out-of-sample period or actual fill records, so it cannot prove that any one indicator/filter will raise real-world profitability.

The same log shows a separate canonical pipeline bottleneck: 30-minute windows with many DISC/RANK/PRE candidates but PASS=0, primarily `family_regime_disallowed.macro` for PULLBACK/BREAKOUT_CONTINUATION under BEARISH BTC (`allow=BULLISH+NEUTRAL`). This is not the Micro alert outbox. The bearish family restriction must not be weakened merely to increase candidate count; the canonical entry policy remains monitor-only.

### A78 source changes

- Micro sample persistence remains independent from notification. Every detected setup can continue contributing to Shadow results, even when it is ineligible for Telegram.
- A Telegram initial alert now requires observed positive BBO spread. Missing/non-positive spread receives the configured fallback cost and cannot qualify as observed spread.
- The default alert gate requires all-in modeled round-trip cost <=0.50%, modeled net target >=0.15%, modeled net reward >=0.75R, closed 5m/15m trend confirmation, positive configured BTC-relative 15m strength, adequate history, aligned latest candle times, and no recent MTF history gap.
- `MICRO_PULLBACK_RECLAIM_1M` is retained in research but its initial Telegram alert is paused by default pending a larger holdout sample.
- Strategy reports now expose Micro alert eligibility/suppression totals and reasons. Telegram initial alerts now include observed spread and MTF/BTC-relative evidence.
- `.env.example` and the runtime environment parser expose A78 quality controls. Existing alert/outcome persistence and Telegram public-link contract remain unchanged.

### Validation limits

All changes remain `MONITOR_ONLY_NO_NEW_BUYS`; the Micro module still has no order API and `V702_INTRADAY_SHADOW_LIVE_ENABLE` remains hard false. The thresholds are conservative screening assumptions, not a claim of a guaranteed increase in TP rate. Only a fresh Shadow holdout with sufficient independent samples can determine whether performance improved. Full test, compile, manifest and archive results are updated in `FINAL_MANIFEST.json` after release validation.

### A78 automated test checkpoint

- Focused Micro + shared cost-model tests: **36 passed, 0 failed**.
- Full repository test suite before release-hash synchronization: **575 passed, 1 skipped, 5 failed**; all five failures were the expected canonical-source digest mismatch caused by modifying `main.py` while the old release manifests still contained the A77 digest. No strategy/runtime test failed.
- **Full repository suite after canonical digest synchronization:** **580 passed, 1 skipped, 0 failed** across 12 non-overlapping batches. Batch pass counts: 32, 31, 26, 33, 44, 34, 50, 86 (+1 skip), 35, 32, 40, and 137. The single skip is `test_release_contracts.py:375`, which requires a historical A51 runtime log not shipped in the clean source release.
- **Compilation:** `python -m compileall -q .` passed.
- **Entrypoint validation:** `python main.py --validate-only` passed with exit code 0, `bot_started=false`, and `live_threads=[]`. No exchange or Telegram credentials were present in the validation environment and no live order was submitted.
- **Packaging:** the final archive is checked against the 99-path manifest, with unique paths and a clean ZIP CRC; it is then extracted separately and `--validate-only` is repeated from that clean extraction.
