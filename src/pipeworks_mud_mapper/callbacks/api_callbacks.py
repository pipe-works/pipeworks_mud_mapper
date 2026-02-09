"""API integration callbacks for the Workspace tab."""

from __future__ import annotations

import json
from typing import Any

import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, ctx, html, no_update

from pipeworks_mud_mapper.services import api_db_service
from pipeworks_mud_mapper.services.api_client import execute_api_request
from pipeworks_mud_mapper.services.app_config import get_path_settings
from pipeworks_mud_mapper.services.io_queue import (
    forget_io_job,
    get_io_job_status,
    submit_io_job,
)

PATHS = get_path_settings()
API_DB_PATH = PATHS["api_db_path"]


def _alert(message: str, color: str = "info") -> dbc.Alert:
    """Return a compact alert for workspace feedback panels."""
    return dbc.Alert(message, color=color, className="mb-0 py-1")


def _format_json(value: Any) -> str:
    """Format a JSON-serializable value for textarea display."""
    if value in (None, {}, []):
        return ""
    return json.dumps(value, indent=2, sort_keys=True)


def _parse_json_field(
    value: str | None,
    *,
    field_label: str,
    expect_dict: bool,
    default: Any,
) -> tuple[Any, str | None]:
    """Parse a JSON textarea into a Python value with validation."""
    if value is None or not str(value).strip():
        return default, None

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        return None, f"{field_label}: invalid JSON ({exc.msg})."

    if expect_dict and not isinstance(parsed, dict):
        return None, f"{field_label}: expected a JSON object."

    return parsed, None


def _merge_headers(
    base_headers: dict[str, Any],
    override_headers: dict[str, Any],
) -> dict[str, Any]:
    """Merge headers with case-insensitive override behavior."""
    merged: dict[str, Any] = {}
    for headers in (base_headers, override_headers):
        for key, value in headers.items():
            if value is None:
                continue
            lower_key = str(key).lower()
            for existing in list(merged.keys()):
                if existing.lower() == lower_key:
                    merged.pop(existing)
                    break
            merged[str(key)] = value
    return merged


def _service_options(services: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Build service dropdown options with disabled markers."""
    options: list[dict[str, str]] = []
    for service in services:
        label = service["name"]
        if not service["enabled"]:
            label = f"{label} (disabled)"
        options.append({"label": label, "value": service["id"]})
    return options


def _command_options(commands: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Build command dropdown options."""
    return [{"label": command["name"], "value": command["id"]} for command in commands]


@callback(
    Output("workspace-api-service-select", "options"),
    Output("workspace-api-service-select", "value"),
    Output("workspace-api-service-feedback", "children"),
    Input("initial-load", "n_intervals"),
    Input("workspace-api-service-refresh", "n_clicks"),
    Input("workspace-api-service-save", "n_clicks"),
    Input("workspace-api-service-delete", "n_clicks"),
    Input("workspace-api-service-new", "n_clicks"),
    State("workspace-api-service-select", "value"),
    State("workspace-api-service-name", "value"),
    State("workspace-api-service-base-url", "value"),
    State("workspace-api-service-auth-type", "value"),
    State("workspace-api-service-auth-secret", "value"),
    State("workspace-api-service-headers", "value"),
    State("workspace-api-service-enabled", "value"),
    State("workspace-api-service-notes", "value"),
    prevent_initial_call=False,
)
def manage_api_services(
    _: int | None,
    __: int | None,
    save_clicks: int | None,
    delete_clicks: int | None,
    new_clicks: int | None,
    selected_service: str | None,
    name: str | None,
    base_url: str | None,
    auth_type: str | None,
    auth_secret: str | None,
    headers_text: str | None,
    enabled_values: list[str] | None,
    notes: str | None,
) -> tuple[list[dict[str, str]], str | None, Any]:
    """Create, update, delete, or list API services."""
    triggered = ctx.triggered_id
    feedback: Any = no_update
    new_selection = selected_service

    # Handle explicit actions (new/save/delete) before refreshing the options list.
    if triggered == "workspace-api-service-new":
        new_selection = None
        feedback = _alert("Ready to create a new service.", color="secondary")
    elif triggered == "workspace-api-service-save":
        if not name or not name.strip():
            feedback = _alert("Service name is required.", color="danger")
        elif not base_url or not base_url.strip():
            feedback = _alert("Base URL is required.", color="danger")
        else:
            # Validate JSON-only fields so we can store a clean dict in SQLite.
            headers, error = _parse_json_field(
                headers_text,
                field_label="Default Headers",
                expect_dict=True,
                default={},
            )
            if error:
                feedback = _alert(error, color="danger")
            else:
                enabled = bool(enabled_values and "enabled" in enabled_values)
                if new_selection:
                    api_db_service.update_service(
                        new_selection,
                        name=name.strip(),
                        base_url=base_url.strip(),
                        auth_type=(auth_type or "none"),
                        auth_secret=(auth_secret or None),
                        default_headers=headers,
                        enabled=enabled,
                        notes=(notes or None),
                        db_path=API_DB_PATH,
                    )
                    feedback = _alert("Service updated.", color="success")
                else:
                    new_selection = api_db_service.create_service(
                        name=name.strip(),
                        base_url=base_url.strip(),
                        auth_type=(auth_type or "none"),
                        auth_secret=(auth_secret or None),
                        default_headers=headers,
                        enabled=enabled,
                        notes=(notes or None),
                        db_path=API_DB_PATH,
                    )
                    feedback = _alert("Service created.", color="success")
    elif triggered == "workspace-api-service-delete":
        if not new_selection:
            feedback = _alert("Select a service to delete.", color="danger")
        else:
            api_db_service.delete_service(new_selection, db_path=API_DB_PATH)
            new_selection = None
            feedback = _alert("Service deleted.", color="warning")

    # Refresh the dropdown list after any mutation.
    services = api_db_service.list_services(API_DB_PATH, include_disabled=True)
    options = _service_options(services)

    if new_selection is None and services and triggered in (None, "initial-load"):
        new_selection = services[0]["id"]

    if new_selection and not any(option["value"] == new_selection for option in options):
        new_selection = None

    return options, new_selection, feedback


@callback(
    Output("workspace-api-service-name", "value"),
    Output("workspace-api-service-base-url", "value"),
    Output("workspace-api-service-auth-type", "value"),
    Output("workspace-api-service-auth-secret", "value"),
    Output("workspace-api-service-headers", "value"),
    Output("workspace-api-service-enabled", "value"),
    Output("workspace-api-service-notes", "value"),
    Input("workspace-api-service-select", "value"),
    prevent_initial_call=False,
)
def populate_service_form(service_id: str | None) -> tuple[Any, ...]:
    """Populate the service form from the selected service."""
    if not service_id:
        return ("", "", "none", "", "", ["enabled"], "")

    # When selection changes, load the current record into the form fields.
    service = api_db_service.get_service(service_id, db_path=API_DB_PATH)
    enabled = ["enabled"] if service["enabled"] else []
    return (
        service["name"],
        service["base_url"],
        service["auth_type"],
        service.get("auth_secret") or "",
        _format_json(service.get("default_headers")),
        enabled,
        service.get("notes") or "",
    )


@callback(
    Output("workspace-api-command-select", "options"),
    Output("workspace-api-command-select", "value"),
    Output("workspace-api-command-feedback", "children"),
    Input("workspace-api-service-select", "value"),
    Input("workspace-api-command-save", "n_clicks"),
    Input("workspace-api-command-delete", "n_clicks"),
    Input("workspace-api-command-new", "n_clicks"),
    State("workspace-api-command-select", "value"),
    State("workspace-api-command-name", "value"),
    State("workspace-api-command-method", "value"),
    State("workspace-api-command-path", "value"),
    State("workspace-api-command-query", "value"),
    State("workspace-api-command-headers", "value"),
    State("workspace-api-command-body", "value"),
    State("workspace-api-command-timeout", "value"),
    prevent_initial_call=False,
)
def manage_api_commands(
    service_id: str | None,
    save_clicks: int | None,
    delete_clicks: int | None,
    new_clicks: int | None,
    selected_command: str | None,
    name: str | None,
    method: str | None,
    path: str | None,
    query_text: str | None,
    headers_text: str | None,
    body_text: str | None,
    timeout_seconds: int | None,
) -> tuple[list[dict[str, str]], str | None, Any]:
    """Create, update, delete, or list API commands for a service."""
    triggered = ctx.triggered_id
    feedback: Any = no_update
    new_selection = selected_command

    # Commands are scoped to the currently selected service.
    if triggered == "workspace-api-command-new":
        new_selection = None
        feedback = _alert("Ready to create a new command.", color="secondary")
    elif triggered == "workspace-api-command-save":
        if not service_id:
            feedback = _alert("Select a service before saving a command.", color="danger")
        elif not name or not name.strip():
            feedback = _alert("Command name is required.", color="danger")
        elif not path or not str(path).strip():
            feedback = _alert("Command path is required.", color="danger")
        else:
            # Parse JSON-only fields into structured dicts for storage.
            query, error = _parse_json_field(
                query_text,
                field_label="Query",
                expect_dict=True,
                default={},
            )
            if error:
                feedback = _alert(error, color="danger")
            else:
                headers, header_error = _parse_json_field(
                    headers_text,
                    field_label="Headers",
                    expect_dict=True,
                    default={},
                )
                if header_error:
                    feedback = _alert(header_error, color="danger")
                else:
                    body, body_error = _parse_json_field(
                        body_text,
                        field_label="Body",
                        expect_dict=False,
                        default=None,
                    )
                    if body_error:
                        feedback = _alert(body_error, color="danger")
                    else:
                        payload = {
                            "service_id": service_id,
                            "name": name.strip(),
                            "method": (method or "GET"),
                            "path": str(path).strip(),
                            "query": query,
                            "headers": headers,
                            "body": body,
                            "timeout_seconds": timeout_seconds,
                        }
                        if new_selection:
                            api_db_service.update_command(
                                new_selection,
                                db_path=API_DB_PATH,
                                **payload,
                            )
                            feedback = _alert("Command updated.", color="success")
                        else:
                            new_selection = api_db_service.create_command(
                                db_path=API_DB_PATH,
                                **payload,
                            )
                            feedback = _alert("Command created.", color="success")
    elif triggered == "workspace-api-command-delete":
        if not new_selection:
            feedback = _alert("Select a command to delete.", color="danger")
        else:
            api_db_service.delete_command(new_selection, db_path=API_DB_PATH)
            new_selection = None
            feedback = _alert("Command deleted.", color="warning")
    elif triggered == "workspace-api-service-select":
        new_selection = None

    if not service_id:
        return [], None, feedback

    # Refresh command list once we know the active service.
    commands = api_db_service.list_commands(service_id, db_path=API_DB_PATH)
    options = _command_options(commands)

    if new_selection is None and commands and triggered == "workspace-api-service-select":
        new_selection = None

    if new_selection and not any(option["value"] == new_selection for option in options):
        new_selection = None

    return options, new_selection, feedback


@callback(
    Output("workspace-api-command-name", "value"),
    Output("workspace-api-command-method", "value"),
    Output("workspace-api-command-path", "value"),
    Output("workspace-api-command-query", "value"),
    Output("workspace-api-command-headers", "value"),
    Output("workspace-api-command-body", "value"),
    Output("workspace-api-command-timeout", "value"),
    Input("workspace-api-command-select", "value"),
    prevent_initial_call=False,
)
def populate_command_form(command_id: str | None) -> tuple[Any, ...]:
    """Populate the command form from the selected command."""
    if not command_id:
        return ("", "GET", "", "", "", "", None)

    # Fetch a single command and hydrate the form inputs.
    command = api_db_service.get_command(command_id, db_path=API_DB_PATH)
    return (
        command["name"],
        command["method"],
        command["path"],
        _format_json(command.get("query")),
        _format_json(command.get("headers")),
        _format_json(command.get("body")),
        command.get("timeout_seconds"),
    )


@callback(
    Output("workspace-api-jobs", "data", allow_duplicate=True),
    Output("workspace-api-run-feedback", "children", allow_duplicate=True),
    Input("workspace-api-command-run", "n_clicks"),
    State("workspace-api-jobs", "data"),
    State("workspace-api-service-select", "value"),
    State("workspace-api-service-base-url", "value"),
    State("workspace-api-service-auth-type", "value"),
    State("workspace-api-service-auth-secret", "value"),
    State("workspace-api-service-headers", "value"),
    State("workspace-api-command-method", "value"),
    State("workspace-api-command-path", "value"),
    State("workspace-api-command-query", "value"),
    State("workspace-api-command-headers", "value"),
    State("workspace-api-command-body", "value"),
    State("workspace-api-command-timeout", "value"),
    prevent_initial_call=True,
)
def run_api_request(
    _: int | None,
    api_jobs: dict | None,
    service_id: str | None,
    base_url: str | None,
    auth_type: str | None,
    auth_secret: str | None,
    service_headers_text: str | None,
    method: str | None,
    path: str | None,
    query_text: str | None,
    headers_text: str | None,
    body_text: str | None,
    timeout_seconds: int | None,
) -> tuple[dict, Any]:
    """Queue an API request in the background and report immediate status."""
    # Use strict validation before running so background jobs stay clean.
    if not service_id:
        return no_update, _alert("Select a service before running a command.", color="danger")

    if not base_url or not base_url.strip():
        return no_update, _alert("Service base URL is required.", color="danger")

    method = (method or "GET").strip().upper()
    path = (path or "").strip()

    service_headers, error = _parse_json_field(
        service_headers_text,
        field_label="Default Headers",
        expect_dict=True,
        default={},
    )
    if error:
        return no_update, _alert(error, color="danger")

    query, error = _parse_json_field(
        query_text,
        field_label="Query",
        expect_dict=True,
        default={},
    )
    if error:
        return no_update, _alert(error, color="danger")

    headers, error = _parse_json_field(
        headers_text,
        field_label="Headers",
        expect_dict=True,
        default={},
    )
    if error:
        return no_update, _alert(error, color="danger")

    body, error = _parse_json_field(
        body_text,
        field_label="Body",
        expect_dict=False,
        default=None,
    )
    if error:
        return no_update, _alert(error, color="danger")

    # Merge service headers with command-specific overrides (case-insensitive).
    merged_headers = _merge_headers(service_headers, headers)

    # Run the HTTP request in the I/O job pool so the UI stays responsive.
    job_id = submit_io_job(
        execute_api_request,
        base_url=base_url.strip(),
        path=path,
        method=method,
        headers=merged_headers,
        query=query,
        body=body,
        auth_type=auth_type or "none",
        auth_secret=auth_secret or None,
        timeout_seconds=timeout_seconds,
    )

    jobs = list((api_jobs or {}).get("jobs", []))
    jobs.append({"id": job_id, "label": f"{method} {path or '/'}"})
    return {"jobs": jobs}, _alert("Request queued.", color="info")


@callback(
    Output("workspace-api-jobs", "data", allow_duplicate=True),
    Output("workspace-api-response", "data", allow_duplicate=True),
    Output("workspace-api-run-feedback", "children", allow_duplicate=True),
    Input("io-job-poll", "n_intervals"),
    State("workspace-api-jobs", "data"),
    prevent_initial_call=True,
)
def poll_api_jobs(_: int, api_jobs: dict | None) -> tuple[Any, Any, Any]:
    """Poll background API jobs and surface response data."""
    jobs = list((api_jobs or {}).get("jobs", []))
    if not jobs:
        return no_update, no_update, no_update

    # Walk all queued jobs and surface the most recent finished result.
    updated_jobs: list[dict[str, Any]] = []
    latest_response: Any = no_update
    feedback: Any = no_update

    for job in jobs:
        job_id = job.get("id")
        if not job_id:
            continue
        status = get_io_job_status(job_id)
        if status is None or status.get("status") == "pending":
            updated_jobs.append(job)
            continue

        forget_io_job(job_id)
        if status.get("status") == "error":
            latest_response = {
                "ok": False,
                "error": status.get("error", "Unknown error"),
            }
            feedback = _alert("Request failed.", color="danger")
        else:
            latest_response = status.get("result")
            feedback = _alert("Response received.", color="success")

    if updated_jobs == jobs and latest_response is no_update:
        return no_update, no_update, no_update

    return {"jobs": updated_jobs}, latest_response, feedback


@callback(
    Output("workspace-api-response-view", "children"),
    Input("workspace-api-response", "data"),
    prevent_initial_call=False,
)
def render_api_response(response: dict | None) -> Any:
    """Render the latest API response in the Workspace UI."""
    if not response:
        return html.Div("No response yet.", className="text-muted small")

    if response.get("ok") is False and response.get("error"):
        return dbc.Alert(
            response.get("error", "Request failed."),
            color="danger",
            className="mb-0",
        )

    status = response.get("status_code", "—")
    method = response.get("method", "REQUEST")
    url = response.get("url", "")
    elapsed = response.get("elapsed_ms")
    timing = f"{elapsed} ms" if elapsed is not None else "—"
    headline = f"{method} {url} • {status} • {timing}"

    body_json = response.get("json")
    body_text = response.get("text") or ""
    if body_json is not None:
        body_payload = json.dumps(body_json, indent=2, sort_keys=True)
    else:
        body_payload = body_text

    return html.Div(
        [
            dbc.Alert(headline, color="info", className="py-1 mb-2"),
            html.Pre(body_payload, className="mb-0"),
        ]
    )
