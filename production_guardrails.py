"""V702 R39 production guardrails.

Read-only expansion shadow accounting, a fail-closed portfolio drawdown latch,
and an explicit new-entry opt-in gate. This module is installed by main.py and
never changes strategy admission thresholds or calls an order API itself.
"""
from __future__ import annotations

import asyncio
import hashlib
import functools
import json
import math
import os
import sqlite3
import threading
import time
from collections import deque
from typing import Any, Dict, Optional, Tuple

from v702_core__policy__forbidden_assets import HARD_FORBIDDEN_BASES
from v702_core__storage__sqlite_writer import SQLITE_WRITER_LOCK

LIVE_OPT_IN_ENV = "UNIFIED_ALLOW_LIVE_TRADING"
LIVE_OPT_IN_TOKEN = "I_ACCEPT_LIVE_RISK"
DEFAULT_DRAWDOWN_PCT = 5.0




def _sqlite_serialized(method):
    """Serialize synchronous DB work through the process-wide writer lock."""
    @functools.wraps(method)
    def _wrapped(self, *args, **kwargs):
        with SQLITE_WRITER_LOCK:
            return method(self, *args, **kwargs)
    _wrapped._v702_sqlite_single_writer = True
    return _wrapped

def _num(value: Any, default: float = 0.0) -> float:
    try:
        x = float(value)
        return x if math.isfinite(x) else default
    except Exception:
        return default


def _symbol_base(symbol: str) -> str:
    s = str(symbol or "").strip().upper().replace("-", "/").replace("_", "/")
    if ":" in s:
        s = s.split(":", 1)[0]
    if "/" in s:
        return s.split("/", 1)[0]
    for suffix in ("USDT", "USDC", "BUSD", "USD"):
        if s.endswith(suffix) and len(s) > len(suffix):
            return s[:-len(suffix)]
    return s


class V702PortfolioDrawdownGuard:
    """Persistent account-equity high-water-mark halt for new entries only."""

    @staticmethod
    def db_path(ns: Dict[str, Any]) -> str:
        cfg = ns.get("CONFIG", {})
        return str(cfg.get("DB_PATH", "./unified_scalper.db"))

    @classmethod
    def _connect(cls, ns: Dict[str, Any], path: Optional[str] = None):
        db_path = path or cls.db_path(ns)
        parent = os.path.dirname(os.path.abspath(db_path))
        os.makedirs(parent, exist_ok=True)
        conn = sqlite3.connect(db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("""CREATE TABLE IF NOT EXISTS v702_portfolio_drawdown_state (
            singleton_id INTEGER PRIMARY KEY CHECK(singleton_id=1),
            peak_equity REAL NOT NULL,
            halted INTEGER NOT NULL DEFAULT 0,
            halt_ts REAL,
            halt_reason TEXT,
            last_equity REAL NOT NULL,
            last_drawdown_pct REAL NOT NULL DEFAULT 0,
            updated_ts REAL NOT NULL,
            last_reset_reason TEXT
        )""")
        # Additive migration for a DB created by an earlier R39 prerelease.
        columns = {str(r[1]) for r in conn.execute("PRAGMA table_info(v702_portfolio_drawdown_state)").fetchall()}
        if "last_reset_reason" not in columns:
            conn.execute("ALTER TABLE v702_portfolio_drawdown_state ADD COLUMN last_reset_reason TEXT")
        conn.commit()
        return conn

    @classmethod
    def evaluate_equity(cls, ns: Dict[str, Any], equity: float, threshold_pct: Optional[float] = None,
                        path: Optional[str] = None) -> Dict[str, Any]:
        """Record an observed equity value and return the sticky drawdown state."""
        equity = _num(equity, -1.0)
        if equity <= 0:
            return {"ok": False, "allowed": False, "reason": "equity_invalid", "equity": equity}
        cfg = ns.get("CONFIG", {})
        threshold = _num(threshold_pct, _num(cfg.get("V702_PORTFOLIO_DRAWDOWN_LIMIT_PCT", DEFAULT_DRAWDOWN_PCT)))
        if not 0.1 <= threshold <= 50.0:
            return {"ok": False, "allowed": False, "reason": "drawdown_threshold_invalid", "equity": equity}
        now = time.time()
        with SQLITE_WRITER_LOCK:
            conn = cls._connect(ns, path)
            try:
                row = conn.execute("SELECT * FROM v702_portfolio_drawdown_state WHERE singleton_id=1").fetchone()
                if row is None:
                    peak = equity
                    halted = 0
                    halt_ts = None
                    halt_reason = None
                else:
                    peak = max(_num(row["peak_equity"], equity), equity)
                    halted = int(row["halted"] or 0)
                    halt_ts = row["halt_ts"]
                    halt_reason = row["halt_reason"]
                drawdown = max(0.0, (peak - equity) / peak * 100.0) if peak > 0 else 100.0
                if not halted and drawdown + 1e-9 >= threshold:
                    halted = 1
                    halt_ts = now
                    halt_reason = f"peak_drawdown_{drawdown:.4f}_pct_ge_{threshold:.4f}_pct"
                conn.execute("""INSERT INTO v702_portfolio_drawdown_state
                    (singleton_id,peak_equity,halted,halt_ts,halt_reason,last_equity,last_drawdown_pct,updated_ts)
                    VALUES (1,?,?,?,?,?,?,?)
                    ON CONFLICT(singleton_id) DO UPDATE SET
                        peak_equity=excluded.peak_equity, halted=excluded.halted,
                        halt_ts=excluded.halt_ts, halt_reason=excluded.halt_reason,
                        last_equity=excluded.last_equity, last_drawdown_pct=excluded.last_drawdown_pct,
                        updated_ts=excluded.updated_ts""",
                    (peak, halted, halt_ts, halt_reason, equity, drawdown, now))
                conn.commit()
                return {"ok": True, "allowed": not bool(halted), "halted": bool(halted),
                        "peak_equity": peak, "equity": equity, "drawdown_pct": drawdown,
                        "threshold_pct": threshold, "halt_reason": halt_reason,
                        "updated_ts": now}
            finally:
                conn.close()
    # Shared short-lived ticker cache. Prices are cached per base asset so the
    # portfolio guard never downloads the entire market on every entry attempt.
    _equity_ticker_cache: Dict[str, Tuple[float, float]] = {}
    _equity_ticker_cache_lock = threading.RLock()

    @classmethod
    async def equity_usdt(cls, exchange, ns: Optional[Dict[str, Any]] = None) -> Tuple[Optional[float], str]:
        """Conservatively value holdings in USDT using a fresh shared balance snapshot.

        Only explicitly configured assets may be excluded. Unpriced holdings fail
        closed. Tickers are fetched for the exact missing symbols and cached for
        at most ten seconds; a full-market ticker download is never the fallback.
        """
        ns = ns if isinstance(ns, dict) else {}
        cfg = ns.get("CONFIG", {}) if isinstance(ns.get("CONFIG", {}), dict) else {}
        stats = ns.get("STATS", {}) if isinstance(ns.get("STATS", {}), dict) else {}
        safe_call = ns.get("safe_api_call")

        async def _call(label: str, factory):
            if callable(safe_call):
                value = safe_call(label, factory, retry_safe=True)
            else:
                value = factory()
            if asyncio.iscoroutine(value) or hasattr(value, "__await__"):
                return await value
            return value

        try:
            # A freshly fetched REAL balance from execution preflight is the
            # single shared snapshot. It contains account-wide totals, not just
            # free USDT, and is valid for no more than ten seconds.
            snapshot = stats.get("v702_equity_balance_snapshot")
            now = time.time()
            balance = None
            if isinstance(snapshot, dict):
                stamp = _num(snapshot.get("ts"), 0.0)
                age = now - stamp
                if 0.0 <= age <= 10.0 and snapshot.get("state") == "REAL":
                    balance = {
                        "total": dict(snapshot.get("total") or {}),
                        "free": dict(snapshot.get("free") or {}),
                        "used": dict(snapshot.get("used") or {}),
                    }
            if balance is None:
                fetch_balance = getattr(exchange, "fetch_balance", None)
                if not callable(fetch_balance):
                    return None, "account_valuation_api_unavailable"
                balance = await _call("portfolio_drawdown_fetch_balance", fetch_balance)
                if not isinstance(balance, dict):
                    return None, "balance_payload_invalid"

            totals = balance.get("total")
            if not isinstance(totals, dict) or not totals:
                free_map = balance.get("free") or {}
                used_map = balance.get("used") or {}
                if not isinstance(free_map, dict) or not isinstance(used_map, dict):
                    return None, "balance_totals_missing"
                totals = {k: _num(free_map.get(k)) + _num(used_map.get(k))
                          for k in set(free_map) | set(used_map)}

            raw_ignore = cfg.get("V702_EQUITY_IGNORE_ASSETS", ())
            if isinstance(raw_ignore, str):
                raw_ignore = [x.strip() for x in raw_ignore.split(",") if x.strip()]
            ignored = {str(x).strip().upper() for x in (raw_ignore or ()) if str(x).strip()}
            holdings = {str(asset).upper(): _num(qty) for asset, qty in totals.items()
                        if _num(qty) > 1e-12 and str(asset).upper() not in ignored}
            if not holdings:
                return None, "no_positive_account_holdings"

            total_usdt = holdings.pop("USDT", 0.0)
            ttl = min(10.0, max(0.0, _num(cfg.get("V702_EQUITY_TICKER_CACHE_TTL_SEC", 10.0), 10.0)))
            prices: Dict[str, float] = {}
            missing = []
            with cls._equity_ticker_cache_lock:
                for asset in holdings:
                    cached = cls._equity_ticker_cache.get(asset)
                    if cached and ttl > 0.0 and 0.0 <= now - cached[1] <= ttl:
                        prices[asset] = cached[0]
                    else:
                        missing.append(asset)

            if missing:
                symbols = [f"{asset}/USDT" for asset in missing]
                fetched: Dict[str, Any] = {}
                fetch_tickers = getattr(exchange, "fetch_tickers", None)
                if callable(fetch_tickers):
                    try:
                        payload = await _call("portfolio_drawdown_fetch_tickers", lambda: fetch_tickers(symbols))
                        if isinstance(payload, dict):
                            fetched.update(payload)
                    except TypeError:
                        # An adapter without a symbols argument must expose
                        # fetch_ticker; intentionally do not fall back to the
                        # expensive unbounded fetch_tickers() form.
                        pass
                    except Exception:
                        pass
                fetch_ticker = getattr(exchange, "fetch_ticker", None)
                for asset, symbol in zip(missing, symbols):
                    ticker = fetched.get(symbol)
                    if not isinstance(ticker, dict) and callable(fetch_ticker):
                        try:
                            ticker = await _call(f"portfolio_drawdown_fetch_ticker_{asset}",
                                                 lambda symbol=symbol: fetch_ticker(symbol))
                        except Exception:
                            ticker = None
                    if not isinstance(ticker, dict):
                        continue
                    price = _num(ticker.get("last"), 0.0)
                    if price <= 0:
                        info = ticker.get("info") or {}
                        price = _num(info.get("lastPrice") or info.get("last") or info.get("price"), 0.0)
                    if price > 0 and math.isfinite(price):
                        prices[asset] = price
                        with cls._equity_ticker_cache_lock:
                            cls._equity_ticker_cache[asset] = (price, time.time())

            for asset, amount in holdings.items():
                price = prices.get(asset)
                if price is None or price <= 0:
                    return None, f"unpriced_asset:{asset}"
                total_usdt += amount * price

            if not math.isfinite(total_usdt) or total_usdt <= 0:
                return None, "account_equity_nonpositive"
            if ignored:
                stats["v702_equity_ignored_assets_last"] = sorted(ignored)
            stats["v702_equity_last_valuation"] = {
                "equity_usdt": float(total_usdt), "valued_assets": len(holdings) + 1,
                "ignored_assets": sorted(ignored), "ticker_cache_ttl_sec": ttl,
                "ts": time.time(), "source": "SHARED_BALANCE_AND_SYMBOL_TICKERS",
            }
            return total_usdt, "ok"
        except Exception as exc:
            return None, f"account_valuation_error:{type(exc).__name__}:{str(exc)[:120]}"

    @classmethod
    async def authorize_entry(cls, ns: Dict[str, Any], exchange, symbol: str) -> Tuple[bool, str, Dict[str, Any]]:
        cfg = ns.get("CONFIG", {})
        env = ns.get("ENV", {})
        # A15 AUTHORITY-PARITY FIX:
        # The central mode resolver is the single authority for whether live
        # entries are permitted. In the user-requested pilot, V702_LIVE_PILOT_ENABLE
        # plus valid credentials/invariants is sufficient; the legacy token is
        # an alternative opt-in, not an additional mandatory token. Previously
        # this second gate required the legacy token unconditionally, silently
        # blocking every pilot order when only the configured pilot was active.
        refresh_mode = ns.get("_V702_R39_REFRESH_ENTRY_MODE")
        if callable(refresh_mode):
            try:
                monitor_only = bool(refresh_mode())
            except Exception as exc:
                return False, "entry_policy_authority_unverified", {
                    "monitor_only": True,
                    "error": f"{type(exc).__name__}:{str(exc)[:120]}",
                }
            if monitor_only:
                policy = str((ns.get("STATS", {}) or {}).get("v702_runtime_entry_policy", "MONITOR_ONLY_NO_NEW_BUYS"))
                return False, "monitor_only_entry_policy_or_invariants", {
                    "monitor_only": True,
                    "entry_policy": policy,
                    "legacy_opt_in_present": os.environ.get(LIVE_OPT_IN_ENV, "").strip() == LIVE_OPT_IN_TOKEN,
                    "pilot_configured": bool(cfg.get("V702_LIVE_PILOT_ENABLE", False)),
                    "forced_off": os.environ.get("UNIFIED_LIVE_PILOT_ENABLE", "").strip().lower() in {"0", "false", "no", "off", "disabled"},
                }
        else:
            # Missing canonical policy authority is an unconditional hard block.
            # The legacy token is diagnostic-only and must never become a fallback.
            return False, "entry_policy_authority_missing", {
                "monitor_only": True, "canonical_resolver_installed": False,
                "legacy_token_ignored": bool(os.environ.get(LIVE_OPT_IN_ENV, "").strip() == LIVE_OPT_IN_TOKEN),
            }
        if not env.get("MEXC_API_KEY") or not env.get("MEXC_API_SECRET"):
            return False, "live_credentials_missing", {"monitor_only": True}
        if not (bool(cfg.get("LONG_ONLY", True))
                and str(cfg.get("MARKET_TYPE", "SPOT")).upper() == "SPOT"
                and str(cfg.get("TRADING_SIDE", "LONG")).upper() == "LONG"
                and not bool(cfg.get("FUTURES_ENABLED", False))
                and not bool(cfg.get("ENABLE_FUTURES", False))
                and not bool(cfg.get("ALLOW_SHORT", False))
                and not bool(cfg.get("ALLOW_SHORTS", False))):
            return False, "live_invariant_violation_spot_long_only", {"monitor_only": True}
        if not bool(cfg.get("POSITION_MANAGER_TASK_ENABLE", True)):
            return False, "position_manager_required_for_live_entries", {"monitor_only": True}
        if "_v587_is_forbidden_coin" in ns:
            try:
                forbidden = ns["_v587_is_forbidden_coin"](symbol)
                if isinstance(forbidden, (tuple, list)) and forbidden and bool(forbidden[0]):
                    return False, "forbidden_asset_final_entry_guard", {"monitor_only": False}
            except Exception:
                return False, "forbidden_asset_check_failed_closed", {"monitor_only": False}
        if not bool(cfg.get("V702_PORTFOLIO_DRAWDOWN_GUARD_ENABLE", True)):
            return False, "portfolio_drawdown_guard_disabled_fail_closed", {"monitor_only": False}
        equity, valuation_reason = await cls.equity_usdt(exchange, ns=ns)
        if equity is None:
            return False, valuation_reason, {"monitor_only": False, "equity_valuation_ok": False}
        # SQLite work is deliberately offloaded; the event loop must remain
        # available for scan deadlines and runtime heartbeat emission.
        state = await asyncio.to_thread(cls.evaluate_equity, ns, equity)
        details = dict(state)
        details["equity_valuation_ok"] = True
        if not state.get("ok"):
            return False, str(state.get("reason") or "drawdown_state_error"), details
        if not state.get("allowed"):
            return False, "portfolio_peak_drawdown_latched", details
        return True, "portfolio_drawdown_ok", details

    # Build-time marker consumed by main.py's terminal A15 validator.
    authorize_entry.__func__._v702_a15_canonical_policy_parity = True

    @classmethod
    async def reset_latch(cls, ns: Dict[str, Any], exchange, reason: str) -> Dict[str, Any]:
        note = str(reason or "").strip()
        if len(note) < 10:
            return {"ok": False, "reason": "manual_reset_reason_must_be_at_least_10_chars"}
        equity, valuation_reason = await cls.equity_usdt(exchange, ns=ns)
        if equity is None:
            return {"ok": False, "reason": f"equity_valuation_failed:{valuation_reason}"}
        def _persist_reset():
            now = time.time()
            with SQLITE_WRITER_LOCK:
                conn = cls._connect(ns)
                try:
                    conn.execute("""INSERT INTO v702_portfolio_drawdown_state
                        (singleton_id,peak_equity,halted,halt_ts,halt_reason,last_equity,last_drawdown_pct,updated_ts,last_reset_reason)
                        VALUES (1,?,0,NULL,NULL,?,0,?,?)
                        ON CONFLICT(singleton_id) DO UPDATE SET peak_equity=excluded.peak_equity,
                            halted=0,halt_ts=NULL,halt_reason=NULL,last_equity=excluded.last_equity,
                            last_drawdown_pct=0,updated_ts=excluded.updated_ts,
                            last_reset_reason=excluded.last_reset_reason""", (equity, equity, now, note))
                    conn.commit()
                    return {"ok": True, "equity": equity, "new_peak_equity": equity, "reason": note, "reset_ts": now}
                finally:
                    conn.close()
        return await asyncio.to_thread(_persist_reset)


class V702ExpansionShadow:
    """Counterfactual journal for PREQUAL outcomes; never an admission authority."""

    TABLE = "v702_expansion_shadow"

    def __init__(self, ns: Dict[str, Any]):
        self.ns = ns
        self._lock = threading.Lock()
        self._pending = deque(maxlen=5000)
        self._dedupe = set()
        self._dedupe_order = deque()
        self._last_report_ts = 0.0
        self._last_error = ""

    def _db_path(self) -> str:
        return V702PortfolioDrawdownGuard.db_path(self.ns)

    def _connect(self, path: Optional[str] = None):
        db_path = path or self._db_path()
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        conn = sqlite3.connect(db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute(f"""CREATE TABLE IF NOT EXISTS {self.TABLE} (
            sample_id TEXT PRIMARY KEY, created_ts REAL NOT NULL, symbol TEXT NOT NULL,
            family TEXT NOT NULL, lane TEXT NOT NULL, source_reason TEXT NOT NULL,
            htf REAL, htf_floor REAL, score REAL, tier TEXT, quote_volume REAL,
            spread_pct REAL, entry REAL, sl REAL, tp1 REAL, tp2 REAL, tp3 REAL,
            risk REAL, status TEXT NOT NULL DEFAULT 'OPEN', first_event TEXT,
            final_outcome TEXT, tp1_hit INTEGER NOT NULL DEFAULT 0,
            tp2_hit INTEGER NOT NULL DEFAULT 0, tp3_hit INTEGER NOT NULL DEFAULT 0,
            sl_hit INTEGER NOT NULL DEFAULT 0, last_bar_ts INTEGER NOT NULL DEFAULT 0,
            bars_observed INTEGER NOT NULL DEFAULT 0, max_mfe_r REAL NOT NULL DEFAULT 0,
            max_mae_r REAL NOT NULL DEFAULT 0, net_r REAL, finished_ts REAL,
            method TEXT NOT NULL DEFAULT 'REFERENCE_ENTRY_ASSUMED_CLOSED_1M',
            updated_ts REAL NOT NULL
        )""")
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{self.TABLE}_status ON {self.TABLE}(status)")
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{self.TABLE}_lane ON {self.TABLE}(lane)")
        conn.commit()
        return conn

    @staticmethod
    def _dict(value: Any) -> Dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @classmethod
    def _get_num(cls, dicts, keys, default=0.0):
        for d in dicts:
            for key in keys:
                if key in d and d.get(key) is not None:
                    x = _num(d.get(key), default)
                    if x != default or str(d.get(key)).strip() in {"0", "0.0"}:
                        return x
        return default

    def record_prequal(self, ranked: Any, snapshots: Any, result: Any) -> None:
        """Queue a pass baseline or tightly scoped HTF/MID rejection for read-only study."""
        try:
            snap_map = snapshots if isinstance(snapshots, dict) else {}
            cand = getattr(ranked, "candidate", ranked)
            if cand is None:
                return
            symbol = str(getattr(cand, "symbol", "") or "").strip().upper()
            if not symbol:
                return
            snap_raw = snap_map.get(symbol) or snap_map.get(symbol.replace("/", "")) or {}
            snap = self._dict(snap_raw)
            feat = self._dict(getattr(cand, "features_snapshot", {}))
            ok = bool(result[0]) if isinstance(result, (tuple, list)) and result else bool(result)
            reason = str(result[1] if isinstance(result, (tuple, list)) and len(result) > 1 else ("" if ok else "unknown_reject"))[:240]
            reason_l = reason.lower()
            tier = str(feat.get("liquidity_tier") or feat.get("tier") or snap.get("liquidity_tier") or snap.get("tier") or "UNKNOWN").upper()
            # Crash, missing-data and unavailable-evidence rejections are never
            # HTF-relief candidates. They represent hard safety/data boundaries,
            # not discretionary trend strictness.
            _hard_exclusions = ("crash", "unavailable", "missing", "invalid", "short_history",
                                "data_gap", "not_ready", "stale", "malformed", "incomplete")
            if any(token in reason_l for token in _hard_exclusions):
                return
            if ok:
                lane = "BASELINE_PASS"
            elif any(t in reason_l for t in ("htf", "higher_timeframe", "higher-timeframe", "timeframe_floor", "trend_context")):
                lane = "HTF_RELIEF"
            elif tier == "MID" and any(t in reason_l for t in ("liquid", "tier", "volume", "depth", "quote")):
                lane = "MID_TIER_COUNTERFACTUAL"
            else:
                return
            entry = _num(getattr(cand, "entry_ref", 0.0), 0.0)
            sl = _num(getattr(cand, "sl_price", 0.0), 0.0)
            risk = entry - sl
            rr1 = _num(getattr(cand, "tp1_rr", 0.0), 0.0)
            rr2 = _num(getattr(cand, "tp2_rr", 0.0), 0.0)
            rr3 = _num(getattr(cand, "tp3_rr", 0.0), 0.0)
            geometry_ok = entry > 0 and sl > 0 and risk > 0 and rr1 > 0 and rr2 >= rr1 and rr3 >= rr2
            tp1 = entry + risk * rr1 if geometry_ok else 0.0
            tp2 = entry + risk * rr2 if geometry_ok else 0.0
            tp3 = entry + risk * rr3 if geometry_ok else 0.0
            if not geometry_ok:
                # Keep the rejection count but do not fabricate target prices.
                ns_stats = self.ns.get("STATS", {})
                ns_stats["v702_cf_shadow_missing_geometry"] = int(ns_stats.get("v702_cf_shadow_missing_geometry", 0) or 0) + 1
                return
            family = str(getattr(cand, "family", "") or getattr(cand, "strategy_mode", "") or "UNKNOWN").upper()
            generated = _num(getattr(cand, "generated_at_ms", 0), 0.0)
            stamp = int(generated) if generated > 0 else int(time.time() * 1000)
            cycle = _num((self.ns.get("STATS", {}) or {}).get("v681_runtime_cycle_id", 0), 0)
            sample_id = hashlib.sha256(f"{symbol}|{family}|{stamp}|{cycle}|{lane}|{reason}".encode()).hexdigest()[:32]
            if sample_id in self._dedupe:
                return
            now = time.time()
            htf = self._get_num((feat, snap), ("htf_score", "htf_strength", "htf", "htf_alignment"), 0.0)
            htf_floor = self._get_num((feat, snap), ("htf_floor", "min_htf_score", "required_htf_score"), 0.0)
            score = self._get_num((self._dict(ranked), feat, snap), ("score", "final_score", "reviewed_score", "strategy_score"), _num(getattr(cand, "engine_score", 0.0)) * 100.0)
            volume = self._get_num((feat, snap), ("quote_volume_usdt", "quote_volume", "volume_usdt_24h", "notional_volume", "quoteVolume"), 0.0)
            spread = self._get_num((feat, snap), ("spread_pct", "spread_percent", "spread_pct_estimate"), 0.0)
            row = (sample_id, now, symbol, family, lane, reason, htf, htf_floor, score, tier,
                   volume, spread, entry, sl, tp1, tp2, tp3, risk, "OPEN", None,
                   None, 0, 0, 0, 0, int(now // 60 * 60000), 0, 0.0, 0.0, None, None,
                   "REFERENCE_ENTRY_ASSUMED_CLOSED_1M", now)
            with self._lock:
                if len(self._pending) == self._pending.maxlen:
                    self.ns.get("STATS", {})["v702_cf_shadow_queue_drops"] = int(self.ns.get("STATS", {}).get("v702_cf_shadow_queue_drops", 0) or 0) + 1
                    return
                while len(self._dedupe) >= 20000 and self._dedupe_order:
                    self._dedupe.discard(self._dedupe_order.popleft())
                self._pending.append(row)
                self._dedupe.add(sample_id)
                self._dedupe_order.append(sample_id)
            stats = self.ns.get("STATS", {})
            stats["v702_cf_shadow_samples_queued"] = int(stats.get("v702_cf_shadow_samples_queued", 0) or 0) + 1
        except Exception as exc:
            stats = self.ns.get("STATS", {})
            stats["v702_cf_shadow_record_errors"] = int(stats.get("v702_cf_shadow_record_errors", 0) or 0) + 1
            self._last_error = f"{type(exc).__name__}:{str(exc)[:120]}"

    @_sqlite_serialized
    def _flush_sync(self) -> int:
        with self._lock:
            rows = list(self._pending)
            self._pending.clear()
        if not rows:
            return 0
        conn = self._connect()
        inserted = 0
        try:
            sql = f"""INSERT OR IGNORE INTO {self.TABLE} (
                sample_id,created_ts,symbol,family,lane,source_reason,htf,htf_floor,score,tier,
                quote_volume,spread_pct,entry,sl,tp1,tp2,tp3,risk,status,first_event,final_outcome,
                tp1_hit,tp2_hit,tp3_hit,sl_hit,last_bar_ts,bars_observed,max_mfe_r,max_mae_r,net_r,
                finished_ts,method,updated_ts) VALUES ({','.join(['?']*33)})"""
            for row in rows:
                cursor = conn.execute(sql, row)
                inserted += int(cursor.rowcount > 0)
            conn.commit()
            return inserted
        finally:
            conn.close()

    @staticmethod
    def _bar(bar: Any):
        if not isinstance(bar, (list, tuple)) or len(bar) < 6:
            return None
        ts = int(_num(bar[0], 0))
        o, h, l, c = (_num(bar[1]), _num(bar[2]), _num(bar[3]), _num(bar[4]))
        if ts <= 0 or min(o, h, l, c) <= 0 or h < l:
            return None
        return {"ts": ts, "open": o, "high": h, "low": l, "close": c}

    @_sqlite_serialized
    def _track_sync_rows(self, exchange_rows):
        conn = self._connect()
        now = time.time()
        try:
            for row, bars in exchange_rows:
                entry, sl, tp1, tp2, tp3, risk = (_num(row[k]) for k in ("entry", "sl", "tp1", "tp2", "tp3", "risk"))
                hit1, hit2, hit3, hit_sl = (int(row[k] or 0) for k in ("tp1_hit", "tp2_hit", "tp3_hit", "sl_hit"))
                status = str(row["status"] or "OPEN")
                first_event = row["first_event"]
                last_bar_ts = int(row["last_bar_ts"] or 0)
                bars_observed = int(row["bars_observed"] or 0)
                mfe = _num(row["max_mfe_r"]); mae = _num(row["max_mae_r"])
                terminal = None
                terminal_price = None
                fee_rate = max(0.0, _num(self.ns.get("CONFIG", {}).get("TAKER_FEE_PCT", 0.10))) / 100.0
                slip_rate = max(0.0, _num(self.ns.get("CONFIG", {}).get("V702_CF_SHADOW_SLIPPAGE_PCT", 0.10))) / 100.0
                runner = bool(self.ns.get("CONFIG", {}).get("ENABLE_RUNNER_MODE", True))
                w1 = max(0.0, min(1.0, _num(self.ns.get("CONFIG", {}).get("TP1_EXIT_PCT", 0.5), 0.5)))
                w2 = max(0.0, min(1.0, _num(self.ns.get("CONFIG", {}).get("TP2_EXIT_PCT", 0.3), 0.3)))
                w3 = max(0.0, min(1.0, _num(self.ns.get("CONFIG", {}).get("RUNNER_KEEP_PCT_AT_TP3", 0.2), 0.2))) if runner else 0.0
                for raw_bar in bars:
                    bar = self._bar(raw_bar)
                    if not bar or bar["ts"] <= last_bar_ts:
                        continue
                    # A closed 1m candle must have ended before wall-clock now.
                    if bar["ts"] + 60000 > int(now * 1000):
                        continue
                    last_bar_ts = bar["ts"]
                    bars_observed += 1
                    mfe = max(mfe, (bar["high"] - entry) / risk)
                    mae = min(mae, (bar["low"] - entry) / risk)
                    touch_sl = bar["low"] <= sl
                    touch1 = bar["high"] >= tp1
                    touch2 = bar["high"] >= tp2
                    touch3 = bar["high"] >= tp3
                    # Intrabar ordering cannot be recovered from OHLC. Use the
                    # conservative canonical policy shared by the Knowledge and
                    # Counterfactual ledgers: a same-bar SL/TP collision is SL-first.
                    if touch_sl:
                        hit_sl = 1
                        terminal = "SL_AFTER_TARGET" if (hit1 or hit2) else "SL"
                        terminal_price = sl
                        break
                    if touch3:
                        hit1 = hit2 = hit3 = 1
                        first_event = first_event or "TP1"
                        terminal = "TP3"
                        terminal_price = tp3
                        break
                    if touch2:
                        if not hit1:
                            hit1 = 1
                            first_event = first_event or "TP1"
                        hit2 = 1
                        if not runner:
                            terminal = "TP2"
                            terminal_price = tp2
                            break
                    elif touch1:
                        hit1 = 1
                        first_event = first_event or "TP1"
                if terminal is None and now - _num(row["created_ts"]) >= _num(self.ns.get("CONFIG", {}).get("V702_CF_SHADOW_MAX_HOLD_SEC", 14400), 14400):
                    terminal = "TIMEOUT"
                    if bars:
                        parsed = [self._bar(b) for b in bars]
                        parsed = [b for b in parsed if b and b["ts"] <= last_bar_ts]
                        terminal_price = parsed[-1]["close"] if parsed else entry
                    else:
                        terminal_price = entry
                if terminal is None:
                    conn.execute(f"""UPDATE {self.TABLE} SET tp1_hit=?,tp2_hit=?,tp3_hit=?,sl_hit=?,
                        first_event=?,last_bar_ts=?,bars_observed=?,max_mfe_r=?,max_mae_r=?,updated_ts=? WHERE sample_id=?""",
                        (hit1, hit2, hit3, hit_sl, first_event, last_bar_ts, bars_observed, mfe, mae, now, row["sample_id"]))
                    continue
                if terminal.startswith("AMBIGUOUS"):
                    net_r = None
                else:
                    risk_r = max(risk, 1e-12)
                    remaining = 1.0
                    gross = 0.0
                    weighted_exit = 0.0
                    if hit1:
                        q1 = min(remaining, w1); gross += q1 * (tp1-entry)/risk_r; weighted_exit += q1 * tp1; remaining -= q1
                    if hit2 and remaining > 1e-12:
                        q2 = min(remaining, w2 if runner else remaining); gross += q2 * (tp2-entry)/risk_r; weighted_exit += q2 * tp2; remaining -= q2
                    if terminal == "TP3" and remaining > 1e-12:
                        q3 = min(remaining, w3 if runner else remaining); gross += q3 * (tp3-entry)/risk_r; weighted_exit += q3 * tp3; remaining -= q3
                    if terminal == "SL":
                        gross -= remaining
                        weighted_exit += remaining * sl
                        remaining = 0.0
                    elif terminal == "SL_AFTER_TARGET":
                        # The live policy moves the residual stop to fee-covered BE
                        # after TP1; model residual at entry, not as another -1R.
                        weighted_exit += remaining * entry
                        remaining = 0.0
                    elif terminal == "TIMEOUT":
                        px = _num(terminal_price, entry)
                        gross += remaining * (px-entry)/risk_r
                        weighted_exit += remaining * px
                        remaining = 0.0
                    if terminal == "TP2" and not runner:
                        # TP2 closes all remaining size in non-runner mode.
                        if remaining > 1e-12:
                            gross += remaining * (tp2-entry)/risk_r
                            weighted_exit += remaining * tp2
                            remaining = 0.0
                    if terminal == "TP3" and remaining > 1e-12:
                        weighted_exit += remaining * tp3
                        gross += remaining * (tp3-entry)/risk_r
                    avg_exit = weighted_exit if weighted_exit > 0 else _num(terminal_price, entry)
                    cost_r = ((fee_rate + slip_rate) * (entry + avg_exit)) / risk_r
                    net_r = gross - cost_r
                conn.execute(f"""UPDATE {self.TABLE} SET status='CLOSED',tp1_hit=?,tp2_hit=?,tp3_hit=?,sl_hit=?,
                    first_event=?,final_outcome=?,last_bar_ts=?,bars_observed=?,max_mfe_r=?,max_mae_r=?,net_r=?,
                    finished_ts=?,updated_ts=? WHERE sample_id=?""",
                    (hit1, hit2, hit3, hit_sl, first_event, terminal, last_bar_ts, bars_observed, mfe, mae,
                     net_r, now, now, row["sample_id"]))
            conn.commit()
        finally:
            conn.close()

    @_sqlite_serialized
    def _fetch_open_rows_sync(self, limit: int):
        conn = self._connect()
        try:
            return conn.execute(
                f"SELECT * FROM {self.TABLE} WHERE status='OPEN' ORDER BY created_ts ASC LIMIT ?",
                (max(1, min(12, int(limit))),),
            ).fetchall()
        finally:
            conn.close()

    async def _poll_once(self, exchange) -> None:
        try:
            await asyncio.to_thread(self._flush_sync)
            max_rows = max(1, min(12, int(self.ns.get("CONFIG", {}).get("V702_CF_SHADOW_MAX_ROWS_PER_POLL", 8) or 8)))
            rows = await asyncio.to_thread(self._fetch_open_rows_sync, max_rows)
            for row in rows:
                age = time.time() - _num(row["created_ts"])
                if age >= _num(self.ns.get("CONFIG", {}).get("V702_CF_SHADOW_MAX_HOLD_SEC", 14400), 14400):
                    await asyncio.to_thread(self._track_sync_rows, [(row, [])])
                    continue
                fetch = getattr(exchange, "fetch_ohlcv", None)
                if not callable(fetch):
                    continue
                since = max(int(row["last_bar_ts"] or 0) + 60000, int(_num(row["created_ts"]) // 60 * 60000) + 60000)
                try:
                    value = fetch(str(row["symbol"]), timeframe="1m", since=since, limit=120)
                    bars = await value if asyncio.iscoroutine(value) else value
                    if isinstance(bars, list) and bars:
                        await asyncio.to_thread(self._track_sync_rows, [(row, bars)])
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    self._last_error = f"ohlcv:{type(exc).__name__}:{str(exc)[:120]}"
                    st = self.ns.get("STATS", {})
                    st["v702_cf_shadow_fetch_errors"] = int(st.get("v702_cf_shadow_fetch_errors", 0) or 0) + 1
            if time.time() - self._last_report_ts >= 900:
                report = await asyncio.to_thread(self.report)
                self.ns.get("STATS", {})["v702_cf_shadow_report"] = report
                self._last_report_ts = time.time()
                logger = self.ns.get("logger")
                if logger:
                    logger.info("[V702-CF-SHADOW] samples=%s lanes=%s method=closed_1m_reference_entry hard_gate_bypass=0",
                                report.get("total_samples", 0), json.dumps(report.get("lanes", {}), sort_keys=True))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._last_error = f"poll:{type(exc).__name__}:{str(exc)[:120]}"
            st = self.ns.get("STATS", {})
            st["v702_cf_shadow_task_errors"] = int(st.get("v702_cf_shadow_task_errors", 0) or 0) + 1

    async def task(self, exchange):
        try:
            while True:
                await self._poll_once(exchange)
                await asyncio.sleep(max(15.0, _num(self.ns.get("CONFIG", {}).get("V702_CF_SHADOW_INTERVAL_SEC", 30), 30)))
        except asyncio.CancelledError:
            raise

    def report(self, path: Optional[str] = None) -> Dict[str, Any]:
        conn = self._connect(path)
        try:
            rows = conn.execute(f"""SELECT lane,COUNT(*) AS n,
                SUM(CASE WHEN status='CLOSED' THEN 1 ELSE 0 END) AS closed,
                SUM(CASE WHEN final_outcome LIKE 'AMBIGUOUS%' THEN 1 ELSE 0 END) AS ambiguous,
                AVG(CASE WHEN status='CLOSED' THEN net_r END) AS avg_net_r
                FROM {self.TABLE} GROUP BY lane""").fetchall()
            lanes = {str(r["lane"]): {"samples": int(r["n"] or 0), "closed": int(r["closed"] or 0),
                     "ambiguous": int(r["ambiguous"] or 0), "avg_net_r": r["avg_net_r"]} for r in rows}
            total = conn.execute(f"SELECT COUNT(*) FROM {self.TABLE}").fetchone()[0]
            return {"scope": "PREQUAL_ONLY_COUNTERFACTUAL_NOT_FULL_BUILDER_ACCEPTANCE",
                    "method": "closed_1m_reference_entry_assumed_fee_and_slippage_modeled",
                    "total_samples": int(total or 0), "lanes": lanes,
                    "live_policy_changed": False, "hard_gate_bypass": False,
                    "last_error": self._last_error}
        finally:
            conn.close()


def install(ns: Dict[str, Any]) -> None:
    """Install once. Function identity of V702 observers/validators is preserved."""
    if ns.get("_V702_R39_GUARDRAILS_INSTALLED"):
        return
    cfg = ns["CONFIG"]
    stats = ns["STATS"]
    cfg.setdefault("V702_EXPANSION_SHADOW_ENABLE", True)
    cfg.setdefault("V702_CF_SHADOW_INTERVAL_SEC", 30.0)
    cfg.setdefault("V702_CF_SHADOW_MAX_ROWS_PER_POLL", 8)
    cfg.setdefault("V702_CF_SHADOW_MAX_HOLD_SEC", 14400.0)
    cfg.setdefault("V702_CF_SHADOW_SLIPPAGE_PCT", 0.10)
    cfg.setdefault("V702_PORTFOLIO_DRAWDOWN_GUARD_ENABLE", True)
    cfg.setdefault("V702_PORTFOLIO_DRAWDOWN_LIMIT_PCT", DEFAULT_DRAWDOWN_PCT)
    # The package configuration alone never arms live entries. A55/A56 still
    # require both explicit environment keys and all canonical hard gates.
    # The environment OFF value remains an independent emergency switch.
    cfg.setdefault("V702_LIVE_PILOT_ENABLE", True)
    cfg.setdefault("V702_A19_DIAGNOSTIC_ONLY_DEFAULT", False)
    ns["V702_A19_DIAGNOSTIC_ONLY_DEFAULT"] = False
    shadow = V702ExpansionShadow(ns)
    ns["V702PortfolioDrawdownGuard"] = V702PortfolioDrawdownGuard
    ns["V702ExpansionShadow"] = V702ExpansionShadow
    ns["_V702_R39_EXPANSION_SHADOW"] = shadow
    ns["_V702_R39_RECORD_PREQUAL"] = shadow.record_prequal

    def _refresh_mode() -> bool:
        env = ns.get("ENV", {})
        forbidden_set = set(ns.get("V702_HARD_FORBIDDEN_BASES", ()) or ())
        invariants_ok = bool(cfg.get("ENABLE_LIVE_TRADING", True)) and not bool(cfg.get("PAPER_TRADING_MODE", False)) \
            and bool(cfg.get("LONG_ONLY", True)) and str(cfg.get("MARKET_TYPE", "SPOT")).upper() == "SPOT" \
            and str(cfg.get("TRADING_SIDE", "LONG")).upper() == "LONG" \
            and not bool(cfg.get("FUTURES_ENABLED", False)) and not bool(cfg.get("ENABLE_FUTURES", False)) \
            and not bool(cfg.get("ALLOW_SHORT", False)) and not bool(cfg.get("ALLOW_SHORTS", False)) \
            and bool(cfg.get("POSITION_MANAGER_TASK_ENABLE", True)) \
            and bool(cfg.get("V702_PORTFOLIO_DRAWDOWN_GUARD_ENABLE", True)) \
            and int(cfg.get("MAX_CONCURRENT_TRADES", 2) or 0) in (1, 2) \
            and float(cfg.get("MIN_LIVE_SCORE", 70.0) or 0.0) >= 70.0 \
            and float(cfg.get("LIQUIDITY_UNIVERSE_MIN_QUOTE_VOLUME", 3_000_000.0) or 0.0) >= 3_000_000.0 \
            and forbidden_set.issuperset(HARD_FORBIDDEN_BASES) \
            and ("V702_R38_HARD_GATE_BYPASS" not in cfg or cfg.get("V702_R38_HARD_GATE_BYPASS") is False)
        control = os.environ.get("UNIFIED_LIVE_PILOT_ENABLE", "").strip().lower()
        forced_off = control in {"0", "false", "no", "off", "disabled"}
        pilot_enabled = bool(cfg.get("V702_LIVE_PILOT_ENABLE", True))
        token_opt_in = os.environ.get(LIVE_OPT_IN_ENV, "").strip() == LIVE_OPT_IN_TOKEN
        # A55/A56 have one authorization authority: the runtime helper that
        # verifies BOTH operator keys, live state, KillSwitch, entry block and
        # software-SL worker health when that stop mode is active. The legacy
        # token is recorded for diagnostics only and cannot arm this release.
        arm_check = ns.get("_v702_live_operator_armed")
        operator_armed = bool(callable(arm_check) and arm_check())
        explicit = (not forced_off) and pilot_enabled and operator_armed
        credentials = bool(env.get("MEXC_API_KEY") and env.get("MEXC_API_SECRET"))
        live_enabled = explicit and credentials and invariants_ok
        cfg["V702_MONITOR_ONLY_MODE"] = not live_enabled
        if live_enabled:
            policy = "USER_REQUESTED_LIVE_PILOT"
        else:
            policy = "MONITOR_ONLY_NO_NEW_BUYS"
        stats["v702_runtime_entry_policy"] = policy
        stats["v702_live_entry_opt_in_present"] = bool(explicit)
        stats["v702_live_operator_two_key_armed"] = bool(operator_armed)
        stats["v702_live_entry_token_opt_in_present"] = bool(token_opt_in)
        stats["v702_live_pilot_configured"] = bool(pilot_enabled)
        stats["v702_live_pilot_forced_off_by_env"] = bool(forced_off)
        stats["v702_live_entry_credentials_present"] = bool(credentials)
        stats["v702_spot_long_only_invariants_ok"] = bool(invariants_ok)
        return not live_enabled

    ns["_V702_R39_REFRESH_ENTRY_MODE"] = _refresh_mode
    ns["_V702_R39_AUTHORIZATION_POLICY_PARITY"] = True
    _refresh_mode()

    prior_submit = ns.get("_V702_SUBMIT_ENTRY_ORIGINAL")
    if callable(prior_submit) and not getattr(prior_submit, "_v702_r39_guarded", False):
        async def _v702_r39_submit_entry_guard(exchange, symbol, qty, price, *args, **kwargs):
            is_paper = bool(kwargs.get("is_paper", args[0] if args else False))
            if is_paper:
                return await prior_submit(exchange, symbol, qty, price, *args, **kwargs)
            # The actual OrderExecutor lifecycle self-test uses this exact local
            # fake exchange while a scoped flag is set. Permit only that mock path;
            # never relax authorization for a live or arbitrary exchange object.
            _wrapped_test_exchange = getattr(exchange, "_exchange", exchange)
            if bool(ns.get("V644_SELFTEST_ACTIVE", False)) and type(_wrapped_test_exchange).__name__ == "_V516MockExchange":
                return await prior_submit(exchange, symbol, qty, price, *args, **kwargs)
            # A19 diagnostic hold is opt-in. The default is live-pilot authorization,
            # still subject to credentials, emergency-off, portfolio risk and all hard gates.
            # This blocks only NEW live entries at the final submit boundary;
            # paper routing and existing-position protection/exit calls continue.
            a19_raw = os.environ.get("UNIFIED_A19_DIAGNOSTIC_ONLY", "0").strip().lower()
            a19_diagnostic_only = a19_raw not in {"0", "false", "no", "off", "disabled"}
            if a19_diagnostic_only:
                now = time.time()
                stats["v702_a19_diagnostic_live_entry_blocks"] = int(stats.get("v702_a19_diagnostic_live_entry_blocks", 0) or 0) + 1
                stats["v702_a19_diagnostic_only_effective"] = True
                stats["v702_a19_diagnostic_hold_last"] = {
                    "symbol": str(symbol or "")[:48], "reason": "a19_diagnostic_only_new_live_entries",
                    "ts": now, "existing_position_management_unchanged": True,
                }
                stats["last_send_fail_reason"] = "a19_diagnostic_only_new_live_entries"
                log = ns.get("logger")
                if log:
                    log.warning("[V702-A19-SAFETY] new live BUY blocked by explicit diagnostic hold symbol=%s; unset the hold or set UNIFIED_A19_DIAGNOSTIC_ONLY=0; exits/protection remain enabled", symbol)
                return False, None, 0.0
            stats["v702_a19_diagnostic_only_effective"] = False
            monitor_only = _refresh_mode()
            if monitor_only:
                reason = "monitor_only_live_entry_opt_in_missing_or_invariants_failed"
                stats["last_send_fail_reason"] = "monitor_only_new_live_buys"
                stats["v702_r39_last_entry_block_reason"] = reason
                stats["v702_monitor_only_entry_blocks"] = int(stats.get("v702_monitor_only_entry_blocks", 0) or 0) + 1
                log = ns.get("logger")
                if log:
                    log.critical("[V702-R39-SAFETY] live BUY blocked symbol=%s reason=%s; existing-position management remains enabled", symbol, reason)
                return False, None, 0.0
            allowed, reason, details = await V702PortfolioDrawdownGuard.authorize_entry(ns, exchange, symbol)
            stats["v702_portfolio_drawdown_last_check"] = {"symbol": str(symbol), "allowed": bool(allowed),
                                                            "reason": str(reason), "details": details, "ts": time.time()}
            if not allowed:
                stats["last_send_fail_reason"] = f"v702_r39_entry_guard:{reason}"
                stats["v702_r39_last_entry_block_reason"] = str(reason)
                stats["v702_portfolio_drawdown_entry_blocks"] = int(stats.get("v702_portfolio_drawdown_entry_blocks", 0) or 0) + 1
                log = ns.get("logger")
                if log:
                    log.critical("[V702-R39-SAFETY] live BUY blocked symbol=%s reason=%s details=%s", symbol, reason, json.dumps(details, default=str)[:500])
                try:
                    rejection = ns.get("record_rejection")
                    if callable(rejection):
                        rejection(kwargs.get("trace_id") or (args[1] if len(args) > 1 else "V702-R39"), str(symbol),
                                  "risk", f"v702_r39_entry_guard:{reason}", "portfolio_drawdown_guard", ctx=details)
                except Exception:
                    stats["v702_r39_rejection_telemetry_errors"] = int(stats.get("v702_r39_rejection_telemetry_errors", 0) or 0) + 1
                return False, None, 0.0
            return await prior_submit(exchange, symbol, qty, price, *args, **kwargs)
        _v702_r39_submit_entry_guard._v702_r39_guarded = True
        ns["_V702_R39_UNGUARDED_SUBMIT_ENTRY"] = prior_submit
        ns["_V702_SUBMIT_ENTRY_ORIGINAL"] = _v702_r39_submit_entry_guard
        ns["_V702_R39_SUBMIT_ENTRY_GUARD"] = _v702_r39_submit_entry_guard

    # The outcome ledger already owns the bounded read-only task lifecycle. Run
    # the extra tracker alongside it without replacing its existing authority.
    ledger = ns.get("KnowledgeOutcomeLedger")
    descriptor = getattr(ledger, "__dict__", {}).get("task") if ledger else None
    if ledger and isinstance(descriptor, classmethod) and not ns.get("_V702_R39_KNOWLEDGE_TASK_WRAPPED"):
        prior_task = descriptor.__func__
        async def _v702_r39_knowledge_and_expansion_task(cls, exchange):
            async def _knowledge():
                try:
                    return await prior_task(cls, exchange)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    stats["v702_knowledge_task_wrapper_errors"] = int(stats.get("v702_knowledge_task_wrapper_errors", 0) or 0) + 1
                    log = ns.get("logger")
                    if log:
                        log.warning("[V702-R39-SHADOW] existing knowledge task failed: %s:%s", type(exc).__name__, str(exc)[:120])
            async def _expansion():
                try:
                    if bool(cfg.get("V702_EXPANSION_SHADOW_ENABLE", True)):
                        await shadow.task(exchange)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    stats["v702_cf_shadow_task_wrapper_errors"] = int(stats.get("v702_cf_shadow_task_wrapper_errors", 0) or 0) + 1
                    log = ns.get("logger")
                    if log:
                        log.warning("[V702-R39-SHADOW] expansion shadow task failed: %s:%s", type(exc).__name__, str(exc)[:120])
            await asyncio.gather(_knowledge(), _expansion())
        ledger.task = classmethod(_v702_r39_knowledge_and_expansion_task)
        ns["_V702_R39_KNOWLEDGE_TASK_WRAPPED"] = True
        ns["_V702_R39_KNOWLEDGE_TASK_ORIGINAL"] = prior_task

    prior_run_bot = ns.get("run_bot")
    if callable(prior_run_bot) and not getattr(prior_run_bot, "_v702_r39_guarded", False):
        async def _v702_r39_run_bot(universe):
            monitor_only = _refresh_mode()
            log = ns.get("logger")
            if log:
                log.warning("[V702-R39-SAFETY] entry_policy=%s; LIVE BUY/API entry calls=%s; configured_live_pilot=%s forced_off=%s credentials=%s invariants=%s; exchange data, Telegram, and existing-position protection/exit management may continue",
                           stats.get("v702_runtime_entry_policy"), "BLOCKED" if monitor_only else "enabled after portfolio drawdown guard",
                           bool(cfg.get("V702_LIVE_PILOT_ENABLE", True)),
                           str(os.environ.get("UNIFIED_LIVE_PILOT_ENABLE", "")).strip().lower() in {"0", "false", "no", "off", "disabled"},
                           bool(ns.get("ENV", {}).get("MEXC_API_KEY") and ns.get("ENV", {}).get("MEXC_API_SECRET")),
                           bool(stats.get("v702_spot_long_only_invariants_ok", False)))
                log.warning("[V702-R39-SHADOW] HTF/MID counterfactual sampling is research-only; no prequalification threshold is changed")
            return await prior_run_bot(universe)
        _v702_r39_run_bot._v702_r39_guarded = True
        ns["_V702_R39_UNGUARDED_RUN_BOT"] = prior_run_bot
        ns["run_bot"] = _v702_r39_run_bot

    ns["_V702_R39_GUARDRAILS_INSTALLED"] = True
