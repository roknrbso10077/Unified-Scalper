from __future__ import annotations

from contextlib import closing

import sqlite3
from pathlib import Path

import main as bot


def test_db_schema_initialization_creates_missing_parent_directory(tmp_path, monkeypatch):
    db_path = tmp_path / "volume" / "runtime" / "unified_scalper.db"
    assert not db_path.parent.exists()
    monkeypatch.setitem(bot.CONFIG, "DB_PATH", str(db_path))

    bot.DBManager.init_schema()

    assert db_path.is_file()
    with closing(sqlite3.connect(db_path)) as conn:
        names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"active_trades", "execution_intents", "daily_state"}.issubset(names)


def test_db_schema_keeps_sqlite_memory_path_supported(monkeypatch, tmp_path):
    monkeypatch.setitem(bot.CONFIG, "DB_PATH", ":memory:")
    bot.DBManager.init_schema()
    assert not (tmp_path / ":memory:").exists()


def test_image_prepares_data_and_compiles_runtime_modules():
    dockerfile = (Path(__file__).parent / "Dockerfile").read_text(encoding="utf-8")
    assert "python -m py_compile /app/main.py" in dockerfile
    assert "mkdir -p /data" in dockerfile
    assert "chown -R appuser:appuser /app /data" in dockerfile
    assert 'CMD ["python", "-u", "main.py"]' in dockerfile


def test_one_shot_validation_clearly_states_bot_was_not_started():
    source = Path(bot.__file__).read_text(encoding="utf-8")
    assert "one_shot=true bot_started=false" in source
    assert "UNIFIED_V699_VALIDATE_ONLY" in source
    assert "UNIFIED_V702_VALIDATE_ONLY" in source
    assert "UNIFIED_VALIDATE_ONLY" in source


def test_hosted_runtime_failures_emit_tracebacks_without_suppressing_failure():
    source = Path(bot.__file__).read_text(encoding="utf-8")
    assert '[V702-BOOT-FAIL] validate_config raised' in source
    assert '[V702-CRASH] uncaught runtime exception' in source
    assert 'exc_info=True' in source


def test_mock_unknown_entry_log_is_distinguished_from_live_block():
    source = Path(bot.__file__).read_text(encoding="utf-8")
    assert "[V517-RECON-SELFTEST] UNKNOWN ENTRY UNRESOLVED" in source
    assert '"synthetic test entry block only; cleared before the live runtime epoch"' in source


def test_botkeep_dotenv_is_loaded_before_environment_snapshot():
    source = Path(bot.__file__).read_text(encoding="utf-8")
    loader = source.index("_load_dotenv(dotenv_path=_DOTENV_PATH, override=False)")
    snapshot = source.index("ENV: Dict[str, Optional[str]] =")
    assert loader < snapshot
    assert "python-dotenv==1.2.4" in (Path(__file__).parent / "requirements-lock.txt").read_text(encoding="utf-8")
    assert "mexc_api_key_present=%s" in source
