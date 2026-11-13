"""Pytest lifecycle diagnostics for the A58 canonical release.

The suite imports the very large strategy module and builds many temporary
callback/function graphs during deterministic self-tests. All fixtures and
background tasks are closed by session teardown; only MainThread remains.
Freeze the now-quiescent object graph at interpreter exit so CPython's final
cyclic-GC pass does not stall while traversing those test-only module cycles.
This does not affect the bot runtime or production garbage collection.
"""
import gc
import faulthandler
import sys
import threading

faulthandler.enable()


def pytest_sessionfinish(session, exitstatus):
    alive = [t for t in threading.enumerate() if t.is_alive()]
    details = [(t.name, t.daemon) for t in alive]
    print("A58_THREADS_AFTER_SESSION=" + repr(details), file=sys.stderr, flush=True)
    # Test sessions must never leave a worker running after teardown.
    if [name for name, _daemon in details if name != "MainThread"]:
        session.exitstatus = 1


def pytest_unconfigure(config):
    # This process is a disposable test runner. Tests are complete and no
    # worker is alive; freezing the retained source/module graph prevents a
    # pathological interpreter-shutdown full-GC traversal under Python 3.13.
    gc.freeze()
    faulthandler.cancel_dump_traceback_later()
