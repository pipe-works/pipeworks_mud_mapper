"""Callbacks for Ollama generation and response application.

This module contains the callbacks that:
- generate descriptions via /api/chat
- apply generated text to room descriptions
- provide clipboard and prompt population helpers
"""

import random
import time
from typing import Any

import httpx
from dash import Input, Output, State, callback, html, no_update

from pipeworks_mud_mapper.services import ollama_client
from pipeworks_mud_mapper.services.ollama_config import (
    DEFAULT_NUM_CTX,
    DEFAULT_NUM_PREDICT,
    DEFAULT_SEED,
    DEFAULT_TARGET_WORDS,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_K,
    DEFAULT_TOP_P,
)
from pipeworks_mud_mapper.services.ollama_state import build_generation_metadata
from pipeworks_mud_mapper.services.ollama_ui import (
    status_error,
    status_info,
    status_ok,
    status_warning,
)
from pipeworks_mud_mapper.services.state import ZoneAction, apply_zone_action


def _ollama_status_payload(content: Any) -> dict[str, Any]:
    """Build a timestamped status payload for the status renderer."""
    return {"content": content, "ts": time.monotonic()}


@callback(
    Output("ollama-response", "value"),
    Output("ollama-status-generation", "data"),
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
        # We intentionally avoid writing to the shared status output here;
        # generation feedback is handled by the status renderer callback.
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
        return "", _ollama_status_payload(status_warning("Please enter a server URL")), None

    if not model:
        return "", _ollama_status_payload(status_warning("Please select a model")), None

    if not user_prompt:
        return "", _ollama_status_payload(status_warning("Please enter a user prompt")), None

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
        # Delegate the HTTP call to the Ollama client for consistency.
        data = ollama_client.chat(
            server_url=server_url,
            model=model,
            messages=messages,
            options={
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
        )

        # Extract response from chat format - the assistant's response is
        # nested under data["message"]["content"].
        generated_text = data.get("message", {}).get("content", "").strip()

        if not generated_text:
            return "", _ollama_status_payload(status_warning("Empty response from model")), None

        # Show success status with seed info for reproducibility
        if seed == -1:
            seed_info = f"(random seed: {actual_seed})"
        else:
            seed_info = f"(seed: {actual_seed})"

        status = status_ok(f"Generated successfully {seed_info}")

        # =====================================================================
        # Build Generation Metadata
        # =====================================================================
        # Delegate to the state helper to keep callbacks thin and testable.
        generation_info = build_generation_metadata(
            model=model,
            actual_seed=actual_seed,
            template_id=template_id,
            temperature=float(temperature),
            top_k=int(top_k),
            top_p=float(top_p),
            num_ctx=int(num_ctx),
            num_predict=int(num_predict),
            target_words=int(target_words),
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        return generated_text, _ollama_status_payload(status), generation_info

    except httpx.ConnectError:
        # Server not reachable - return None for metadata since no generation occurred
        return "", _ollama_status_payload(status_error("Cannot connect to server")), None
    except httpx.TimeoutException:
        # Request timed out - return None for metadata
        return "", _ollama_status_payload(status_error("Request timed out")), None
    except httpx.HTTPStatusError as e:
        # Server returned an error - return None for metadata
        return (
            "",
            _ollama_status_payload(status_error(f"Server error: {e.response.status_code}")),
            None,
        )
    except Exception as e:
        # Unexpected error - return None for metadata
        return "", _ollama_status_payload(status_error(f"Error: {str(e)[:50]}")), None


@callback(
    Output("room-description", "value", allow_duplicate=True),
    Output("current-zone-data", "data", allow_duplicate=True),
    Output("has-unsaved-changes", "data", allow_duplicate=True),
    Output("ollama-status-send", "data"),
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
        return (
            no_update,
            no_update,
            no_update,
            _ollama_status_payload(status_info("Nothing to send", muted=True)),
        )

    # If no room is selected, just update the form field.
    # Note: We can't store metadata without a room to attach it to.
    if not selected_room or not zone_data:
        status = status_info("Sent to form (select a room to apply)")
        return response_text, no_update, no_update, _ollama_status_payload(status)

    action = ZoneAction(
        type="APPLY_GENERATION",
        payload={
            "selected_room": selected_room,
            "response_text": response_text,
            "generation_info": generation_info,
            "validation_info": validation_info,
        },
    )
    transition = apply_zone_action(zone_data, action)

    if not transition.changed or transition.zone_data is None:
        return (
            response_text,
            no_update,
            no_update,
            _ollama_status_payload(status_warning("Room not found in zone")),
        )

    # Emit debug logging for traceability.
    if generation_info:
        print(
            f"[DEBUG] send_to_description: attached llm_generation metadata "
            f"(model={generation_info.get('model')}, seed={generation_info.get('actual_seed')})"
        )
    else:
        print(
            "[DEBUG] send_to_description: no generation metadata available, cleared llm_generation"
        )

    status = status_ok(f"Applied to '{selected_room}'")
    print(f"[DEBUG] send_to_description: setting has_unsaved=True for room '{selected_room}'")
    return response_text, transition.zone_data, True, _ollama_status_payload(status)


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
    Output("ollama-status-prompt", "data"),
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
        return no_update, _ollama_status_payload(status_info("No description to use", muted=True))

    # Build a prompt that asks to improve/rewrite the existing description
    if room_name:
        prompt = f"Rewrite this description for a room called '{room_name}':\n\n{room_description}"
    else:
        prompt = f"Rewrite this room description:\n\n{room_description}"

    status = status_ok("Description copied to prompt")
    return prompt, _ollama_status_payload(status)


@callback(
    Output("ollama-status-system", "data"),
    Input("ollama-copy-system-prompt-btn", "n_clicks"),
    State("ollama-system-prompt", "value"),
    prevent_initial_call=True,
)
def copy_system_prompt(n_clicks: int, system_prompt: str) -> html.Span:
    """Copy the system prompt to clipboard and show feedback."""
    if not n_clicks:
        return no_update

    if not system_prompt:
        return _ollama_status_payload(status_info("No system prompt to copy", muted=True))

    return _ollama_status_payload(status_ok("System prompt copied!"))


def _latest_status_payload(payloads: list[dict | None]) -> dict | None:
    """Return the most recent status payload from a list."""
    latest: dict | None = None
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        timestamp = payload.get("ts")
        if timestamp is None:
            continue
        if latest is None or timestamp > latest.get("ts", -1):
            latest = payload
    return latest


@callback(
    Output("ollama-status", "children"),
    Input("ollama-status-generation", "data"),
    Input("ollama-status-send", "data"),
    Input("ollama-status-prompt", "data"),
    Input("ollama-status-system", "data"),
    Input("ollama-status-template", "data"),
)
def render_ollama_status(*payloads: dict | None) -> Any:
    """Render the latest Ollama status payload from any source."""
    latest = _latest_status_payload(list(payloads))
    if not latest:
        return no_update

    content = latest.get("content")
    if content is None:
        return no_update

    return content
