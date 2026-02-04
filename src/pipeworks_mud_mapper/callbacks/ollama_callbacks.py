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

Model Parameters
----------------
The generate_description callback accepts several model parameters that
control the LLM's behavior:

+---------------+---------+----------------------------------------------+
| Parameter     | Default | Purpose                                      |
+===============+=========+==============================================+
| seed          | -1      | -1 = random, 0+ = reproducible generation    |
+---------------+---------+----------------------------------------------+
| temperature   | 0.7     | Controls creativity (0=focused, 2=creative)  |
+---------------+---------+----------------------------------------------+
| top_k         | 40      | Limits vocab to top K probable tokens        |
+---------------+---------+----------------------------------------------+
| top_p         | 0.9     | Nucleus sampling threshold (cumulative prob) |
+---------------+---------+----------------------------------------------+
| num_ctx       | 4096    | Context window size in tokens                |
+---------------+---------+----------------------------------------------+
| num_predict   | 512     | Maximum tokens to generate                   |
+---------------+---------+----------------------------------------------+

Seed Handling
-------------
When seed is -1, a random seed is generated using an isolated Random
instance to avoid poisoning the global random state. This is critical
for determinism in other parts of the application.

::

    # WRONG - affects global state
    random.seed(42)

    # CORRECT - isolated instance
    rng = random.Random()  # Uses system entropy
    actual_seed = rng.randint(0, 2**31 - 1)

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
- ``ollama-params-toggle``: Toggle parameters collapse
- ``ollama-seed-decrease``: Decrement seed button
- ``ollama-seed-increase``: Increment seed button
- ``ollama-seed-random-check``: Random seed checkbox

**States:**

- ``ollama-server-url``: Ollama server URL
- ``ollama-model-dropdown``: Selected model
- ``ollama-system-prompt``: System prompt text (from template or custom)
- ``ollama-user-prompt``: User prompt text
- ``ollama-response``: Generated response text
- ``ollama-system-prompt-collapse``: Collapse state
- ``ollama-params-collapse``: Parameters collapse state
- ``ollama-seed-value``: Seed value (-1 or fixed)
- ``ollama-temperature``: Temperature parameter
- ``ollama-top-k``: Top-K parameter
- ``ollama-top-p``: Top-P parameter
- ``ollama-num-ctx``: Context window parameter
- ``ollama-num-predict``: Max tokens parameter
- ``room-description``: Current room description (for populate)

**Outputs:**

- ``ollama-model-dropdown``: Updated model options
- ``ollama-template-dropdown``: Updated template options
- ``ollama-connection-status``: Connection status indicator
- ``ollama-system-prompt``: Compiled system prompt (from template)
- ``ollama-system-prompt-collapse``: Collapse open/closed state
- ``ollama-params-collapse``: Parameters collapse state
- ``ollama-params-chevron``: Parameters chevron icon class
- ``ollama-seed-value``: Updated seed value
- ``ollama-seed-random-check``: Updated random checkbox state
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
- ``layout/ollama_panel.py``: UI components for Ollama section
- ``services/template_service.py``: Template loading and compilation
- ``models/template.py``: Pydantic template models
"""

import random
from datetime import UTC, datetime

import httpx
from dash import Input, Output, State, callback, ctx, html, no_update

from pipeworks_mud_mapper.layout.ollama_panel import (
    DEFAULT_NUM_CTX,
    DEFAULT_NUM_PREDICT,
    DEFAULT_SEED,
    DEFAULT_TARGET_WORDS,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_K,
    DEFAULT_TOP_P,
)
from pipeworks_mud_mapper.services import validate_description

# Default timeout for Ollama API calls (seconds)
# This is set relatively high to accommodate slower hardware (e.g., Raspberry Pi)
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
        - model_options: List of dicts with 'label' and 'value' keys
        - connection_status: HTML element showing connection state
        - placeholder: Dropdown placeholder text
    """
    # Guard: Don't process if button wasn't actually clicked
    if not n_clicks:
        return no_update, no_update, no_update

    # Validate server URL is provided
    if not server_url:
        status = html.Small(
            [
                html.I(className="bi bi-exclamation-circle text-warning me-1"),
                "Please enter a server URL",
            ],
            className="text-warning",
        )
        return [], status, "Enter server URL first"

    # Normalize URL: Remove trailing slash to avoid double slashes in endpoint
    server_url = server_url.rstrip("/")

    try:
        # Use httpx context manager for proper connection cleanup
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{server_url}/api/tags")
            response.raise_for_status()
            data = response.json()

        # Extract models list from response
        models = data.get("models", [])

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
        status = html.Small(
            [
                html.I(className="bi bi-check-circle-fill text-success me-1"),
                f"Connected ({len(models)} model{'s' if len(models) != 1 else ''})",
            ],
            className="text-success",
        )
        return options, status, "Select a model"

    except httpx.ConnectError:
        # Server not reachable (not running, wrong host/port, firewall, etc.)
        status = html.Small(
            [
                html.I(className="bi bi-x-circle-fill text-danger me-1"),
                "Not connected - cannot reach server",
            ],
            className="text-danger",
        )
        return [], status, "Connection failed"

    except httpx.HTTPStatusError as e:
        # Server returned an HTTP error (4xx, 5xx)
        status = html.Small(
            [
                html.I(className="bi bi-x-circle-fill text-danger me-1"),
                f"Not connected - HTTP {e.response.status_code}",
            ],
            className="text-danger",
        )
        return [], status, "Connection failed"

    except Exception as e:
        # Catch-all for unexpected errors (JSON parse, network issues, etc.)
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
    # Output metadata to store for later use when "Send to Description" is clicked.
    # This dict contains all generation parameters for reproducibility/provenance.
    Output("ollama-last-generation-info", "data"),
    Input("ollama-generate-btn", "n_clicks"),
    State("ollama-server-url", "value"),
    State("ollama-model-dropdown", "value"),
    State("ollama-system-prompt", "value"),
    State("ollama-user-prompt", "value"),
    # Model parameters from the Parameters section
    State("ollama-seed-value", "value"),
    State("ollama-temperature", "value"),
    State("ollama-top-k", "value"),
    State("ollama-top-p", "value"),
    State("ollama-num-ctx", "value"),
    State("ollama-num-predict", "value"),
    # Template ID and target words for metadata tracking
    State("ollama-template-dropdown", "value"),
    State("ollama-target-words", "value"),
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
    seed: int | None,
    temperature: float | None,
    top_k: int | None,
    top_p: float | None,
    num_ctx: int | None,
    num_predict: int | None,
    template_id: str | None,
    target_words: int | None,
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

    Metadata Output
    ---------------
    On successful generation, this callback outputs metadata to the
    ``ollama-last-generation-info`` store. This metadata is a dict matching
    the ``OllamaGenerationInfo`` model fields:

    - model: The Ollama model used
    - actual_seed: The seed value that was actually used (even if -1 was requested)
    - template_id: The template used, or "__custom__" for manual prompts
    - temperature, top_k, top_p, num_ctx, num_predict: Model parameters
    - system_prompt: The full compiled system prompt
    - user_prompt: The user's prompt text
    - generated_at: ISO 8601 timestamp

    This metadata can later be attached to a room when "Send to Description"
    is clicked, enabling reproducibility and provenance tracking.

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
    seed : int | None
        Random seed for reproducibility. -1 means random (uses isolated RNG).
        If None, defaults to DEFAULT_SEED (-1).
    temperature : float | None
        Controls randomness (0.0=deterministic, 2.0=very creative).
        If None, defaults to DEFAULT_TEMPERATURE (0.7).
    top_k : int | None
        Limits vocabulary to top K probable tokens.
        If None, defaults to DEFAULT_TOP_K (40).
    top_p : float | None
        Nucleus sampling threshold (cumulative probability).
        If None, defaults to DEFAULT_TOP_P (0.9).
    num_ctx : int | None
        Context window size in tokens.
        If None, defaults to DEFAULT_NUM_CTX (4096).
    num_predict : int | None
        Maximum tokens to generate.
        If None, defaults to DEFAULT_NUM_PREDICT (512).
    template_id : str | None
        The template ID selected in the dropdown, or "__custom__" for manual.
        Used for metadata tracking.

    Returns
    -------
    tuple
        (response_text, status_message, generation_info)
        - response_text: Generated description from the LLM
        - status_message: HTML element showing generation status
        - generation_info: Dict with all generation parameters for metadata,
          or None on error

    Notes
    -----
    Uses ``/api/chat`` instead of ``/api/generate`` for proper
    system/user message separation. This lets the model's chat
    template format them correctly.

    **Seed Handling:**

    When seed is -1, we generate a random seed using an isolated Random
    instance. This is critical to avoid poisoning the global random state,
    which could affect determinism in other parts of the application
    (e.g., name generation, character issuance).

    The isolated RNG uses system entropy for seeding, providing good
    randomness without touching the global ``random`` module state.

    See Also
    --------
    OllamaGenerationInfo : The Pydantic model that validates this metadata.
    send_to_description : The callback that stores metadata in room data.
    """
    # Guard: Don't process if button wasn't actually clicked
    if not n_clicks:
        return no_update, no_update, no_update

    # =========================================================================
    # Input Validation
    # =========================================================================
    # Validate all required inputs before making the API call.
    # On validation errors, we return None for the metadata (third return value)
    # since no generation occurred.

    if not server_url:
        return "", html.Span("Please enter a server URL", className="text-warning"), None

    if not model:
        return "", html.Span("Please select a model", className="text-warning"), None

    if not user_prompt:
        return "", html.Span("Please enter a user prompt", className="text-warning"), None

    # =========================================================================
    # Apply Default Values for Parameters
    # =========================================================================
    # Use defaults if values are None (can happen if inputs weren't rendered yet)

    seed = seed if seed is not None else DEFAULT_SEED
    temperature = temperature if temperature is not None else DEFAULT_TEMPERATURE
    top_k = top_k if top_k is not None else DEFAULT_TOP_K
    top_p = top_p if top_p is not None else DEFAULT_TOP_P
    num_ctx = num_ctx if num_ctx is not None else DEFAULT_NUM_CTX
    num_predict = num_predict if num_predict is not None else DEFAULT_NUM_PREDICT
    target_words = target_words if target_words is not None else DEFAULT_TARGET_WORDS

    # =========================================================================
    # Handle Seed Value
    # =========================================================================
    # When seed is -1, generate a random seed using an ISOLATED Random instance.
    # This is critical: we must NOT use random.seed() or random.randint() directly
    # because that would poison the global random state, potentially breaking
    # determinism in other parts of the application (e.g., name generation).
    #
    # By creating a new Random() instance with no seed argument, we get an
    # instance seeded from system entropy (os.urandom or similar), completely
    # independent of the global random state.

    if seed == -1:
        # Create isolated RNG instance - uses system entropy, doesn't affect global state
        rng = random.Random()  # nosec B311 - not used for security, just LLM seed
        # Generate a random seed in the valid range for most LLMs (32-bit signed int)
        actual_seed = rng.randint(0, 2**31 - 1)
    else:
        # Use the provided seed directly for reproducible generation
        actual_seed = int(seed)

    # =========================================================================
    # Prepare API Request
    # =========================================================================
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

    # =========================================================================
    # Make API Request
    # =========================================================================

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
                    "options": {
                        # Seed for reproducibility (actual_seed is always >= 0)
                        "seed": actual_seed,
                        # Temperature controls randomness/creativity
                        "temperature": float(temperature),
                        # Top-K limits vocabulary to most probable tokens
                        "top_k": int(top_k),
                        # Top-P is nucleus sampling threshold
                        "top_p": float(top_p),
                        # Context window size (how much the model can "see")
                        "num_ctx": int(num_ctx),
                        # Maximum tokens to generate
                        "num_predict": int(num_predict),
                    },
                },
            )
            response.raise_for_status()
            data = response.json()

        # Extract response from chat format - the assistant's response is
        # nested under data["message"]["content"] (not data["response"])
        generated_text = data.get("message", {}).get("content", "").strip()

        if not generated_text:
            return "", html.Span("Empty response from model", className="text-warning"), None

        # Show success status with seed info for reproducibility
        if seed == -1:
            seed_info = f"(random seed: {actual_seed})"
        else:
            seed_info = f"(seed: {actual_seed})"

        status = html.Span(
            [
                html.I(className="bi bi-check-circle text-success me-1"),
                f"Generated successfully {seed_info}",
            ]
        )

        # =====================================================================
        # Build Generation Metadata
        # =====================================================================
        # Create a dict matching OllamaGenerationInfo fields. This metadata
        # will be stored in the dcc.Store and can later be attached to the
        # room when "Send to Description" is clicked.
        #
        # The metadata serves two purposes:
        # 1. Reproducibility: With the same model, seed, and parameters,
        #    Ollama should produce identical output.
        # 2. Provenance: Authors can see how a description was generated,
        #    what prompts were used, and when.
        generation_info = {
            # Model identification
            "model": model,
            # The seed that was actually used (critical for reproducibility).
            # If the user requested -1 (random), this contains the generated
            # random seed, enabling exact reproduction later.
            "actual_seed": actual_seed,
            # Template used, or "__custom__" if none/manual editing.
            # We use "__custom__" as fallback if no template was selected.
            "template_id": template_id if template_id else "__custom__",
            # Model parameters - these are the actual values used after defaults
            "temperature": float(temperature),
            "top_k": int(top_k),
            "top_p": float(top_p),
            "num_ctx": int(num_ctx),
            "num_predict": int(num_predict),
            # Target word count used in system prompt compilation
            "target_words": int(target_words),
            # Prompts - stored in full for exact reproducibility
            "system_prompt": system_prompt or "",
            "user_prompt": user_prompt,
            # UTC timestamp in ISO 8601 format for JSON serialization
            "generated_at": datetime.now(UTC).isoformat(),
        }

        return generated_text, status, generation_info

    except httpx.ConnectError:
        # Server not reachable - return None for metadata since no generation occurred
        return (
            "",
            html.Span(
                [
                    html.I(className="bi bi-x-circle text-danger me-1"),
                    "Cannot connect to server",
                ]
            ),
            None,
        )
    except httpx.TimeoutException:
        # Request timed out - return None for metadata
        return (
            "",
            html.Span(
                [
                    html.I(className="bi bi-x-circle text-danger me-1"),
                    "Request timed out",
                ]
            ),
            None,
        )
    except httpx.HTTPStatusError as e:
        # Server returned an error - return None for metadata
        return (
            "",
            html.Span(
                [
                    html.I(className="bi bi-x-circle text-danger me-1"),
                    f"Server error: {e.response.status_code}",
                ]
            ),
            None,
        )
    except Exception as e:
        # Unexpected error - return None for metadata
        return (
            "",
            html.Span(
                [
                    html.I(className="bi bi-x-circle text-danger me-1"),
                    f"Error: {str(e)[:50]}",
                ]
            ),
            None,
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
    # Get the generation metadata from the last successful generation.
    # This contains model, seed, parameters, and prompts for reproducibility.
    State("ollama-last-generation-info", "data"),
    State("ollama-validation-info", "data"),
    prevent_initial_call=True,
)
def send_to_description(
    n_clicks: int,
    response_text: str,
    selected_room: str | None,
    zone_data: dict | None,
    generation_info: dict | None,
    validation_info: dict | None,
):
    """Send the generated response to the room description field.

    Also updates the zone data directly so the change is immediately
    reflected in the save state. When generation metadata is available,
    it is stored in the room's ``llm_generation`` field for provenance
    tracking and reproducibility.

    Metadata Storage
    ----------------
    When a room is updated with an LLM-generated description, the
    ``llm_generation`` field is populated with:

    - model: The Ollama model used
    - actual_seed: The seed value that was actually used
    - template_id: The template used, or "__custom__"
    - temperature, top_k, top_p, num_ctx, num_predict: Model parameters
    - system_prompt: The full compiled system prompt
    - user_prompt: The user's prompt text
    - generated_at: ISO 8601 timestamp

    This metadata is:

    - **Preserved** when saving to .map.json (authoring source)
    - **Stripped** when exporting to zone .json (game truth)

    This follows the same pattern as coordinates - authoring scaffolding
    that supports map creation but isn't part of the final game state.

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
    generation_info : dict | None
        LLM generation metadata from the last generation, or None if
        no successful generation has occurred.
    validation_info : dict | None
        Validator metadata from the last response validation, or None if
        no validation data is available.

    Returns
    -------
    tuple
        (description_value, zone_data, has_unsaved, status_message)

    See Also
    --------
    generate_description : Creates the generation_info metadata.
    OllamaGenerationInfo : The Pydantic model that validates this metadata.
    export_zone : Strips llm_generation when exporting to zone files.
    """
    if not n_clicks:
        return no_update, no_update, no_update, no_update

    if not response_text:
        return no_update, no_update, no_update, html.Span("Nothing to send", className="text-muted")

    # If no room is selected, just update the form field.
    # Note: We can't store metadata without a room to attach it to.
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

    # Create updated zone data (copies for Dash reactivity).
    # We need to create new dict instances so Dash detects the change
    # and triggers dependent callbacks.
    updated_zone = dict(zone_data)
    updated_zone["rooms"] = dict(zone_data.get("rooms", {}))
    updated_room = dict(rooms[selected_room])

    # Update the room description with the generated text
    updated_room["description"] = response_text.strip()

    # =========================================================================
    # Store LLM Generation Metadata
    # =========================================================================
    # If we have generation metadata from the last successful generation,
    # attach it to the room for provenance tracking. This metadata will be:
    # - Preserved when saving to .map.json (for authoring/reproducibility)
    # - Stripped when exporting to zone .json (not needed by game server)
    #
    # If no metadata is available (e.g., user edited the response manually
    # or generation failed), we clear any existing metadata since it would
    # no longer accurately describe the description.

    if generation_info:
        # Attach the generation metadata to the room.
        # The keys match OllamaGenerationInfo fields for validation when loading.
        updated_room["llm_generation"] = generation_info
        print(
            f"[DEBUG] send_to_description: attached llm_generation metadata "
            f"(model={generation_info.get('model')}, seed={generation_info.get('actual_seed')})"
        )
    else:
        # No metadata available - clear any existing metadata.
        # This can happen if the user manually edited the response text
        # or if the generation failed.
        updated_room.pop("llm_generation", None)
        print(
            "[DEBUG] send_to_description: no generation metadata available, cleared llm_generation"
        )

    # Attach validator output for authoring visibility.
    # This is stripped during zone export (like llm_generation).
    if validation_info:
        updated_room["description_validation"] = validation_info
    else:
        updated_room.pop("description_validation", None)

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
    Output("ollama-system-prompt-chevron", "className"),
    Output("ollama-status", "children", allow_duplicate=True),
    Input("ollama-template-dropdown", "value"),
    Input("ollama-target-words", "value"),
    prevent_initial_call=True,
)
def handle_template_selection(template_id: str | None, target_words: int | None) -> tuple:
    """Handle template selection and target word count changes.

    When a template is selected or target words change, compiles the
    template into a system prompt with the specified word count guidance
    and updates the display. The system prompt becomes read-only
    when using a template, editable when "Custom" is selected.

    NOTE: Unlike the previous implementation, this now keeps the
    system prompt collapse CLOSED by default (is_open=False).
    Users who want to see the compiled prompt can click to expand.

    Parameters
    ----------
    template_id : str | None
        The selected template ID, or "__custom__" for manual editing.
    target_words : int | None
        Target word count for generated descriptions. If None, defaults
        to DEFAULT_TARGET_WORDS (300).

    Returns
    -------
    tuple
        (system_prompt, read_only, collapse_open, chevron_class, status_message)
    """
    # Apply default if target_words is None
    if target_words is None:
        target_words = DEFAULT_TARGET_WORDS
    # Import here to avoid circular imports - template_service imports models
    # which could potentially import callbacks in the future
    from pipeworks_mud_mapper.services import template_service

    # No selection made - don't update anything
    if not template_id:
        return no_update, no_update, no_update, no_update, no_update

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
        # Return: prompt text, NOT read-only (editable), collapse OPEN for custom mode,
        # chevron down (open state), status
        return default_prompt, False, True, "bi bi-chevron-down me-1", status

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
        return no_update, no_update, no_update, no_update, status

    # Compile the template JSON into a comprehensive system prompt string
    # This combines Core Rules + theme + voice + constraints + examples
    # The target_words parameter controls the word count guidance in the prompt
    system_prompt = template_service.compile_system_prompt(template, target_words=target_words)

    status = html.Span(
        [
            html.I(className="bi bi-check-circle text-success me-1"),
            f"Loaded: {template.template_name} v{template.version}",
        ]
    )
    # Return: compiled prompt, read-only (not editable), collapse CLOSED by default,
    # chevron right (closed state), status
    # NOTE: Changed from is_open=True to is_open=False to keep system prompt hidden
    return system_prompt, True, False, "bi bi-chevron-right me-1", status


@callback(
    Output("ollama-system-prompt-collapse", "is_open", allow_duplicate=True),
    Output("ollama-system-prompt-chevron", "className", allow_duplicate=True),
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
    Output("ollama-params-collapse", "is_open"),
    Output("ollama-params-chevron", "className"),
    Input("ollama-params-toggle", "n_clicks"),
    State("ollama-params-collapse", "is_open"),
    prevent_initial_call=True,
)
def toggle_params_collapse(n_clicks: int, is_open: bool) -> tuple:
    """Toggle the parameters section collapse open/closed.

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
    Output("ollama-seed-value", "value"),
    Output("ollama-seed-random-check", "value"),
    Input("ollama-seed-decrease", "n_clicks"),
    Input("ollama-seed-increase", "n_clicks"),
    Input("ollama-seed-random-check", "value"),
    State("ollama-seed-value", "value"),
    prevent_initial_call=True,
)
def handle_seed_controls(
    decrease_clicks: int,
    increase_clicks: int,
    random_checked: bool,
    current_seed: int,
) -> tuple:
    """Handle seed control interactions (buttons and checkbox).

    This callback manages the interaction between:
    - The seed value input
    - The +/- buttons for incrementing/decrementing
    - The "Random each time" checkbox

    Logic:
    - If random checkbox is checked, seed is set to -1
    - If random checkbox is unchecked and seed is -1, set seed to 0
    - +/- buttons only work when not in random mode (seed >= 0)

    Parameters
    ----------
    decrease_clicks : int
        Click count for the decrease button.
    increase_clicks : int
        Click count for the increase button.
    random_checked : bool
        Whether the "Random each time" checkbox is checked.
    current_seed : int
        Current seed value from the input.

    Returns
    -------
    tuple
        (new_seed_value, random_checkbox_value)
    """
    # Determine which input triggered the callback
    triggered_id = ctx.triggered_id

    # Handle random checkbox changes
    if triggered_id == "ollama-seed-random-check":
        if random_checked:
            # Random mode enabled: set seed to -1
            return -1, True
        else:
            # Random mode disabled: set seed to 0 (or keep current if valid)
            if current_seed == -1:
                return 0, False
            else:
                return current_seed, False

    # Handle +/- button clicks (only when not in random mode)
    if current_seed == -1:
        # In random mode, buttons don't change the seed
        # But we update the checkbox to True in case it got out of sync
        return -1, True

    # Ensure current_seed is an integer
    seed = int(current_seed) if current_seed is not None else 0

    if triggered_id == "ollama-seed-decrease":
        # Decrement seed, minimum is 0 (not -1, which means random)
        new_seed = max(0, seed - 1)
        return new_seed, False

    if triggered_id == "ollama-seed-increase":
        # Increment seed, no upper limit but keep it reasonable
        new_seed = seed + 1
        return new_seed, False

    # Default: no change
    return no_update, no_update


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


@callback(
    Output("ollama-validator-status", "children"),
    Output("ollama-validator-summary", "children"),
    Output("ollama-validator-hits", "children"),
    Output("ollama-validator-history", "children"),
    Output("ollama-validation-history", "data"),
    Output("ollama-validation-info", "data"),
    Input("ollama-response", "value"),
    State("ollama-target-words", "value"),
    State("ollama-validation-history", "data"),
    prevent_initial_call=True,
)
def validate_ollama_response(
    response_text: str | None,
    target_words: int | None,
    history: list[dict] | None,
):
    """Validate the latest LLM response and update the staging panel.

    This callback is advisory. It never blocks authors from applying a
    description. Instead, it surfaces hard-rule hits and aggregates a
    small in-memory history to make drift visible during iteration.
    """
    if not response_text:
        status = html.Small(
            [
                html.I(className="bi bi-dot text-muted me-1"),
                "Waiting for a response",
            ],
            className="text-muted",
        )
        summary = html.Small("No response to validate yet.", className="text-muted")
        hits = html.Small("No rule hits yet.", className="text-muted")
        history_display = _render_validation_history(history)
        return status, summary, hits, history_display, no_update, no_update

    target_words = target_words if target_words is not None else DEFAULT_TARGET_WORDS
    # The validator is deterministic and uses the UI target for word bounds.
    result = validate_description(response_text, target_words=target_words)

    if result.valid:
        status = html.Small(
            [
                html.I(className="bi bi-check-circle-fill text-success me-1"),
                "Pass (hard rules)",
            ],
            className="text-success",
        )
    else:
        status = html.Small(
            [
                html.I(className="bi bi-exclamation-triangle-fill text-warning me-1"),
                "Review needed",
            ],
            className="text-warning",
        )

    word_count = result.metrics.get("word_count")
    min_words = result.metrics.get("min_words")
    max_words = result.metrics.get("max_words")
    if word_count is not None and min_words is not None and max_words is not None:
        summary_text = (
            f"Words: {word_count} " f"(target {target_words}, range {min_words}-{max_words})"
        )
    else:
        summary_text = f"Target words: {target_words}"

    hard_count = len(result.hard_failures)
    if hard_count:
        summary_text = f"{summary_text} • Hard failures: {hard_count}"
    summary = html.Small(summary_text, className="text-muted")

    hits = _render_rule_hits(result)

    # Maintain a tiny ring buffer to keep the UI readable.
    history_list = list(history or [])
    history_list.append(
        {
            "timestamp": datetime.now(UTC).strftime("%H:%M:%S"),
            "valid": result.valid,
            "word_count": word_count,
            "hard_failures": hard_count,
        }
    )
    history_list = history_list[-3:]
    history_display = _render_validation_history(history_list)

    # Persist the latest validator output for map authoring metadata.
    validation_info = {
        "valid": result.valid,
        "hard_failures": result.hard_failures,
        "soft_failures": result.soft_failures,
        "metrics": result.metrics,
        "rule_hits": result.rule_hits,
        "validated_at": datetime.now(UTC).isoformat(),
    }

    return status, summary, hits, history_display, history_list, validation_info


def _render_rule_hits(result) -> html.Div:
    """Format rule hits for the staging panel."""
    if not result.rule_hits:
        return html.Small("No rule hits.", className="text-muted")

    lines = []
    for rule_name, hits in result.rule_hits.items():
        lines.append(html.Div(f"{rule_name.replace('_', ' ')}: {', '.join(sorted(set(hits)))}"))

    return html.Div(lines, className="text-muted")


def _render_validation_history(history: list[dict] | None) -> html.Div:
    """Render a compact, last-three history list."""
    if not history:
        return html.Small("No checks yet.", className="text-muted")

    rows = []
    for entry in history[-3:][::-1]:
        status = "pass" if entry.get("valid") else "review"
        word_count = entry.get("word_count")
        words_text = f"{word_count}w" if word_count is not None else "n/a"
        hard_failures = entry.get("hard_failures", 0)
        rows.append(
            html.Div(
                f"{entry.get('timestamp', '--:--:--')} • {status} • "
                f"{words_text} • {hard_failures} hits"
            )
        )

    return html.Div(rows, className="text-muted")
