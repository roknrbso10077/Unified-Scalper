FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    V702_HEARTBEAT_FILE=/tmp/unified_scalper_heartbeat.json \
    V702_HEARTBEAT_STALE_SEC=2100 \
    V702_RUNTIME_HEARTBEAT_FILE=/tmp/unified_scalper_runtime_heartbeat.json \
    V702_RUNTIME_HEARTBEAT_STALE_SEC=60 \
    V702_PM_HEARTBEAT_FILE=/tmp/unified_scalper_pm_heartbeat.json \
    V702_PM_HEARTBEAT_STALE_SEC=30

WORKDIR /app

# STRICT_HASH_LOCK=1 is used by CI after resolving a complete transitive lock.
# Railway defaults to 0 and installs the direct pins in requirements.in, so
# deployments do not fail on the intentionally-unhashed source constraints.
ARG STRICT_HASH_LOCK=0
COPY requirements.txt requirements-lock.txt /app/
COPY requirements.in /app/
RUN python -m pip install --no-cache-dir "pip==24.3.1" && \
    if [ "$STRICT_HASH_LOCK" = "1" ]; then \
        grep -q -- "--hash=sha256:" /app/requirements-lock.txt || { echo "requirements-lock.txt is missing SHA-256 hashes" >&2; exit 1; }; \
        python -m pip install --no-cache-dir --require-hashes -r /app/requirements-lock.txt; \
    elif [ "$STRICT_HASH_LOCK" = "0" ]; then \
        python -m pip install --no-cache-dir -r /app/requirements.in; \
    else \
        echo "STRICT_HASH_LOCK must be 0 or 1" >&2; exit 1; \
    fi && \
    python -m pip check

COPY main.py production_guardrails.py v702_counterfactual_shadow.py v702_intraday_shadow.py healthcheck.py /app/
COPY .env.example /app/.env.example
COPY v702_core__policy__family_policy.py v702_core__policy__forbidden_assets.py \
     v702_core__storage__sqlite_writer.py v702_core__scoring__floor_policy.py \
     v702_core__pipeline__event_time_buckets.py v702_core__pipeline__rejection.py \
     v702_core__execution__handoff.py v702_core__execution__cost_model.py \
     v702_core__telegram__funnel.py /app/

RUN python -m py_compile /app/main.py /app/production_guardrails.py \
        /app/v702_counterfactual_shadow.py /app/v702_intraday_shadow.py \
        /app/healthcheck.py /app/v702_core__policy__family_policy.py \
        /app/v702_core__policy__forbidden_assets.py \
        /app/v702_core__storage__sqlite_writer.py \
        /app/v702_core__scoring__floor_policy.py \
        /app/v702_core__pipeline__event_time_buckets.py \
        /app/v702_core__pipeline__rejection.py \
        /app/v702_core__execution__handoff.py /app/v702_core__execution__cost_model.py \
        /app/v702_core__telegram__funnel.py && \
    useradd --create-home --uid 10001 appuser && \
    mkdir -p /data && \
    chown -R appuser:appuser /app /data
USER appuser

# Docker HEALTHCHECK validates heartbeat freshness. Railway only evaluates its
# deployment healthcheck during rollout; it is not a continuous watchdog.
HEALTHCHECK --interval=60s --timeout=5s --start-period=360s --retries=3 CMD ["python", "/app/healthcheck.py"]

CMD ["python", "-u", "main.py"]
