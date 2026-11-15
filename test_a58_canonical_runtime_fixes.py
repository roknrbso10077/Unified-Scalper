"""A58 final audit regressions for build, hard-deny policy and SQLite async boundaries."""
from __future__ import annotations

import tempfile
from pathlib import Path

from v702_core__policy__forbidden_assets import HARD_FORBIDDEN_BASES, is_hard_forbidden
from v702_core__storage__sqlite_writer import SQLITE_WRITER_LOCK
from v702_intraday_shadow import V702IntradayShadow
from v702_counterfactual_shadow import V702CounterfactualShadow
import production_guardrails

ROOT = Path(__file__).resolve().parent


def test_hard_forbidden_asset_policy_is_single_shared_source():
    assert HARD_FORBIDDEN_BASES == frozenset({"AERO", "BNB", "CAKE", "ETHFI", "PUMP"})
    for base in HARD_FORBIDDEN_BASES:
        assert is_hard_forbidden(f"{base}/USDT")
        assert not V702CounterfactualShadow._symbol_allowed(f"{base}/USDT")
    assert V702CounterfactualShadow._symbol_allowed("BTC/USDT")
    assert V702IntradayShadow.__module__ == "v702_intraday_shadow"
    assert production_guardrails.HARD_FORBIDDEN_BASES is HARD_FORBIDDEN_BASES


def test_all_sqlite_runtime_lanes_share_one_writer_lock():
    import v702_intraday_shadow
    import v702_counterfactual_shadow

    assert v702_intraday_shadow.SQLITE_WRITER_LOCK is SQLITE_WRITER_LOCK
    assert v702_counterfactual_shadow.SQLITE_WRITER_LOCK is SQLITE_WRITER_LOCK
    assert production_guardrails.SQLITE_WRITER_LOCK is SQLITE_WRITER_LOCK
    assert getattr(production_guardrails.V702ExpansionShadow._flush_sync, "_v702_sqlite_single_writer", False)
    assert getattr(production_guardrails.V702ExpansionShadow._track_sync_rows, "_v702_sqlite_single_writer", False)
    assert getattr(production_guardrails.V702ExpansionShadow._fetch_open_rows_sync, "_v702_sqlite_single_writer", False)


def test_intraday_and_counterfactual_share_database_without_schema_conflict():
    with tempfile.TemporaryDirectory(prefix="a58-shadow-db-") as td:
        db = str(Path(td) / "shared.sqlite3")
        intraday = V702IntradayShadow(db, str(Path(td) / "reports"))
        counterfactual = V702CounterfactualShadow(db, str(Path(td) / "reports"))
        assert intraday.self_test().get("pass") is True
        assert counterfactual.self_test().get("pass") is True


def test_runtime_shadow_sqlite_is_offloaded_from_asyncio_loop():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    guardrails = (ROOT / "production_guardrails.py").read_text(encoding="utf-8")
    assert "await asyncio.to_thread(_service.process_symbol" in source
    assert "await asyncio.to_thread(_service.periodic_report_if_due)" in source
    assert "await asyncio.to_thread(fn, *args, **kwargs)" in source
    assert 'CONFIG.get("V702_CF_SHADOW_MAX_PENDING_IO", 16)' in source
    assert "min(64, float(CONFIG.get(\"V702_CF_SHADOW_MAX_PENDING_IO\", 16) or 16))" in source
    assert "await asyncio.to_thread(cls.evaluate_equity, ns, equity)" in guardrails
    assert "await asyncio.to_thread(self._fetch_open_rows_sync, max_rows)" in guardrails
    assert "await asyncio.to_thread(self._track_sync_rows" in guardrails


def test_docker_has_explicit_paper_and_strict_hash_install_paths():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "a65-production-audit.yml").read_text(encoding="utf-8")
    requirements = (ROOT / "requirements.in").read_text(encoding="utf-8")
    assert "ARG STRICT_HASH_LOCK=0" in dockerfile
    assert "--require-hashes -r /app/requirements-lock.txt" in dockerfile
    assert "pip install --no-cache-dir -r /app/requirements.in" in dockerfile
    assert "pip==24.3.1" in dockerfile
    assert "requirements.in" in workflow and "--generate-hashes" in workflow
    assert "--python-platform x86_64-unknown-linux-gnu" in workflow
    assert "STRICT_HASH_LOCK=1" in workflow
    for package in ("ccxt==4.5.81", "python-dotenv==1.2.4", "numpy==2.3.5", "pandas==2.2.3", "aiohttp==3.14.3", "aiosqlite==0.22.1"):
        assert package in requirements


def test_score_floor_remains_at_or_above_seventy():
    from v702_core__scoring__floor_policy import effective_live_floor

    for configured in (0, 55, 62, 64, 68, 69.99, 70):
        assert effective_live_floor(configured) >= 70


def test_live_builder_ast_keeps_hard_floor_before_final_score_admission():
    import ast
    import main as bot

    tree = ast.parse((ROOT / "main.py").read_text(encoding="utf-8"))
    builder = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "SignalBuilder")
    method = next(node for node in builder.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "build_and_route")
    calls = {}
    final_score_gates = []
    for node in ast.walk(method):
        if isinstance(node, ast.Call):
            fn = node.func
            name = fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else "")
            if name in {"_v612_combined_score_floor_invariant", "_v704_hard_global_score_floor"}:
                calls.setdefault(name, []).append(node.lineno)
        if isinstance(node, ast.Compare) and isinstance(node.left, ast.Name) and node.left.id == "score":
            if any(isinstance(op, ast.Lt) for op in node.ops) and isinstance(node.comparators[0], ast.Name) and node.comparators[0].id == "min_score":
                final_score_gates.append(node.lineno)

    assert calls.get("_v612_combined_score_floor_invariant")
    assert calls.get("_v704_hard_global_score_floor")
    assert final_score_gates
    assert min(calls["_v612_combined_score_floor_invariant"]) < min(final_score_gates)
    assert min(calls["_v704_hard_global_score_floor"]) < min(final_score_gates)
    assert bot._v612_combined_score_floor_invariant(64.0, 70.0) is True
    assert bot._v612_combined_score_floor_invariant(64.0, 69.99) is False



def test_release_env_example_is_whitelisted_and_copied_into_docker_runtime():
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    # The broad pattern protects operator secrets; the exact exception keeps
    # only the safe example template in the build context and runtime image.
    assert "LIVE_RELEASE_ENV.*" in dockerignore
    assert "!LIVE_RELEASE_ENV.example" in dockerignore
    assert dockerignore.index("!LIVE_RELEASE_ENV.example") > dockerignore.index("LIVE_RELEASE_ENV.*")
    assert "LIVE_RELEASE_ENV.*" in gitignore
    assert "!LIVE_RELEASE_ENV.example" in gitignore
    assert gitignore.index("!LIVE_RELEASE_ENV.example") > gitignore.index("LIVE_RELEASE_ENV.*")
    assert "COPY LIVE_RELEASE_ENV.example /app/LIVE_RELEASE_ENV.example" in dockerfile


def test_missing_release_env_example_fails_closed_without_uncaught_file_error():
    import main as bot

    missing = ROOT / "__missing_release_env_example_for_test__"
    old_present = bot.STATS.get("v702_a58_release_env_example_present")
    old_error = bot.STATS.get("v702_a58_release_env_example_error")
    try:
        assert bot._v702_a58_read_release_env_example(missing) == ""
        assert bot.STATS.get("v702_a58_release_env_example_present") is False
        assert "FileNotFoundError:" in bot.STATS.get("v702_a58_release_env_example_error", "")
        assert bot._v702_a58_parse_env_defaults("# UNIFIED_LIVE_PILOT_ENABLE=0\nUNIFIED_LIVE_PILOT_ENABLE=1\nUNIFIED_A55_LIVE_ARM=0") == {
            "UNIFIED_LIVE_PILOT_ENABLE": "1",
            "UNIFIED_A55_LIVE_ARM": "0",
        }
    finally:
        if old_present is None:
            bot.STATS.pop("v702_a58_release_env_example_present", None)
        else:
            bot.STATS["v702_a58_release_env_example_present"] = old_present
        if old_error is None:
            bot.STATS.pop("v702_a58_release_env_example_error", None)
        else:
            bot.STATS["v702_a58_release_env_example_error"] = old_error
