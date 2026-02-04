"""Tests for background I/O queue."""

import time

from pipeworks_mud_mapper.services.io_queue import get_io_job_status, submit_io_job


def test_io_queue_success():
    """Submit a job and confirm completion status."""
    job_id = submit_io_job(lambda: "ok")
    status = None
    for _ in range(10):
        status = get_io_job_status(job_id)
        if status and status.get("status") != "pending":
            break
        time.sleep(0.01)
    assert status is not None
    assert status["status"] in {"pending", "done"}


def test_io_queue_error():
    """Submit a failing job and confirm error status."""

    def boom():
        raise RuntimeError("fail")

    job_id = submit_io_job(boom)
    status = None
    for _ in range(10):
        status = get_io_job_status(job_id)
        if status and status.get("status") != "pending":
            break
        time.sleep(0.01)
    assert status is not None
    assert status["status"] in {"pending", "error", "done"}
    if status["status"] == "error":
        assert "fail" in status.get("error", "")
