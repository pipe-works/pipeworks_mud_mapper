"""Callbacks for Ollama model discovery and connectivity.

This module focuses on operations that query the Ollama server for
model availability and connection status. Keeping these callbacks
isolated reduces the size of the main Ollama callback surface.
"""

import httpx
from dash import Input, Output, State, callback, html, no_update

from pipeworks_mud_mapper.services import ollama_client
from pipeworks_mud_mapper.services.ollama_ui import (
    status_error_filled,
    status_ok_filled,
    status_warning,
)


@callback(
    Output("ollama-model-dropdown", "options"),
    Output("ollama-connection-status", "children"),
    Output("ollama-model-dropdown", "placeholder"),
    Input("ollama-refresh-models-btn", "n_clicks"),
    State("ollama-server-url", "value"),
    prevent_initial_call=True,
    running=[
        # Spin the refresh icon while fetching models
        (
            Output("ollama-refresh-icon", "className"),
            "bi bi-arrow-clockwise spinning",
            "bi bi-arrow-clockwise",
        ),
        # Disable button during fetch
        (Output("ollama-refresh-models-btn", "disabled"), True, False),
        # Show "Connecting..." status
        (
            Output("ollama-connection-status", "children"),
            html.Small(
                [
                    html.I(className="bi bi-hourglass-split text-info me-1"),
                    "Connecting...",
                ],
                className="text-info",
            ),
            None,  # Will be replaced by callback output
        ),
    ],
)
def refresh_ollama_models(n_clicks: int, server_url: str) -> tuple:
    """Fetch available models from the Ollama server.

    Calls the Ollama /api/tags endpoint to retrieve the list of installed
    models and returns dropdown options plus a connection status message.

    Parameters
    ----------
    n_clicks : int
        Click count for the refresh button.
    server_url : str
        Ollama server URL (e.g., http://localhost:11434).

    Returns
    -------
    tuple
        (model_options, connection_status, placeholder)
        - model_options: List of dicts with 'label' and 'value' keys
        - connection_status: HTML element showing connection state
        - placeholder: Dropdown placeholder text
    """
    # Guard: Don't process if button wasn't actually clicked
    if not n_clicks:
        return no_update, no_update, no_update

    # Validate server URL is provided
    if not server_url:
        status = status_warning("Please enter a server URL")
        return [], status, "Enter server URL first"

    # Normalize URL: Remove trailing slash to avoid double slashes in endpoint
    server_url = server_url.rstrip("/")

    try:
        # Fetch the models list from the Ollama server.
        models = ollama_client.list_models(server_url)

        # Handle edge case: Connected but no models installed
        if not models:
            status = html.Small(
                [
                    html.I(className="bi bi-check-circle text-success me-1"),
                    "Connected - no models installed",
                ],
                className="text-warning",
            )
            return [], status, "No models available"

        # Build dropdown options from model names
        options = [{"label": m["name"], "value": m["name"]} for m in models]

        # Show success status with model count
        status = status_ok_filled(
            f"Connected ({len(models)} model{'s' if len(models) != 1 else ''})"
        )
        return options, status, "Select a model"

    except httpx.ConnectError:
        # Server not reachable (not running, wrong host/port, firewall, etc.)
        status = status_error_filled("Not connected - cannot reach server")
        return [], status, "Connection failed"

    except httpx.HTTPStatusError as e:
        # Server returned an HTTP error (4xx, 5xx)
        status = status_error_filled(f"Not connected - HTTP {e.response.status_code}")
        return [], status, "Connection failed"

    except Exception as e:
        # Catch-all for unexpected errors (JSON parse, network issues, etc.)
        status = status_error_filled(f"Error: {str(e)[:30]}")
        return [], status, "Connection failed"
