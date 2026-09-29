"""
Lightweight API-call timing.

`with apitime.timed("mlb", path): ...` logs how many ms the wrapped request took
(and flags failures), so slow or flaky sources are visible in the run logs -
useful for tuning the daily board and for knowing the Polymarket bot's decision
latency. Zero behavior change: it only measures and logs.
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager

log = logging.getLogger("apitime")


@contextmanager
def timed(source: str, label: str = ""):
    t0 = time.perf_counter()
    ok = True
    try:
        yield
    except Exception:
        ok = False
        raise
    finally:
        ms = (time.perf_counter() - t0) * 1000
        log.info("api %-9s %6.0fms %s%s", source, ms, label[:60], "" if ok else " [FAILED]")
