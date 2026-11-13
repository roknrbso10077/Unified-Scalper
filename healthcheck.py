#!/usr/bin/env python3
"""Container liveness check with strict numeric validation.

Heartbeat freshness is the hard check. Telemetry degradation remains separate
and opt-in as a hard failure, so a telemetry warning alone cannot restart a
process managing an open position.
"""
from __future__ import annotations
import json
import math
import os
import sys
import time
from pathlib import Path


def _env_bool(name: str, default: bool = False) -> bool:
    value = str(os.environ.get(name, "1" if default else "0")).strip().lower()
    return value in {"1", "true", "yes", "on"}


def _finite_number(value, name: str, *, minimum=None, maximum=None) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name}_not_numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name}_non_finite")
    if minimum is not None and number < minimum:
        raise ValueError(f"{name}_below_minimum")
    if maximum is not None and number > maximum:
        raise ValueError(f"{name}_above_maximum")
    return number


def _reject_json_constant(value: str):
    raise ValueError(f"non_standard_json_number:{value}")


def _read_object(path: str, label: str) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=_reject_json_constant)
    if not isinstance(payload, dict):
        raise ValueError(f"{label}_payload_not_object")
    return payload


def main() -> int:
    try:
        now = time.time()
        path = os.environ.get("V702_HEARTBEAT_FILE", "/tmp/unified_scalper_heartbeat.json")
        configured_stale = _finite_number(os.environ.get("V702_HEARTBEAT_STALE_SEC", "2100"), "stale_after", minimum=0.0)
        stale_after = max(60.0, configured_stale)
        configured_warn = _finite_number(os.environ.get("V702_HEALTHCHECK_TELEMETRY_DROP_THRESHOLD_PCT", "10"), "telemetry_threshold", minimum=0.0, maximum=100.0)
        warn_pct = configured_warn
        fail_on_telemetry = _env_bool("V702_HEALTHCHECK_FAIL_ON_TELEMETRY_DEGRADE", False)

        payload = _read_object(path, "heartbeat")
        stamp = _finite_number(payload.get("timestamp", 0.0), "timestamp")
        age = now - stamp
        if not math.isfinite(age) or stamp <= 0 or age < -5.0 or age > stale_after:
            print(f"unhealthy: heartbeat_age_sec={age:.1f} threshold_sec={stale_after:.1f}", flush=True)
            return 1

        # Independent runtime heartbeat has a short deadline, unlike the slower
        # telemetry heartbeat. This detects a frozen main event loop promptly.
        runtime_path = os.environ.get("V702_RUNTIME_HEARTBEAT_FILE", "/tmp/unified_scalper_runtime_heartbeat.json")
        runtime_stale = max(10.0, _finite_number(os.environ.get("V702_RUNTIME_HEARTBEAT_STALE_SEC", "60"), "runtime_stale", minimum=0.0))
        runtime = _read_object(runtime_path, "runtime_heartbeat")
        runtime_stamp = _finite_number(runtime.get("timestamp", 0.0), "runtime_timestamp")
        runtime_age = now - runtime_stamp
        if not math.isfinite(runtime_age) or runtime_stamp <= 0 or runtime_age < -5.0 or runtime_age > runtime_stale:
            print(f"unhealthy: runtime_heartbeat_age_sec={runtime_age:.1f} threshold_sec={runtime_stale:.1f}", flush=True)
            return 1
        open_positions_num = _finite_number(runtime.get("open_positions", 0), "open_positions", minimum=0.0)
        if not open_positions_num.is_integer():
            raise ValueError("runtime_open_positions_not_integer")
        open_positions = int(open_positions_num)

        # A live position protected only by software SL requires its own fresh
        # heartbeat, from the same process incarnation as the runtime heartbeat.
        pm_age_detail = "pm=idle_no_open_position"
        if open_positions > 0:
            pm_path = os.environ.get("V702_PM_HEARTBEAT_FILE", "/tmp/unified_scalper_pm_heartbeat.json")
            pm_stale = max(5.0, _finite_number(os.environ.get("V702_PM_HEARTBEAT_STALE_SEC", "30"), "pm_stale", minimum=0.0))
            pm = _read_object(pm_path, "position_manager_heartbeat")
            pm_stamp = _finite_number(pm.get("timestamp", 0.0), "pm_timestamp")
            pm_age = now - pm_stamp
            runtime_boot = str(runtime.get("boot_id") or "")
            pm_boot = str(pm.get("boot_id") or "")
            pm_positions_num = _finite_number(pm.get("open_positions", 0), "pm_open_positions", minimum=0.0)
            if not pm_positions_num.is_integer():
                raise ValueError("pm_open_positions_not_integer")
            pm_positions = int(pm_positions_num)
            if (not math.isfinite(pm_age) or pm_stamp <= 0 or pm_age < -5.0
                    or pm_age > pm_stale or not runtime_boot or pm_boot != runtime_boot
                    or pm_positions < 1 or str(pm.get("state", "")).upper() == "STOPPED"):
                print(
                    f"unhealthy: position_manager_heartbeat_age_sec={pm_age:.1f} "
                    f"threshold_sec={pm_stale:.1f} runtime_positions={open_positions} "
                    f"manager_positions={pm_positions} same_boot={bool(runtime_boot and pm_boot == runtime_boot)}",
                    flush=True,
                )
                return 1
            pm_age_detail = f"pm_age_sec={max(0.0, pm_age):.1f} pm_positions={pm_positions}"

        telemetry = payload.get("telemetry", {})
        telemetry_state = "unavailable"
        telemetry_detail = ""
        if isinstance(telemetry, dict) and "drop_pct_last_window" in telemetry:
            try:
                events_num = _finite_number(telemetry.get("events_last_window", 0), "events", minimum=0.0)
                dropped_num = _finite_number(telemetry.get("dropped_last_window", 0), "dropped", minimum=0.0)
                drop_pct = _finite_number(telemetry.get("drop_pct_last_window", 0), "drop_pct", minimum=0.0, maximum=100.0)
                if not events_num.is_integer() or not dropped_num.is_integer():
                    raise ValueError("telemetry_count_not_integer")
                events, dropped = int(events_num), int(dropped_num)
                telemetry_state = "DEGRADED" if events > 0 and drop_pct > warn_pct else "OK"
                telemetry_detail = f"telemetry={telemetry_state} window_events={events} window_dropped={dropped} drop_pct={drop_pct:.1f} threshold_pct={warn_pct:.1f}"
                if telemetry_state == "DEGRADED" and fail_on_telemetry:
                    print(f"unhealthy: heartbeat_age_sec={max(0.0, age):.1f} state={str(payload.get('state','UNKNOWN'))[:40]} {telemetry_detail}", flush=True)
                    return 1
            except (TypeError, ValueError, OverflowError):
                telemetry_state = "UNKNOWN"
                telemetry_detail = "telemetry=UNKNOWN invalid_payload=true"
        else:
            telemetry_detail = "telemetry=unavailable"

        print(
            f"healthy: heartbeat_age_sec={max(0.0, age):.1f} "
            f"runtime_age_sec={max(0.0, runtime_age):.1f} open_positions={open_positions} "
            f"{pm_age_detail} state={str(payload.get('state','UNKNOWN'))[:40]} {telemetry_detail}",
            flush=True,
        )
        return 0
    except Exception as exc:
        print(f"unhealthy: heartbeat_unavailable={type(exc).__name__}:{str(exc)[:100]}", flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
