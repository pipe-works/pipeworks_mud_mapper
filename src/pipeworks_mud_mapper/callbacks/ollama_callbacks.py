"""Ollama LLM integration callbacks.

This module handles communication with a local Ollama server for
generating room descriptions using LLMs.

Component Dependencies
----------------------
**Inputs:**
- ``ollama-refresh-models-btn``: Refresh available models
- ``ollama-generate-btn``: Generate description
- ``ollama-copy-btn``: Copy response to clipboard

**States:**
- ``ollama-server-url``: Ollama server URL
- ``ollama-model-dropdown``: Selected model
- ``ollama-system-prompt``: System prompt text
- ``ollama-user-prompt``: User prompt text

**Outputs:**
- ``ollama-model-dropdown``: Updated model options
- ``ollama-response``: Generated text
- ``ollama-status``: Status messages
- ``ollama-clipboard``: Clipboard content

See Also
--------
- ``layout/properties_panel.py``: UI components for Ollama section
"""

import httpx
from dash import Input, Output, State, callback, html, no_update

# Default timeout for Ollama API calls (seconds)
OLLAMA_TIMEOUT = 60.0


@callback(
    Output("ollama-model-dropdown", "options"),
    Output("ollama-status", "children"),
    Input("ollama-refresh-models-btn", "n_clicks"),
    State("ollama-server-url", "value"),
    prevent_initial_call=True,
)
def refresh_ollama_models(n_clicks: int, server_url: str) -> tuple:
    """Fetch available models from the Ollama server.

    Calls the Ollama /api/tags endpoint to get the list of
    available models and populates the dropdown.

    Parameters
    ----------
    n_clicks : int
        Click count for the refresh button.
    server_url : str
        Ollama server URL (e.g., http://localhost:11434).

    Returns
    -------
    tuple
        (model_options, status_message)
    """
    if not n_clicks:
        return no_update, no_update

    if not server_url:
        return [], html.Span("Please enter a server URL", className="text-warning")

    # Normalize URL
    server_url = server_url.rstrip("/")

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{server_url}/api/tags")
            response.raise_for_status()
            data = response.json()

        models = data.get("models", [])
        if not models:
            return [], html.Span("No models found on server", className="text-warning")

        # Build dropdown options
        options = [{"label": m["name"], "value": m["name"]} for m in models]

        status = html.Span(
            [
                html.I(className="bi bi-check-circle text-success me-1"),
                f"Found {len(models)} model(s)",
            ]
        )
        return options, status

    except httpx.ConnectError:
        return [], html.Span(
            [
                html.I(className="bi bi-x-circle text-danger me-1"),
                "Cannot connect to server",
            ]
        )
    except httpx.HTTPStatusError as e:
        return [], html.Span(
            [
                html.I(className="bi bi-x-circle text-danger me-1"),
                f"Server error: {e.response.status_code}",
            ]
        )
    except Exception as e:
        return [], html.Span(
            [
                html.I(className="bi bi-x-circle text-danger me-1"),
                f"Error: {str(e)[:50]}",
            ]
        )


@callback(
    Output("ollama-response", "value"),
    Output("ollama-status", "children", allow_duplicate=True),
    Output("ollama-generate-btn", "disabled"),
    Input("ollama-generate-btn", "n_clicks"),
    State("ollama-server-url", "value"),
    State("ollama-model-dropdown", "value"),
    State("ollama-system-prompt", "value"),
    State("ollama-user-prompt", "value"),
    prevent_initial_call=True,
)
def generate_description(
    n_clicks: int,
    server_url: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
) -> tuple:
    """Generate a room description using Ollama.

    Sends a request to the Ollama /api/generate endpoint with the
    system and user prompts, and returns the generated text.

    Parameters
    ----------
    n_clicks : int
        Click count for the generate button.
    server_url : str
        Ollama server URL.
    model : str
        Selected model name.
    system_prompt : str
        System prompt for the LLM.
    user_prompt : str
        User prompt describing what to generate.

    Returns
    -------
    tuple
        (response_text, status_message, button_disabled)
    """
    if not n_clicks:
        return no_update, no_update, no_update

    # Validate inputs
    if not server_url:
        return "", html.Span("Please enter a server URL", className="text-warning"), False

    if not model:
        return "", html.Span("Please select a model", className="text-warning"), False

    if not user_prompt:
        return "", html.Span("Please enter a user prompt", className="text-warning"), False

    # Normalize URL
    server_url = server_url.rstrip("/")

    # Build the prompt
    full_prompt = user_prompt
    if system_prompt:
        full_prompt = f"{system_prompt}\n\n{user_prompt}"

    try:
        # Show generating status
        with httpx.Client(timeout=OLLAMA_TIMEOUT) as client:
            response = client.post(
                f"{server_url}/api/generate",
                json={
                    "model": model,
                    "prompt": full_prompt,
                    "stream": False,
                },
            )
            response.raise_for_status()
            data = response.json()

        generated_text = data.get("response", "").strip()

        if not generated_text:
            return "", html.Span("Empty response from model", className="text-warning"), False

        status = html.Span(
            [
                html.I(className="bi bi-check-circle text-success me-1"),
                "Generated successfully",
            ]
        )
        return generated_text, status, False

    except httpx.ConnectError:
        return (
            "",
            html.Span(
                [
                    html.I(className="bi bi-x-circle text-danger me-1"),
                    "Cannot connect to server",
                ]
            ),
            False,
        )
    except httpx.TimeoutException:
        return (
            "",
            html.Span(
                [
                    html.I(className="bi bi-x-circle text-danger me-1"),
                    "Request timed out",
                ]
            ),
            False,
        )
    except httpx.HTTPStatusError as e:
        return (
            "",
            html.Span(
                [
                    html.I(className="bi bi-x-circle text-danger me-1"),
                    f"Server error: {e.response.status_code}",
                ]
            ),
            False,
        )
    except Exception as e:
        return (
            "",
            html.Span(
                [
                    html.I(className="bi bi-x-circle text-danger me-1"),
                    f"Error: {str(e)[:50]}",
                ]
            ),
            False,
        )


@callback(
    Output("ollama-status", "children", allow_duplicate=True),
    Input("ollama-copy-btn", "n_clicks"),
    State("ollama-response", "value"),
    prevent_initial_call=True,
)
def handle_copy_click(n_clicks: int, response_text: str):
    """Show feedback when copy button is clicked.

    Note: Actual clipboard functionality is handled by dcc.Clipboard
    component. This callback just shows a status message.

    Parameters
    ----------
    n_clicks : int
        Click count for the copy button.
    response_text : str
        Current response text.

    Returns
    -------
    html component
        Status message.
    """
    if not n_clicks:
        return no_update

    if not response_text:
        return html.Span("Nothing to copy", className="text-muted")

    return html.Span(
        [
            html.I(className="bi bi-clipboard-check text-success me-1"),
            "Copied to clipboard!",
        ]
    )
