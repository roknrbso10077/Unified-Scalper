"""A20: make persisted shadow performance results discoverable and visible in logs."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

import main as bot
from v702_intraday_shadow import V702IntradayShadow


def test_a20_knowledge_report_exposes_db_path_and_family_timeframe_results(tmp_path):
    db = tmp_path / "edge.sqlite3"
    with patch.dict(bot.CONFIG, {"DB_PATH": str(db), "V702_KNOWLEDGE_EDGE_MIN_SAMPLES": 30}):
        bot.KnowledgeOutcomeLedger.ensure_schema()
        conn = sqlite3.connect(str(db))
        for i, (first, final) in enumerate((("TP1", "TP3"), ("SL", "SL"), ("TP2", "SL_AFTER_TP2")), 1):
            conn.execute("""INSERT INTO knowledge_outcomes
                (alert_id,alerted_at,symbol,family,strategy_mode,strategy_style,timeframe_profile,
                 entry,sl,risk_unit,tp1,tp2,tp3,tp1_rr,tp2_rr,tp3_rr,status,first_event,final_outcome,
                 entry_triggered_at,created_at,updated_at,reviewed_score,volume_ratio,htf,rs,chase_atr,tier,
                 max_mfe_r,max_mae_r,tp1_hit_at,tp2_hit_at,tp3_hit_at,sl_hit_at,first_touch_label,terminal_label)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (f"alert-{i}", 1000.0+i, "BTC/USDT", "PULLBACK", "PULLBACK", "SCALP", "15M_5M",
                 100.0, 98.0, 2.0, 102.0, 104.0, 106.0, 1.0, 2.0, 3.0, "FINAL", first, final,
                 1001.0+i, 1000.0+i, 1000.0+i, 92.0, 1.6, 90.0, 0.01, 0.2, "MID",
                 1.5, -0.5, 1002.0 if first in {"TP1", "TP2"} else None,
                 1003.0 if first == "TP2" else None, 1004.0 if final == "TP3" else None,
                 1005.0 if str(final).startswith("SL") else None,
                 "WIN" if first in {"TP1", "TP2", "TP3"} else "LOSS",
                 "WIN" if final == "TP3" else "LOSS"))
        conn.commit(); conn.close()
        report = bot.KnowledgeOutcomeLedger._edge_report()
        assert report["database_path"] == str(db.resolve())
        assert report["database_total_alert_rows"] == 3
        assert report["database_finalized_alert_rows"] == 3
        assert "PULLBACK|STYLE=SCALP|TF=15M_5M" in report["by_family_timeframe"]
        group = report["by_family_timeframe"]["PULLBACK|STYLE=SCALP|TF=15M_5M"]
        assert group["entries"] == 3
        assert group["sample_sufficient"] is False
        assert report["overall"]["modeled_realized_count"] >= 1


def test_a20_intraday_report_exports_db_and_report_paths(tmp_path):
    db = tmp_path / "intraday.sqlite3"
    out = tmp_path / "reports"
    service = V702IntradayShadow(str(db), str(out))
    report = service.write_report(service.report())
    assert report["live_execution"] is False
    assert report["db_path"] == str(db.resolve())
    assert Path(report["report_files"]["json"]).is_file()
    assert Path(report["report_files"]["markdown"]).is_file()
    disk = json.loads(Path(report["report_files"]["json"]).read_text(encoding="utf-8"))
    assert disk["db_path"] == str(db.resolve())
    assert disk["report_files"]["markdown"] == report["report_files"]["markdown"]


def test_a20_strategy_stats_are_in_periodic_logs_and_no_gates_are_relaxed():
    source = Path(bot.__file__).read_text(encoding="utf-8")
    assert "[V702-KNOWLEDGE-DB] path=%s" in source
    assert "[V702-KNOWLEDGE-FAMILY-TF]" in source
    assert "STRATEGY × TIMEFRAME EDGE — SHADOW ONLY" in source
    assert "[V702-KNOWLEDGE-TELEGRAM]" in source
    assert "_tf_section" in source and "_db_path_for_tg" in source
    assert "expectancy_net_R=%s" in source and "profit_factor_net_R=%s" in source and "max_drawdown_R=%s" in source
    assert bot.V702_A20_CANONICAL_REVISION.endswith("A20-STRATEGY-TIMEFRAME-EDGE-LOGGING")
    assert bot.V702_PACKAGE_AUDIT_REVISION.startswith(bot.V702_A21_CANONICAL_REVISION)
    assert bot.CONFIG.get("MIN_LIVE_SCORE", 0) >= 70
    assert bot.CONFIG.get("LONG_ONLY") is True
    assert bot.FINAL_CANONICAL_RUNTIME.get("hard_gate_bypass") is False
    assert bot._v702_a20_terminal_self_test()["pass"]
