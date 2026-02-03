"""Ollama LLM integration callbacks.

This module handles communication with a local Ollama server for
generating room descriptions using LLMs, with support for template-based
system prompts following the Craft of Constraint philosophy.

API Endpoint
------------
Uses Ollama's ``/api/chat`` endpoint with proper message roles (system/user)
for better prompt handling. This allows the model's chat template to format
system and user content correctly.

Template System
---------------
Templates are JSON files in ``data/ollama/templates/`` that compile into
comprehensive system prompts. The template dropdown allows authors to:

- Select pre-built templates (e.g., "Ledgerfall Goblin")
- Use "Custom" mode for manual editing
- View the compiled system prompt (read-only when using templates)

Component Dependencies
----------------------
**Inputs:**
- ``ollama-refresh-models-btn``: Refresh available models
- ``ollama-generate-btn``: Generate description
- ``ollama-send-to-description-btn``: Send response to room description
- ``ollama-populate-prompt-btn``: Populate prompt from room description
- ``ollama-clipboard``: Clipboard copy event
- ``ollama-template-dropdown``: Template selector
- ``ollama-system-prompt-toggle``: Toggle system prompt collapse

**States:**
- ``ollama-server-url``: Ollama server URL
- ``ollama-model-dropdown``: Selected model
- ``ollama-system-prompt``: System prompt text (from template or custom)
- ``ollama-user-prompt``: User prompt text
- ``ollama-response``: Generated response text
- ``ollama-system-prompt-collapse``: Collapse state
- ``room-description``: Current room description (for populate)

**Outputs:**
- ``ollama-model-dropdown``: Updated model options
- ``ollama-template-dropdown``: Updated template options
- ``ollama-connection-status``: Connection status indicator
- ``ollama-system-prompt``: Compiled system prompt (from template)
- ``ollama-system-prompt-collapse``: Collapse open/closed state
- ``ollama-response``: Generated text
- ``ollama-status``: Status messages
- ``ollama-clipboard-feedback``: Clipboard copy feedback
- ``room-description``: Room description field (via send button)
- ``ollama-user-prompt``: User prompt (via populate button)

Loading State Indicators
------------------------
Uses Dash's ``running`` callback parameter for real-time feedback:

- **Model refresh**: Spins the refresh icon while fetching models
- **Generation**: Shows "Generating..." with spinner during LLM inference

This is especially important for slower hardware (e.g., Raspberry Pi
running gemma2:2b) where generation can take significant time.

See Also
--------
- ``layout/properties_panel.py``: UI components for Ollama section
- ``services/template_service.py``: Template loading and compilation
- ``models/template.py``: Pydantic template models
"""

import httpx
from dash import Input, Output, State, callback, html, no_update

# Default timeout for Ollama API calls (seconds)
OLLAMA_TIMEOUT = 60.0


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
        (model_options, connection_status, placeholder)
    """
    if not n_clicks:
        return no_update, no_update, no_update

    if not server_url:
        status = html.Small(
            [
                html.I(className="bi bi-exclamation-circle text-warning me-1"),
                "Please enter a server URL",
            ],
            className="text-warning",
        )
        return [], status, "Enter server URL first"

    # Normalize URL
    server_url = server_url.rstrip("/")

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{server_url}/api/tags")
            response.raise_for_status()
            data = response.json()

        models = data.get("models", [])
        if not models:
            status = html.Small(
                [
                    html.I(className="bi bi-check-circle text-success me-1"),
                    "Connected - no models installed",
                ],
                className="text-warning",
            )
            return [], status, "No models available"

        # Build dropdown options
        options = [{"label": m["name"], "value": m["name"]} for m in models]

        status = html.Small(
            [
                html.I(className="bi bi-check-circle-fill text-success me-1"),
                f"Connected ({len(models)} model{'s' if len(models) != 1 else ''})",
            ],
            className="text-success",
        )
        return options, status, "Select a model"

    except httpx.ConnectError:
        status = html.Small(
            [
                html.I(className="bi bi-x-circle-fill text-danger me-1"),
                "Not connected - cannot reach server",
            ],
            className="text-danger",
        )
        return [], status, "Connection failed"
    except httpx.HTTPStatusError as e:
        status = html.Small(
            [
                html.I(className="bi bi-x-circle-fill text-danger me-1"),
                f"Not connected - HTTP {e.response.status_code}",
            ],
            className="text-danger",
        )
        return [], status, "Connection failed"
    except Exception as e:
        status = html.Small(
            [
                html.I(className="bi bi-x-circle-fill text-danger me-1"),
                f"Error: {str(e)[:30]}",
            ],
            className="text-danger",
        )
        return [], status, "Connection failed"


@callback(
    Output("ollama-response", "value"),
    Output("ollama-status", "children"),
    Input("ollama-generate-btn", "n_clicks"),
    State("ollama-server-url", "value"),
    State("ollama-model-dropdown", "value"),
    State("ollama-system-prompt", "value"),
    State("ollama-user-prompt", "value"),
    prevent_initial_call=True,
    running=[
        # Disable the button during generation
        (Output("ollama-generate-btn", "disabled"), True, False),
        # Show spinner icon instead of magic wand
        (
            Output("ollama-generate-icon", "className"),
            "bi bi-hourglass-split spinning",
            "bi bi-magic me-1",
        ),
        # Change button text to "Generating..."
        (Output("ollama-generate-text", "children"), "Generating...", "Generate"),
        # Show status message during generation
        (
            Output("ollama-status", "children"),
            html.Span(
                [
                    html.I(className="bi bi-hourglass-split text-info me-1 spinning"),
                    "Generating description...",
                ],
                className="text-info",
            ),
            None,  # Will be replaced by callback output
        ),
        # Clear previous response while generating
        (Output("ollama-response", "value"), "", None),
    ],
)
def generate_description(
    n_clicks: int,
    server_url: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
) -> tuple:
    """Generate a room description using Ollama.

    Sends a request to the Ollama ``/api/chat`` endpoint with proper
    message roles (system/user) for better prompt handling by the LLM.

    The ``running`` callback parameter provides real-time feedback:

    - Button shows "Generating..." with spinner
    - Status shows "Generating description..."
    - Previous response is cleared

    This is especially important for slower hardware where generation
    can take significant time (e.g., Raspberry Pi with gemma2:2b).

    Parameters
    ----------
    n_clicks : int
        Click count for the generate button.
    server_url : str
        Ollama server URL.
    model : str
        Selected model name.
    system_prompt : str
        System prompt for the LLM (from template or custom).
    user_prompt : str
        User prompt describing what to generate.

    Returns
    -------
    tuple
        (response_text, status_message)

    Notes
    -----
    Uses ``/api/chat`` instead of ``/api/generate`` for proper
    system/user message separation. This lets the model's chat
    template format them correctly.
    """
    if not n_clicks:
        return no_update, no_update

    # Validate inputs
    if not server_url:
        return "", html.Span("Please enter a server URL", className="text-warning")

    if not model:
        return "", html.Span("Please select a model", className="text-warning")

    if not user_prompt:
        return "", html.Span("Please enter a user prompt", className="text-warning")

    # Normalize URL - remove trailing slash to avoid double slashes in endpoint
    server_url = server_url.rstrip("/")

    # Build messages array with proper roles for /api/chat endpoint.
    # The /api/chat endpoint expects a "messages" array where each message
    # has a "role" (system/user/assistant) and "content" field.
    # This allows the model's chat template to properly format the
    # system prompt separately from user content.
    messages = []
    if system_prompt:
        # System prompt is sent as a separate message with role "system"
        # This is the compiled template or custom prompt from the UI
        messages.append({"role": "system", "content": system_prompt})
    # User prompt describes what room description the author wants
    messages.append({"role": "user", "content": user_prompt})

    try:
        with httpx.Client(timeout=OLLAMA_TIMEOUT) as client:
            # Use /api/chat instead of /api/generate for proper message roles.
            # This lets models with chat templates (like llama3, mistral) handle
            # system vs user content correctly.
            response = client.post(
                f"{server_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,  # Wait for complete response
                },
            )
            response.raise_for_status()
            data = response.json()

        # Extract response from chat format - the assistant's response is
        # nested under data["message"]["content"] (not data["response"])
        generated_text = data.get("message", {}).get("content", "").strip()

        if not generated_text:
            return "", html.Span("Empty response from model", className="text-warning")

        status = html.Span(
            [
                html.I(className="bi bi-check-circle text-success me-1"),
                "Generated successfully",
            ]
        )
        return generated_text, status

    except httpx.ConnectError:
        return (
            "",
            html.Span(
                [
                    html.I(className="bi bi-x-circle text-danger me-1"),
                    "Cannot connect to server",
                ]
            ),
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
        )


@callback(
    Output("room-description", "value", allow_duplicate=True),
    Output("current-zone-data", "data", allow_duplicate=True),
    Output("has-unsaved-changes", "data", allow_duplicate=True),
    Output("ollama-status", "children", allow_duplicate=True),
    Input("ollama-send-to-description-btn", "n_clicks"),
    State("ollama-response", "value"),
    State("selected-room", "data"),
    State("current-zone-data", "data"),
    prevent_initial_call=True,
)
def send_to_description(
    n_clicks: int,
    response_text: str,
    selected_room: str | None,
    zone_data: dict | None,
):
    """Send the generated response to the room description field.

    Also updates the zone data directly so the change is immediately
    reflected in the save state.

    Parameters
    ----------
    n_clicks : int
        Click count for the send button.
    response_text : str
        Current response text.
    selected_room : str | None
        Currently selected room ID.
    zone_data : dict | None
        Current zone data.

    Returns
    -------
    tuple
        (description_value, zone_data, has_unsaved, status_message)
    """
    if not n_clicks:
        return no_update, no_update, no_update, no_update

    if not response_text:
        return no_update, no_update, no_update, html.Span("Nothing to send", className="text-muted")

    # If no room is selected, just update the form field
    if not selected_room or not zone_data:
        status = html.Span(
            [
                html.I(className="bi bi-info-circle text-info me-1"),
                "Sent to form (select a room to apply)",
            ]
        )
        return response_text, no_update, no_update, status

    # Update zone data directly
    rooms = zone_data.get("rooms", {})
    if selected_room not in rooms:
        return (
            response_text,
            no_update,
            no_update,
            html.Span("Room not found in zone", className="text-warning"),
        )

    # Create updated zone data (copies for Dash reactivity)
    updated_zone = dict(zone_data)
    updated_zone["rooms"] = dict(zone_data.get("rooms", {}))
    updated_room = dict(rooms[selected_room])
    updated_room["description"] = response_text.strip()
    updated_zone["rooms"][selected_room] = updated_room

    status = html.Span(
        [
            html.I(className="bi bi-check-circle text-success me-1"),
            f"Applied to '{selected_room}'",
        ]
    )
    print(f"[DEBUG] send_to_description: setting has_unsaved=True for room '{selected_room}'")
    return response_text, updated_zone, True, status


@callback(
    Output("ollama-clipboard-feedback", "children"),
    Input("ollama-clipboard", "n_clicks"),
    State("ollama-response", "value"),
    prevent_initial_call=True,
)
def handle_clipboard_copy(n_clicks: int, response_text: str):
    """Show feedback when clipboard copy happens.

    Parameters
    ----------
    n_clicks : int
        Click count for the clipboard component.
    response_text : str
        Current response text.

    Returns
    -------
    html component
        Feedback message.
    """
    if not n_clicks:
        return no_update

    if not response_text:
        return html.Small("Nothing to copy", className="text-muted")

    return html.Small(
        [
            html.I(className="bi bi-clipboard-check text-success me-1"),
            "Copied to clipboard",
        ],
        className="text-success",
    )


@callback(
    Output("ollama-user-prompt", "value"),
    Output("ollama-status", "children", allow_duplicate=True),
    Input("ollama-populate-prompt-btn", "n_clicks"),
    State("room-description", "value"),
    State("room-name", "value"),
    prevent_initial_call=True,
)
def populate_prompt_from_description(
    n_clicks: int,
    room_description: str | None,
    room_name: str | None,
) -> tuple:
    """Populate the user prompt with the current room description.

    Allows users to use existing description text as a starting point
    for LLM refinement or regeneration.

    Parameters
    ----------
    n_clicks : int
        Click count for the populate button.
    room_description : str | None
        Current room description text.
    room_name : str | None
        Current room name (for context).

    Returns
    -------
    tuple
        (user_prompt_value, status_message)
    """
    if not n_clicks:
        return no_update, no_update

    if not room_description:
        return (
            no_update,
            html.Span(
                [
                    html.I(className="bi bi-info-circle text-muted me-1"),
                    "No description to use",
                ],
                className="text-muted",
            ),
        )

    # Build a prompt that asks to improve/rewrite the existing description
    if room_name:
        prompt = f"Rewrite this description for a room called '{room_name}':\n\n{room_description}"
    else:
        prompt = f"Rewrite this room description:\n\n{room_description}"

    status = html.Span(
        [
            html.I(className="bi bi-check-circle text-success me-1"),
            "Description copied to prompt",
        ]
    )
    return prompt, status


# =============================================================================
# Template Callbacks
# =============================================================================


@callback(
    Output("ollama-template-dropdown", "options"),
    Input("ollama-refresh-models-btn", "n_clicks"),  # Refresh templates when models refresh
    prevent_initial_call=False,  # Load templates on app startup
)
def load_template_options(n_clicks: int) -> list[dict]:
    """Load available templates for the dropdown.

    Called on app startup and when the refresh button is clicked.
    Templates are loaded from ``data/ollama/templates/``.

    Parameters
    ----------
    n_clicks : int
        Click count (unused, just triggers refresh).

    Returns
    -------
    list[dict]
        Dropdown options with 'label' and 'value' keys.
        Includes a "Custom" option at the end.
    """
    from pipeworks_mud_mapper.services import template_service

    # Get templates from service
    templates = template_service.list_templates()

    # Add "Custom" option at the end for manual editing
    templates.append({"label": "Custom (edit manually)", "value": "__custom__"})

    return templates


@callback(
    Output("ollama-system-prompt", "value"),
    Output("ollama-system-prompt", "readOnly"),
    Output("ollama-system-prompt-collapse", "is_open"),
    Output("ollama-status", "children", allow_duplicate=True),
    Input("ollama-template-dropdown", "value"),
    prevent_initial_call=True,
)
def handle_template_selection(template_id: str | None) -> tuple:
    """Handle template selection from the dropdown.

    When a template is selected, compiles it into a system prompt
    and updates the display. The system prompt becomes read-only
    when using a template, editable when "Custom" is selected.

    Parameters
    ----------
    template_id : str | None
        The selected template ID, or "__custom__" for manual editing.

    Returns
    -------
    tuple
        (system_prompt, read_only, collapse_open, status_message)
    """
    # Import here to avoid circular imports - template_service imports models
    # which could potentially import callbacks in the future
    from pipeworks_mud_mapper.services import template_service

    # No selection made - don't update anything
    if not template_id:
        return no_update, no_update, no_update, no_update

    # Handle "Custom" mode - this special value enables manual editing
    # of the system prompt rather than using a template
    if template_id == "__custom__":
        # Get the simple default prompt for manual editing
        default_prompt = template_service.get_default_system_prompt()
        status = html.Span(
            [
                html.I(className="bi bi-pencil text-info me-1"),
                "Custom mode - edit system prompt freely",
            ]
        )
        # Return: prompt text, NOT read-only (editable), collapse open, status
        return default_prompt, False, True, status

    # Load the selected template from data/ollama/templates/
    # Returns None if template file not found or validation fails
    template = template_service.load_template(template_id)
    if not template:
        status = html.Span(
            [
                html.I(className="bi bi-exclamation-triangle text-warning me-1"),
                f"Template '{template_id}' not found",
            ]
        )
        # Don't update the prompt on error - keep whatever was there
        return no_update, no_update, no_update, status

    # Compile the template JSON into a comprehensive system prompt string
    # This combines Core Rules + theme + voice + constraints + examples
    system_prompt = template_service.compile_system_prompt(template)

    status = html.Span(
        [
            html.I(className="bi bi-check-circle text-success me-1"),
            f"Loaded: {template.template_name} v{template.version}",
        ]
    )
    # Return: compiled prompt, read-only (not editable), collapse open, status
    return system_prompt, True, True, status


@callback(
    Output("ollama-system-prompt-collapse", "is_open", allow_duplicate=True),
    Output("ollama-system-prompt-chevron", "className"),
    Input("ollama-system-prompt-toggle", "n_clicks"),
    State("ollama-system-prompt-collapse", "is_open"),
    prevent_initial_call=True,
)
def toggle_system_prompt_collapse(n_clicks: int, is_open: bool) -> tuple:
    """Toggle the system prompt collapse open/closed.

    Parameters
    ----------
    n_clicks : int
        Click count for the toggle button.
    is_open : bool
        Current collapse state.

    Returns
    -------
    tuple
        (new_is_open, icon_class)
    """
    if not n_clicks:
        return no_update, no_update

    new_is_open = not is_open
    # Chevron down when open, right when closed
    icon_class = "bi bi-chevron-down me-1" if new_is_open else "bi bi-chevron-right me-1"

    return new_is_open, icon_class


@callback(
    Output("ollama-status", "children", allow_duplicate=True),
    Input("ollama-copy-system-prompt-btn", "n_clicks"),
    State("ollama-system-prompt", "value"),
    prevent_initial_call=True,
)
def copy_system_prompt(n_clicks: int, system_prompt: str) -> html.Span:
    """Copy the system prompt to clipboard and show feedback.

    Note: The actual clipboard copy is handled by JavaScript via
    the button's data-clipboard attributes. This callback just
    provides feedback.

    Parameters
    ----------
    n_clicks : int
        Click count for the copy button.
    system_prompt : str
        Current system prompt text.

    Returns
    -------
    html.Span
        Status message confirming the copy.
    """
    if not n_clicks:
        return no_update

    if not system_prompt:
        return html.Span(
            [
                html.I(className="bi bi-info-circle text-muted me-1"),
                "No system prompt to copy",
            ],
            className="text-muted",
        )

    return html.Span(
        [
            html.I(className="bi bi-clipboard-check text-success me-1"),
            "System prompt copied!",
        ],
        className="text-success",
    )
