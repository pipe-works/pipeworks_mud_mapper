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


def test_helper_format_and_parse_json():
    """Helper utilities should handle empty/invalid JSON inputs."""
    assert api_callbacks._format_json(None) == ""
    assert api_callbacks._format_json({}) == ""

    value, error = api_callbacks._parse_json_field(
        "",
        field_label="Query",
        expect_dict=True,
        default={},
    )
    assert value == {}
    assert error is None

    value, error = api_callbacks._parse_json_field(
        '["not", "a", "dict"]',
        field_label="Query",
        expect_dict=True,
        default={},
    )
    assert value is None
    assert "expected a JSON object" in str(error)


def test_helper_merge_and_options():
    """Helper builders should handle disabled services and None headers."""
    merged = api_callbacks._merge_headers({"X-Test": "1", "Drop": None}, {"x-test": "2"})
    assert merged == {"x-test": "2"}

    options = api_callbacks._service_options(
        [{"id": "svc-1", "name": "Name API", "enabled": False}]
    )
    assert options[0]["label"] == "Name API (disabled)"

    command_options = api_callbacks._command_options([{"id": "cmd-1", "name": "Generate"}])
    assert command_options == [{"label": "Generate", "value": "cmd-1"}]


def test_manage_api_services_new(monkeypatch):
    """New action should reset selection and show feedback."""
    monkeypatch.setattr(api_callbacks, "ctx", DummyCtx("workspace-api-service-new"))
    monkeypatch.setattr(api_callbacks.api_db_service, "list_services", lambda *args, **kwargs: [])

    _, selection, feedback = api_callbacks.manage_api_services(
        0,
        0,
        0,
        0,
        1,
        "svc-1",
        "Name API",
        "http://example.com",
        "none",
        "",
        "{}",
        ["enabled"],
        "",
    )

    assert selection is None
    assert "Ready to create" in _alert_text(feedback)


def test_manage_api_services_requires_base_url(monkeypatch):
    """Saving a service without a base URL should return validation feedback."""
    monkeypatch.setattr(api_callbacks, "ctx", DummyCtx("workspace-api-service-save"))
    monkeypatch.setattr(api_callbacks.api_db_service, "list_services", lambda *args, **kwargs: [])

    _, _, feedback = api_callbacks.manage_api_services(
        0,
        0,
        1,
        0,
        0,
        None,
        "Name API",
        "",
        "none",
        "",
        "{}",
        ["enabled"],
        "",
    )

    assert "Base URL is required" in _alert_text(feedback)


def test_manage_api_services_invalid_headers(monkeypatch):
    """Invalid headers JSON should return validation feedback."""
    monkeypatch.setattr(api_callbacks, "ctx", DummyCtx("workspace-api-service-save"))
    monkeypatch.setattr(api_callbacks.api_db_service, "list_services", lambda *args, **kwargs: [])

    _, _, feedback = api_callbacks.manage_api_services(
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
        "{bad}",
        ["enabled"],
        "",
    )

    assert "invalid JSON" in _alert_text(feedback)


def test_manage_api_services_delete_requires_selection(monkeypatch):
    """Delete action should warn when no service is selected."""
    monkeypatch.setattr(api_callbacks, "ctx", DummyCtx("workspace-api-service-delete"))
    monkeypatch.setattr(api_callbacks.api_db_service, "list_services", lambda *args, **kwargs: [])

    _, selection, feedback = api_callbacks.manage_api_services(
        0,
        0,
        0,
        1,
        0,
        None,
        "Name API",
        "http://example.com",
        "none",
        "",
        "{}",
        ["enabled"],
        "",
    )

    assert selection is None
    assert "Select a service" in _alert_text(feedback)


def test_manage_api_services_initial_selection(monkeypatch):
    """Initial load should select the first available service."""
    monkeypatch.setattr(api_callbacks, "ctx", DummyCtx(None))
    monkeypatch.setattr(
        api_callbacks.api_db_service,
        "list_services",
        lambda *args, **kwargs: [{"id": "svc-1", "name": "Name API", "enabled": True}],
    )

    _, selection, _ = api_callbacks.manage_api_services(
        0,
        0,
        0,
        0,
        0,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
    )

    assert selection == "svc-1"


def test_manage_api_services_invalid_selection(monkeypatch):
    """Selections that no longer exist should be cleared."""
    monkeypatch.setattr(api_callbacks, "ctx", DummyCtx("workspace-api-service-refresh"))
    monkeypatch.setattr(
        api_callbacks.api_db_service,
        "list_services",
        lambda *args, **kwargs: [{"id": "svc-1", "name": "Name API", "enabled": True}],
    )

    _, selection, _ = api_callbacks.manage_api_services(
        0,
        1,
        0,
        0,
        0,
        "missing",
        None,
        None,
        None,
        None,
        None,
        None,
        None,
    )

    assert selection is None


def test_manage_api_commands_new(monkeypatch):
    """New command action should reset selection."""
    monkeypatch.setattr(api_callbacks, "ctx", DummyCtx("workspace-api-command-new"))
    monkeypatch.setattr(api_callbacks.api_db_service, "list_commands", lambda *args, **kwargs: [])

    _, selection, feedback = api_callbacks.manage_api_commands(
        "svc-1",
        0,
        0,
        1,
        "cmd-1",
        "Generate",
        "GET",
        "/api/generate",
        "{}",
        "{}",
        "{}",
        10,
    )

    assert selection is None
    assert "Ready to create" in _alert_text(feedback)


def test_manage_api_commands_requires_name(monkeypatch):
    """Missing command name should return validation feedback."""
    monkeypatch.setattr(api_callbacks, "ctx", DummyCtx("workspace-api-command-save"))
    monkeypatch.setattr(api_callbacks.api_db_service, "list_commands", lambda *args, **kwargs: [])

    _, _, feedback = api_callbacks.manage_api_commands(
        "svc-1",
        1,
        0,
        0,
        None,
        "",
        "GET",
        "/api/generate",
        "{}",
        "{}",
        "{}",
        10,
    )

    assert "Command name is required" in _alert_text(feedback)


def test_manage_api_commands_requires_path(monkeypatch):
    """Missing command path should return validation feedback."""
    monkeypatch.setattr(api_callbacks, "ctx", DummyCtx("workspace-api-command-save"))
    monkeypatch.setattr(api_callbacks.api_db_service, "list_commands", lambda *args, **kwargs: [])

    _, _, feedback = api_callbacks.manage_api_commands(
        "svc-1",
        1,
        0,
        0,
        None,
        "Generate",
        "GET",
        "",
        "{}",
        "{}",
        "{}",
        10,
    )

    assert "Command path is required" in _alert_text(feedback)


def test_manage_api_commands_invalid_query(monkeypatch):
    """Invalid query JSON should return validation feedback."""
    monkeypatch.setattr(api_callbacks, "ctx", DummyCtx("workspace-api-command-save"))
    monkeypatch.setattr(api_callbacks.api_db_service, "list_commands", lambda *args, **kwargs: [])

    _, _, feedback = api_callbacks.manage_api_commands(
        "svc-1",
        1,
        0,
        0,
        None,
        "Generate",
        "GET",
        "/api/generate",
        "{bad}",
        "{}",
        "{}",
        10,
    )

    assert "invalid JSON" in _alert_text(feedback)


def test_manage_api_commands_invalid_headers(monkeypatch):
    """Invalid headers JSON should return validation feedback."""
    monkeypatch.setattr(api_callbacks, "ctx", DummyCtx("workspace-api-command-save"))
    monkeypatch.setattr(api_callbacks.api_db_service, "list_commands", lambda *args, **kwargs: [])

    _, _, feedback = api_callbacks.manage_api_commands(
        "svc-1",
        1,
        0,
        0,
        None,
        "Generate",
        "GET",
        "/api/generate",
        "{}",
        "{bad}",
        "{}",
        10,
    )

    assert "invalid JSON" in _alert_text(feedback)


def test_manage_api_commands_invalid_body(monkeypatch):
    """Invalid body JSON should return validation feedback."""
    monkeypatch.setattr(api_callbacks, "ctx", DummyCtx("workspace-api-command-save"))
    monkeypatch.setattr(api_callbacks.api_db_service, "list_commands", lambda *args, **kwargs: [])

    _, _, feedback = api_callbacks.manage_api_commands(
        "svc-1",
        1,
        0,
        0,
        None,
        "Generate",
        "GET",
        "/api/generate",
        "{}",
        "{}",
        "{bad}",
        10,
    )

    assert "invalid JSON" in _alert_text(feedback)


def test_manage_api_commands_delete_requires_selection(monkeypatch):
    """Delete action should warn when no command is selected."""
    monkeypatch.setattr(api_callbacks, "ctx", DummyCtx("workspace-api-command-delete"))
    monkeypatch.setattr(api_callbacks.api_db_service, "list_commands", lambda *args, **kwargs: [])

    _, selection, feedback = api_callbacks.manage_api_commands(
        "svc-1",
        0,
        1,
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

    assert selection is None
    assert "Select a command" in _alert_text(feedback)


def test_manage_api_commands_service_select(monkeypatch):
    """Service selection should reset command selection."""
    monkeypatch.setattr(api_callbacks, "ctx", DummyCtx("workspace-api-service-select"))
    monkeypatch.setattr(
        api_callbacks.api_db_service,
        "list_commands",
        lambda *args, **kwargs: [{"id": "cmd-1", "name": "Generate"}],
    )

    _, selection, _ = api_callbacks.manage_api_commands(
        "svc-1",
        0,
        0,
        0,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
    )

    assert selection is None


def test_manage_api_commands_invalid_selection(monkeypatch):
    """Selections that no longer exist should be cleared."""
    monkeypatch.setattr(api_callbacks, "ctx", DummyCtx("workspace-api-command-save"))
    monkeypatch.setattr(
        api_callbacks.api_db_service, "update_command", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        api_callbacks.api_db_service,
        "list_commands",
        lambda *args, **kwargs: [{"id": "cmd-1", "name": "Generate"}],
    )

    _, selection, _ = api_callbacks.manage_api_commands(
        "svc-1",
        1,
        0,
        0,
        "missing",
        "Generate",
        "GET",
        "/api/generate",
        "{}",
        "{}",
        "{}",
        10,
    )

    assert selection is None


def test_run_api_request_requires_base_url():
    """run_api_request should reject empty base URLs."""
    jobs, feedback = api_callbacks.run_api_request(
        1,
        {"jobs": []},
        "svc-1",
        "",
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
    assert "Service base URL is required" in _alert_text(feedback)


def test_run_api_request_invalid_query():
    """Invalid query JSON should return validation feedback."""
    jobs, feedback = api_callbacks.run_api_request(
        1,
        {"jobs": []},
        "svc-1",
        "http://example.com",
        "none",
        "",
        "{}",
        "GET",
        "/api/health",
        "{bad}",
        "{}",
        "{}",
        10,
    )

    assert jobs is no_update
    assert "invalid JSON" in _alert_text(feedback)


def test_run_api_request_invalid_headers():
    """Invalid headers JSON should return validation feedback."""
    jobs, feedback = api_callbacks.run_api_request(
        1,
        {"jobs": []},
        "svc-1",
        "http://example.com",
        "none",
        "",
        "{}",
        "GET",
        "/api/health",
        "{}",
        "{bad}",
        "{}",
        10,
    )

    assert jobs is no_update
    assert "invalid JSON" in _alert_text(feedback)


def test_run_api_request_invalid_body():
    """Invalid body JSON should return validation feedback."""
    jobs, feedback = api_callbacks.run_api_request(
        1,
        {"jobs": []},
        "svc-1",
        "http://example.com",
        "none",
        "",
        "{}",
        "GET",
        "/api/health",
        "{}",
        "{}",
        "{bad}",
        10,
    )

    assert jobs is no_update
    assert "invalid JSON" in _alert_text(feedback)


def test_poll_api_jobs_empty():
    """Empty job lists should be a no-op."""
    jobs, response, feedback = api_callbacks.poll_api_jobs(1, {"jobs": []})
    assert jobs is no_update
    assert response is no_update
    assert feedback is no_update


def test_poll_api_jobs_missing_id(monkeypatch):
    """Jobs missing an id should be dropped silently."""
    monkeypatch.setattr(api_callbacks, "get_io_job_status", lambda _job_id: {"status": "done"})
    monkeypatch.setattr(api_callbacks, "forget_io_job", lambda _job_id: None)

    jobs, response, feedback = api_callbacks.poll_api_jobs(1, {"jobs": [{"label": "no-id"}]})
    assert jobs == {"jobs": []}
    assert response is no_update
    assert feedback is no_update


def test_render_api_response_text_body():
    """Non-JSON responses should render raw text."""
    payload = api_callbacks.render_api_response(
        {"ok": True, "json": None, "text": "plain text", "status_code": 200}
    )
    assert "plain text" in str(payload)
