from __future__ import annotations

from threading import Lock


_GPU_LOCK = Lock()


def gpu_lock() -> Lock:
    return _GPU_LOCK
