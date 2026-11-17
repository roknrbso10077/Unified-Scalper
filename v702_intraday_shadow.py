"""V702 A9 intraday strategy research lane (shadow-only, no order authority).

Strategies:
- MICRO_MOMENTUM_1M: closed-bar range break with volume/body/chase checks.
- MICRO_SWEEP_RECLAIM_1M: local low sweep and close reclaim.
- MICRO_PULLBACK_RECLAIM_1M: local EMA9 reclaim while local EMA9/21 structure is constructive.
- VWAP_RECLAIM_RS_5M: UTC-session VWAP reclaim plus coin-relative strength vs BTC.
- ADAPTIVE_RS_PULLBACK_15M: top-10 4h relative strength, BTC/asset trend filters,
  15m structural pullback and 5m resumption; 50% at 1.5R then confirmed 15m trail.

All signals are recorded only as virtual experiments. No exchange order APIs are
imported or called. Outcomes use closed 1m candles, pessimistic SL-first handling
when SL and TP are both touched in a candle, and round-trip cost deductions.
"""
from __future__ import annotations

import ast
from contextlib import contextmanager
import hashlib
import json
import math
import sqlite3
import statistics
import time
from datetime import datetime, time as datetime_time, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from v702_core__policy__forbidden_assets import HARD_FORBIDDEN_BASES
from v702_core__storage__sqlite_writer import SQLITE_WRITER_LOCK
from v702_core__execution__cost_model import unified_round_trip_cost_model

try:
    import pandas as pd
except Exception:  # pragma: no cover - guarded by runtime install/validator
    pd = None

SCHEMA_VERSION = 4
STRATEGIES = (
    "MICRO_MOMENTUM_1M",
    "MICRO_SWEEP_RECLAIM_1M",
    "MICRO_PULLBACK_RECLAIM_1M",
    "VWAP_RECLAIM_RS_5M",
    "ADAPTIVE_RS_PULLBACK_15M",
)
_HARD_EXCLUDED_BASES = HARD_FORBIDDEN_BASES


def select_balanced_shadow_symbols(
    core_pool: Sequence[Any],
    micro_pool: Sequence[Any],
    rs_leader_symbols: Sequence[str] = (),
    batch_size: int = 24,
    core_offset: int = 0,
    micro_offset: int = 0,
) -> Dict[str, Any]:
    """Select a rotating, fair core/micro cohort without RS crowd-out.

    RS leaders can consume only core slots (up to 25% of that quota); they can
    never displace a symbol reserved for the micro-liquidity cohort.
    Pools may contain symbols or ``(symbol, quote_volume)`` tuples.
    """
    def symbols(pool):
        out, seen = [], set()
        for item in pool or ():
            value = item[0] if isinstance(item, (tuple, list)) and item else item
            value = str(value or "").upper().strip()
            if value and value not in seen:
                seen.add(value); out.append(value)
        return out

    core = symbols(core_pool); micro = symbols(micro_pool)
    batch = max(0, min(40, int(batch_size or 0)))
    if batch == 0 or (not core and not micro):
        return {"selected": [], "core_selected": 0, "micro_selected": 0,
                "core_offset": 0, "micro_offset": 0, "rs_leaders_selected": 0}

    # 50/50 target when both pools exist. If one is short/empty, unused places
    # are filled from the other pool without reducing the available micro quota.
    if core and micro:
        core_quota = (batch + 1) // 2
        micro_quota = batch - core_quota
    elif core:
        core_quota, micro_quota = batch, 0
    else:
        core_quota, micro_quota = 0, batch

    def rotate(pool, offset, limit):
        if not pool or limit <= 0:
            return [], int(offset or 0)
        start = int(offset or 0) % len(pool)
        count = min(len(pool), int(limit))
        return [pool[(start + i) % len(pool)] for i in range(count)], (start + count) % len(pool)

    core_rotated, next_core = rotate(core, core_offset, core_quota)
    micro_rotated, next_micro = rotate(micro, micro_offset, micro_quota)
    core_set = set(core)
    leaders = []
    seen_leaders = set()
    for item in rs_leader_symbols or ():
        sym = str(item or "").upper().strip()
        if sym in core_set and sym not in seen_leaders:
            leaders.append(sym); seen_leaders.add(sym)
    leader_cap = min(len(leaders), core_quota, max(1, core_quota // 4)) if core_quota else 0
    chosen_core = []
    for sym in leaders[:leader_cap] + core_rotated:
        if sym not in chosen_core:
            chosen_core.append(sym)
        if len(chosen_core) >= core_quota:
            break
    chosen_micro = list(micro_rotated[:micro_quota])

    # Fill only after honoring reserved cohort slots. Prefer the underfilled
    # cohort first, then use the other pool; duplicate symbols are never returned.
    selected = list(chosen_core) + list(chosen_micro)
    selected_set = set(selected)
    for pool, target in ((micro, micro_quota), (core, core_quota)):
        current = len(chosen_micro) if target == micro_quota and pool is micro else len(chosen_core)
        if current >= target:
            continue
        for sym in pool:
            if sym not in selected_set:
                selected.append(sym); selected_set.add(sym)
                if len(selected) >= batch:
                    break
        if len(selected) >= batch:
            break
    if len(selected) < batch:
        for sym in core + micro:
            if sym not in selected_set:
                selected.append(sym); selected_set.add(sym)
                if len(selected) >= batch:
                    break
    core_count = sum(1 for x in selected if x in core_set)
    micro_set = set(micro)
    micro_count = sum(1 for x in selected if x in micro_set)
    return {"selected": selected[:batch], "core_selected": core_count,
            "micro_selected": micro_count, "core_offset": next_core,
            "micro_offset": next_micro,
            "rs_leaders_selected": sum(1 for x in selected if x in set(leaders[:leader_cap]))}


def _num(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        out = float(value)
        return out if math.isfinite(out) else default
    except Exception:
        return default


def _json(value: Any) -> str:
    def clean(obj):
        if isinstance(obj, dict): return {str(k): clean(v) for k, v in obj.items()}
        if isinstance(obj, (tuple, list)): return [clean(v) for v in obj]
        if isinstance(obj, (str, int, bool)) or obj is None: return obj
        if isinstance(obj, float): return obj if math.isfinite(obj) else None
        try:
            if hasattr(obj, "item"): return clean(obj.item())
        except Exception:
            pass
        return str(obj)[:200]
    return json.dumps(clean(value), ensure_ascii=False, separators=(",", ":"))


def _frame_ok(frame: Any, minimum: int) -> bool:
    try:
        if pd is None or frame is None or len(frame) < minimum:
            return False
        required = {"open", "high", "low", "close", "volume"}
        if not required.issubset(set(frame.columns)):
            return False
        cols = frame[list(required)].apply(pd.to_numeric, errors="coerce")
        return bool(cols.iloc[-minimum:].notna().all().all() and (cols.iloc[-minimum:][["open", "high", "low", "close"]] > 0).all().all())
    except Exception:
        return False


def _ts_ms(index_value: Any) -> Optional[int]:
    try:
        if hasattr(index_value, "timestamp"):
            return int(float(index_value.timestamp()) * 1000)
        # DataFrame index may be an epoch in milliseconds.
        value = int(index_value)
        return value if value > 10_000_000_000 else value * 1000
    except Exception:
        try:
            ts = pd.Timestamp(index_value)
            if ts.tzinfo is None: ts = ts.tz_localize("UTC")
            return int(ts.timestamp() * 1000)
        except Exception:
            return None


def _closed_rows(df: Any, timeframe_ms: int) -> List[Dict[str, float]]:
    """Return bars whose close time has actually passed.

    Do not blindly discard the final row: historical frames often contain only
    closed candles, while live exchange frames can end with a forming candle.
    ``attrs['as_of_ms']`` and ``attrs['close_grace_ms']`` make replay/tests fully
    deterministic; live frames use wall-clock time and a small close grace.
    """
    if not _frame_ok(df, 2):
        return []
    try:
        as_of_ms = _num(getattr(df, "attrs", {}).get("as_of_ms"), None)
        if as_of_ms is None:
            as_of_ms = time.time() * 1000.0
        grace_ms = _num(getattr(df, "attrs", {}).get("close_grace_ms"), 1_000.0)
        grace_ms = max(0.0, min(float(timeframe_ms) * 0.25, float(grace_ms or 0.0)))
    except Exception:
        as_of_ms = time.time() * 1000.0
        grace_ms = 1_000.0
    rows: List[Dict[str, float]] = []
    previous_ts = None
    for i in range(len(df)):
        row = df.iloc[i]
        ts = _ts_ms(df.index[i])
        if ts is None:
            return []
        if float(ts + timeframe_ms) > float(as_of_ms) - grace_ms:
            continue
        try:
            o = float(row["open"]); h = float(row["high"]); l = float(row["low"])
            c = float(row["close"]); v = float(row["volume"])
            values = (o, h, l, c, v)
            if not all(math.isfinite(x) for x in values):
                return []
            # OHLC must describe a possible candle. Invalid bars invalidate the
            # source frame; silently skipping them could bridge an unknown event.
            if l <= 0 or v < 0 or h < l or l > min(o, c) or h < max(o, c):
                return []
            if previous_ts is not None and int(ts) <= int(previous_ts):
                return []
            gap_before = bool(previous_ts is not None and int(ts) - int(previous_ts) > int(timeframe_ms * 1.5))
            item = {
                "ts": float(ts), "open": o, "high": h, "low": l,
                "close": c, "volume": v, "close_ts": float(ts + timeframe_ms),
                "gap_before": gap_before,
            }
            rows.append(item)
            previous_ts = int(ts)
        except Exception:
            return []
    return rows


def _atr(rows: Sequence[Dict[str, float]], period: int = 14) -> Optional[float]:
    if len(rows) < period + 2: return None
    trs = []
    for i in range(1, len(rows)):
        b, prev = rows[i], rows[i - 1]
        trs.append(max(b["high"] - b["low"], abs(b["high"] - prev["close"]), abs(b["low"] - prev["close"])))
    vals = trs[-period:]
    if not vals: return None
    value = sum(vals) / len(vals)
    return value if math.isfinite(value) and value > 0 else None


def _ema(values: Sequence[float], period: int) -> List[float]:
    if not values: return []
    alpha = 2.0 / (float(period) + 1.0)
    out = [float(values[0])]
    for x in values[1:]: out.append(alpha * float(x) + (1.0 - alpha) * out[-1])
    return out


def _risk_geometry(entry: float, stop: float, atr: float) -> Optional[Tuple[float, float]]:
    if not all(math.isfinite(x) and x > 0 for x in (entry, stop, atr)) or stop >= entry:
        return None
    risk = entry - stop
    risk_pct = 100.0 * risk / entry
    # Avoid unrealistically tiny and structurally absurd shadow stops. This is a
    # research-quality bound, not a live-trade gate, because no orders are sent.
    if not 0.12 <= risk_pct <= 2.5 or risk < 0.25 * atr or risk > 3.5 * atr:
        return None
    target = entry + risk  # one-R initial target, scored after modeled costs
    return risk, target


def _return(rows: Sequence[Dict[str, float]], back: int) -> Optional[float]:
    """Return over `back` closed bars; inputs already exclude the open candle."""
    if back < 1 or len(rows) < back + 1: return None
    old = rows[-(back + 1)]["close"]
    cur = rows[-1]["close"]
    if old <= 0: return None
    return cur / old - 1.0


class V702IntradayShadow:
    """Bounded SQLite shadow study; has no live-trading surface."""

    def __init__(self, db_path: str, report_dir: str, config_getter=None, forbidden_fn=None):
        self.db_path = str(db_path or "./unified_scalper.db")
        self.report_dir = Path(report_dir or "./reports")
        self._config_getter = config_getter or (lambda: {})
        self._forbidden_fn = forbidden_fn
        self._last_retention = {"total": 0, "pending": 0, "deleted_terminal": 0, "over_cap": 0}
        self._initialize()

    def _prune_sample_rows(self, conn, max_rows: int):
        """Prune oldest resolved rows, never unresolved PENDING samples."""
        max_rows = max(1, int(max_rows))
        total = int(conn.execute("SELECT COUNT(*) FROM v702_intraday_shadow_samples").fetchone()[0])
        pending = int(conn.execute("SELECT COUNT(*) FROM v702_intraday_shadow_samples WHERE status='PENDING'").fetchone()[0])
        excess = max(0, total - max_rows)
        deleted = 0
        if excess:
            cur = conn.execute(
                "DELETE FROM v702_intraday_shadow_samples WHERE sample_id IN ("
                "SELECT sample_id FROM v702_intraday_shadow_samples WHERE status!='PENDING' "
                "ORDER BY created_ts ASC LIMIT ?)", (excess,)
            )
            deleted = max(0, int(cur.rowcount or 0))
        remaining = int(conn.execute("SELECT COUNT(*) FROM v702_intraday_shadow_samples").fetchone()[0])
        self._last_retention = {"total": remaining, "pending": pending,
                                "deleted_terminal": deleted, "over_cap": max(0, remaining - max_rows)}
        return dict(self._last_retention)

    def _cfg(self) -> Dict[str, Any]:
        try:
            cfg = self._config_getter()
            return cfg if isinstance(cfg, dict) else {}
        except Exception:
            return {}

    def _connect(self):
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    @contextmanager
    def _db(self):
        """Close every SQLite connection deterministically, including error paths."""
        # Serialize before opening the connection so a concurrent ledger/guard
        # writer cannot leave this scanner worker waiting on SQLite busy_timeout.
        with SQLITE_WRITER_LOCK:
            conn = self._connect()
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def _initialize(self):
        parent = Path(self.db_path).expanduser().resolve().parent
        parent.mkdir(parents=True, exist_ok=True)
        with self._db() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""CREATE TABLE IF NOT EXISTS v702_intraday_shadow_samples (
                sample_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                strategy_mode TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                signal_ts_ms INTEGER NOT NULL,
                created_ts REAL NOT NULL,
                entry REAL NOT NULL,
                stop REAL NOT NULL,
                target REAL NOT NULL,
                risk_unit REAL NOT NULL,
                risk_pct REAL NOT NULL,
                last_candle_ts_ms INTEGER NOT NULL DEFAULT 0,
                bars_seen INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL,
                exit_price REAL,
                gross_r REAL,
                net_r REAL,
                net_pct REAL,
                cost_pct REAL NOT NULL,
                quote_volume_24h REAL,
                tier TEXT NOT NULL DEFAULT '',
                features_json TEXT NOT NULL DEFAULT '{}',
                resolved_ts REAL,
                note TEXT NOT NULL DEFAULT '',
                tp1_hit INTEGER NOT NULL DEFAULT 0,
                partial_realized_r REAL NOT NULL DEFAULT 0.0,
                trailing_stop REAL,
                UNIQUE(symbol,strategy_mode,signal_ts_ms)
            )""")
            _sample_columns = {str(r[1]) for r in conn.execute("PRAGMA table_info(v702_intraday_shadow_samples)").fetchall()}
            for _name, _sql in (("tp1_hit", "INTEGER NOT NULL DEFAULT 0"),
                                ("partial_realized_r", "REAL NOT NULL DEFAULT 0.0"),
                                ("trailing_stop", "REAL")):
                if _name not in _sample_columns:
                    conn.execute(f"ALTER TABLE v702_intraday_shadow_samples ADD COLUMN {_name} {_sql}")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_v702_intraday_status ON v702_intraday_shadow_samples(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_v702_intraday_strategy ON v702_intraday_shadow_samples(strategy_mode,status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_v702_intraday_symbol ON v702_intraday_shadow_samples(symbol,signal_ts_ms)")
            conn.execute("""CREATE TABLE IF NOT EXISTS v702_intraday_shadow_evaluations (
                evaluation_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                strategy_mode TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                bar_ts_ms INTEGER NOT NULL,
                evaluated_ts REAL NOT NULL,
                outcome TEXT NOT NULL,
                reason TEXT NOT NULL,
                cost_pct REAL,
                post_cost_viable INTEGER,
                quote_volume_24h REAL,
                features_json TEXT NOT NULL DEFAULT '{}'
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_v702_intraday_eval_strategy ON v702_intraday_shadow_evaluations(strategy_mode,outcome)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_v702_intraday_eval_symbol ON v702_intraday_shadow_evaluations(symbol,bar_ts_ms)")
            conn.execute("""CREATE TABLE IF NOT EXISTS v702_intraday_shadow_meta (
                k TEXT PRIMARY KEY, v TEXT NOT NULL, updated_ts REAL NOT NULL
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS v702_intraday_shadow_alerts (
                alert_id TEXT PRIMARY KEY, sample_id TEXT NOT NULL UNIQUE, symbol TEXT NOT NULL,
                strategy_mode TEXT NOT NULL, signal_ts_ms INTEGER NOT NULL, created_ts REAL NOT NULL,
                state TEXT NOT NULL DEFAULT 'PENDING', payload_json TEXT NOT NULL DEFAULT '{}',
                updated_ts REAL NOT NULL, note TEXT NOT NULL DEFAULT ''
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_v702_intraday_alert_state ON v702_intraday_shadow_alerts(state,created_ts)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_v702_intraday_alert_symbol ON v702_intraday_shadow_alerts(symbol,created_ts)")
            conn.execute("""CREATE TABLE IF NOT EXISTS v702_intraday_shadow_outcomes (
                outcome_id TEXT PRIMARY KEY, sample_id TEXT NOT NULL UNIQUE, symbol TEXT NOT NULL,
                strategy_mode TEXT NOT NULL, timeframe TEXT NOT NULL, signal_ts_ms INTEGER NOT NULL,
                resolved_ts REAL NOT NULL, outcome TEXT NOT NULL, exit_price REAL, gross_r REAL,
                net_r REAL, net_pct REAL, cost_pct REAL NOT NULL DEFAULT 0.0, bars_seen INTEGER NOT NULL DEFAULT 0,
                state TEXT NOT NULL DEFAULT 'PENDING', payload_json TEXT NOT NULL DEFAULT '{}',
                updated_ts REAL NOT NULL, note TEXT NOT NULL DEFAULT ''
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_v702_intraday_outcome_state ON v702_intraday_shadow_outcomes(state,resolved_ts)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_v702_intraday_outcome_strategy ON v702_intraday_shadow_outcomes(strategy_mode,outcome,resolved_ts)")
            conn.execute("""CREATE TABLE IF NOT EXISTS v702_intraday_shadow_daily_outbox (
                report_date TEXT PRIMARY KEY, created_ts REAL NOT NULL, state TEXT NOT NULL DEFAULT 'PENDING',
                payload_json TEXT NOT NULL DEFAULT '{}', updated_ts REAL NOT NULL, note TEXT NOT NULL DEFAULT ''
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_v702_intraday_daily_state ON v702_intraday_shadow_daily_outbox(state,created_ts)")

    @staticmethod
    def _symbol_allowed(symbol: str) -> bool:
        sym = str(symbol or "").upper().strip()
        if not sym.endswith("/USDT") or sym.count("/") != 1: return False
        base = sym.split("/", 1)[0]
        return bool(base) and base not in _HARD_EXCLUDED_BASES

    def _is_forbidden(self, symbol: str) -> bool:
        if not self._symbol_allowed(symbol): return True
        if callable(self._forbidden_fn):
            try:
                value = self._forbidden_fn(symbol)
                if isinstance(value, tuple): return bool(value[0])
                return bool(value)
            except Exception:
                # Research must fail closed if the canonical exclusion lookup errors.
                return True
        return False

    def _crash_guard(self, snapshot: Dict[str, Any]) -> Tuple[bool, str]:
        btc = _closed_rows(snapshot.get("df_btc_5m"), 300_000)
        if len(btc) >= 5:
            old, cur = btc[-4]["close"], btc[-1]["close"]
            if old > 0 and (cur / old - 1.0) <= -0.015:
                return True, "btc_15m_crash_guard"
        # Don't require bullish higher timeframe: only pause during hard downside shock.
        return False, ""

    def _cost_pct(self, entry: float, snapshot: Dict[str, Any]) -> float:
        cfg = self._cfg()
        local_cfg = dict(cfg)
        local_cfg["V702_SMALL_NET_SPREAD_FALLBACK_PCT"] = _num(
            cfg.get("V702_INTRADAY_SPREAD_FALLBACK_PCT"), 0.15
        )
        local_cfg["V702_SMALL_NET_SLIPPAGE_PER_SIDE_PCT"] = _num(
            cfg.get("V702_INTRADAY_SLIPPAGE_PER_SIDE_PCT"), 0.05
        )
        model = unified_round_trip_cost_model(
            local_cfg,
            spread_pct=snapshot.get("spread_pct"),
        )
        return max(0.0, float(model.get("round_trip_cost_pct", 0.0)))

    def _make_signals_1m(self, rows: Sequence[Dict[str, float]], diagnostics: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """Generate the three 1m patterns and report one deterministic reason per engine.

        The optional diagnostics dictionary is telemetry-only. The strategy predicates
        and hard thresholds remain the same as the original A9 shadow implementation.
        """
        cfg = self._cfg()
        minimum_volume_ratio = max(0.5, _num(cfg.get("V702_INTRADAY_MIN_VOLUME_RATIO"), 1.10) or 1.10)
        max_chase = float(cfg.get("V702_INTRADAY_MAX_CHASE_ATR", 0.80))
        out: List[Dict[str, Any]] = []
        diag = diagnostics if isinstance(diagnostics, dict) else {}
        modes = ("MICRO_MOMENTUM_1M", "MICRO_SWEEP_RECLAIM_1M", "MICRO_PULLBACK_RECLAIM_1M")
        for mode in modes:
            diag[mode] = "not_evaluated"
        if len(rows) < 35:
            for mode in modes: diag[mode] = "closed_bars_below_35"
            return out
        b = rows[-1]  # rows are closed bars only
        hist = rows[:-1]
        atr = _atr(hist + [b], 14)
        if atr is None or atr <= 0:
            for mode in modes: diag[mode] = "atr_unavailable_or_invalid"
            return out
        entry = b["close"]
        candle_range = max(b["high"] - b["low"], 1e-12)
        body_ratio = abs(b["close"] - b["open"]) / candle_range
        close_location = (b["close"] - b["low"]) / candle_range
        vol_base = statistics.fmean(x["volume"] for x in rows[-22:-2]) if len(rows) >= 22 else 0.0
        vol_ratio = b["volume"] / vol_base if vol_base > 0 else 0.0
        highs = [x["high"] for x in rows[-12:-2]]
        lows = [x["low"] for x in rows[-12:-2]]

        # 1) Micro momentum break: local closed-bar breakout; no HTF bullish gate.
        mode = "MICRO_MOMENTUM_1M"
        if not highs:
            diag[mode] = "breakout_reference_unavailable"
        elif b["close"] <= max(highs):
            diag[mode] = "breakout_not_confirmed"
        elif b["close"] <= b["open"]:
            diag[mode] = "signal_candle_not_bullish"
        elif body_ratio < 0.48:
            diag[mode] = "body_ratio_below_floor"
        elif vol_ratio < minimum_volume_ratio:
            diag[mode] = "volume_ratio_below_floor"
        else:
            ref = max(highs)
            chase = (b["close"] - ref) / atr
            stop = min([x["low"] for x in rows[-5:]]) - 0.08 * atr
            geom = _risk_geometry(entry, stop, atr)
            if chase > max_chase:
                diag[mode] = "chase_atr_above_ceiling"
            elif not geom:
                diag[mode] = "risk_geometry_invalid"
            else:
                risk, target = geom
                out.append({"mode":mode,"tf":"1m","bar":b,"entry":entry,"stop":stop,"target":target,"risk":risk,"atr":atr,
                    "features":{"volume_ratio":vol_ratio,"body_ratio":body_ratio,"close_location":close_location,"chase_atr":chase,"breakout_ref":ref,"signal":"closed_bar_range_break"}})
                diag[mode] = "signal"

        # 2) Sweep and reclaim the local lows; keep all original conditions intact.
        mode = "MICRO_SWEEP_RECLAIM_1M"
        if not lows:
            diag[mode] = "sweep_reference_unavailable"
        else:
            prior_low = min(lows)
            swept = b["low"] < prior_low and b["close"] > prior_low
            if not swept:
                diag[mode] = "sweep_reclaim_not_confirmed"
            elif b["close"] <= b["open"]:
                diag[mode] = "reclaim_candle_not_bullish"
            elif close_location < 0.58:
                diag[mode] = "close_location_below_floor"
            elif vol_ratio < max(0.75, minimum_volume_ratio * 0.75):
                diag[mode] = "volume_ratio_below_floor"
            else:
                stop = min(b["low"], prior_low) - 0.10 * atr
                geom = _risk_geometry(entry, stop, atr)
                if not geom:
                    diag[mode] = "risk_geometry_invalid"
                else:
                    risk, target = geom
                    out.append({"mode":mode,"tf":"1m","bar":b,"entry":entry,"stop":stop,"target":target,"risk":risk,"atr":atr,
                        "features":{"volume_ratio":vol_ratio,"body_ratio":body_ratio,"close_location":close_location,"swept_level":prior_low,"signal":"sweep_then_closed_reclaim"}})
                    diag[mode] = "signal"

        # 3) Local EMA9 reclaim with a constructive EMA9/21 stack.
        mode = "MICRO_PULLBACK_RECLAIM_1M"
        closes = [x["close"] for x in rows]
        e9, e21 = _ema(closes, 9), _ema(closes, 21)
        if len(e9) < 3 or len(e21) < 3:
            diag[mode] = "ema_warmup_insufficient"
        else:
            prev, cur = rows[-2], rows[-1]
            cross_up = prev["close"] <= e9[-2] and cur["close"] > e9[-1]
            local_stack = e9[-1] >= e21[-1]
            distance = abs(cur["close"] - e9[-1]) / atr
            if not cross_up:
                diag[mode] = "ema9_reclaim_not_confirmed"
            elif not local_stack:
                diag[mode] = "ema9_ema21_stack_not_bullish"
            elif cur["close"] <= cur["open"]:
                diag[mode] = "signal_candle_not_bullish"
            elif close_location < 0.55:
                diag[mode] = "close_location_below_floor"
            elif distance > 0.65:
                diag[mode] = "distance_from_ema9_above_ceiling"
            elif vol_ratio < 0.75:
                diag[mode] = "volume_ratio_below_floor"
            else:
                stop = min(x["low"] for x in rows[-5:]) - 0.08 * atr
                geom = _risk_geometry(entry, stop, atr)
                if not geom:
                    diag[mode] = "risk_geometry_invalid"
                else:
                    risk, target = geom
                    out.append({"mode":mode,"tf":"1m","bar":b,"entry":entry,"stop":stop,"target":target,"risk":risk,"atr":atr,
                        "features":{"volume_ratio":vol_ratio,"body_ratio":body_ratio,"close_location":close_location,"ema9":e9[-1],"ema21":e21[-1],"distance_ema9_atr":distance,"signal":"local_ema9_reclaim"}})
                    diag[mode] = "signal"
        return out

    def _make_vwap_rs_signal_detailed(self, snapshot: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], str]:
        df5, df15 = snapshot.get("df_5m"), snapshot.get("df_15m")
        btc5, btc15 = snapshot.get("df_btc_5m"), snapshot.get("df_btc_15m")
        rows5 = _closed_rows(df5, 300_000)
        rows15 = _closed_rows(df15, 900_000)
        btc_rows5 = _closed_rows(btc5, 300_000)
        btc_rows15 = _closed_rows(btc15, 900_000)
        if min(len(rows5), len(rows15), len(btc_rows5), len(btc_rows15)) < 10:
            return None, "closed_bars_or_relative_strength_history_insufficient"
        b, prev = rows5[-1], rows5[-2]
        day = time.strftime("%Y-%m-%d", time.gmtime(b["ts"] / 1000.0))
        day_rows = [row for row in rows5 if time.strftime("%Y-%m-%d", time.gmtime(row["ts"] / 1000.0)) == day]
        prev_day = time.strftime("%Y-%m-%d", time.gmtime(prev["ts"] / 1000.0))
        if len(day_rows) < 4 or prev_day != day:
            return None, "utc_session_history_or_boundary_insufficient"
        def vwap_through(target_ts):
            acc_pv = acc_v = 0.0
            for row in day_rows:
                if row["ts"] > target_ts: break
                typical = (row["high"] + row["low"] + row["close"]) / 3.0
                acc_pv += typical * row["volume"]
                acc_v += row["volume"]
            return acc_pv / acc_v if acc_v > 0 else None
        vw_prev = vwap_through(prev["ts"])
        vw_cur = vwap_through(b["ts"])
        if not vw_prev or not vw_cur:
            return None, "vwap_unavailable"
        reclaim = prev["close"] <= vw_prev and b["close"] > vw_cur and b["close"] > b["open"]
        sym_r5, btc_r5 = _return(rows5, 5), _return(btc_rows5, 5)
        sym_r15, btc_r15 = _return(rows15, 3), _return(btc_rows15, 3)
        if None in (sym_r5, btc_r5, sym_r15, btc_r15):
            return None, "relative_strength_unavailable"
        rs5 = sym_r5 - btc_r5
        rs15 = sym_r15 - btc_r15
        cfg = self._cfg()
        min_rs5 = float(cfg.get("V702_VWAP_RS_MIN_RS_5M", 0.0000))
        min_rs15 = float(cfg.get("V702_VWAP_RS_MIN_RS_15M", 0.0000))
        if not reclaim:
            return None, "vwap_reclaim_not_confirmed"
        if rs5 < min_rs5:
            return None, "relative_strength_5m_below_floor"
        if rs15 < min_rs15:
            return None, "relative_strength_15m_below_floor"
        vbase = statistics.fmean(x["volume"] for x in rows5[-22:-2]) if len(rows5) >= 22 else 0.0
        vr = b["volume"] / vbase if vbase > 0 else 0.0
        if vr < float(cfg.get("V702_VWAP_RS_MIN_VOLUME_RATIO", 0.80)):
            return None, "volume_ratio_below_floor"
        atr = _atr(rows5, 14)
        if atr is None:
            return None, "atr_unavailable_or_invalid"
        stop = min(x["low"] for x in rows5[-4:]) - 0.10 * atr
        geom = _risk_geometry(b["close"], stop, atr)
        if not geom:
            return None, "risk_geometry_invalid"
        risk, target = geom
        return ({"mode":"VWAP_RECLAIM_RS_5M","tf":"5m","bar":b,"entry":b["close"],"stop":stop,"target":target,"risk":risk,"atr":atr,
            "features":{"vwap_prev":vw_prev,"vwap_current":vw_cur,"rs_5m":rs5,"rs_15m":rs15,"volume_ratio":vr,"signal":"utc_session_vwap_reclaim_plus_rs"}}, "signal")

    def _make_vwap_rs_signal(self, snapshot: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # Backward-compatible test/public API; diagnostic reason is consumed by process_symbol.
        signal, _reason = self._make_vwap_rs_signal_detailed(snapshot)
        return signal

    @staticmethod
    def _efficiency_ratio(rows: Sequence[Dict[str, float]], lookback: int = 10) -> Optional[float]:
        if lookback < 2 or len(rows) < lookback + 1:
            return None
        closes = [float(x["close"]) for x in rows[-(lookback + 1):]]
        denominator = sum(abs(closes[i] - closes[i - 1]) for i in range(1, len(closes)))
        if denominator <= 0:
            return 0.0
        return abs(closes[-1] - closes[0]) / denominator

    @staticmethod
    def rank_relative_strength(market_data_map: Dict[str, Dict[str, Any]], top_n: int = 10) -> Dict[str, Dict[str, float]]:
        """Rank scanned symbols by latest closed 4h return relative to BTC/USDT."""
        if not isinstance(market_data_map, dict) or not market_data_map:
            return {}
        btc_rows = None
        for _snap in market_data_map.values():
            if isinstance(_snap, dict) and _snap.get("df_btc_4h") is not None:
                btc_rows = _closed_rows(_snap.get("df_btc_4h"), 14_400_000)
                if len(btc_rows) >= 2:
                    break
        btc_return = _return(btc_rows or [], 1)
        if btc_return is None:
            return {}
        scores = []
        for symbol, snap in market_data_map.items():
            try:
                if not V702IntradayShadow._symbol_allowed(str(symbol)) or not isinstance(snap, dict):
                    continue
                rows = _closed_rows(snap.get("df_4h"), 14_400_000)
                asset_return = _return(rows, 1)
                if asset_return is None:
                    continue
                relative = asset_return - btc_return
                if math.isfinite(relative):
                    scores.append((str(symbol).upper(), float(relative)))
            except Exception:
                continue
        scores.sort(key=lambda item: (-item[1], item[0]))
        limit = max(1, min(50, int(top_n or 10)))
        return {symbol: {"rank": float(i + 1), "rs_4h": float(score)}
                for i, (symbol, score) in enumerate(scores[:limit])}

    def _make_adaptive_rs_pullback_signal_detailed(self, snapshot: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], str]:
        """15m trend pullback + 5m resumption, for shadow study only."""
        rows4 = _closed_rows(snapshot.get("df_4h"), 14_400_000)
        rows1 = _closed_rows(snapshot.get("df_1h"), 3_600_000)
        rows15 = _closed_rows(snapshot.get("df_15m"), 900_000)
        rows5 = _closed_rows(snapshot.get("df_5m"), 300_000)
        btc4 = _closed_rows(snapshot.get("df_btc_4h"), 14_400_000)
        if min(len(rows4), len(rows1), len(rows15), len(rows5), len(btc4)) < 55:
            return None, "closed_mtf_history_insufficient"

        rank_info = snapshot.get("adaptive_rs_rank") if isinstance(snapshot.get("adaptive_rs_rank"), dict) else {}
        rank = _num(rank_info.get("rank"), None)
        rs4 = _num(rank_info.get("rs_4h"), None)
        if rank is None or rank > 10:
            return None, "relative_strength_not_top_10"
        if rs4 is None or rs4 < 0.003:
            return None, "relative_strength_4h_below_0_30_pct"

        btc_closes = [x["close"] for x in btc4]
        btc_ema20, btc_ema50 = _ema(btc_closes, 20)[-1], _ema(btc_closes, 50)[-1]
        btc_er = self._efficiency_ratio(btc4, 10)
        if btc4[-1]["close"] <= btc_ema50 or btc_ema20 <= btc_ema50:
            return None, "btc_4h_not_bullish_over_ema50"
        if btc_er is None or btc_er < 0.25:
            return None, "btc_4h_efficiency_ratio_below_0_25"

        asset_closes = [x["close"] for x in rows1]
        ema20_1h, ema50_1h = _ema(asset_closes, 20)[-1], _ema(asset_closes, 50)[-1]
        if rows1[-1]["close"] <= ema50_1h or ema20_1h <= ema50_1h:
            return None, "asset_1h_trend_not_bullish_over_ema50"

        closes15 = [x["close"] for x in rows15]
        ema20_15 = _ema(closes15, 20)[-1]
        atr15 = _atr(rows15, 14)
        if atr15 is None:
            return None, "atr_15m_unavailable"
        pullback_rows = rows15[-5:]
        pullback_low = min(x["low"] for x in pullback_rows)
        prior_swing_low = min(x["low"] for x in rows15[-12:-5])
        if pullback_low <= prior_swing_low:
            return None, "15m_pullback_broke_prior_swing_low"
        if pullback_low > ema20_15 + 0.35 * atr15:
            return None, "15m_pullback_not_near_ema20"
        if rows15[-1]["close"] < ema20_15 - 0.20 * atr15 or rows15[-1]["close"] <= rows15[-2]["close"]:
            return None, "15m_pullback_not_reclaiming_ema20"

        atr5 = _atr(rows5, 14)
        if atr5 is None:
            return None, "atr_5m_unavailable"
        b = rows5[-1]
        reference_high = max(x["high"] for x in rows5[-5:-1])
        if b["close"] <= reference_high or b["close"] <= b["open"]:
            return None, "5m_resumption_breakout_not_confirmed"
        volume_base = statistics.fmean(x["volume"] for x in rows5[-22:-2]) if len(rows5) >= 22 else 0.0
        volume_ratio = b["volume"] / volume_base if volume_base > 0 else 0.0
        minimum_volume = max(1.0, _num(self._cfg().get("V702_ADAPTIVE_RS_MIN_VOLUME_RATIO"), 1.10) or 1.10)
        if volume_ratio < minimum_volume:
            return None, "5m_volume_ratio_below_floor"
        chase_atr = (b["close"] - reference_high) / max(atr5, 1e-12)
        max_chase = max(0.1, _num(self._cfg().get("V702_ADAPTIVE_RS_MAX_CHASE_ATR"), 0.60) or 0.60)
        if chase_atr > max_chase:
            return None, "5m_breakout_chase_atr_above_ceiling"

        entry = b["close"]
        structural_stop = pullback_low - 0.10 * atr15
        min_stop_distance = 1.50 * atr15
        stop = min(structural_stop, entry - min_stop_distance)
        risk = entry - stop
        risk_pct = 100.0 * risk / max(entry, 1e-12)
        risk_atr = risk / max(atr15, 1e-12)
        if stop <= 0 or risk_pct < 0.12 or risk_pct > 2.5 or risk_atr < 1.5 or risk_atr > 3.5:
            return None, "adaptive_stop_geometry_outside_1_5_to_3_5_atr"
        target = entry + 1.5 * risk
        return ({
            "mode": "ADAPTIVE_RS_PULLBACK_15M", "tf": "5m", "bar": b,
            "entry": entry, "stop": stop, "target": target, "risk": risk,
            "atr": atr15,
            "features": {
                "rank_4h": rank, "rs_4h": rs4, "btc_4h_efficiency_ratio": btc_er,
                "btc_4h_close": btc4[-1]["close"], "btc_4h_ema50": btc_ema50,
                "asset_1h_ema20": ema20_1h, "asset_1h_ema50": ema50_1h,
                "asset_15m_ema20": ema20_15, "pullback_low": pullback_low,
                "prior_swing_low": prior_swing_low, "atr_15m": atr15,
                "risk_atr_15m": risk_atr, "volume_ratio_5m": volume_ratio,
                "chase_atr_5m": chase_atr, "target_rr": 1.5,
                "exit_policy": "50_PERCENT_AT_1_5R_THEN_CONFIRMED_15M_SWING_TRAIL",
                "experiment": "SHADOW_ONLY_NO_ORDERS",
            },
        }, "signal")

    def _make_adaptive_rs_pullback_signal(self, snapshot: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        signal, _reason = self._make_adaptive_rs_pullback_signal_detailed(snapshot)
        return signal

    @staticmethod
    def _confirmed_15m_trailing_stops(rows15: Sequence[Dict[str, float]]) -> List[Tuple[int, float]]:
        """Return confirmed 15m swing-low stops; each only becomes known after its right bar closes."""
        out: List[Tuple[int, float]] = []
        for i in range(2, len(rows15)):
            pivot = rows15[i - 1]
            if pivot["low"] < rows15[i - 2]["low"] and pivot["low"] <= rows15[i]["low"]:
                atr = _atr(rows15[:i + 1], 14)
                if atr and atr > 0:
                    stop = float(pivot["low"]) - 0.10 * float(atr)
                    if stop > 0:
                        out.append((int(rows15[i]["close_ts"]), stop))
        return out

    def _record_evaluations(self, symbol: str, evaluations: Sequence[Dict[str, Any]]) -> int:
        """Persist one deduplicated evaluation per closed strategy bar."""
        if not evaluations:
            return 0
        inserted_total = 0
        try:
            with self._db() as conn:
                for item in evaluations:
                    mode = str(item.get("strategy_mode", "") or "")
                    tf = str(item.get("timeframe", "") or "")
                    bar_ts = int(item.get("bar_ts_ms", 0) or 0)
                    if mode not in STRATEGIES or not tf or bar_ts <= 0:
                        continue
                    material = f"{str(symbol).upper()}|{mode}|{tf}|{bar_ts}"
                    evaluation_id = hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]
                    cur = conn.execute("""INSERT OR IGNORE INTO v702_intraday_shadow_evaluations
                        (evaluation_id,symbol,strategy_mode,timeframe,bar_ts_ms,evaluated_ts,outcome,reason,cost_pct,post_cost_viable,quote_volume_24h,features_json)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (evaluation_id,str(symbol).upper(),mode,tf,bar_ts,time.time(),str(item.get("outcome","REJECT")),
                         str(item.get("reason","unspecified"))[:120],_num(item.get("cost_pct"),None),
                         (1 if bool(item.get("post_cost_viable")) else 0) if item.get("post_cost_viable") is not None else None,
                         _num(item.get("quote_volume_24h"),None),_json(item.get("features") or {})))
                    inserted_total += max(0, int(cur.rowcount or 0))
                max_rows = int(max(1000, min(200000, _num(self._cfg().get("V702_INTRADAY_SHADOW_MAX_ROWS"), 50000) or 50000)))
                total = int(conn.execute("SELECT COUNT(*) FROM v702_intraday_shadow_evaluations").fetchone()[0])
                if total > max_rows:
                    conn.execute("DELETE FROM v702_intraday_shadow_evaluations WHERE evaluation_id IN (SELECT evaluation_id FROM v702_intraday_shadow_evaluations ORDER BY evaluated_ts ASC LIMIT ?)", (total - max_rows,))
        except Exception:
            return inserted_total
        return inserted_total

    def _assess_liquidation_spot_absorption(
        self, snapshot: Dict[str, Any], symbol: Optional[str] = None, now_ms: Optional[int] = None
    ) -> Dict[str, Any]:
        """Validate external liquidation/Spot evidence; never fabricate missing feeds.

        The current A75/A76 package has no Futures liquidation/OI/Funding provider.
        This contract is optional and Shadow-only; absent/stale evidence is UNAVAILABLE.
        """
        context = snapshot.get("liquidation_spot_absorption") if isinstance(snapshot, dict) else None
        if not isinstance(context, dict):
            return {"status": "UNAVAILABLE", "reason": "provider_not_configured",
                    "evidence_contract": "LSA_V1", "score": None}
        required = (
            "source", "observed_at_ms", "symbol", "long_liquidations_usdt_15m",
            "baseline_long_liquidations_usdt_15m", "open_interest_change_pct_15m",
            "funding_rate_current", "funding_rate_previous",
            "spot_buy_volume_usdt_5m", "spot_sell_volume_usdt_5m", "reclaimed_support",
        )
        missing = [key for key in required if key not in context]
        if missing:
            return {"status": "UNAVAILABLE", "reason": "incomplete_provider_schema",
                    "missing_fields": missing, "evidence_contract": "LSA_V1", "score": None}
        try:
            observed = int(context.get("observed_at_ms"))
            now = int(now_ms if now_ms is not None else time.time() * 1000)
            max_age_ms = int(max(30.0, min(300.0, _num(self._cfg().get("V702_INTRADAY_LSA_MAX_AGE_SEC"), 120.0) or 120.0)) * 1000)
            age_ms = now - observed
            expected_symbol = str(symbol or snapshot.get("symbol") or "").upper().strip()
            actual_symbol = str(context.get("symbol") or "").upper().strip()
            source = str(context.get("source") or "").strip()[:80]
            numeric_keys = (
                "long_liquidations_usdt_15m", "baseline_long_liquidations_usdt_15m",
                "open_interest_change_pct_15m", "funding_rate_current", "funding_rate_previous",
                "spot_buy_volume_usdt_5m", "spot_sell_volume_usdt_5m",
            )
            values = {key: _num(context.get(key), None) for key in numeric_keys}
            if (not source or not actual_symbol or (expected_symbol and actual_symbol != expected_symbol)
                    or age_ms < -5000 or age_ms > max_age_ms
                    or any(value is None for value in values.values())
                    or values["long_liquidations_usdt_15m"] < 0
                    or values["baseline_long_liquidations_usdt_15m"] <= 0
                    or values["spot_buy_volume_usdt_5m"] < 0
                    or values["spot_sell_volume_usdt_5m"] < 0
                    or not isinstance(context.get("reclaimed_support"), bool)):
                return {"status": "UNAVAILABLE", "reason": "invalid_identity_freshness_or_values",
                        "source": source or None, "age_ms": age_ms if "age_ms" in locals() else None,
                        "evidence_contract": "LSA_V1", "score": None}
            liquidation_ratio = values["long_liquidations_usdt_15m"] / values["baseline_long_liquidations_usdt_15m"]
            spot_total = values["spot_buy_volume_usdt_5m"] + values["spot_sell_volume_usdt_5m"]
            buy_share = values["spot_buy_volume_usdt_5m"] / spot_total if spot_total > 0 else 0.0
            thresholds = {
                "liquidation_burst_ratio_min": _num(self._cfg().get("V702_INTRADAY_LSA_MIN_LIQUIDATION_BURST_RATIO"), 2.5) or 2.5,
                "open_interest_change_pct_max": _num(self._cfg().get("V702_INTRADAY_LSA_MAX_OI_CHANGE_PCT"), -2.0) or -2.0,
                "spot_buy_share_min": _num(self._cfg().get("V702_INTRADAY_LSA_MIN_SPOT_BUY_SHARE"), 0.55) or 0.55,
            }
            tests = {
                "liquidation_burst": liquidation_ratio >= thresholds["liquidation_burst_ratio_min"],
                "open_interest_contraction": values["open_interest_change_pct_15m"] <= thresholds["open_interest_change_pct_max"],
                "funding_decreased": values["funding_rate_current"] <= values["funding_rate_previous"],
                "spot_buy_flow": buy_share >= thresholds["spot_buy_share_min"],
                "support_reclaimed": bool(context.get("reclaimed_support")),
            }
            passed = sum(1 for ok in tests.values() if ok)
            return {
                "status": "QUALIFIED" if all(tests.values()) else "NOT_CONFIRMED",
                "reason": "all_lsa_conditions_met" if all(tests.values()) else "one_or_more_conditions_not_met",
                "evidence_contract": "LSA_V1", "source": source, "symbol": actual_symbol,
                "age_ms": age_ms, "liquidation_burst_ratio": round(liquidation_ratio, 4),
                "open_interest_change_pct_15m": values["open_interest_change_pct_15m"],
                "funding_rate_current": values["funding_rate_current"],
                "funding_rate_previous": values["funding_rate_previous"],
                "spot_buy_share_5m": round(buy_share, 4), "tests": tests,
                "conditions_passed": passed, "conditions_total": len(tests),
                "thresholds": thresholds, "score": passed / len(tests),
                "interpretation": "evidence_consistent_with_forced_long_unwind_and_spot_buy_flow; buyer_identity_not_proven",
            }
        except Exception as exc:
            return {"status": "UNAVAILABLE", "reason": f"provider_validation_error:{type(exc).__name__}",
                    "evidence_contract": "LSA_V1", "score": None}

    def pending_micro_alerts(self, limit: int = 4, max_age_sec: float = 180.0) -> List[Dict[str, Any]]:
        """Return fresh alert-outbox items; expire stale items instead of sending late setups."""
        limit = max(1, min(10, int(limit or 4)))
        max_age = max(30.0, min(600.0, _num(max_age_sec, 180.0) or 180.0))
        now = time.time()
        try:
            with self._db() as conn:
                conn.execute("UPDATE v702_intraday_shadow_alerts SET state='EXPIRED',updated_ts=?,note='alert_ttl_expired' WHERE state='PENDING' AND created_ts<?", (now, now-max_age))
                # Retain unresolved PENDING alerts; trim only old terminal/queued
                # research rows when the outbox exceeds its bounded capacity.
                max_alert_rows = int(max(1000, min(50000, _num(self._cfg().get("V702_INTRADAY_SHADOW_ALERT_MAX_ROWS"), 10000) or 10000)))
                alert_total = int(conn.execute("SELECT COUNT(*) FROM v702_intraday_shadow_alerts").fetchone()[0])
                alert_excess = max(0, alert_total - max_alert_rows)
                if alert_excess:
                    conn.execute("DELETE FROM v702_intraday_shadow_alerts WHERE alert_id IN (SELECT alert_id FROM v702_intraday_shadow_alerts WHERE state!='PENDING' ORDER BY created_ts ASC LIMIT ?)", (alert_excess,))
                rows = conn.execute("SELECT sample_id,symbol,strategy_mode,signal_ts_ms,created_ts,payload_json FROM v702_intraday_shadow_alerts WHERE state='PENDING' AND created_ts>=? ORDER BY created_ts ASC LIMIT ?", (now-max_age, limit)).fetchall()
            out = []
            for sample_id, sym, mode, signal_ts, created, payload in rows:
                try: body = json.loads(payload or "{}")
                except Exception: body = {}
                out.append({"sample_id": sample_id, "symbol": sym, "strategy_mode": mode,
                            "signal_ts_ms": int(signal_ts), "created_ts": float(created), "payload": body})
            return out
        except Exception:
            return []

    def mark_micro_alert_queued(self, sample_id: str, note: str = "telegram_durable_outbox_accepted") -> bool:
        """Mark a Shadow alert only after TelegramDispatcher accepts durable enqueue."""
        try:
            with self._db() as conn:
                cur = conn.execute("UPDATE v702_intraday_shadow_alerts SET state='QUEUED',updated_ts=?,note=? WHERE sample_id=? AND state='PENDING'", (time.time(), str(note or "")[:120], str(sample_id or "")))
                return bool(cur.rowcount)
        except Exception:
            return False

    def _record_signal(self, symbol: str, signal: Dict[str, Any], snapshot: Dict[str, Any]) -> bool:
        entry, stop, _initial_target, risk = (float(signal[k]) for k in ("entry", "stop", "target", "risk"))
        risk_pct = 100.0 * risk / entry
        cfg = self._cfg()
        mode = str(signal.get("mode", ""))
        adaptive = mode == "ADAPTIVE_RS_PULLBACK_15M"
        cost_pct = self._cost_pct(entry, snapshot)
        fee_side = max(0.0, _num(cfg.get("TAKER_FEE_PCT"), 0.10) or 0.0)
        slip_side = max(0.0, _num(cfg.get("V702_INTRADAY_SLIPPAGE_PER_SIDE_PCT"), 0.05) or 0.0)
        spread = _num(snapshot.get("spread_pct"), None)
        if spread is None:
            spread = max(0.0, _num(cfg.get("V702_INTRADAY_SPREAD_FALLBACK_PCT"), 0.15) or 0.0)
        # One full-size round trip already prices 100% of the exited quantity.
        # Splitting that exit into 50% + 50% does not double the proportional
        # exchange fee or spread; do not charge an artificial second half-roundtrip.
        extra_partial_exit_cost = 0.0
        desired_net_pct = max(0.0, _num(cfg.get("V702_INTRADAY_MIN_NET_PROFIT_PCT"), 0.10) or 0.0)
        minimum_net_rr = max(0.0, _num(cfg.get("V702_INTRADAY_MIN_NET_RR"), 0.25) or 0.0)
        fee_coverage = max(1.0, _num(cfg.get("V702_INTRADAY_TP1_FEE_COVERAGE"), 2.5) or 2.5)
        target_rr_cap = max(1.0, min(5.0, _num(cfg.get("V702_INTRADAY_MAX_TARGET_RR"), 3.0) or 3.0))
        target_buffer_rr = max(0.0, _num(cfg.get("V702_INTRADAY_TARGET_BUFFER_R"), 0.03) or 0.0)
        if adaptive:
            target_rr = 1.5
            # The 50% TP1 cash-out must itself cover the configured net floor and
            # multiple of estimated round-trip fees; runner upside is not assumed.
            partial_gross_pct = 0.5 * target_rr * risk_pct
            fee_roundtrip_pct = 2.0 * fee_side
            target_net_pct = partial_gross_pct - cost_pct
            target_net_r = 0.5 * target_rr - cost_pct / max(risk_pct, 1e-12)
            required_partial_cost_coverage = fee_coverage * fee_roundtrip_pct
            post_cost_viable = bool(
                partial_gross_pct + 1e-9 >= desired_net_pct + required_partial_cost_coverage
                and target_net_pct + 1e-9 >= desired_net_pct
                and target_net_r + 1e-9 >= minimum_net_rr
            )
            target = entry + risk * target_rr
            required_rr = target_rr
        else:
            required_rr = max(1.0, (cost_pct + desired_net_pct) / max(risk_pct, 1e-12),
                              cost_pct / max(risk_pct, 1e-12) + minimum_net_rr,
                              fee_coverage * (2.0 * fee_side) / max(risk_pct, 1e-12))
            target_rr = min(target_rr_cap, required_rr + target_buffer_rr)
            target = entry + risk * target_rr
            target_net_pct = 100.0 * (target - entry) / max(entry, 1e-12) - cost_pct
            target_net_r = target_rr - cost_pct / max(risk_pct, 1e-12)
            post_cost_viable = bool(
                required_rr + target_buffer_rr <= target_rr_cap + 1e-9
                and target_net_pct + 1e-9 >= desired_net_pct
                and target_net_r + 1e-9 >= minimum_net_rr
            )
        bar = signal["bar"]
        signal_close_ms = int(float(bar["close_ts"]))
        material = f"{symbol}|{mode}|{signal_close_ms}"
        sample_id = hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]
        qv = _num(snapshot.get("quote_vol_24h"), None)
        tier = str(snapshot.get("tier") or "")[:24]
        features = dict(signal.get("features") or {})
        features.update({
            "entry":entry,"stop":stop,"target":target,"risk_pct":risk_pct,"cost_pct":cost_pct,
            "target_rr":target_rr,"required_target_rr_before_cap":required_rr,
            "target_rr_capped_for_research":bool(not adaptive and required_rr + target_buffer_rr > target_rr_cap),
            "minimum_net_profit_pct_target":desired_net_pct,
            "target_net_pct_after_costs":target_net_pct,"target_net_r_after_costs":target_net_r,
            "post_cost_target_viable":post_cost_viable,
            "partial_tp1_extra_exit_cost_pct":extra_partial_exit_cost,
            "quote_volume_24h":qv,"macro_regime":snapshot.get("macro_regime"),
            "experiment":"SHADOW_ONLY_NO_ORDERS",
            "higher_timeframe_bullish_required":bool(adaptive),
            "crash_guard":"BTC_5M_15MIN_SHOCK_ONLY",
        })
        try:
            with self._db() as conn:
                cur = conn.execute("""INSERT OR IGNORE INTO v702_intraday_shadow_samples
                    (sample_id,symbol,strategy_mode,timeframe,signal_ts_ms,created_ts,entry,stop,target,risk_unit,risk_pct,
                     last_candle_ts_ms,bars_seen,status,cost_pct,quote_volume_24h,tier,features_json,note)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (sample_id,symbol,mode,signal["tf"],signal_close_ms,time.time(),entry,stop,target,risk,risk_pct,
                     signal_close_ms - 60_000,0,"PENDING",cost_pct,qv,tier,_json(features),
                     "virtual_entry_at_closed_signal_bar;adaptive_partial_exit" if adaptive else "virtual_entry_at_closed_signal_bar"))
                inserted = cur.rowcount > 0
                if inserted and mode in {"MICRO_MOMENTUM_1M", "MICRO_SWEEP_RECLAIM_1M", "MICRO_PULLBACK_RECLAIM_1M"} and bool(cfg.get("V702_INTRADAY_SHADOW_TELEGRAM_ALERTS_ENABLE", True)):
                    now_alert = time.time()
                    cooldown = max(30.0, min(900.0, _num(cfg.get("V702_INTRADAY_SHADOW_ALERT_COOLDOWN_SEC"), 180.0) or 180.0))
                    recent = conn.execute("SELECT 1 FROM v702_intraday_shadow_alerts WHERE symbol=? AND created_ts>=? AND state IN ('PENDING','QUEUED') LIMIT 1", (symbol, now_alert-cooldown)).fetchone()
                    if not recent:
                        alert_payload = {
                            "sample_id": sample_id,
                            "entry": entry, "stop": stop, "target": target, "risk_pct": risk_pct,
                            "cost_pct": cost_pct, "target_net_pct_after_costs": target_net_pct,
                            "target_net_r_after_costs": target_net_r, "post_cost_target_viable": post_cost_viable,
                            "quote_volume_24h": qv, "tier": tier,
                            "liquidation_spot_absorption": features.get("liquidation_spot_absorption", {"status":"UNAVAILABLE","reason":"provider_not_configured"}),
                            "economic_status": "VIABLE_AFTER_MODELED_COSTS" if post_cost_viable else "TECHNICAL_ONLY_COST_GATE_NOT_MET",
                            "timeframe": str(signal.get("tf", "1m")),
                            "alert_mode": "MONITOR_ONLY_NO_ORDERS",
                        }
                        alert_id = hashlib.sha256(("MICRO_SHADOW_ALERT|" + sample_id).encode("utf-8")).hexdigest()[:32]
                        conn.execute("""INSERT OR IGNORE INTO v702_intraday_shadow_alerts
                            (alert_id,sample_id,symbol,strategy_mode,signal_ts_ms,created_ts,state,payload_json,updated_ts,note)
                            VALUES(?,?,?,?,?,?, 'PENDING',?,?,?)""",
                            (alert_id,sample_id,symbol,mode,signal_close_ms,now_alert,_json(alert_payload),now_alert,"new_closed_bar_shadow_signal"))
                max_rows = int(max(1000, min(200000, _num(self._cfg().get("V702_INTRADAY_SHADOW_MAX_ROWS"), 50000) or 50000)))
                if inserted:
                    self._prune_sample_rows(conn, max_rows)
            return inserted
        except Exception:
            return False

    def _update_pending(
        self,
        symbol: str,
        closed_1m_rows: Sequence[Dict[str, float]],
        closed_15m_rows: Sequence[Dict[str, float]] = (),
    ) -> int:
        cfg = self._cfg()
        max_bars = int(max(5, min(120, _num(cfg.get("V702_INTRADAY_SHADOW_MAX_HOLD_BARS"), 30) or 30)))
        trailing_stops = self._confirmed_15m_trailing_stops(closed_15m_rows or ())
        updated = 0
        try:
            with self._db() as conn:
                pending = conn.execute("""SELECT sample_id,strategy_mode,timeframe,entry,stop,target,risk_unit,risk_pct,
                    last_candle_ts_ms,bars_seen,cost_pct,signal_ts_ms,tp1_hit,partial_realized_r,trailing_stop
                    FROM v702_intraday_shadow_samples WHERE symbol=? AND status='PENDING' ORDER BY signal_ts_ms ASC""", (symbol,)).fetchall()
                for rec in pending:
                    (sid, strategy_mode, timeframe, entry, stop, target, risk, risk_pct, last_ts, bars_seen,
                     cost_pct, signal_ts, tp1_hit, partial_realized_r, trailing_stop) = rec
                    adaptive = str(strategy_mode) == "ADAPTIVE_RS_PULLBACK_15M"
                    state = None
                    exit_price = gross_r = net_r = net_pct = None
                    last_seen = int(last_ts or 0)
                    count = int(bars_seen or 0)
                    has_partial = bool(tp1_hit) if adaptive else False
                    partial_r = float(partial_realized_r or 0.0) if has_partial else 0.0
                    current_trail = _num(trailing_stop, None)
                    for bar in closed_1m_rows:
                        bar_ts = int(bar["ts"])
                        if bar_ts < int(signal_ts) or bar_ts <= last_seen:
                            continue
                        # Do not resolve a simulated trade across an unobserved
                        # 1m interval: the missing candle could have touched SL.
                        _expected_from = max(int(last_seen or 0), int(signal_ts or 0))
                        if bool(bar.get("gap_before")) or (_expected_from > 0 and bar_ts - _expected_from > 90_000):
                            state = "AMBIGUOUS_DATA_GAP"
                            exit_price = None
                            gross_r = net_r = net_pct = None
                            last_seen = bar_ts
                            break
                        last_seen = bar_ts
                        count += 1
                        # Only a swing low confirmed before this 1m bar can protect it.
                        if adaptive and has_partial:
                            usable = [level for confirm_ts, level in trailing_stops if int(signal_ts) < confirm_ts <= bar_ts]
                            if usable:
                                current_trail = max(float(stop), float(current_trail or stop), max(usable))
                        active_stop = max(float(stop), float(current_trail or stop)) if adaptive and has_partial else float(stop)
                        hit_sl = float(bar["low"]) <= active_stop
                        hit_tp = float(bar["high"]) >= float(target)
                        if not has_partial:
                            if hit_sl:  # conservative SL-first, including same-candle touch
                                state, exit_price, gross_r = "SL", active_stop, -1.0
                                break
                            if hit_tp:
                                if adaptive:
                                    has_partial = True
                                    partial_r = 0.5 * ((float(target) - float(entry)) / max(float(risk), 1e-12))
                                    current_trail = max(float(stop), float(current_trail or stop))
                                    if count >= max_bars:
                                        state, exit_price = "TIMEOUT", float(bar["close"])
                                        gross_r = partial_r + 0.5 * ((exit_price - float(entry)) / max(float(risk), 1e-12))
                                        break
                                    continue
                                state, exit_price = "TP1", float(target)
                                gross_r = (float(target) - float(entry)) / max(float(risk), 1e-12)
                                break
                        else:
                            if hit_sl:
                                state, exit_price = "TRAILING_EXIT", active_stop
                                gross_r = partial_r + 0.5 * ((float(exit_price) - float(entry)) / max(float(risk), 1e-12))
                                break
                            if count >= max_bars:
                                state, exit_price = "TIMEOUT", float(bar["close"])
                                gross_r = partial_r + 0.5 * ((exit_price - float(entry)) / max(float(risk), 1e-12))
                                break
                        if not adaptive and count >= max_bars:
                            state, exit_price = "TIMEOUT", float(bar["close"])
                            gross_r = (exit_price - float(entry)) / max(float(risk), 1e-12)
                            break
                        if adaptive and count >= max_bars:
                            state, exit_price = "TIMEOUT", float(bar["close"])
                            if has_partial:
                                gross_r = partial_r + 0.5 * ((exit_price - float(entry)) / max(float(risk), 1e-12))
                            else:
                                gross_r = (exit_price - float(entry)) / max(float(risk), 1e-12)
                            break
                    if state:
                        if str(state).startswith("AMBIGUOUS"):
                            net_r = net_pct = None
                        else:
                            cost_r = float(cost_pct) / max(float(risk_pct), 1e-12)
                            net_r = float(gross_r) - cost_r
                            net_pct = net_r * float(risk_pct)
                        resolved_epoch = time.time()
                        outcome_note = ("DATA_GAP_OUTCOME_UNRESOLVED_NO_EDGE_CREDIT" if str(state).startswith("AMBIGUOUS") else
                                        "SL_FIRST_IF_AMBIGUOUS;UNIFIED_ROUNDTRIP_COST_DEDUCTED" + (";50PCT_TP1_1_5R_TRAIL_15M" if adaptive and has_partial else ""))
                        conn.execute("""UPDATE v702_intraday_shadow_samples
                            SET last_candle_ts_ms=?,bars_seen=?,status=?,exit_price=?,gross_r=?,net_r=?,net_pct=?,
                                resolved_ts=?,note=?,tp1_hit=?,partial_realized_r=?,trailing_stop=?
                            WHERE sample_id=? AND status='PENDING'""",
                            (last_seen,count,state,exit_price,gross_r,net_r,net_pct,resolved_epoch,
                             outcome_note,1 if has_partial else 0,partial_r,current_trail,sid))
                        # Persist a result notification in the same transaction as the sample resolution.
                        # Only 1m micro samples with an initial alert record receive this follow-up.
                        if str(strategy_mode) in {"MICRO_MOMENTUM_1M", "MICRO_SWEEP_RECLAIM_1M", "MICRO_PULLBACK_RECLAIM_1M"}:
                            initial_alert = conn.execute("SELECT state FROM v702_intraday_shadow_alerts WHERE sample_id=?", (sid,)).fetchone()
                            if initial_alert and str(initial_alert[0]) in {"PENDING", "QUEUED"} and bool(cfg.get("V702_INTRADAY_SHADOW_OUTCOME_TELEGRAM_ENABLE", True)):
                                outcome_id = hashlib.sha256(("MICRO_SHADOW_OUTCOME|" + str(sid)).encode("utf-8")).hexdigest()[:32]
                                outcome_payload = {
                                    "sample_id": str(sid), "symbol": str(symbol), "strategy_mode": str(strategy_mode),
                                    "timeframe": str(timeframe or "1m"), "signal_ts_ms": int(signal_ts),
                                    "resolved_ts": resolved_epoch, "outcome": str(state),
                                    "entry": float(entry), "stop": float(stop), "target": float(target),
                                    "exit_price": None if exit_price is None else float(exit_price),
                                    "gross_r": None if gross_r is None else float(gross_r),
                                    "net_r": None if net_r is None else float(net_r),
                                    "net_pct": None if net_pct is None else float(net_pct),
                                    "cost_pct": float(cost_pct), "bars_seen": int(count),
                                    "ambiguous": bool(str(state).startswith("AMBIGUOUS")),
                                    "mode": "MONITOR_ONLY_NO_ORDERS",
                                }
                                conn.execute("""INSERT OR IGNORE INTO v702_intraday_shadow_outcomes
                                    (outcome_id,sample_id,symbol,strategy_mode,timeframe,signal_ts_ms,resolved_ts,outcome,
                                     exit_price,gross_r,net_r,net_pct,cost_pct,bars_seen,state,payload_json,updated_ts,note)
                                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,'PENDING',?,?,?)""",
                                    (outcome_id,str(sid),str(symbol),str(strategy_mode),str(timeframe or "1m"),int(signal_ts),
                                     resolved_epoch,str(state),exit_price,gross_r,net_r,net_pct,float(cost_pct),int(count),
                                     _json(outcome_payload),resolved_epoch,outcome_note[:180]))
                                # Bounded cleanup only removes already queued terminal notifications.
                                outbox_total = int(conn.execute("SELECT COUNT(*) FROM v702_intraday_shadow_outcomes").fetchone()[0])
                                if outbox_total > 20000:
                                    conn.execute("DELETE FROM v702_intraday_shadow_outcomes WHERE sample_id IN (SELECT sample_id FROM v702_intraday_shadow_outcomes WHERE state='QUEUED' ORDER BY resolved_ts ASC LIMIT ?)", (outbox_total-18000,))
                        updated += 1
                    else:
                        conn.execute("""UPDATE v702_intraday_shadow_samples
                            SET last_candle_ts_ms=?,bars_seen=?,tp1_hit=?,partial_realized_r=?,trailing_stop=?
                            WHERE sample_id=? AND status='PENDING'""",
                            (last_seen,count,1 if has_partial else 0,partial_r,current_trail,sid))
        except Exception:
            return updated
        return updated

    def process_symbol(self, symbol: str, df_1m: Any, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        result: Dict[str, Any] = {"signals":0,"resolved":0,"pending":0,"skipped":0,"evaluations":0,"rejections":0,"engine_cycle":{},"reject_reasons":{}}
        cfg = self._cfg()
        if not bool(cfg.get("V702_INTRADAY_SHADOW_ENABLE", True)) or bool(cfg.get("V702_INTRADAY_SHADOW_LIVE_ENABLE", False)):
            result["skipped"] = 1; result["skip_reason"] = "shadow_lane_disabled_or_live_flag_set"; return result
        if self._is_forbidden(symbol):
            result["skipped"] = 1; result["skip_reason"] = "forbidden_asset"; return result
        symbol = str(symbol).upper().strip()
        qv = _num(snapshot.get("quote_vol_24h"), 0.0) or 0.0
        min_qv = max(0.0, _num(cfg.get("V702_INTRADAY_SHADOW_MIN_QUOTE_VOLUME_USDT"), 1_000_000.0) or 0.0)
        rows = _closed_rows(df_1m, 60_000)
        min_bars = max(35, int(cfg.get("V702_INTRADAY_SHADOW_MIN_1M_CANDLES", 40)))
        if len(rows) < min_bars or qv < min_qv:
            reason = "quote_volume_below_floor" if qv < min_qv else "closed_1m_bars_insufficient"
            ts_now_ms = int(time.time() * 1000)
            # Bucket invalid/missing-bar observations to avoid repeated scan overcounting.
            base_1m_ts = int(rows[-1]["close_ts"]) if rows else (ts_now_ms // 60_000) * 60_000
            rows5 = _closed_rows(snapshot.get("df_5m"), 300_000)
            base_5m_ts = int(rows5[-1]["close_ts"]) if rows5 else (ts_now_ms // 300_000) * 300_000
            items = []
            for mode in STRATEGIES:
                tf = "5m" if mode in {"VWAP_RECLAIM_RS_5M", "ADAPTIVE_RS_PULLBACK_15M"} else "1m"
                items.append({"strategy_mode":mode,"timeframe":tf,"bar_ts_ms":base_5m_ts if tf=="5m" else base_1m_ts,
                              "outcome":"SKIP","reason":reason,"quote_volume_24h":qv})
            result["evaluations"] = self._record_evaluations(symbol, items)
            # Preserve distinct per-engine cycle metrics even when data/volume
            # prevents indicator evaluation. These are SKIP observations, not signals.
            for mode in STRATEGIES:
                result["engine_cycle"][mode] = {
                    "evaluated": 1, "signals": 0, "rejected": 0, "blocked": 0, "skipped": 1,
                    "reject_reasons": {reason: 1},
                }
            result["skipped"] = 1; result["skip_reason"] = reason
            result["pending"] = self._count_pending(symbol)
            return result

        rows15 = _closed_rows(snapshot.get("df_15m"), 900_000)
        result["resolved"] = self._update_pending(symbol, rows, rows15)
        blocked, block_reason = self._crash_guard(snapshot)
        evals: List[Dict[str, Any]] = []
        signals: List[Dict[str, Any]] = []
        diag: Dict[str, str] = {}
        rows5 = _closed_rows(snapshot.get("df_5m"), 300_000)
        bar_1m = int(rows[-1]["close_ts"]) if rows else (int(time.time() * 1000) // 60_000) * 60_000
        bar_5m = int(rows5[-1]["close_ts"]) if rows5 else (int(time.time() * 1000) // 300_000) * 300_000

        if blocked:
            for mode in STRATEGIES:
                tf = "5m" if mode in {"VWAP_RECLAIM_RS_5M", "ADAPTIVE_RS_PULLBACK_15M"} else "1m"
                evals.append({"strategy_mode":mode,"timeframe":tf,"bar_ts_ms":bar_5m if tf=="5m" else bar_1m,
                              "outcome":"BLOCKED","reason":str(block_reason or "btc_15m_crash_guard"),"quote_volume_24h":qv})
        else:
            one_min_signals = self._make_signals_1m(rows, diagnostics=diag)
            for _micro_signal in one_min_signals:
                _micro_features = dict(_micro_signal.get("features") or {})
                _micro_features["liquidation_spot_absorption"] = self._assess_liquidation_spot_absorption(snapshot, symbol=symbol)
                _micro_signal["features"] = _micro_features
            signals.extend(one_min_signals)
            vwap_signal, vwap_reason = self._make_vwap_rs_signal_detailed(snapshot)
            if vwap_signal:
                signals.append(vwap_signal)
            diag["VWAP_RECLAIM_RS_5M"] = vwap_reason
            adaptive_signal, adaptive_reason = self._make_adaptive_rs_pullback_signal_detailed(snapshot)
            if adaptive_signal:
                signals.append(adaptive_signal)
            diag["ADAPTIVE_RS_PULLBACK_15M"] = adaptive_reason
            signal_by_mode = {str(x.get("mode")):x for x in signals}
            for mode in STRATEGIES:
                sig = signal_by_mode.get(mode)
                tf = "5m" if mode in {"VWAP_RECLAIM_RS_5M", "ADAPTIVE_RS_PULLBACK_15M"} else "1m"
                bar_ts = bar_5m if tf == "5m" else bar_1m
                if sig:
                    cost_pct = self._cost_pct(float(sig["entry"]), snapshot)
                    risk_pct = 100.0 * float(sig["risk"]) / max(float(sig["entry"]), 1e-12)
                    desired_net_pct = max(0.0, _num(cfg.get("V702_INTRADAY_MIN_NET_PROFIT_PCT"), 0.10) or 0.0)
                    min_net_rr = max(0.0, _num(cfg.get("V702_INTRADAY_MIN_NET_RR"), 0.25) or 0.0)
                    fee_side = max(0.0, _num(cfg.get("TAKER_FEE_PCT"), 0.10) or 0.0)
                    fee_coverage = max(1.0, _num(cfg.get("V702_INTRADAY_TP1_FEE_COVERAGE"), 2.5) or 2.5)
                    cap = max(1.0, min(5.0, _num(cfg.get("V702_INTRADAY_MAX_TARGET_RR"), 3.0) or 3.0))
                    buffer = max(0.0, _num(cfg.get("V702_INTRADAY_TARGET_BUFFER_R"), 0.03) or 0.0)
                    if mode == "ADAPTIVE_RS_PULLBACK_15M":
                        target_rr = 1.5
                        # cost_pct is one complete entry + 100%-exit round trip.
                        # The 50/50 exit split changes execution timing, not the
                        # total proportional fee/spread basis.
                        total_cost = cost_pct
                        partial_gross_pct = 0.5 * target_rr * risk_pct
                        target_net_pct = partial_gross_pct - total_cost
                        target_net_r = 0.5 * target_rr - total_cost / max(risk_pct, 1e-12)
                        viable = bool(
                            partial_gross_pct + 1e-9 >= desired_net_pct + fee_coverage * 2.0 * fee_side
                            and target_net_pct + 1e-9 >= desired_net_pct
                            and target_net_r + 1e-9 >= min_net_rr
                        )
                        required_rr = target_rr
                    else:
                        required_rr = max(1.0, (cost_pct + desired_net_pct) / max(risk_pct, 1e-12),
                                          cost_pct / max(risk_pct, 1e-12) + min_net_rr,
                                          fee_coverage * (2.0 * fee_side) / max(risk_pct, 1e-12))
                        target_rr = min(cap, required_rr + buffer)
                        target_net_pct = 100.0 * float(sig["risk"]) * target_rr / max(float(sig["entry"]), 1e-12) - cost_pct
                        target_net_r = target_rr - cost_pct / max(risk_pct, 1e-12)
                        viable = bool(required_rr + buffer <= cap + 1e-9 and target_net_pct + 1e-9 >= desired_net_pct and target_net_r + 1e-9 >= min_net_rr)
                    features = dict(sig.get("features") or {})
                    features.update({"cost_pct":cost_pct,"target_net_pct_after_costs":target_net_pct,
                                     "target_net_r_after_costs":target_net_r,"required_target_rr_before_cap":required_rr,
                                     "target_rr_cap":cap,"post_cost_target_viable":viable})
                    evals.append({"strategy_mode":mode,"timeframe":tf,"bar_ts_ms":bar_ts,"outcome":"SIGNAL",
                                  "reason":"signal" if viable else "signal_target_capped_by_cost_rr_ceiling",
                                  "cost_pct":cost_pct,"post_cost_viable":viable,"quote_volume_24h":qv,"features":features})
                else:
                    reason = str(diag.get(mode, "signal_not_generated") or "signal_not_generated")
                    evals.append({"strategy_mode":mode,"timeframe":tf,"bar_ts_ms":bar_ts,"outcome":"REJECT",
                                  "reason":reason,"quote_volume_24h":qv})

        result["evaluations"] = self._record_evaluations(symbol, evals)
        for item in evals:
            mode = str(item.get("strategy_mode", "UNKNOWN"))
            mode_stats = result["engine_cycle"].setdefault(mode, {"evaluated":0,"signals":0,"rejected":0,"blocked":0,"skipped":0,"reject_reasons":{}})
            mode_stats["evaluated"] += 1
            outcome = str(item.get("outcome", "REJECT"))
            if outcome == "SIGNAL": mode_stats["signals"] += 1
            elif outcome == "REJECT":
                mode_stats["rejected"] += 1
                why = str(item.get("reason", "unspecified"))
                mode_stats["reject_reasons"][why] = int(mode_stats["reject_reasons"].get(why, 0) or 0) + 1
                result["rejections"] += 1
                result["reject_reasons"][why] = int(result["reject_reasons"].get(why, 0) or 0) + 1
            elif outcome == "BLOCKED":
                mode_stats["blocked"] += 1
                why = str(item.get("reason", "unspecified"))
                mode_stats["reject_reasons"][why] = int(mode_stats["reject_reasons"].get(why, 0) or 0) + 1
            elif outcome == "SKIP":
                mode_stats["skipped"] += 1
                why = str(item.get("reason", "unspecified"))
                mode_stats["reject_reasons"][why] = int(mode_stats["reject_reasons"].get(why, 0) or 0) + 1

        # Samples are still virtual-only; this does not expose any order authority.
        for signal in signals:
            if self._record_signal(symbol, signal, snapshot):
                result["signals"] += 1
        result["pending"] = self._count_pending(symbol)
        return result

    def _count_pending(self, symbol: Optional[str] = None) -> int:
        try:
            with self._db() as conn:
                if symbol:
                    return int(conn.execute("SELECT COUNT(*) FROM v702_intraday_shadow_samples WHERE status='PENDING' AND symbol=?", (symbol,)).fetchone()[0])
                return int(conn.execute("SELECT COUNT(*) FROM v702_intraday_shadow_samples WHERE status='PENDING'").fetchone()[0])
        except Exception:
            return 0

    def report(self) -> Dict[str, Any]:
        try:
            _db_resolved = str(Path(self.db_path).expanduser().resolve())
        except Exception:
            _db_resolved = self.db_path
        try:
            _db_size = int(Path(_db_resolved).stat().st_size)
        except Exception:
            _db_size = None
        try:
            _report_dir_resolved = str(self.report_dir.expanduser().resolve())
        except Exception:
            _report_dir_resolved = str(self.report_dir)
        report: Dict[str, Any] = {"schema_version":SCHEMA_VERSION,"mode":"SHADOW_ONLY_NO_ORDERS","generated_at_epoch":time.time(),"live_execution":False,"db_path":_db_resolved,"db_bytes":_db_size,"report_dir":_report_dir_resolved,"strategies":{},"totals":{}}
        try:
            with self._db() as conn:
                sample_rows = conn.execute("SELECT strategy_mode,status,net_r,net_pct,gross_r,created_ts,resolved_ts,note,cost_pct,features_json,tp1_hit FROM v702_intraday_shadow_samples ORDER BY created_ts ASC").fetchall()
                eval_rows = conn.execute("SELECT strategy_mode,outcome,reason,cost_pct,post_cost_viable,quote_volume_24h,features_json FROM v702_intraday_shadow_evaluations ORDER BY evaluated_ts ASC").fetchall()
                pending = int(conn.execute("SELECT COUNT(*) FROM v702_intraday_shadow_samples WHERE status='PENDING'").fetchone()[0])
                total = int(conn.execute("SELECT COUNT(*) FROM v702_intraday_shadow_samples").fetchone()[0])
                alert_state_rows = conn.execute("SELECT state,COUNT(*) FROM v702_intraday_shadow_alerts GROUP BY state").fetchall()
                alert_states = {str(k): int(v) for k, v in alert_state_rows}
                outcome_state_rows = conn.execute("SELECT state,COUNT(*) FROM v702_intraday_shadow_outcomes GROUP BY state").fetchall()
                outcome_states = {str(k): int(v) for k, v in outcome_state_rows}
                daily_state_rows = conn.execute("SELECT state,COUNT(*) FROM v702_intraday_shadow_daily_outbox GROUP BY state").fetchall()
                daily_states = {str(k): int(v) for k, v in daily_state_rows}
            all_eval_signals = all_eval_rejects = all_eval_skips = all_eval_count = 0
            for mode in STRATEGIES:
                subset = [r for r in sample_rows if r[0] == mode]
                evaluations = [r for r in eval_rows if r[0] == mode]
                resolved = [r for r in subset if r[1] in {"TP1","SL","TIMEOUT","TRAILING_EXIT","AMBIGUOUS_DATA_GAP"}]
                nets = [float(r[2]) for r in resolved if r[2] is not None]
                pos = sum(v for v in nets if v > 0)
                neg = -sum(v for v in nets if v < 0)
                curve, peak, max_dd = 0.0, 0.0, 0.0
                for r in resolved:
                    curve += float(r[2]); peak = max(peak, curve); max_dd = max(max_dd, peak - curve)
                by_reason: Dict[str, int] = {}
                for ev in evaluations:
                    if str(ev[1]) in {"REJECT","BLOCKED","SKIP"}:
                        reason = str(ev[2] or "unspecified")
                        by_reason[reason] = int(by_reason.get(reason, 0) or 0) + 1
                viable_signals = sum(1 for ev in evaluations if ev[1] == "SIGNAL" and ev[4] == 1)
                capped_signals = sum(1 for ev in evaluations if ev[1] == "SIGNAL" and ev[4] == 0)
                known_costs = [float(ev[3]) for ev in evaluations if ev[1] == "SIGNAL" and ev[3] is not None]
                sample_costs = [float(r[8]) for r in subset if r[8] is not None]
                eval_count = len(evaluations)
                signal_count = sum(1 for ev in evaluations if ev[1] == "SIGNAL")
                reject_count = sum(1 for ev in evaluations if ev[1] in {"REJECT","BLOCKED"})
                skip_count = sum(1 for ev in evaluations if ev[1] == "SKIP")
                all_eval_count += eval_count; all_eval_signals += signal_count; all_eval_rejects += reject_count; all_eval_skips += skip_count
                report["strategies"][mode] = {
                    "evaluations":eval_count,"signals":signal_count,"rejections":reject_count,"skipped_evaluations":skip_count,
                    "rejection_reasons":dict(sorted(by_reason.items(), key=lambda kv:(-kv[1],kv[0]))[:12]),
                    "post_cost_target_viable_signals":viable_signals,"post_cost_target_capped_signals":capped_signals,
                    "avg_signal_cost_pct":statistics.fmean(known_costs) if known_costs else None,
                    "avg_sample_cost_pct":statistics.fmean(sample_costs) if sample_costs else None,
                    "samples":len(subset),"resolved":len(resolved),"pending":sum(1 for r in subset if r[1]=="PENDING"),
                    "win_rate_net_positive":(sum(v>0 for v in nets)/len(nets)) if nets else None,
                    "avg_net_r":statistics.fmean(nets) if nets else None,
                    "median_net_r":statistics.median(nets) if nets else None,
                    "avg_net_pct":statistics.fmean(float(r[3]) for r in resolved if r[3] is not None) if any(r[3] is not None for r in resolved) else None,
                    "profit_factor_net_r":(pos/neg) if neg>0 else (None if pos==0 else "INF_NO_LOSSES"),
                    "max_drawdown_r":max_dd,
                    "outcomes":{"TP1":sum(r[1]=="TP1" for r in subset),"SL":sum(r[1]=="SL" for r in subset),"TIMEOUT":sum(r[1]=="TIMEOUT" for r in subset),"TRAILING_EXIT":sum(r[1]=="TRAILING_EXIT" for r in subset),"AMBIGUOUS_DATA_GAP":sum(r[1]=="AMBIGUOUS_DATA_GAP" for r in subset),"partial_tp1_hits":sum(1 for r in subset if bool(r[10]))},
                    "sample_quality":"TOO_SMALL" if len(nets)<30 else ("PRELIMINARY" if len(nets)<100 else "NEEDS_OUT_OF_SAMPLE_VALIDATION"),
                    "scored_outcomes":len(nets),
                }
            report["totals"]={"samples":total,"pending":pending,"resolved":sum(v["resolved"] for v in report["strategies"].values()),
                              "evaluations":all_eval_count,"signals":all_eval_signals,"rejections":all_eval_rejects,"skipped_evaluations":all_eval_skips}
            report["micro_alerts"] = {
                "enabled": bool(self._cfg().get("V702_INTRADAY_SHADOW_TELEGRAM_ALERTS_ENABLE", True)),
                "states": alert_states, "pending": int(alert_states.get("PENDING", 0)),
                "queued": int(alert_states.get("QUEUED", 0)), "expired": int(alert_states.get("EXPIRED", 0)),
                "max_per_batch": int(max(1, min(10, _num(self._cfg().get("V702_INTRADAY_SHADOW_TELEGRAM_MAX_PER_BATCH"), 3) or 3))),
            }
            report["micro_outcome_notifications"] = {
                "enabled": bool(self._cfg().get("V702_INTRADAY_SHADOW_OUTCOME_TELEGRAM_ENABLE", True)),
                "states": outcome_states, "pending": int(outcome_states.get("PENDING", 0)),
                "queued": int(outcome_states.get("QUEUED", 0)),
            }
            report["daily_telegram_reports"] = {
                "enabled": bool(self._cfg().get("V702_INTRADAY_SHADOW_DAILY_TELEGRAM_ENABLE", True)),
                "states": daily_states, "pending": int(daily_states.get("PENDING", 0)),
                "queued": int(daily_states.get("QUEUED", 0)),
                "timezone": str(self._cfg().get("V702_INTRADAY_SHADOW_DAILY_TIMEZONE", "Africa/Cairo")),
            }
            report["liquidation_spot_absorption"] = {
                "provider_status": "UNCONFIGURED",
                "data_contract": "LSA_V1",
                "note": "No native Futures liquidation/Open Interest/Funding/Spot-CVD provider is configured in this release; missing evidence remains UNAVAILABLE and cannot gate or authorize orders.",
            }
        except Exception as exc:
            report["error"]=f"{type(exc).__name__}:{str(exc)[:180]}"
        return report

    def pending_micro_outcomes(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Return persistent, retryable micro outcome notifications."""
        limit = max(1, min(20, int(limit or 5)))
        try:
            with self._db() as conn:
                rows = conn.execute("""SELECT sample_id,symbol,strategy_mode,timeframe,resolved_ts,outcome,payload_json
                    FROM v702_intraday_shadow_outcomes WHERE state='PENDING' ORDER BY resolved_ts ASC LIMIT ?""", (limit,)).fetchall()
            out = []
            for sid, symbol, mode, tf, resolved_ts, outcome, payload in rows:
                try: body = json.loads(payload or "{}")
                except Exception: body = {}
                out.append({"sample_id":str(sid),"symbol":str(symbol),"strategy_mode":str(mode),
                            "timeframe":str(tf),"resolved_ts":float(resolved_ts),"outcome":str(outcome),"payload":body})
            return out
        except Exception:
            return []

    def mark_micro_outcome_queued(self, sample_id: str, note: str = "telegram_durable_outbox_accepted") -> bool:
        try:
            with self._db() as conn:
                cur = conn.execute("UPDATE v702_intraday_shadow_outcomes SET state='QUEUED',updated_ts=?,note=? WHERE sample_id=? AND state='PENDING'",
                                   (time.time(), str(note or "")[:160], str(sample_id or "")))
                return bool(cur.rowcount)
        except Exception:
            return False

    def ensure_daily_telegram_report(self, now_ts: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Create one previous-local-day per-strategy report after the configured Cairo-local time."""
        cfg = self._cfg()
        if not bool(cfg.get("V702_INTRADAY_SHADOW_DAILY_TELEGRAM_ENABLE", True)):
            return None
        try:
            tz_name = str(cfg.get("V702_INTRADAY_SHADOW_DAILY_TIMEZONE", "Africa/Cairo") or "Africa/Cairo")
            tz = ZoneInfo(tz_name)
            now_dt = datetime.fromtimestamp(float(now_ts if now_ts is not None else time.time()), tz=tz)
            ready_hour = max(0, min(23, int(_num(cfg.get("V702_INTRADAY_SHADOW_DAILY_REPORT_HOUR"), 0) or 0)))
            ready_minute = max(0, min(59, int(_num(cfg.get("V702_INTRADAY_SHADOW_DAILY_REPORT_MINUTE"), 5) or 5)))
            if (now_dt.hour, now_dt.minute) < (ready_hour, ready_minute):
                return None
            report_day = now_dt.date() - timedelta(days=1)
            day_start = datetime.combine(report_day, datetime_time.min, tzinfo=tz).timestamp()
            day_end = datetime.combine(report_day + timedelta(days=1), datetime_time.min, tzinfo=tz).timestamp()
            strategy_rows = {}
            with self._db() as conn:
                for mode in STRATEGIES:
                    created = int(conn.execute("SELECT COUNT(*) FROM v702_intraday_shadow_samples WHERE strategy_mode=? AND created_ts>=? AND created_ts<?",
                                               (mode, day_start, day_end)).fetchone()[0])
                    outcome_rows = conn.execute("""SELECT status,net_r,net_pct FROM v702_intraday_shadow_samples
                        WHERE strategy_mode=? AND resolved_ts>=? AND resolved_ts<? AND status!='PENDING'""",
                        (mode, day_start, day_end)).fetchall()
                    outcomes = {key: sum(1 for row in outcome_rows if row[0] == key)
                                for key in ("TP1", "SL", "TIMEOUT", "TRAILING_EXIT", "AMBIGUOUS_DATA_GAP")}
                    valid_net = [float(row[1]) for row in outcome_rows if row[1] is not None]
                    valid_pct = [float(row[2]) for row in outcome_rows if row[2] is not None]
                    strategy_rows[mode] = {
                        "signals_created": created, "resolved": len(outcome_rows), "outcomes": outcomes,
                        "net_positive": sum(1 for value in valid_net if value > 0),
                        "net_negative": sum(1 for value in valid_net if value < 0),
                        "avg_net_r": statistics.fmean(valid_net) if valid_net else None,
                        "avg_net_pct": statistics.fmean(valid_pct) if valid_pct else None,
                        "ambiguous_excluded_from_net": outcomes["AMBIGUOUS_DATA_GAP"],
                    }
                payload = {"report_date": report_day.isoformat(), "timezone": tz_name,
                           "mode": "SHADOW_ONLY_NO_ORDERS", "strategies": strategy_rows,
                           "totals": {"signals_created": sum(x["signals_created"] for x in strategy_rows.values()),
                                      "resolved": sum(x["resolved"] for x in strategy_rows.values()),
                                      "tp1": sum(x["outcomes"]["TP1"] for x in strategy_rows.values()),
                                      "sl": sum(x["outcomes"]["SL"] for x in strategy_rows.values()),
                                      "timeouts": sum(x["outcomes"]["TIMEOUT"] for x in strategy_rows.values()),
                                      "ambiguous": sum(x["outcomes"]["AMBIGUOUS_DATA_GAP"] for x in strategy_rows.values())}}
                conn.execute("INSERT OR IGNORE INTO v702_intraday_shadow_daily_outbox(report_date,created_ts,state,payload_json,updated_ts,note) VALUES(?,?,'PENDING',?,?,?)",
                             (report_day.isoformat(), time.time(), _json(payload), time.time(), "daily_strategy_outcome_digest"))
                row = conn.execute("SELECT report_date,payload_json FROM v702_intraday_shadow_daily_outbox WHERE state='PENDING' ORDER BY report_date ASC LIMIT 1").fetchone()
            if not row:
                return None
            try: body = json.loads(row[1] or "{}")
            except Exception: body = {}
            return {"report_date":str(row[0]),"payload":body}
        except Exception:
            return None

    def mark_daily_telegram_report_queued(self, report_date: str, note: str = "telegram_durable_outbox_accepted") -> bool:
        try:
            with self._db() as conn:
                cur = conn.execute("UPDATE v702_intraday_shadow_daily_outbox SET state='QUEUED',updated_ts=?,note=? WHERE report_date=? AND state='PENDING'",
                                   (time.time(), str(note or "")[:160], str(report_date or "")))
                return bool(cur.rowcount)
        except Exception:
            return False

    def write_report(self, report: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        report = report or self.report()
        try:
            self.report_dir.mkdir(parents=True, exist_ok=True)
            jp = self.report_dir / "V702_INTRADAY_SHADOW_LATEST.json"
            mp = self.report_dir / "V702_INTRADAY_SHADOW_LATEST.md"
            report["report_files"] = {"json":str(jp.resolve()), "markdown":str(mp.resolve())}
            jp.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
            lines = ["# V702 A9 Intraday Shadow Study", "", "**Mode: SHADOW ONLY. No live orders are generated or submitted.**", "",
                     "Signals: 1m micro-momentum, 1m sweep-reclaim, 1m local pullback-reclaim, 5m UTC-session VWAP reclaim + relative strength, and shadow-only 15m Adaptive RS Pullback with 5m resumption.",
                     "Costs use the shared measured all-in book/VWAP + symbol fee model with a 0.05% measurement buffer; without measurement, use observed/fallback spread + two-sided slippage + conservative fee estimate.",
                     "Same-candle SL/TP ambiguity resolves as SL first. The Adaptive RS lane requires BTC and asset higher-timeframe alignment; earlier micro lanes retain their original regime rules.", "",
                     "| Strategy | Evals | Signals | Rejects | Samples | Resolved | Pending | Net win rate | Avg net R | PF net R | Max DD R | Quality |",
                     "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
            def f(x):
                if x is None: return "n/a"
                if isinstance(x,str): return x
                return f"{x:.3f}" if isinstance(x,float) else str(x)
            for mode in STRATEGIES:
                r = report.get("strategies",{}).get(mode,{})
                lines.append("| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
                    mode,r.get("evaluations",0),r.get("signals",0),r.get("rejections",0),r.get("samples",0),r.get("resolved",0),r.get("pending",0),
                    f(r.get("win_rate_net_positive")),f(r.get("avg_net_r")),f(r.get("profit_factor_net_r")),f(r.get("max_drawdown_r")),r.get("sample_quality","n/a")))
                reasons = r.get("rejection_reasons", {}) or {}
                lines.append("  - Reject reasons: " + (", ".join(f"{k}={v}" for k,v in list(reasons.items())[:5]) if reasons else "none recorded"))
                lines.append("  - Post-cost targets: viable={} capped={} avg_cost_pct={}".format(
                    r.get("post_cost_target_viable_signals",0),r.get("post_cost_target_capped_signals",0),f(r.get("avg_signal_cost_pct"))))
            lines += ["", "## Telegram outcome delivery", "",
                      "- Micro 1m TP1 / SL / TIMEOUT / AMBIGUOUS_DATA_GAP outcomes are persisted in a separate retryable SQLite outbox when the originating Micro alert exists.",
                      "- Telegram queue acceptance is not delivery ACK. Messages explicitly identify virtual closed-candle outcomes, not exchange fills or realized PnL.",
                      "- Daily per-strategy Telegram reports summarize the previous Africa/Cairo calendar day; ambiguous data-gap outcomes are excluded from net performance calculations.",
                      "", "## Decision criteria", "", "- Fewer than 30 scored net outcomes: too early to judge.", "- 30–99: preliminary only.", "- 100 or more: more informative but still requires holdout/out-of-sample and paper-trading confirmation.", "- A strategy is not accepted solely on win rate; inspect mean net R, profit factor, drawdown, costs, regimes, and sample independence.", "- This report does not establish live fill quality or real-world profitability.", ""]
            mp.write_text("\n".join(lines), encoding="utf-8")
        except Exception as exc:
            report["report_write_error"]=f"{type(exc).__name__}:{str(exc)[:180]}"
        return report

    def periodic_report_if_due(self, force: bool = False) -> Optional[Dict[str, Any]]:
        cfg = self._cfg()
        if not bool(cfg.get("V702_INTRADAY_SHADOW_ENABLE", True)): return None
        interval = max(60.0, min(86400.0, _num(cfg.get("V702_INTRADAY_SHADOW_REPORT_INTERVAL_SEC"), 900.0) or 900.0))
        now = time.time()
        try:
            with self._db() as conn:
                row = conn.execute("SELECT v FROM v702_intraday_shadow_meta WHERE k='last_report_epoch'").fetchone()
                last = _num(row[0], 0.0) if row else 0.0
                if not force and now - (last or 0.0) < interval: return None
                conn.execute("INSERT OR REPLACE INTO v702_intraday_shadow_meta(k,v,updated_ts) VALUES(?,?,?)",("last_report_epoch",str(now),now))
            report = self.write_report(self.report())
            return report
        except Exception:
            return None

    def self_test(self) -> Dict[str, Any]:
        try:
            with self._db() as conn:
                cols = {r[1] for r in conn.execute("PRAGMA table_info(v702_intraday_shadow_samples)").fetchall()}
                tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            report = self.report()
            checks = {
                "schema_present": {"sample_id","strategy_mode","signal_ts_ms","entry","stop","target","net_r","status"}.issubset(cols),
                "all_shadow_strategies_reported": all(x in report.get("strategies",{}) for x in STRATEGIES),
                "shadow_only": report.get("mode")=="SHADOW_ONLY_NO_ORDERS" and report.get("live_execution") is False,
                "no_execution_api_in_module": not any(
                    isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr in {"create_order", "create_market_buy", "submit_entry", "submit_order"}
                    for node in ast.walk(ast.parse(Path(__file__).read_text(encoding="utf-8")))
                ),
                "persistent_tables_present": {"v702_intraday_shadow_samples","v702_intraday_shadow_meta","v702_intraday_shadow_alerts","v702_intraday_shadow_outcomes","v702_intraday_shadow_daily_outbox"}.issubset(tables),
                "shadow_alert_outbox_present": "v702_intraday_shadow_alerts" in tables,
                "shadow_outcome_outbox_present": "v702_intraday_shadow_outcomes" in tables,
                "daily_report_outbox_present": "v702_intraday_shadow_daily_outbox" in tables,
                "balanced_core_micro_selector_available": callable(select_balanced_shadow_symbols),
                "lsa_missing_data_fails_unavailable": self._assess_liquidation_spot_absorption({}).get("status") == "UNAVAILABLE",
            }
            return {"pass":all(checks.values()),"checks":checks,"schema_version":SCHEMA_VERSION}
        except Exception as exc:
            return {"pass":False,"checks":{"exception_free":False},"error":f"{type(exc).__name__}:{str(exc)[:180]}"}
