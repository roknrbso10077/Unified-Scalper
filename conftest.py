"""Pytest lifecycle diagnostics for the A58 canonical release."""
import faulthandler
import sys
import threading

faulthandler.enable()


def pytest_sessionfinish(session, exitstatus):
    alive = [t for t in threading.enumerate() if t.is_alive()]
    print(
        "A58_THREADS_AFTER_SESSION=" + repr([(t.name, t.daemon) for t in alive]),
        file=sys.stderr,
        flush=True,
    )


def pytest_unconfigure(config):
    # Arm a one-shot diagnostic only after pytest plugins have completed their
    # shutdown hooks.  If interpreter finalization blocks, this captures its
    # main-thread state.  A successful interpreter exit cancels it naturally.
    faulthandler.dump_traceback_later(8, repeat=False)
