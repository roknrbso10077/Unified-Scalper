"""A25/A26 regressions: config validation must pass before the LIVE epoch is armed.

The source AST is deliberately parsed in a short-lived child process.  ``main.py``
is large, and retaining its full AST in pytest's collection process causes expensive
interpreter shutdown after the test session has already reported all tests passing.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = (ROOT / "main.py").read_text(encoding="utf-8")
_AST_PROBE = r'''
import ast, json, pathlib, sys
source = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
tree = ast.parse(source)
def calls(node, name):
    return [n for n in ast.walk(node) if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name) and n.func.id == name]
main_fn = next(n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "main")
validate_idx = next(i for i, n in enumerate(main_fn.body)
                    if isinstance(n, ast.Try) and any(
                        isinstance(stmt, ast.Assign) and any(
                            isinstance(t, ast.Name) and t.id == "_cfg_ok" for t in stmt.targets
                        ) for stmt in n.body
                    ))
guard_idx = next(i for i, n in enumerate(main_fn.body)
                 if isinstance(n, ast.If) and isinstance(n.test, ast.UnaryOp)
                 and isinstance(n.test.op, ast.Not) and isinstance(n.test.operand, ast.Name)
                 and n.test.operand.id == "_cfg_ok")
arm_idx = next(i for i, n in enumerate(main_fn.body) if calls(n, "_v699_arm_live_epoch"))
guard = main_fn.body[guard_idx]
entry = next(n for n in tree.body if isinstance(n, ast.If)
             and isinstance(n.test, ast.Compare)
             and isinstance(n.test.left, ast.Name) and n.test.left.id == "__name__")
print(json.dumps({
  "validate_idx": validate_idx,
  "guard_idx": guard_idx,
  "arm_idx": arm_idx,
  "guard_raises": any(isinstance(n, ast.Raise) for n in ast.walk(guard)),
  "entry_arms_live_epoch": bool(calls(entry, "_v699_arm_live_epoch")),
  "entry_calls_main": bool(calls(entry, "main")),
}))
'''

def _main_ast_summary():
    completed = subprocess.run(
        [sys.executable, "-c", _AST_PROBE, str(ROOT / "main.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, (
        "isolated AST probe failed: " + completed.stderr[-2000:]
    )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError("isolated AST probe returned invalid JSON") from exc


AST_SUMMARY = _main_ast_summary()


def test_live_epoch_arm_occurs_only_after_validate_config_success_guard():
    assert AST_SUMMARY["validate_idx"] < AST_SUMMARY["guard_idx"] < AST_SUMMARY["arm_idx"]
    assert AST_SUMMARY["guard_raises"] is True


def test_module_entrypoint_does_not_arm_live_epoch_before_validation():
    assert AST_SUMMARY["entry_arms_live_epoch"] is False
    assert AST_SUMMARY["entry_calls_main"] is True


def test_failed_boot_logs_current_terminal_reports_and_stays_fail_closed():
    assert "active_terminal_validation_diagnostics" in SOURCE
    assert "v702_a26_terminal_self_test" in SOURCE
    assert "historical_superseded" in SOURCE
    assert "v702_a24_terminal_self_test" in SOURCE
    assert "v702_r23_final_validation" in SOURCE
    assert "v699_full_validation_observability" in SOURCE
    assert "[V702-A28-VALIDATION] fail_closed" in SOURCE
    assert "package_revision=%s" in SOURCE
    assert 'raise SystemExit("config_invalid")' in SOURCE
    # No retry or bypass is allowed after the terminal canonical validator fails.
    assert "raise SystemExit(\"config_invalid\")" in SOURCE
