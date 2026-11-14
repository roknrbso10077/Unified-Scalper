# UNIFIED SCALPER V702 — A63 CANONICAL FINAL

**Release ID:** `UNIFIED-SCALPER-V702-A63-CANONICAL-FINAL`  
**Release date:** 2026-11-14  
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

After obtaining the A63 archive, verify its contents from the package root:

```bash
sha256sum -c A63_SHA256SUMS.txt
```

`A62` and older release metadata are historical only; A63 distribution integrity is defined by `A63_RELEASE_MANIFEST.json` and `A63_SHA256SUMS.txt`. A63 retains the A62 runtime, tests and historical audit documents, then adds fail-closed execution reconciliation, A63 Edge/Paper evidence isolation, digest snapshot handling, CI/development dependency inputs, the A63 audit, manifest, checksums and regression coverage. The non-executable `HISTORICAL_A53_main.py.baseline` snapshot was already absent from the supplied A60 package and is not a drop-in rollback. `LIVE_RELEASE_ENV.example` is a public, non-secret runtime validation artifact: `.dockerignore` explicitly re-includes it and Dockerfile copies it to `/app`; actual `.env`, `LIVE_RELEASE_ENV`, secrets and runtime databases remain excluded. A rollback requires the complete matching historical distribution, configuration and environment.

The GitHub Actions workflow `.github/workflows/a63-production-audit.yml` is the active A63 production audit workflow. It targets Python 3.12 and `linux/amd64`, resolves transitive dependency hashes from `requirements.in`, installs with `--require-hashes`, runs compilation and `python main.py --validate-only` before pytest, publishes the generated lock artifact, builds the Docker image with `STRICT_HASH_LOCK=1`, and tests both healthy and stale PositionManager heartbeat cases. It does not contact MEXC or Telegram. Make sure the hidden `.github/workflows/` path is pushed to GitHub using Git; a web upload that omits hidden directories will not activate this workflow.

## Final release evidence

See `A63_FINAL_PRODUCTION_AUDIT_AR.md`, `A63_RELEASE_MANIFEST.json`, and `A63_SHA256SUMS.txt` for the current production audit. A58.2 Docker boot-artifact handling, A59 Bearish/HTF reject-shadow observability, A60 Paper outcome-model closure and A61 Builder/Edge evidence closure remain intact. A62 fixes stale structured Telegram blocker records being replayed in later Digest windows after successful delivery. A63 adds fail-closed order identity and precision checks, separates same-attempt market evidence from account/execution eligibility, enforces closed-candle coverage for Paper evidence, and uses snapshot-and-swap Digest generations. Queue acceptance is explicitly not a Telegram delivery ACK. The legacy and structured queues remain protected against reset races. Strategy admission, Score, HTF, liquidity, PreSend, queue, execution and protection gates are unchanged. The active decision remains **NO-GO for unattended live trading**.

Historical changes and lineage are retained in `CHANGELOG.md` and `DOCS__audits__V702_A*_*.md`.
