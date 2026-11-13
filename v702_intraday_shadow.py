"""V702 A9 intraday strategy research lane (shadow-only, no order authority).

Strategies:
- MICRO_MOMENTUM_1M: closed-bar range break with volume/body/chase checks.
- MICRO_SWEEP_RECLAIM_1M: local low sweep and close reclaim.
- MICRO_PULLBACK_RECLAIM_1M: local EMA9 reclaim while local EMA9/21 structure is constructive.
- VWAP_RECLAIM_RS_5M: UTC-session VWAP reclaim plus coin-relative strength vs BTC.

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
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from v702_core__policy__forbidden_assets import HARD_FORBIDDEN_BASES
from v702_core__storage__sqlite_writer import SQLITE_WRITER_LOCK

try:
    import pandas as pd
except Exception:  # pragma: no cover - guarded by runtime install/validator
    pd = None

SCHEMA_VERSION = 1
STRATEGIES = (
    "MICRO_MOMENTUM_1M",
    "MICRO_SWEEP_RECLAIM_1M",
    "MICRO_PULLBACK_RECLAIM_1M",
    "VWAP_RECLAIM_RS_5M",
)
_HARD_EXCLUDED_BASES = HARD_FORBIDDEN_BASES


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
    """Return closed bars only. Exchanges generally include one in-progress final row."""
    if not _frame_ok(df, 2):
        return []
    rows: List[Dict[str, float]] = []
    # Deliberately drop the final potentially-open candle.
    for i in range(max(0, len(df) - 1)):
        row = df.iloc[i]
        ts = _ts_ms(df.index[i])
        if ts is None: continue
        try:
            item = {
                "ts": float(ts),
                "open": float(row["open"]), "high": float(row["high"]),
                "low": float(row["low"]), "close": float(row["close"]),
                "volume": max(0.0, float(row["volume"])),
                "close_ts": float(ts + timeframe_ms),
            }
            if all(math.isfinite(item[k]) for k in ("open", "high", "low", "close", "volume")) and item["low"] > 0 and item["high"] >= item["low"]:
                rows.append(item)
        except Exception:
            continue
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
        self._initialize()

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
                UNIQUE(symbol,strategy_mode,signal_ts_ms)
            )""")
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
        # CONFIG expresses fee in percentage points: 0.10 means 0.10% per side.
        fee_side = max(0.0, _num(cfg.get("TAKER_FEE_PCT"), 0.10) or 0.0)
        slip_side = max(0.0, _num(cfg.get("V702_INTRADAY_SLIPPAGE_PER_SIDE_PCT"), 0.05) or 0.0)
        spread_fallback = max(0.0, _num(cfg.get("V702_INTRADAY_SPREAD_FALLBACK_PCT"), 0.15) or 0.0)
        spread = _num(snapshot.get("spread_pct"), None)
        if spread is None:
            ticker = snapshot.get("ticker") if isinstance(snapshot.get("ticker"), dict) else {}
            bid, ask = _num(ticker.get("bid"), None), _num(ticker.get("ask"), None)
            if bid and ask and ask >= bid and (ask + bid) > 0:
                spread = 100.0 * (ask - bid) / ((ask + bid) / 2.0)
        spread = max(spread_fallback, spread or 0.0)
        return max(0.0, 2.0 * fee_side + spread + 2.0 * slip_side)

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

    def _record_signal(self, symbol: str, signal: Dict[str, Any], snapshot: Dict[str, Any]) -> bool:
        entry, stop, _initial_target, risk = (float(signal[k]) for k in ("entry", "stop", "target", "risk"))
        risk_pct = 100.0 * risk / entry
        cost_pct = self._cost_pct(entry, snapshot)
        cfg = self._cfg()
        fee_side = max(0.0, _num(cfg.get("TAKER_FEE_PCT"), 0.10) or 0.0)
        desired_net_pct = max(0.0, _num(cfg.get("V702_INTRADAY_MIN_NET_PROFIT_PCT"), 0.10) or 0.0)
        minimum_net_rr = max(0.0, _num(cfg.get("V702_INTRADAY_MIN_NET_RR"), 0.25) or 0.0)
        fee_coverage = max(1.0, _num(cfg.get("V702_INTRADAY_TP1_FEE_COVERAGE"), 2.5) or 2.5)
        target_rr_cap = max(1.0, min(5.0, _num(cfg.get("V702_INTRADAY_MAX_TARGET_RR"), 3.0) or 3.0))
        target_buffer_rr = max(0.0, _num(cfg.get("V702_INTRADAY_TARGET_BUFFER_R"), 0.03) or 0.0)
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
        mode = str(signal["mode"])
        material = f"{symbol}|{mode}|{signal_close_ms}"
        sample_id = hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]
        qv = _num(snapshot.get("quote_vol_24h"), None)
        tier = str(snapshot.get("tier") or "")[:24]
        features = dict(signal.get("features") or {})
        features.update({"entry":entry,"stop":stop,"target":target,"risk_pct":risk_pct,"cost_pct":cost_pct,
                         "target_rr":target_rr,"required_target_rr_before_cap":required_rr,
                         "target_rr_capped_for_research":bool(required_rr + target_buffer_rr > target_rr_cap),
                         "minimum_net_profit_pct_target":desired_net_pct,
                         "target_net_pct_after_costs":target_net_pct,"target_net_r_after_costs":target_net_r,
                         "post_cost_target_viable":post_cost_viable,
                         "quote_volume_24h":qv,"macro_regime":snapshot.get("macro_regime"),
                         "experiment":"SHADOW_ONLY_NO_ORDERS","higher_timeframe_bullish_required":False,
                         "crash_guard":"BTC_5M_15MIN_SHOCK_ONLY"})
        try:
            with self._db() as conn:
                cur = conn.execute("""INSERT OR IGNORE INTO v702_intraday_shadow_samples
                    (sample_id,symbol,strategy_mode,timeframe,signal_ts_ms,created_ts,entry,stop,target,risk_unit,risk_pct,
                     last_candle_ts_ms,bars_seen,status,cost_pct,quote_volume_24h,tier,features_json,note)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (sample_id,symbol,mode,signal["tf"],signal_close_ms,time.time(),entry,stop,target,risk,risk_pct,
                     signal_close_ms - 60_000,0,"PENDING",cost_pct,qv,tier,_json(features),"virtual_entry_at_closed_signal_bar"))
                inserted = cur.rowcount > 0
                max_rows = int(max(1000, min(200000, _num(self._cfg().get("V702_INTRADAY_SHADOW_MAX_ROWS"), 50000) or 50000)))
                if inserted:
                    total = int(conn.execute("SELECT COUNT(*) FROM v702_intraday_shadow_samples").fetchone()[0])
                    if total > max_rows:
                        conn.execute("DELETE FROM v702_intraday_shadow_samples WHERE sample_id IN (SELECT sample_id FROM v702_intraday_shadow_samples ORDER BY created_ts ASC LIMIT ?)", (total - max_rows,))
            return inserted
        except Exception:
            return False

    def _update_pending(self, symbol: str, closed_1m_rows: Sequence[Dict[str, float]]) -> int:
        cfg = self._cfg()
        max_bars = int(max(5, min(120, _num(cfg.get("V702_INTRADAY_SHADOW_MAX_HOLD_BARS"), 30) or 30)))
        updated = 0
        try:
            with self._db() as conn:
                pending = conn.execute("""SELECT sample_id,entry,stop,target,risk_unit,risk_pct,last_candle_ts_ms,bars_seen,cost_pct,signal_ts_ms
                    FROM v702_intraday_shadow_samples WHERE symbol=? AND status='PENDING' ORDER BY signal_ts_ms ASC""", (symbol,)).fetchall()
                for rec in pending:
                    sid, entry, stop, target, risk, risk_pct, last_ts, bars_seen, cost_pct, signal_ts = rec
                    state = None
                    exit_price = gross_r = net_r = net_pct = None
                    last_seen = int(last_ts or 0)
                    count = int(bars_seen or 0)
                    for bar in closed_1m_rows:
                        bar_ts = int(bar["ts"])
                        if bar_ts < int(signal_ts) or bar_ts <= last_seen: continue
                        last_seen = bar_ts
                        count += 1
                        hit_sl = float(bar["low"]) <= float(stop)
                        hit_tp = float(bar["high"]) >= float(target)
                        if hit_sl:  # conservative SL-first, including same-candle touch
                            state, exit_price, gross_r = "SL", float(stop), -1.0
                            break
                        if hit_tp:
                            state, exit_price = "TP1", float(target)
                            gross_r = (float(target) - float(entry)) / max(float(risk), 1e-12)
                            break
                        if count >= max_bars:
                            state, exit_price = "TIMEOUT", float(bar["close"])
                            gross_r = (exit_price - float(entry)) / max(float(risk), 1e-12)
                            break
                    if state:
                        cost_r = float(cost_pct) / max(float(risk_pct), 1e-12)
                        net_r = float(gross_r) - cost_r
                        net_pct = net_r * float(risk_pct)
                        conn.execute("""UPDATE v702_intraday_shadow_samples SET last_candle_ts_ms=?,bars_seen=?,status=?,exit_price=?,gross_r=?,net_r=?,net_pct=?,resolved_ts=?,note=? WHERE sample_id=? AND status='PENDING'""",
                            (last_seen,count,state,exit_price,gross_r,net_r,net_pct,time.time(),"SL_FIRST_IF_AMBIGUOUS;ROUNDTRIP_COST_DEDUCTED",sid))
                        updated += 1
                    else:
                        conn.execute("UPDATE v702_intraday_shadow_samples SET last_candle_ts_ms=?,bars_seen=? WHERE sample_id=? AND status='PENDING'",
                                     (last_seen,count,sid))
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
                tf = "5m" if mode == "VWAP_RECLAIM_RS_5M" else "1m"
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

        result["resolved"] = self._update_pending(symbol, rows)
        blocked, block_reason = self._crash_guard(snapshot)
        evals: List[Dict[str, Any]] = []
        signals: List[Dict[str, Any]] = []
        diag: Dict[str, str] = {}
        rows5 = _closed_rows(snapshot.get("df_5m"), 300_000)
        bar_1m = int(rows[-1]["close_ts"]) if rows else (int(time.time() * 1000) // 60_000) * 60_000
        bar_5m = int(rows5[-1]["close_ts"]) if rows5 else (int(time.time() * 1000) // 300_000) * 300_000

        if blocked:
            for mode in STRATEGIES:
                tf = "5m" if mode == "VWAP_RECLAIM_RS_5M" else "1m"
                evals.append({"strategy_mode":mode,"timeframe":tf,"bar_ts_ms":bar_5m if tf=="5m" else bar_1m,
                              "outcome":"BLOCKED","reason":str(block_reason or "btc_15m_crash_guard"),"quote_volume_24h":qv})
        else:
            one_min_signals = self._make_signals_1m(rows, diagnostics=diag)
            signals.extend(one_min_signals)
            vwap_signal, vwap_reason = self._make_vwap_rs_signal_detailed(snapshot)
            if vwap_signal:
                signals.append(vwap_signal)
            diag["VWAP_RECLAIM_RS_5M"] = vwap_reason
            signal_by_mode = {str(x.get("mode")):x for x in signals}
            for mode in STRATEGIES:
                sig = signal_by_mode.get(mode)
                tf = "5m" if mode == "VWAP_RECLAIM_RS_5M" else "1m"
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
                sample_rows = conn.execute("SELECT strategy_mode,status,net_r,net_pct,gross_r,created_ts,resolved_ts,note,cost_pct,features_json FROM v702_intraday_shadow_samples ORDER BY created_ts ASC").fetchall()
                eval_rows = conn.execute("SELECT strategy_mode,outcome,reason,cost_pct,post_cost_viable,quote_volume_24h,features_json FROM v702_intraday_shadow_evaluations ORDER BY evaluated_ts ASC").fetchall()
                pending = int(conn.execute("SELECT COUNT(*) FROM v702_intraday_shadow_samples WHERE status='PENDING'").fetchone()[0])
                total = int(conn.execute("SELECT COUNT(*) FROM v702_intraday_shadow_samples").fetchone()[0])
            all_eval_signals = all_eval_rejects = all_eval_skips = all_eval_count = 0
            for mode in STRATEGIES:
                subset = [r for r in sample_rows if r[0] == mode]
                evaluations = [r for r in eval_rows if r[0] == mode]
                resolved = [r for r in subset if r[1] in {"TP1","SL","TIMEOUT"} and r[2] is not None]
                nets = [float(r[2]) for r in resolved]
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
                    "outcomes":{"TP1":sum(r[1]=="TP1" for r in subset),"SL":sum(r[1]=="SL" for r in subset),"TIMEOUT":sum(r[1]=="TIMEOUT" for r in subset)},
                    "sample_quality":"TOO_SMALL" if len(resolved)<30 else ("PRELIMINARY" if len(resolved)<100 else "NEEDS_OUT_OF_SAMPLE_VALIDATION"),
                }
            report["totals"]={"samples":total,"pending":pending,"resolved":sum(v["resolved"] for v in report["strategies"].values()),
                              "evaluations":all_eval_count,"signals":all_eval_signals,"rejections":all_eval_rejects,"skipped_evaluations":all_eval_skips}
        except Exception as exc:
            report["error"]=f"{type(exc).__name__}:{str(exc)[:180]}"
        return report

    def write_report(self, report: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        report = report or self.report()
        try:
            self.report_dir.mkdir(parents=True, exist_ok=True)
            jp = self.report_dir / "V702_INTRADAY_SHADOW_LATEST.json"
            mp = self.report_dir / "V702_INTRADAY_SHADOW_LATEST.md"
            report["report_files"] = {"json":str(jp.resolve()), "markdown":str(mp.resolve())}
            jp.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
            lines = ["# V702 A9 Intraday Shadow Study", "", "**Mode: SHADOW ONLY. No live orders are generated or submitted.**", "",
                     "Signals: 1m micro-momentum, 1m sweep-reclaim, 1m local pullback-reclaim, and 5m UTC-session VWAP reclaim + relative strength.",
                     "Costs deduct two-sided fee, estimated full spread (using a conservative fallback when not measured), and two-sided slippage.",
                     "Same-candle SL/TP ambiguity resolves as SL first. Higher timeframe bullish trend is not required; BTC shock guard remains active.", "",
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
            lines += ["", "## Decision criteria", "", "- Fewer than 30 resolved outcomes: too early to judge.", "- 30–99: preliminary only.", "- 100 or more: more informative but still requires holdout/out-of-sample and paper-trading confirmation.", "- A strategy is not accepted solely on win rate; inspect mean net R, profit factor, drawdown, costs, regimes, and sample independence.", "- This report does not establish live fill quality or real-world profitability.", ""]
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
                "four_strategies_reported": all(x in report.get("strategies",{}) for x in STRATEGIES),
                "shadow_only": report.get("mode")=="SHADOW_ONLY_NO_ORDERS" and report.get("live_execution") is False,
                "no_execution_api_in_module": not any(
                    isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr in {"create_order", "create_market_buy", "submit_entry", "submit_order"}
                    for node in ast.walk(ast.parse(Path(__file__).read_text(encoding="utf-8")))
                ),
                "persistent_tables_present": {"v702_intraday_shadow_samples","v702_intraday_shadow_meta"}.issubset(tables),
            }
            return {"pass":all(checks.values()),"checks":checks,"schema_version":SCHEMA_VERSION}
        except Exception as exc:
            return {"pass":False,"checks":{"exception_free":False},"error":f"{type(exc).__name__}:{str(exc)[:180]}"}
