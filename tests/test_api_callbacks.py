"""Tests for Workspace API callbacks."""

from __future__ import annotations

from typing import Any

import dash_bootstrap_components as dbc
from dash import no_update

from pipeworks_mud_mapper.callbacks import api_callbacks


class DummyCtx:
    """Simple stand-in for dash.ctx in unit tests."""

    def __init__(self, triggered_id: Any):
        self.triggered_id = triggered_id


def _alert_text(alert: dbc.Alert | Any) -> str:
    """Extract human-readable text from an Alert-like component."""
    if isinstance(alert, dbc.Alert):
        return str(alert.children)
    return str(alert)


def test_manage_api_services_requires_name(monkeypatch):
    """Saving a service without a name should return validation feedback."""
    monkeypatch.setattr(api_callbacks, "ctx", DummyCtx("workspace-api-service-save"))
    monkeypatch.setattr(
        api_callbacks.api_db_service,
        "list_services",
        lambda *args, **kwargs: [],
    )

    options, selection, feedback = api_callbacks.manage_api_services(
        0,
        0,
        1,
        0,
        0,
        None,
        None,
        "http://example.com",
        "none",
        "",
        "{}",
        ["enabled"],
        "",
    )

    assert options == []
    assert selection is None
    assert "Service name is required" in _alert_text(feedback)


def test_manage_api_services_create(monkeypatch):
    """Creating a new service should call create_service and return new selection."""
    calls: dict[str, Any] = {}

    def _create_service(**kwargs):
        calls.update(kwargs)
        return "svc-1"

    monkeypatch.setattr(api_callbacks, "ctx", DummyCtx("workspace-api-service-save"))
    monkeypatch.setattr(api_callbacks.api_db_service, "create_service", _create_service)
    monkeypatch.setattr(
        api_callbacks.api_db_service,
        "list_services",
        lambda *args, **kwargs: [{"id": "svc-1", "name": "Name API", "enabled": True}],
    )

    options, selection, feedback = api_callbacks.manage_api_services(
        0,
        0,
        1,
        0,
        0,
        None,
        "Name API",
        "http://example.com",
        "none",
        "",
        "{}",
        ["enabled"],
        "notes",
    )

    assert calls["name"] == "Name API"
    assert selection == "svc-1"
    assert options[0]["label"] == "Name API"
    assert "created" in _alert_text(feedback).lower()


def test_manage_api_services_update(monkeypatch):
    """Updating an existing service should call update_service."""
    called = {"updated": False}

    def _update_service(service_id, **kwargs):
        called["updated"] = True
        called["id"] = service_id

    monkeypatch.setattr(api_callbacks, "ctx", DummyCtx("workspace-api-service-save"))
    monkeypatch.setattr(api_callbacks.api_db_service, "update_service", _update_service)
    monkeypatch.setattr(
        api_callbacks.api_db_service,
        "list_services",
        lambda *args, **kwargs: [{"id": "svc-1", "name": "Name API", "enabled": True}],
    )

    _, selection, feedback = api_callbacks.manage_api_services(
        0,
        0,
        1,
        0,
        0,
        "svc-1",
        "Name API",
        "http://example.com",
        "none",
        "",
        "{}",
        ["enabled"],
        "",
    )

    assert called["updated"] is True
    assert called["id"] == "svc-1"
    assert selection == "svc-1"
    assert "updated" in _alert_text(feedback).lower()


def test_manage_api_services_delete(monkeypatch):
    """Deleting a service should clear selection and call delete_service."""
    deleted: dict[str, Any] = {}

    def _delete_service(service_id, **kwargs):
        deleted["id"] = service_id

    monkeypatch.setattr(api_callbacks, "ctx", DummyCtx("workspace-api-service-delete"))
    monkeypatch.setattr(api_callbacks.api_db_service, "delete_service", _delete_service)
    monkeypatch.setattr(api_callbacks.api_db_service, "list_services", lambda *args, **kwargs: [])

    _, selection, feedback = api_callbacks.manage_api_services(
        0,
        0,
        0,
        1,
        0,
        "svc-1",
        "Name API",
        "http://example.com",
        "none",
        "",
        "{}",
        ["enabled"],
        "",
    )

    assert deleted["id"] == "svc-1"
    assert selection is None
    assert "deleted" in _alert_text(feedback).lower()


def test_populate_service_form_defaults():
    """Empty selection should reset service form defaults."""
    values = api_callbacks.populate_service_form(None)
    assert values == ("", "", "none", "", "", ["enabled"], "")


def test_populate_service_form_load(monkeypatch):
    """Selecting a service should hydrate the form fields."""
    monkeypatch.setattr(
        api_callbacks.api_db_service,
        "get_service",
        lambda *_args, **_kwargs: {
            "name": "Name API",
            "base_url": "http://example.com",
            "auth_type": "bearer",
            "auth_secret": "token",
            "default_headers": {"X-Test": "1"},
            "enabled": False,
            "notes": "Notes",
        },
    )

    values = api_callbacks.populate_service_form("svc-1")
    assert values[0] == "Name API"
    assert values[1] == "http://example.com"
    assert values[2] == "bearer"
    assert values[3] == "token"
    assert "X-Test" in values[4]
    assert values[5] == []
    assert values[6] == "Notes"


def test_manage_api_commands_requires_service(monkeypatch):
    """Command save should fail when no service is selected."""
    monkeypatch.setattr(api_callbacks, "ctx", DummyCtx("workspace-api-command-save"))
    options, selection, feedback = api_callbacks.manage_api_commands(
        None,
        1,
        0,
        0,
        None,
        "Generate",
        "GET",
        "/api/generate",
        "{}",
        "{}",
        "{}",
        10,
    )
    assert options == []
    assert selection is None
    assert "Select a service" in _alert_text(feedback)


def test_manage_api_commands_create(monkeypatch):
    """Creating a new command should call create_command and return selection."""
    created: dict[str, Any] = {}

    def _create_command(**kwargs):
        created.update(kwargs)
        return "cmd-1"

    monkeypatch.setattr(api_callbacks, "ctx", DummyCtx("workspace-api-command-save"))
    monkeypatch.setattr(api_callbacks.api_db_service, "create_command", _create_command)
    monkeypatch.setattr(
        api_callbacks.api_db_service,
        "list_commands",
        lambda *args, **kwargs: [{"id": "cmd-1", "name": "Generate"}],
    )

    options, selection, feedback = api_callbacks.manage_api_commands(
        "svc-1",
        1,
        0,
        0,
        None,
        "Generate",
        "POST",
        "/api/generate",
        "{}",
        "{}",
        "{}",
        10,
    )

    assert created["service_id"] == "svc-1"
    assert selection == "cmd-1"
    assert options[0]["label"] == "Generate"
    assert "created" in _alert_text(feedback).lower()


def test_manage_api_commands_update(monkeypatch):
    """Updating a command should call update_command."""
    called = {"updated": False}

    def _update_command(command_id, **kwargs):
        called["updated"] = True
        called["id"] = command_id

    monkeypatch.setattr(api_callbacks, "ctx", DummyCtx("workspace-api-command-save"))
    monkeypatch.setattr(api_callbacks.api_db_service, "update_command", _update_command)
    monkeypatch.setattr(
        api_callbacks.api_db_service,
        "list_commands",
        lambda *args, **kwargs: [{"id": "cmd-1", "name": "Generate"}],
    )

    _, selection, feedback = api_callbacks.manage_api_commands(
        "svc-1",
        1,
        0,
        0,
        "cmd-1",
        "Generate",
        "POST",
        "/api/generate",
        "{}",
        "{}",
        "{}",
        10,
    )

    assert called["updated"] is True
    assert called["id"] == "cmd-1"
    assert selection == "cmd-1"
    assert "updated" in _alert_text(feedback).lower()


def test_manage_api_commands_delete(monkeypatch):
    """Deleting a command should clear selection and call delete_command."""
    deleted: dict[str, Any] = {}

    def _delete_command(command_id, **kwargs):
        deleted["id"] = command_id

    monkeypatch.setattr(api_callbacks, "ctx", DummyCtx("workspace-api-command-delete"))
    monkeypatch.setattr(api_callbacks.api_db_service, "delete_command", _delete_command)
    monkeypatch.setattr(api_callbacks.api_db_service, "list_commands", lambda *args, **kwargs: [])

    _, selection, feedback = api_callbacks.manage_api_commands(
        "svc-1",
        0,
        1,
        0,
        "cmd-1",
        "Generate",
        "POST",
        "/api/generate",
        "{}",
        "{}",
        "{}",
        10,
    )

    assert deleted["id"] == "cmd-1"
    assert selection is None
    assert "deleted" in _alert_text(feedback).lower()


def test_populate_command_form_defaults():
    """Empty selection should reset command form defaults."""
    values = api_callbacks.populate_command_form(None)
    assert values == ("", "GET", "", "", "", "", None)


def test_populate_command_form_load(monkeypatch):
    """Selecting a command should hydrate the form fields."""
    monkeypatch.setattr(
        api_callbacks.api_db_service,
        "get_command",
        lambda *_args, **_kwargs: {
            "name": "Generate",
            "method": "POST",
            "path": "/api/generate",
            "query": {"q": 1},
            "headers": {"X-Test": "1"},
            "body": {"foo": "bar"},
            "timeout_seconds": 10,
        },
    )

    values = api_callbacks.populate_command_form("cmd-1")
    assert values[0] == "Generate"
    assert values[1] == "POST"
    assert values[2] == "/api/generate"
    assert "q" in values[3]
    assert "X-Test" in values[4]
    assert "foo" in values[5]
    assert values[6] == 10


def test_run_api_request_requires_service():
    """run_api_request should refuse to run without a selected service."""
    jobs, feedback = api_callbacks.run_api_request(
        1,
        {"jobs": []},
        None,
        "http://example.com",
        "none",
        "",
        "{}",
        "GET",
        "/api/health",
        "{}",
        "{}",
        "{}",
        10,
    )

    assert jobs is no_update
    assert "Select a service" in _alert_text(feedback)


def test_run_api_request_invalid_json(monkeypatch):
    """Invalid JSON in headers should return validation feedback."""
    jobs, feedback = api_callbacks.run_api_request(
        1,
        {"jobs": []},
        "svc-1",
        "http://example.com",
        "none",
        "",
        "{oops}",
        "GET",
        "/api/health",
        "{}",
        "{}",
        "{}",
        10,
    )

    assert jobs is no_update
    assert "invalid JSON" in _alert_text(feedback)


def test_run_api_request_success(monkeypatch):
    """Valid request should queue a background job and merge headers."""
    captured: dict[str, Any] = {}

    def _submit_io_job(func, **kwargs):
        captured["func"] = func
        captured["kwargs"] = kwargs
        return "job-1"

    monkeypatch.setattr(api_callbacks, "submit_io_job", _submit_io_job)

    jobs, feedback = api_callbacks.run_api_request(
        1,
        {"jobs": []},
        "svc-1",
        "http://example.com",
        "none",
        "",
        '{"X-Test": "1"}',
        "GET",
        "/api/health",
        "{}",
        '{"x-test": "2", "Other": "3"}',
        "{}",
        10,
    )

    assert jobs["jobs"][0]["id"] == "job-1"
    assert captured["kwargs"]["headers"]["x-test"] == "2"
    assert captured["kwargs"]["headers"]["Other"] == "3"
    assert "queued" in _alert_text(feedback).lower()


def test_poll_api_jobs_pending(monkeypatch):
    """Pending jobs should remain queued with no feedback updates."""
    monkeypatch.setattr(api_callbacks, "get_io_job_status", lambda _job_id: {"status": "pending"})

    jobs, response, feedback = api_callbacks.poll_api_jobs(1, {"jobs": [{"id": "job-1"}]})
    assert jobs is no_update
    assert response is no_update
    assert feedback is no_update


def test_poll_api_jobs_error(monkeypatch):
    """Failed jobs should surface error payloads."""
    monkeypatch.setattr(
        api_callbacks,
        "get_io_job_status",
        lambda _job_id: {"status": "error", "error": "boom"},
    )
    monkeypatch.setattr(api_callbacks, "forget_io_job", lambda _job_id: None)

    jobs, response, feedback = api_callbacks.poll_api_jobs(1, {"jobs": [{"id": "job-1"}]})
    assert jobs == {"jobs": []}
    assert response["ok"] is False
    assert response["error"] == "boom"
    assert "failed" in _alert_text(feedback).lower()


def test_poll_api_jobs_success(monkeypatch):
    """Completed jobs should surface the result payload."""
    monkeypatch.setattr(
        api_callbacks,
        "get_io_job_status",
        lambda _job_id: {"status": "done", "result": {"ok": True}},
    )
    monkeypatch.setattr(api_callbacks, "forget_io_job", lambda _job_id: None)

    jobs, response, feedback = api_callbacks.poll_api_jobs(1, {"jobs": [{"id": "job-1"}]})
    assert jobs == {"jobs": []}
    assert response == {"ok": True}
    assert "received" in _alert_text(feedback).lower()


def test_render_api_response_variants():
    """Renderers should handle empty, error, and JSON responses."""
    empty = api_callbacks.render_api_response(None)
    assert "No response yet" in str(empty)

    error = api_callbacks.render_api_response({"ok": False, "error": "boom"})
    assert "boom" in str(error)

    payload = api_callbacks.render_api_response({"ok": True, "json": {"a": 1}, "text": ""})
    assert "a" in str(payload)
