"""Callbacks for Ollama generation and response application.

This module contains the callbacks that:
- generate descriptions via /api/chat
- apply generated text to room descriptions
- provide clipboard and prompt population helpers
"""

import random
from datetime import UTC, datetime

import httpx
from dash import Input, Output, State, callback, html, no_update

from pipeworks_mud_mapper.services.ollama_config import (
    DEFAULT_NUM_CTX,
    DEFAULT_NUM_PREDICT,
    DEFAULT_SEED,
    DEFAULT_TARGET_WORDS,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_K,
    DEFAULT_TOP_P,
    OLLAMA_TIMEOUT_SECONDS,
)
from pipeworks_mud_mapper.services.ollama_ui import (
    status_error,
    status_info,
    status_ok,
    status_warning,
)


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

    Metadata Output
    ---------------
    On successful generation, this callback outputs metadata to the
    ``ollama-last-generation-info`` store. This metadata is a dict matching
    the ``OllamaGenerationInfo`` model fields.
    """
    # Guard: Don't process if button wasn't actually clicked
    if not n_clicks:
        return no_update, no_update, no_update

    # =========================================================================
    # Input Validation
    # =========================================================================
    # Validate all required inputs before making the API call. When validation
    # fails, return None for metadata since no generation occurred.

    if not server_url:
        return "", status_warning("Please enter a server URL"), None

    if not model:
        return "", status_warning("Please select a model"), None

    if not user_prompt:
        return "", status_warning("Please enter a user prompt"), None

    # =========================================================================
    # Apply Default Values for Parameters
    # =========================================================================
    # Use defaults if values are None (can happen if inputs weren't rendered yet).

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
    # This avoids poisoning the global random state used elsewhere in the app.

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
    messages = []
    if system_prompt:
        # System prompt is sent as a separate message with role "system".
        messages.append({"role": "system", "content": system_prompt})
    # User prompt describes what room description the author wants.
    messages.append({"role": "user", "content": user_prompt})

    # =========================================================================
    # Make API Request
    # =========================================================================

    try:
        with httpx.Client(timeout=OLLAMA_TIMEOUT_SECONDS) as client:
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
        # nested under data["message"]["content"].
        generated_text = data.get("message", {}).get("content", "").strip()

        if not generated_text:
            return "", status_warning("Empty response from model"), None

        # Show success status with seed info for reproducibility
        if seed == -1:
            seed_info = f"(random seed: {actual_seed})"
        else:
            seed_info = f"(seed: {actual_seed})"

        status = status_ok(f"Generated successfully {seed_info}")

        # =====================================================================
        # Build Generation Metadata
        # =====================================================================
        # Create a dict matching OllamaGenerationInfo fields. This metadata will
        # be stored in the dcc.Store and can later be attached to the room when
        # "Send to Description" is clicked.
        generation_info = {
            # Model identification
            "model": model,
            # The seed that was actually used (critical for reproducibility).
            "actual_seed": actual_seed,
            # Template used, or "__custom__" if none/manual editing.
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
        return "", status_error("Cannot connect to server"), None
    except httpx.TimeoutException:
        # Request timed out - return None for metadata
        return "", status_error("Request timed out"), None
    except httpx.HTTPStatusError as e:
        # Server returned an error - return None for metadata
        return "", status_error(f"Server error: {e.response.status_code}"), None
    except Exception as e:
        # Unexpected error - return None for metadata
        return "", status_error(f"Error: {str(e)[:50]}"), None


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
    it is stored in the room's ``llm_generation`` field for provenance.
    """
    if not n_clicks:
        return no_update, no_update, no_update, no_update

    if not response_text:
        return no_update, no_update, no_update, status_info("Nothing to send", muted=True)

    # If no room is selected, just update the form field.
    # Note: We can't store metadata without a room to attach it to.
    if not selected_room or not zone_data:
        status = status_info("Sent to form (select a room to apply)")
        return response_text, no_update, no_update, status

    # Update zone data directly
    rooms = zone_data.get("rooms", {})
    if selected_room not in rooms:
        return (
            response_text,
            no_update,
            no_update,
            status_warning("Room not found in zone"),
        )

    # Create updated zone data (copies for Dash reactivity).
    updated_zone = dict(zone_data)
    updated_zone["rooms"] = dict(zone_data.get("rooms", {}))
    updated_room = dict(rooms[selected_room])

    # Update the room description with the generated text
    updated_room["description"] = response_text.strip()

    # =========================================================================
    # Store LLM Generation Metadata
    # =========================================================================
    if generation_info:
        # Attach the generation metadata to the room.
        updated_room["llm_generation"] = generation_info
        print(
            f"[DEBUG] send_to_description: attached llm_generation metadata "
            f"(model={generation_info.get('model')}, seed={generation_info.get('actual_seed')})"
        )
    else:
        # No metadata available - clear any existing metadata.
        updated_room.pop("llm_generation", None)
        print(
            "[DEBUG] send_to_description: no generation metadata available, cleared llm_generation"
        )

    # Attach validator output for authoring visibility.
    if validation_info:
        updated_room["description_validation"] = validation_info
    else:
        updated_room.pop("description_validation", None)

    updated_zone["rooms"][selected_room] = updated_room

    status = status_ok(f"Applied to '{selected_room}'")
    print(f"[DEBUG] send_to_description: setting has_unsaved=True for room '{selected_room}'")
    return response_text, updated_zone, True, status


@callback(
    Output("ollama-clipboard-feedback", "children"),
    Input("ollama-clipboard", "n_clicks"),
    State("ollama-response", "value"),
    prevent_initial_call=True,
)
def handle_clipboard_copy(n_clicks: int, response_text: str):
    """Show feedback when clipboard copy happens."""
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
    """Populate the user prompt with the current room description."""
    if not n_clicks:
        return no_update, no_update

    if not room_description:
        return no_update, status_info("No description to use", muted=True)

    # Build a prompt that asks to improve/rewrite the existing description
    if room_name:
        prompt = f"Rewrite this description for a room called '{room_name}':\n\n{room_description}"
    else:
        prompt = f"Rewrite this room description:\n\n{room_description}"

    status = status_ok("Description copied to prompt")
    return prompt, status


@callback(
    Output("ollama-status", "children", allow_duplicate=True),
    Input("ollama-copy-system-prompt-btn", "n_clicks"),
    State("ollama-system-prompt", "value"),
    prevent_initial_call=True,
)
def copy_system_prompt(n_clicks: int, system_prompt: str) -> html.Span:
    """Copy the system prompt to clipboard and show feedback."""
    if not n_clicks:
        return no_update

    if not system_prompt:
        return status_info("No system prompt to copy", muted=True)

    return status_ok("System prompt copied!")
