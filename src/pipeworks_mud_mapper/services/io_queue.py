"""Background I/O queue for long-running file operations.

This module provides a tiny thread pool and job registry so callbacks
can offload disk-heavy operations without blocking the UI thread.
"""

from __future__ import annotations

import threading
import uuid
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any


class IOJobRegistry:
    """Thread-safe registry for background I/O jobs."""

    def __init__(self, max_workers: int = 2) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._lock = threading.Lock()
        self._jobs: dict[str, Future] = {}

    def submit(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
        """Submit a job and return the job id."""
        job_id = uuid.uuid4().hex
        future = self._executor.submit(func, *args, **kwargs)
        with self._lock:
            self._jobs[job_id] = future
        return job_id

    def status(self, job_id: str) -> dict[str, Any] | None:
        """Return status info for a job id."""
        with self._lock:
            future = self._jobs.get(job_id)

        if future is None:
            return None

        if not future.done():
            return {"status": "pending"}

        try:
            result = future.result()
            return {"status": "done", "result": result}
        except Exception as exc:  # pragma: no cover - error path surfaced in callback
            return {"status": "error", "error": str(exc)}

    def forget(self, job_id: str) -> None:
        """Remove a job id from the registry."""
        with self._lock:
            self._jobs.pop(job_id, None)


_IO_REGISTRY = IOJobRegistry()


def submit_io_job(func: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
    """Submit a background I/O job and return its id."""
    return _IO_REGISTRY.submit(func, *args, **kwargs)


def get_io_job_status(job_id: str) -> dict[str, Any] | None:
    """Return the status dict for a job id."""
    return _IO_REGISTRY.status(job_id)


def forget_io_job(job_id: str) -> None:
    """Remove a job id from the registry."""
    _IO_REGISTRY.forget(job_id)
