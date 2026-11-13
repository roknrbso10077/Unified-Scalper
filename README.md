# UNIFIED SCALPER V702 — A59 CANONICAL FINAL

**Release ID:** `UNIFIED-SCALPER-V702-A59-CANONICAL-FINAL`  
**Release date:** 2026-11-13  
**Canonical executable:** `main.py`  
**Production decision:** `NO_GO_UNATTENDED_LIVE`

## Operational status

This package is approved for offline validation, monitoring and supervised paper/shadow research only. It is **not approved for unattended live trading**. Offline tests do not establish exchange connectivity, actual order/fill/cancel behavior, Telegram delivery, protective-stop reliability, deployment correctness or profitability. No profit is guaranteed.

Live keys remain disabled by default:

```dotenv
UNIFIED_LIVE_PILOT_ENABLE=0
UNIFIED_A55_LIVE_ARM=0
```

لا يكفي المفتاح الأول وحده؛ يجب أن يكون `UNIFIED_LIVE_PILOT_ENABLE=1` و`UNIFIED_A55_LIVE_ARM=1` مفعّلين معاً قبل أي BUY حي. Do not turn these values on as part of deployment or CI. A real entry also requires every existing policy, EdgeGate, ProductionCapabilityGate, fresh PositionManager health lease, portfolio drawdown, balance, sizing, market-quality, protection and execution check. Any missing authority or unverifiable protection must fail closed.

## Strategy and risk invariants

- Spot only; LONG_ONLY; Futures and short selling disabled.
- Minimum live score remains **70**. No score, HTF, liquidity, fake-break, structure, spread, fee or risk gate has been relaxed.
- Maximum concurrent positions: **2**. Maximum planned ticket: **75 USDT**. These are upper bounds, not a recommendation to trade.
- Forbidden bases: `PUMP`, `BNB`, `CAKE`, `AERO`, `ETHFI`.
- The paper-ledger default active capacity is **20**, with a hard ceiling of **120**. Selected-route paper entries require a buffered upside breakout; a simple reference touch is not a fill.
- Same-candle stop/target ambiguity is conservatively resolved as **stop first**.

## Run and validate

Use Python 3.12 for the declared target runtime. `requirements.in` is the single source of six pinned direct dependencies. Railway's default Docker build uses those pins and allows pip to resolve transitive packages; it does not claim a hash-reproducible installation. CI compiles the complete Python 3.12 `linux/amd64` transitive graph with SHA-256 hashes into `requirements-lock.txt`, verifies it with `pip --require-hashes`, uses `STRICT_HASH_LOCK=1` for the Docker build, and publishes the resolved lock as a workflow artifact. The checked-in `requirements-lock.txt` is only a direct-pin seed and must not be passed to `--require-hashes`.

```bash
python main.py --validate-only
python -u main.py
```

`--validate-only` must exit with code 0, report `bot_started=false`, and leave no background threads. The normal command starts the monitor/paper runtime; it does not override the live-off defaults.

## Durable storage

Mount a persistent volume at `/data` and set `RAILWAY_RUN_UID=0` in Railway Variables so the process can write to the Railway volume (Railway mounts volumes as root-owned). Keep the service restart policy set to `Always`. Then set:

```dotenv
SCALPER_DB=/data/unified_scalper.db
V702_KNOWLEDGE_RECIPE_EXPORT_PATH=/data/knowledge_recipe_memory.json
```

Do not store API keys in the repository or ZIP. Supply them only through the deployment secret manager. Do not package `.env`, credentials, runtime databases, generated market data or logs.

## Safety and health monitoring

The generic heartbeat remains a 30-minute process digest and its 2,100-second stale threshold is intentionally matched to that cadence; it is not the fast watchdog. The independent runtime heartbeat must be fresh within 60 seconds. When any position is open, a PositionManager heartbeat from the same process boot must be fresh within 30 seconds and show an active position. Docker HEALTHCHECK fails closed on stale/missing protection-manager evidence when the container runtime monitors it. Railway's deployment healthcheck is a startup gate only and is not a continuous watchdog; do not configure a Railway HTTP Healthcheck Path because this bot does not expose an HTTP server. Use an external alert/monitor against the runtime and PositionManager heartbeat files or Telegram watchdog alerts for ongoing supervision. On every restart, recovered-position protection reconciliation runs before market scanning; a failure blocks new entries.

MEXC Spot native stop support must not be assumed. Where protection is software-SL-only, the process and PositionManager must remain healthy. A container restart or stale heartbeat is an operational safety event, not proof that a position is protected.

## Release integrity

After obtaining the A58 archive, verify its contents from the package root:

```bash
sha256sum -c A59_SHA256SUMS.txt
```

`A58` and older release metadata are historical only; A59 distribution integrity is defined exclusively by `A59_RELEASE_MANIFEST.json` and `A59_SHA256SUMS.txt`. The A59 ZIP preserves the full canonical code/test set and adds this release report, manifest and checksum index. `LIVE_RELEASE_ENV.example` is a public, non-secret runtime validation artifact: `.dockerignore` explicitly re-includes it and Dockerfile copies it to `/app`; actual `.env`, `LIVE_RELEASE_ENV`, and secret files remain excluded. `HISTORICAL_A53_main.py.baseline` is an A53 source snapshot, not a drop-in rollback. A rollback requires the complete matching historical distribution, configuration and environment.

The GitHub Actions workflow `.github/workflows/a58-production-audit.yml` targets Python 3.12 and `linux/amd64`, resolves transitive dependency hashes from `requirements.in`, installs with `--require-hashes`, publishes the generated lock artifact, runs compilation and pytest, builds the Docker image with `STRICT_HASH_LOCK=1`, and tests both healthy and stale PositionManager heartbeat cases. It does not contact MEXC or Telegram. Make sure the hidden `.github/workflows/` path is pushed to GitHub using Git; a web upload that omits hidden directories will not activate this workflow.

## Final release evidence

See `A59_FINAL_PRODUCTION_AUDIT_AR.md`, `A59_RELEASE_MANIFEST.json`, and `A59_SHA256SUMS.txt` for the A59 production audit. The A58.2 Railway boot-artifact fix is retained. A59 adds isolated Shadow outcome-observation lanes for raw Bearish macro-policy rejects and HTF strength-floor rejects, closes the canonical `BEARISH_RECOVERY` context-policy contract, and fixes compacted digest truncation so rejection diagnostics remain visible. The HTF lane complements (and intentionally overlaps) the narrower `HTF_RELIEF` near-miss cohort; neither lane claims downstream admission or grants live authority. The local validate-only result is recorded in the A59 manifest; it is not a Railway OOM diagnosis. The active decision remains **NO-GO for unattended live trading** until controlled live tests verify small-notional order submission, fills, partial fills, cancellation, network-outage reconciliation, real Telegram delivery and protection recovery, followed by a sufficiently long supervised paper evaluation.

Historical changes and lineage are retained in `CHANGELOG.md` and `DOCS__audits__V702_A*_*.md`.
