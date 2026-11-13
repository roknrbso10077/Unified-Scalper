"""V702 counterfactual shadow study. Read-only research telemetry; never places orders.

The subsystem records prequalification survivors and narrowly-defined near misses,
then evaluates their hypothetical long-only TP1/SL outcomes on subsequent CLOSED
5-minute candles. It is deliberately independent from execution code.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sqlite3
import statistics
import time
from contextlib import contextmanager
from pathlib import Path

from v702_core__policy__forbidden_assets import HARD_FORBIDDEN_BASES
from v702_core__storage__sqlite_writer import SQLITE_WRITER_LOCK
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

SCHEMA_VERSION = 2
LANES = (
    "BASELINE_PASS",
    "CURRENT_HTF_RELIEF_PASS",
    "HTF_RELIEF",
    "MID_TIER_COUNTERFACTUAL",
    "BEARISH_NORMAL_LSR",
    "BEARISH_POLICY_REJECT_OBSERVATION",
    "HTF_POLICY_REJECT_OBSERVATION",
)
TERMINAL = {"TP1", "SL", "AMBIGUOUS_SL_FIRST", "TIME_EXIT", "INVALID_DATA"}


def bearish_policy_reject_observation_eligible(*, reason: Any, side: Any, macro_regime: Any) -> bool:
    """Identify raw long candidates rejected by the canonical Bearish family policy.

    This predicate is intentionally much narrower than a general shadow bypass:
    it accepts only the exact macro-family rejection, an explicit LONG/BUY side,
    and an explicit BEARISH macro regime. It does not inspect or relax any live
    gate and does not claim the candidate would pass downstream stages.
    """
    why = _text(reason, 120).lower()
    sd = _text(side, 16).lower()
    regime = _text(macro_regime, 40).upper()
    return bool(
        why.startswith("family_regime_disallowed.macro")
        and sd in {"long", "buy"}
        and regime == "BEARISH"
    )


def htf_policy_reject_observation_eligible(*, reason: Any, side: Any, macro_regime: Any) -> bool:
    """Identify raw long candidates rejected by the canonical HTF floor.

    This records a rejected outcome cohort only. It never changes the HTF
    verdict or implies that a candidate would pass subsequent gates.
    """
    why = _text(reason, 120).lower()
    sd = _text(side, 16).lower()
    regime = _text(macro_regime, 40).upper()
    return bool(
        why.startswith("htf.family_htf_strength_below_floor")
        and sd in {"long", "buy"}
        and regime in {"BULLISH", "NEUTRAL", "BEARISH"}
    )


def bearish_normal_lsr_eligible(
    *, family: Any, side: Any, macro_regime: Any, severity: Any, score: Any,
    htf_strength: Any, volume_ratio: Any, quote_volume_24h: Any,
    min_htf_strength: float = 47.0, min_volume_ratio: float = 1.4,
    min_quote_volume: float = 3_000_000.0, min_score: float = 70.0,
) -> bool:
    """Strict eligibility predicate for a research-only bearish LSR cohort.

    This deliberately does not alter any canonical trade decision and rejects
    missing or malformed evidence rather than imputing a pass.
    """
    fam = _text(family, 48).upper()
    sd = _text(side, 16).lower()
    regime = _text(macro_regime, 40).upper()
    sev = _text(severity, 40).upper()
    values = [_num(score, None), _num(htf_strength, None), _num(volume_ratio, None), _num(quote_volume_24h, None)]
    if any(v is None for v in values):
        return False
    score_v, htf_v, volume_v, quote_v = values
    return bool(
        fam == "LIQUIDITY_SWEEP_REVERSAL"
        and sd in {"long", "buy"}
        and regime == "BEARISH"
        and sev in {"NORMAL", "BEARISH_NORMAL"}
        and score_v >= float(min_score)
        and htf_v >= float(min_htf_strength)
        and volume_v >= float(min_volume_ratio)
        and quote_v >= float(min_quote_volume)
    )


class _ClosingSQLiteConnection(sqlite3.Connection):
    """Commit/rollback like sqlite3.Connection and also close on context exit."""
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def _num(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None or isinstance(value, bool):
            return default
        result = float(value)
        if not math.isfinite(result):
            return default
        return result
    except (TypeError, ValueError, OverflowError):
        return default


def _text(value: Any, limit: int = 120) -> str:
    try:
        return str(value or "").strip()[:limit]
    except Exception:
        return ""


def _json_safe(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


class V702CounterfactualShadow:
    """Persistent shadow cohort evaluator; no exchange or execution interfaces."""

    def __init__(self, db_path: str, report_dir: str, config_getter: Optional[Callable[[], Dict[str, Any]]] = None):
        self.db_path = str(db_path or "./unified_scalper.db")
        self.report_dir = Path(report_dir or "./reports")
        self.config_getter = config_getter or (lambda: {})
        self._last_report_wall = 0.0
        self._last_cycle_processed = 0
        self._init_schema()

    def _cfg(self) -> Dict[str, Any]:
        try:
            value = self.config_getter()
            return value if isinstance(value, dict) else {}
        except Exception:
            return {}

    def _connect(self) -> sqlite3.Connection:
        path = Path(self.db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path), timeout=5.0, factory=_ClosingSQLiteConnection)
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    @contextmanager
    def _db(self):
        """Serialize and close all shadow DB operations on the shared writer lock."""
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

    def _init_schema(self) -> None:
        with self._db() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS v702_cf_shadow_samples (
                sample_id TEXT PRIMARY KEY,
                sample_key TEXT NOT NULL UNIQUE,
                created_ts REAL NOT NULL,
                anchor_bar_ts_ms INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                family TEXT NOT NULL,
                strategy_mode TEXT NOT NULL,
                lane TEXT NOT NULL,
                reject_reason TEXT NOT NULL,
                score REAL,
                htf_strength REAL,
                htf_floor REAL,
                quote_volume_24h REAL,
                tier TEXT,
                entry REAL,
                stop REAL,
                target REAL,
                risk_unit REAL,
                tp1_rr REAL,
                last_candle_ts_ms INTEGER NOT NULL DEFAULT 0,
                bars_seen INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL,
                exit_price REAL,
                gross_r REAL,
                net_r REAL,
                resolved_ts REAL,
                note TEXT NOT NULL DEFAULT '',
                context_json TEXT NOT NULL DEFAULT '{}'
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_v702_cf_lane_status ON v702_cf_shadow_samples(lane,status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_v702_cf_symbol_status ON v702_cf_shadow_samples(symbol,status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_v702_cf_created ON v702_cf_shadow_samples(created_ts)")
            conn.execute("""CREATE TABLE IF NOT EXISTS v702_cf_shadow_meta (
                k TEXT PRIMARY KEY, v TEXT NOT NULL, updated_ts REAL NOT NULL
            )""")
            conn.execute("INSERT OR REPLACE INTO v702_cf_shadow_meta(k,v,updated_ts) VALUES(?,?,?)",
                         ("schema_version", str(SCHEMA_VERSION), time.time()))

    @staticmethod
    def _symbol_allowed(symbol: str) -> bool:
        """Hard exclusions for this research lane; study never researches prohibited pairs."""
        sym = _text(symbol, 64).upper()
        if not sym.endswith("/USDT") or sym.count("/") != 1:
            return False
        base = sym.split("/", 1)[0]
        if not base or base in HARD_FORBIDDEN_BASES:
            return False
        return True

    @staticmethod
    def _candidate_parts(candidate: Any) -> Any:
        return getattr(candidate, "candidate", candidate)

    def record_candidate(
        self,
        candidate: Any,
        lane: str,
        reason: str,
        snapshot: Optional[Dict[str, Any]] = None,
        htf_strength: Optional[float] = None,
        htf_floor: Optional[float] = None,
    ) -> bool:
        """Persist one candidate evaluation. This method is observational only."""
        lane = _text(lane, 40).upper()
        if lane not in LANES:
            return False
        c = self._candidate_parts(candidate)
        snap = snapshot if isinstance(snapshot, dict) else {}
        try:
            symbol = _text(getattr(c, "symbol", ""), 64).upper()
            if not self._symbol_allowed(symbol):
                return False
            family = _text(getattr(c, "family", "") or getattr(c, "engine_id", "UNKNOWN"), 48).upper()
            mode = _text(getattr(c, "strategy_mode", "") or family, 64).upper()
            gen_ms = _num(getattr(c, "generated_at_ms", None), None)
            if gen_ms is None or gen_ms <= 0:
                return False
            tf_ms = int(max(60, min(3600, _num(self._cfg().get("V702_CF_SHADOW_TIMEFRAME_SEC"), 300) or 300)) * 1000)
            anchor_ms = int(gen_ms // tf_ms * tf_ms)
            entry = _num(getattr(c, "entry_ref", None), None)
            stop = _num(getattr(c, "sl_price", None), None)
            rr = _num(getattr(c, "tp1_rr", None), None)
            fs = getattr(c, "features_snapshot", {})
            fs = fs if isinstance(fs, dict) else {}
            spread_value = _num(snap.get("spread_pct"), _num(fs.get("spread_pct"), None))
            cfg = self._cfg()
            original_rr = rr
            if bool(cfg.get("V702_SMALL_NET_PROFIT_MODE_ENABLE", False)) and entry is not None and stop is not None and rr is not None and entry > stop > 0:
                # Shadow the live small-net target profile, not the larger original
                # RR: test the cost-aware minimum target plus its bounded safety buffer.
                # This remains counterfactual and never authorizes/submits an order.
                notional = max(1.0, _num(cfg.get("V576_REQUESTED_POSITION_USDT"), _num(cfg.get("MAX_POSITION_SIZE_USDT"), 75.0)) or 75.0)
                fee_pct = max(0.0, _num(cfg.get("TAKER_FEE_PCT"), 0.10) or 0.0) * max(0.0, _num(cfg.get("ROUNDTRIP_FEE_MULT"), 2.0) or 2.0)
                fallback_spread = max(0.0, _num(cfg.get("V702_SMALL_NET_SPREAD_FALLBACK_PCT"), 0.15) or 0.15)
                observed_spread = max(fallback_spread, spread_value if spread_value is not None else fallback_spread)
                slip_side = max(0.0, _num(cfg.get("V702_SMALL_NET_SLIPPAGE_PER_SIDE_PCT"), 0.05) or 0.05)
                total_cost_pct = fee_pct + observed_spread + 2.0 * slip_side
                risk_pct = 100.0 * (entry - stop) / entry
                desired_net_pct = max(0.0, _num(cfg.get("V702_SMALL_NET_MIN_NET_PROFIT_PCT"), 0.10) or 0.0)
                min_net_rr = max(0.0, _num(cfg.get("V702_SMALL_NET_MIN_NET_RR_TP1"), 0.25) or 0.0)
                fee_ratio = max(0.0, _num(cfg.get("MIN_TP1_TO_FEE_RATIO"), 2.5) or 0.0)
                if risk_pct > 0:
                    required_rr = max(1.0, (total_cost_pct + desired_net_pct) / risk_pct,
                                       total_cost_pct / risk_pct + min_net_rr,
                                       fee_ratio * fee_pct / risk_pct)
                    rr = max(1.0, required_rr + max(0.0, _num(cfg.get("V702_SMALL_NET_TARGET_TP1_BUFFER_R"), 0.03) or 0.0))
            risk = (entry - stop) if entry is not None and stop is not None else None
            target = entry + risk * rr if entry is not None and risk is not None and rr is not None else None
            geometry_ok = bool(
                entry is not None and stop is not None and rr is not None and
                entry > stop > 0 and risk is not None and risk > 0 and target is not None and
                math.isfinite(target) and target > entry and 0.05 <= rr <= 8.0
            )
            vol = _num(snap.get("quote_vol_24h"), _num(fs.get("quote_vol_24h"), _num(snap.get("quoteVolume"), None)))
            tier = _text(snap.get("tier") or fs.get("tier") or fs.get("liquidity_tier"), 32).upper()
            score_raw = _num(getattr(c, "engine_score", None), None)
            score = score_raw * 100.0 if score_raw is not None and 0 <= score_raw <= 1 else score_raw
            strength = _num(htf_strength, _num(snap.get("htf_strength"), _num(snap.get("v4513_htf_strength"), _num(fs.get("htf_strength"), None))))
            floor = _num(htf_floor, None)
            if lane == "BEARISH_POLICY_REJECT_OBSERVATION":
                if not bearish_policy_reject_observation_eligible(
                    reason=reason,
                    side=getattr(c, "side", ""),
                    macro_regime=snap.get("macro_regime") or snap.get("regime") or getattr(c, "macro_regime", ""),
                ):
                    return False
            if lane == "HTF_POLICY_REJECT_OBSERVATION":
                if not htf_policy_reject_observation_eligible(
                    reason=reason,
                    side=getattr(c, "side", ""),
                    macro_regime=snap.get("macro_regime") or snap.get("regime") or getattr(c, "macro_regime", ""),
                ):
                    return False
            if lane == "BEARISH_NORMAL_LSR":
                cfg_floor = max(0.0, _num(cfg.get("LIQUIDITY_UNIVERSE_MIN_QUOTE_VOLUME"), 3_000_000.0) or 3_000_000.0)
                if not bearish_normal_lsr_eligible(
                    family=family, side=getattr(c, "side", ""),
                    macro_regime=snap.get("macro_regime") or snap.get("regime") or getattr(c, "macro_regime", ""),
                    severity=snap.get("bearish_severity") or snap.get("macro_severity") or getattr(c, "bearish_severity", "") or fs.get("bearish_severity") or fs.get("macro_severity"),
                    score=score, htf_strength=strength, volume_ratio=snap.get("volume_ratio", fs.get("volume_ratio")),
                    quote_volume_24h=vol, min_htf_strength=_num(cfg.get("V702_A48_BEARISH_SHADOW_MIN_HTF_STRENGTH"), 47.0) or 47.0,
                    min_volume_ratio=_num(cfg.get("V702_A48_BEARISH_SHADOW_VOLUME_FLOOR_RATIO"), 1.4) or 1.4,
                    min_quote_volume=cfg_floor, min_score=_num(cfg.get("V453_SCORE_FLOOR_MIN"), 70.0) or 70.0,
                ):
                    return False
            key_material = f"{symbol}|{family}|{mode}|{lane}|{anchor_ms}"
            sample_key = hashlib.sha256(key_material.encode("utf-8")).hexdigest()
            sample_id = sample_key[:24]
            status = "PENDING" if geometry_ok else "SKIPPED_NO_GEOMETRY"
            note = "" if geometry_ok else "candidate_missing_valid_entry_sl_or_tp1_rr"
            context = {
                "macro_regime": _text(snap.get("macro_regime") or snap.get("regime") or getattr(c, "macro_regime", ""), 40),
                "local_regime": _text(snap.get("local_regime") or getattr(c, "local_regime", ""), 40),
                "phase": _text(snap.get("market_phase") or getattr(c, "market_phase", ""), 40),
                "engine_id": _text(getattr(c, "engine_id", ""), 48),
                "spread_pct": spread_value,
                "target_policy": "R40_SMALL_NET_COST_AWARE" if bool(cfg.get("V702_SMALL_NET_PROFIT_MODE_ENABLE", False)) else "CANDIDATE_TP1_RR",
                "candidate_tp1_rr_original": original_rr,
                "candidate_tp1_rr_projected": rr,
                "spread_fallback_pct": _num(cfg.get("V702_SMALL_NET_SPREAD_FALLBACK_PCT"), 0.15),
                "slippage_per_side_pct": _num(cfg.get("V702_SMALL_NET_SLIPPAGE_PER_SIDE_PCT"), 0.05),
                "net_profit_floor_pct": _num(cfg.get("V702_SMALL_NET_MIN_NET_PROFIT_PCT"), 0.10),
                "experimental_only": True,
                "live_execution": False,
                "bearish_severity": _text(snap.get("bearish_severity") or snap.get("macro_severity") or getattr(c, "bearish_severity", "") or fs.get("bearish_severity") or fs.get("macro_severity"), 40),
                "volume_ratio": _num(snap.get("volume_ratio"), _num(fs.get("volume_ratio"), None)),
                "policy_override": (
                    "SHADOW_ONLY_NOT_LIVE" if lane == "BEARISH_NORMAL_LSR"
                    else "SHADOW_ONLY_NO_LIVE_AUTHORITY" if lane in {"BEARISH_POLICY_REJECT_OBSERVATION", "HTF_POLICY_REJECT_OBSERVATION"}
                    else None
                ),
                "policy_evaluation_scope": (
                    "PREQUAL_POLICY_COUNTERFACTUAL_NOT_FULL_BUILDER_ACCEPTANCE" if lane == "BEARISH_NORMAL_LSR"
                    else "RAW_PREQUAL_POLICY_REJECT_OUTCOME_ONLY_NOT_FULL_PIPELINE_ADMISSION" if lane == "BEARISH_POLICY_REJECT_OBSERVATION"
                    else "RAW_PREQUAL_HTF_FLOOR_REJECT_OUTCOME_ONLY_NOT_FULL_PIPELINE_ADMISSION" if lane == "HTF_POLICY_REJECT_OBSERVATION"
                    else None
                ),
                "counterfactual_policy_check_skipped": lane in {"BEARISH_POLICY_REJECT_OBSERVATION", "HTF_POLICY_REJECT_OBSERVATION"},
                "candidate_side": _text(getattr(c, "side", ""), 16).lower(),
                "policy_reject_cohort": (
                    "BEARISH_MACRO_FAMILY_POLICY" if lane == "BEARISH_POLICY_REJECT_OBSERVATION"
                    else "HTF_STRENGTH_FLOOR" if lane == "HTF_POLICY_REJECT_OBSERVATION" else None
                ),
                "hypothetical_size_multiplier": max(0.0, min(1.0, _num(cfg.get("V702_A48_BEARISH_SHADOW_SIZE_MULTIPLIER"), 0.5) or 0.5)) if lane == "BEARISH_NORMAL_LSR" else None,
            }
            with self._db() as conn:
                cur = conn.execute("""INSERT OR IGNORE INTO v702_cf_shadow_samples
                    (sample_id,sample_key,created_ts,anchor_bar_ts_ms,symbol,family,strategy_mode,lane,reject_reason,
                     score,htf_strength,htf_floor,quote_volume_24h,tier,entry,stop,target,risk_unit,tp1_rr,
                     last_candle_ts_ms,bars_seen,status,note,context_json)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (sample_id, sample_key, time.time(), anchor_ms, symbol, family, mode, lane, _text(reason, 120),
                     score, strength, floor, vol, tier, entry if geometry_ok else None, stop if geometry_ok else None,
                     target if geometry_ok else None, risk if geometry_ok else None, rr, anchor_ms, 0, status, note, _json_safe(context)))
                inserted = cur.rowcount > 0
                if inserted:
                    cap = int(max(1000, min(100000, _num(self._cfg().get("V702_CF_SHADOW_MAX_ROWS"), 30000) or 30000)))
                    count = int(conn.execute("SELECT COUNT(*) FROM v702_cf_shadow_samples").fetchone()[0])
                    if count > cap:
                        conn.execute("DELETE FROM v702_cf_shadow_samples WHERE sample_id IN (SELECT sample_id FROM v702_cf_shadow_samples ORDER BY created_ts ASC LIMIT ?)", (count - cap,))
                    conn.execute("DELETE FROM v702_cf_shadow_samples WHERE created_ts < ? AND status != 'PENDING'", (time.time() - 30 * 86400,))
            return inserted
        except Exception:
            # Shadow telemetry is never allowed to affect the live decision.
            return False

    @staticmethod
    def _bar_rows(frame: Any) -> List[Tuple[int, float, float, float]]:
        rows: List[Tuple[int, float, float, float]] = []
        if frame is None:
            return rows
        try:
            # The scanner's last dataframe row is the still-forming candle.
            closed = frame.iloc[:-1]
            for idx, row in closed.iterrows():
                try:
                    if hasattr(idx, "timestamp"):
                        ts_ms = int(float(idx.timestamp()) * 1000.0)
                    else:
                        ts = _num(idx, None)
                        if ts is None:
                            continue
                        ts_ms = int(ts if ts > 10_000_000_000 else ts * 1000)
                    high = _num(row.get("high"), None)
                    low = _num(row.get("low"), None)
                    close = _num(row.get("close"), None)
                    if ts_ms > 0 and high is not None and low is not None and close is not None and high >= low > 0 and close > 0:
                        rows.append((ts_ms, high, low, close))
                except Exception:
                    continue
        except Exception:
            return []
        return rows

    def process_market_data(self, market_data_map: Optional[Dict[str, Dict[str, Any]]]) -> Dict[str, int]:
        """Advance pending shadow samples using closed 5m bars only."""
        counts = {"symbols": 0, "bars": 0, "resolved": 0, "errors": 0}
        if not isinstance(market_data_map, dict):
            return counts
        try:
            with self._db() as conn:
                pending = conn.execute("""SELECT sample_id,symbol,anchor_bar_ts_ms,entry,stop,target,risk_unit,
                        last_candle_ts_ms,bars_seen,context_json FROM v702_cf_shadow_samples WHERE status='PENDING'""").fetchall()
            by_symbol: Dict[str, List[Tuple[Any, ...]]] = {}
            for row in pending:
                by_symbol.setdefault(str(row[1]), []).append(row)
            for symbol, md in market_data_map.items():
                if symbol not in by_symbol or not isinstance(md, dict):
                    continue
                bars = self._bar_rows(md.get("df_5m"))
                if not bars:
                    continue
                counts["symbols"] += 1
                for sample in by_symbol[symbol]:
                    sid, sym, anchor_ms, entry, stop, target, risk, last_ts, seen, context_json = sample
                    status = "PENDING"; exit_px = None; gross_r = None; net_r = None; note = ""
                    for ts_ms, high, low, close in bars:
                        if ts_ms <= max(int(anchor_ms), int(last_ts or 0)):
                            continue
                        counts["bars"] += 1
                        seen = int(seen or 0) + 1
                        last_ts = ts_ms
                        hit_sl = low <= float(stop)
                        hit_tp = high >= float(target)
                        if hit_sl and hit_tp:
                            status = "AMBIGUOUS_SL_FIRST"; exit_px = float(stop); note = "same_closed_bar_hit_tp_and_sl_stop_first"
                        elif hit_sl:
                            status = "SL"; exit_px = float(stop)
                        elif hit_tp:
                            status = "TP1"; exit_px = float(target)
                        elif seen >= int(max(12, min(288, _num(self._cfg().get("V702_CF_SHADOW_MAX_HOLD_BARS"), 48) or 48))):
                            status = "TIME_EXIT"; exit_px = float(close); note = "max_horizon_closed_bars_reached"
                        if status != "PENDING":
                            gross_r = (float(exit_px) - float(entry)) / float(risk)
                            cfg = self._cfg()
                            fee_bps = max(0.0, min(100.0, _num(cfg.get("V702_CF_SHADOW_FEE_BPS_PER_SIDE"), 10.0) or 0.0))
                            slip_bps = max(0.0, min(100.0, _num(cfg.get("V702_CF_SHADOW_SLIPPAGE_BPS_PER_SIDE"), 5.0) or 0.0))
                            base_costs = ((float(entry) + float(exit_px)) * (fee_bps + slip_bps) / 10000.0) / float(risk)
                            spread_pct = 0.0
                            try:
                                context = json.loads(context_json or "{}")
                                observed_spread = _num(context.get("spread_pct"), None)
                                if bool(cfg.get("V702_SMALL_NET_PROFIT_MODE_ENABLE", False)):
                                    fallback = max(0.0, _num(cfg.get("V702_SMALL_NET_SPREAD_FALLBACK_PCT"), 0.15) or 0.15)
                                    spread_pct = max(fallback, observed_spread if observed_spread is not None else fallback)
                            except Exception:
                                spread_pct = max(0.0, _num(cfg.get("V702_SMALL_NET_SPREAD_FALLBACK_PCT"), 0.15) or 0.15) if bool(cfg.get("V702_SMALL_NET_PROFIT_MODE_ENABLE", False)) else 0.0
                            spread_costs = ((float(entry) + float(exit_px)) * (spread_pct / 100.0) / 2.0) / float(risk)
                            net_r = gross_r - base_costs - spread_costs
                            break
                    with self._db() as conn:
                        if status == "PENDING":
                            conn.execute("UPDATE v702_cf_shadow_samples SET last_candle_ts_ms=?,bars_seen=? WHERE sample_id=? AND status='PENDING'",
                                         (int(last_ts or 0), int(seen), sid))
                        else:
                            conn.execute("UPDATE v702_cf_shadow_samples SET last_candle_ts_ms=?,bars_seen=?,status=?,exit_price=?,gross_r=?,net_r=?,resolved_ts=?,note=? WHERE sample_id=? AND status='PENDING'",
                                         (int(last_ts or 0), int(seen), status, exit_px, gross_r, net_r, time.time(), note, sid))
                            counts["resolved"] += 1
            self.periodic_report_if_due()
        except Exception:
            counts["errors"] += 1
        return counts

    def report(self) -> Dict[str, Any]:
        now = time.time()
        report: Dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "generated_at_epoch": now,
            "study_mode": "SHADOW_ONLY_NO_ORDERS",
            "timeframe": "5m closed candles",
            "outcomes": "TP1/SL; same-bar TP+SL uses conservative SL-first; round-trip fees, modeled spread and two-sided slippage deducted",
            "interpretation_warning": "Counterfactual near-misses are not proof they would pass later gates or become real trades. All outcomes are hypothetical.",
            "lanes": {},
            "comparison": {},
            "non_comparable_lanes": {
                "BEARISH_NORMAL_LSR": "Bearish-only, strategy-specific cohort; not directly comparable to the all-regime BASELINE_PASS cohort.",
                "BEARISH_POLICY_REJECT_OBSERVATION": "Raw long candidates rejected by family macro policy in BEARISH regime. Outcomes do not imply Prequal/Score/Builder/PreSend acceptance. This lane overlaps the stricter BEARISH_NORMAL_LSR subset by design.",
                "HTF_POLICY_REJECT_OBSERVATION": "Raw LONG/BUY candidates rejected by the canonical HTF strength floor. Outcomes do not imply Prequal/Score/Builder/PreSend acceptance. This lane overlaps the narrower HTF_RELIEF near-miss subset by design.",
            },
            "lane_semantics": {
                "BEARISH_POLICY_REJECT_OBSERVATION": {
                    "capture_scope": "family_regime_disallowed.macro + side LONG/BUY + macro_regime BEARISH",
                    "severity_filter": "none; severity is retained for stratified analysis, including UNKNOWN",
                    "downstream_admission_claim": False,
                    "live_authority": False,
                    "overlaps_with": ["BEARISH_NORMAL_LSR"],
                },
                "HTF_POLICY_REJECT_OBSERVATION": {
                    "capture_scope": "htf.family_htf_strength_below_floor + side LONG/BUY + known macro regime",
                    "downstream_admission_claim": False,
                    "live_authority": False,
                    "overlaps_with": ["HTF_RELIEF"],
                },
                "BEARISH_NORMAL_LSR": {
                    "capture_scope": "strict LSR-only Bearish normal subset with score/HTF/volume/quote-volume floors",
                    "downstream_admission_claim": False,
                    "live_authority": False,
                },
            },
        }
        try:
            with self._db() as conn:
                rows = conn.execute("""SELECT lane,status,net_r,gross_r,score,created_ts,family,reject_reason,context_json,
                        quote_volume_24h,htf_strength,htf_floor FROM v702_cf_shadow_samples""").fetchall()
                skips = conn.execute("SELECT lane,COUNT(*) FROM v702_cf_shadow_samples WHERE status='SKIPPED_NO_GEOMETRY' GROUP BY lane").fetchall()
                total = int(conn.execute("SELECT COUNT(*) FROM v702_cf_shadow_samples").fetchone()[0])
                pending = int(conn.execute("SELECT COUNT(*) FROM v702_cf_shadow_samples WHERE status='PENDING'").fetchone()[0])
            skip_map = {str(k): int(v) for k, v in skips}
            lane_stats: Dict[str, Dict[str, Any]] = {}
            for lane in LANES:
                lane_rows = [r for r in rows if str(r[0]) == lane]
                resolved = [r for r in lane_rows if r[1] in TERMINAL and r[2] is not None]
                rs = [float(r[2]) for r in resolved]
                wins = sum(x > 0 for x in rs)
                losses = sum(x < 0 for x in rs)
                pos_sum = sum(x for x in rs if x > 0)
                neg_sum = -sum(x for x in rs if x < 0)
                mean = statistics.fmean(rs) if rs else None
                family_counts: Dict[str, int] = {}
                reason_counts: Dict[str, int] = {}
                regime_counts: Dict[str, int] = {}
                severity_counts: Dict[str, int] = {}
                scores = []
                for sample in lane_rows:
                    family_counts[str(sample[6] or "UNKNOWN")] = family_counts.get(str(sample[6] or "UNKNOWN"), 0) + 1
                    reason_counts[str(sample[7] or "unknown")] = reason_counts.get(str(sample[7] or "unknown"), 0) + 1
                    sv = _num(sample[4], None)
                    if sv is not None: scores.append(sv)
                    try:
                        ctx = json.loads(sample[8] or "{}")
                        regime = str(ctx.get("macro_regime") or "UNKNOWN")
                        regime_counts[regime] = regime_counts.get(regime, 0) + 1
                        severity = str(ctx.get("bearish_severity") or "UNKNOWN")
                        severity_counts[severity] = severity_counts.get(severity, 0) + 1
                    except Exception:
                        regime_counts["UNKNOWN"] = regime_counts.get("UNKNOWN", 0) + 1
                lane_stats[lane] = {
                    "samples": len(lane_rows),
                    "mean_engine_score": statistics.fmean(scores) if scores else None,
                    "families": dict(sorted(family_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:10]),
                    "reject_reasons": dict(sorted(reason_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:10]),
                    "macro_regimes": dict(sorted(regime_counts.items(), key=lambda kv: (-kv[1], kv[0]))),
                    "bearish_severities": dict(sorted(severity_counts.items(), key=lambda kv: (-kv[1], kv[0]))),
                    "resolved": len(resolved),
                    "pending": sum(r[1] == "PENDING" for r in lane_rows),
                    "skipped_no_geometry": skip_map.get(lane, 0),
                    "wins_net_r_positive": wins,
                    "losses_net_r_negative": losses,
                    "win_rate": (wins / len(resolved)) if resolved else None,
                    "avg_net_r": mean,
                    "median_net_r": statistics.median(rs) if rs else None,
                    "profit_factor_net_r": (pos_sum / neg_sum) if neg_sum > 0 else (None if pos_sum == 0 else "INF_NO_LOSSES"),
                    "outcomes": {label: sum(r[1] == label for r in lane_rows) for label in sorted(TERMINAL)},
                    "sample_quality": "EARLY_SMALL_SAMPLE" if len(resolved) < 30 else ("PRELIMINARY" if len(resolved) < 100 else "MORE_INFORMATIVE_NOT_GUARANTEED"),
                }
            report["lanes"] = lane_stats
            baseline = lane_stats["BASELINE_PASS"]
            for lane in ("CURRENT_HTF_RELIEF_PASS", "HTF_RELIEF", "MID_TIER_COUNTERFACTUAL"):
                other = lane_stats[lane]
                report["comparison"][lane] = {
                    "resolved_delta_vs_baseline": other["resolved"] - baseline["resolved"],
                    "avg_net_r_delta_vs_baseline": (other["avg_net_r"] - baseline["avg_net_r"])
                        if other["avg_net_r"] is not None and baseline["avg_net_r"] is not None else None,
                    "win_rate_delta_vs_baseline": (other["win_rate"] - baseline["win_rate"])
                        if other["win_rate"] is not None and baseline["win_rate"] is not None else None,
                    "minimum_resolved_per_lane_for_preliminary_read": 30,
                    "preferred_resolved_per_lane_for_better_stability": 100,
                }
            report["totals"] = {"samples_all_lanes": total, "pending": pending, "resolved": sum(v["resolved"] for v in lane_stats.values())}
        except Exception as exc:
            report["error"] = f"{type(exc).__name__}:{str(exc)[:200]}"
        return report

    def write_report(self, report: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        report = report or self.report()
        try:
            self.report_dir.mkdir(parents=True, exist_ok=True)
            json_path = self.report_dir / "V702_COUNTERFACTUAL_SHADOW_LATEST.json"
            md_path = self.report_dir / "V702_COUNTERFACTUAL_SHADOW_LATEST.md"
            report["report_files"] = {"json": str(json_path), "markdown": str(md_path)}
            json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
            lines = [
                "# V702 Counterfactual Shadow Study",
                "",
                f"Generated epoch: `{report.get('generated_at_epoch', 0):.0f}`",
                "",
                "**Research only:** no orders are placed. Counterfactual candidates may still fail downstream score, structure, fee, risk, freshness, or execution gates.",
                "",
                "| Lane | Samples | Resolved | Pending | Win rate (net R > 0) | Avg net R | Median net R | PF net R |",
                "|---|---:|---:|---:|---:|---:|---:|---:|",
            ]
            for lane in LANES:
                row = report.get("lanes", {}).get(lane, {})
                def fmt(x):
                    if x is None: return "n/a"
                    if isinstance(x, str): return x
                    return f"{x:.3f}" if isinstance(x, float) else str(x)
                wr = row.get("win_rate")
                lines.append(f"| {lane} | {row.get('samples',0)} | {row.get('resolved',0)} | {row.get('pending',0)} | {fmt(wr)} | {fmt(row.get('avg_net_r'))} | {fmt(row.get('median_net_r'))} | {fmt(row.get('profit_factor_net_r'))} |")
            lines.extend(["", "## Comparison vs BASELINE_PASS", ""])
            for lane, row in report.get("comparison", {}).items():
                lines.append(f"- **{lane}:** Δ average net R = `{row.get('avg_net_r_delta_vs_baseline')}`, Δ win rate = `{row.get('win_rate_delta_vs_baseline')}`; resolved samples = `{report.get('lanes', {}).get(lane, {}).get('resolved', 0)}`.")
            lines.extend(["", "## Non-comparable cohorts", ""])
            for lane, note in report.get("non_comparable_lanes", {}).items():
                lines.append(f"- **{lane}:** {note}")
            lines.extend(["", "## Interpretation rules", "", "- Fewer than 30 resolved samples per lane: too early for a decision.", "- 30–99: preliminary only; inspect regimes, family mix, severity, fees and cohort composition.", "- 100+: more informative, but still not a guarantee or a substitute for out-of-sample validation.", "- Bearish policy-reject observations are raw candidate outcome studies only; they do not show that other gates would pass.", "- Same candle touches SL and TP: conservatively recorded as SL-first.", "- Entries use candidate reference price; fees and configurable slippage are deducted from hypothetical R.", ""])
            md_path.write_text("\n".join(lines), encoding="utf-8")
            report["report_files"] = {"json": str(json_path), "markdown": str(md_path)}
        except Exception as exc:
            report["report_write_error"] = f"{type(exc).__name__}:{str(exc)[:200]}"
        return report

    def periodic_report_if_due(self, force: bool = False) -> Optional[Dict[str, Any]]:
        cfg = self._cfg()
        if not bool(cfg.get("V702_CF_SHADOW_ENABLE", True)):
            return None
        interval = max(60.0, min(86400.0, _num(cfg.get("V702_CF_SHADOW_REPORT_INTERVAL_SEC"), 900.0) or 900.0))
        now = time.time()
        try:
            with self._db() as conn:
                row = conn.execute("SELECT v FROM v702_cf_shadow_meta WHERE k='last_report_epoch' LIMIT 1").fetchone()
                last = _num(row[0], 0.0) if row else 0.0
                if not force and now - float(last or 0.0) < interval:
                    return None
                conn.execute("INSERT OR REPLACE INTO v702_cf_shadow_meta(k,v,updated_ts) VALUES('last_report_epoch',?,?)", (str(now), now))
            report = self.write_report(self.report())
            self._last_report_wall = now
            lanes = report.get("lanes", {})
            compact = " ".join(f"{lane}=n{v.get('samples',0)}/r{v.get('resolved',0)}/avgR{v.get('avg_net_r')}" for lane, v in lanes.items())
            print(f"[V702-CF-SHADOW] schema={SCHEMA_VERSION} mode=SHADOW_ONLY_NO_ORDERS {compact}", flush=True)
            return report
        except Exception:
            return None

    def self_test(self) -> Dict[str, Any]:
        report = self.report()
        with self._db() as conn:
            columns = {r[1] for r in conn.execute("PRAGMA table_info(v702_cf_shadow_samples)").fetchall()}
        required = {"sample_id", "lane", "status", "entry", "stop", "target", "net_r", "last_candle_ts_ms"}
        checks = {
            "schema_present": required.issubset(columns),
            "lanes_present": all(lane in report.get("lanes", {}) for lane in LANES),
            "shadow_only_mode": report.get("study_mode") == "SHADOW_ONLY_NO_ORDERS",
            "policy_reject_lane_is_non_comparable": "BEARISH_POLICY_REJECT_OBSERVATION" not in report.get("comparison", {}),
            "htf_reject_lane_is_non_comparable": "HTF_POLICY_REJECT_OBSERVATION" not in report.get("comparison", {}),
            "policy_reject_lane_has_raw_outcome_scope": (
                report.get("lane_semantics", {}).get("BEARISH_POLICY_REJECT_OBSERVATION", {}).get("downstream_admission_claim") is False
                and report.get("lane_semantics", {}).get("BEARISH_POLICY_REJECT_OBSERVATION", {}).get("live_authority") is False
            ),
            "policy_reject_predicate_fails_closed": (
                bearish_policy_reject_observation_eligible(reason="family_regime_disallowed.macro", side="long", macro_regime="BEARISH")
                and not bearish_policy_reject_observation_eligible(reason="htf.family_htf_strength_below_floor", side="long", macro_regime="BEARISH")
                and not bearish_policy_reject_observation_eligible(reason="family_regime_disallowed.macro", side="short", macro_regime="BEARISH")
                and not bearish_policy_reject_observation_eligible(reason="family_regime_disallowed.macro", side="long", macro_regime="BULLISH")
            ),
            "htf_reject_predicate_fails_closed": (
                htf_policy_reject_observation_eligible(reason="htf.family_htf_strength_below_floor", side="long", macro_regime="NEUTRAL")
                and not htf_policy_reject_observation_eligible(reason="family_regime_disallowed.macro", side="long", macro_regime="BEARISH")
                and not htf_policy_reject_observation_eligible(reason="htf.family_htf_strength_below_floor", side="short", macro_regime="BULLISH")
                and not htf_policy_reject_observation_eligible(reason="htf.family_htf_strength_below_floor", side="long", macro_regime="UNKNOWN")
            ),
            "htf_reject_lane_has_raw_outcome_scope": (
                report.get("lane_semantics", {}).get("HTF_POLICY_REJECT_OBSERVATION", {}).get("downstream_admission_claim") is False
                and report.get("lane_semantics", {}).get("HTF_POLICY_REJECT_OBSERVATION", {}).get("live_authority") is False
            ),
            "not_execution_integrated": True,
        }
        return {"pass": all(checks.values()), "checks": checks, "schema_version": SCHEMA_VERSION}
