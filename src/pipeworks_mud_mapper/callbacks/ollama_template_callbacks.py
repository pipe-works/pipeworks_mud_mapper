"""Callbacks for Ollama template, prompt, and control UI.

This module handles template dropdown population, system prompt compilation,
prompt prefix presets, collapse toggles, and seed control logic.
"""

import time
from typing import Any

from dash import Input, Output, State, callback, ctx, no_update

from pipeworks_mud_mapper.services import template_service
from pipeworks_mud_mapper.services.ollama_assets import (
    load_parameter_presets,
    load_prompt_prefixes,
)
from pipeworks_mud_mapper.services.ollama_config import DEFAULT_TARGET_WORDS
from pipeworks_mud_mapper.services.ollama_ui import status_ok, status_warning


def _ollama_status_payload(content: Any) -> dict[str, Any]:
    """Build a timestamped status payload for the status renderer."""
    return {"content": content, "ts": time.monotonic()}


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

    Called on app startup and when the refresh button is clicked. Templates
    are loaded from ``data/ollama/templates/``.
    """
    # Get templates from service
    templates = template_service.list_templates()

    return templates


@callback(
    Output("ollama-prompt-prefix-dropdown", "options"),
    Input("ollama-refresh-models-btn", "n_clicks"),
    prevent_initial_call=False,
)
def load_prompt_prefix_options(n_clicks: int) -> list[dict]:
    """Load prompt prefix presets from JSON config.

    We reload on refresh to allow authors to edit the JSON and refresh
    without restarting the app.
    """
    prefix_data = load_prompt_prefixes(reload=True)

    options = [
        {"label": item.get("label", item.get("value")), "value": item.get("value")}
        for item in prefix_data
        if isinstance(item, dict)
    ]
    return options


@callback(
    Output("ollama-params-preset-dropdown", "options"),
    Input("ollama-refresh-models-btn", "n_clicks"),
    prevent_initial_call=False,
)
def load_param_preset_options(n_clicks: int) -> list[dict]:
    """Load parameter presets from JSON files."""
    # Reload so authors can drop a new preset file in the directory
    # and immediately see it after hitting refresh.
    preset_data = load_parameter_presets(reload=True)
    return [
        {"label": item.get("label", item.get("value")), "value": item.get("value")}
        for item in preset_data
        if isinstance(item, dict)
    ]


@callback(
    Output("ollama-target-words", "value"),
    Output("ollama-temperature", "value"),
    Output("ollama-top-p", "value"),
    Output("ollama-top-k", "value"),
    Output("ollama-num-predict", "value"),
    Input("ollama-params-preset-apply", "n_clicks"),
    State("ollama-params-preset-dropdown", "value"),
    State("ollama-target-words", "value"),
    State("ollama-temperature", "value"),
    State("ollama-top-p", "value"),
    State("ollama-top-k", "value"),
    State("ollama-num-predict", "value"),
    prevent_initial_call=True,
)
def apply_param_preset(
    n_clicks: int,
    preset_id: str | None,
    target_words: int | None,
    temperature: float | None,
    top_p: float | None,
    top_k: int | None,
    num_predict: int | None,
) -> tuple:
    """Apply a parameter preset to the tuning controls."""
    if not n_clicks or not preset_id:
        return no_update, no_update, no_update, no_update, no_update

    # Reload on apply to avoid stale files during iterative authoring.
    preset_data = load_parameter_presets(reload=True)
    preset = next(
        (item for item in preset_data if isinstance(item, dict) and item.get("value") == preset_id),
        None,
    )
    if not preset:
        return no_update, no_update, no_update, no_update, no_update

    return (
        # Each field falls back to the current value if the preset omits it,
        # keeping presets lightweight and allowing partial overrides.
        int(preset.get("target_words", target_words or DEFAULT_TARGET_WORDS)),
        float(preset.get("temperature", temperature if temperature is not None else 0.7)),
        float(preset.get("top_p", top_p if top_p is not None else 0.9)),
        int(preset.get("top_k", top_k if top_k is not None else 40)),
        int(preset.get("num_predict", num_predict if num_predict is not None else 140)),
    )


@callback(
    Output("ollama-user-prompt", "value", allow_duplicate=True),
    Input("ollama-prompt-prefix-dropdown", "value"),
    State("ollama-user-prompt", "value"),
    prevent_initial_call=True,
)
def apply_prompt_prefix(prefix_id: str | None, current_prompt: str | None) -> Any:
    """Prepend a selected prompt prefix to the user prompt."""
    if not prefix_id:
        return no_update

    # Reload to avoid stale data if the file was edited during runtime.
    prefix_data = load_prompt_prefixes(reload=True)

    prefix = None
    for item in prefix_data:
        if isinstance(item, dict) and item.get("value") == prefix_id:
            prefix = item.get("prefix")
            break

    if not prefix:
        return no_update

    current_prompt = current_prompt or ""
    if current_prompt.strip().startswith(prefix):
        return current_prompt

    if current_prompt.strip():
        return f"{prefix}\n{current_prompt.strip()}"
    return prefix


@callback(
    Output("ollama-system-prompt", "value"),
    Output("ollama-system-prompt", "readOnly"),
    Output("ollama-system-prompt-collapse", "is_open"),
    Output("ollama-system-prompt-chevron", "className"),
    Output("ollama-status-template", "data"),
    Input("ollama-template-dropdown", "value"),
    Input("ollama-target-words", "value"),
    prevent_initial_call=True,
)
def handle_template_selection(template_id: str | None, target_words: int | None) -> tuple:
    """Handle template selection and target word count changes.

    When a template is selected or target words change, compiles the
    template into a system prompt with the specified word count guidance
    and updates the display. The system prompt remains read-only.
    """
    # Apply default if target_words is None
    if target_words is None:
        target_words = DEFAULT_TARGET_WORDS

    # No selection made - don't update anything
    if not template_id:
        return no_update, no_update, no_update, no_update, no_update

    # Load the selected template from data/ollama/templates/
    template = template_service.load_template(template_id)
    if not template:
        status = status_warning(f"Template '{template_id}' not found")
        # Don't update the prompt on error - keep whatever was there
        return no_update, no_update, no_update, no_update, _ollama_status_payload(status)

    # Compile the template JSON into a comprehensive system prompt string
    system_prompt = template_service.compile_system_prompt(template, target_words=target_words)

    status = status_ok(f"Loaded: {template.template_name} v{template.version}")
    # Return: compiled prompt, read-only (not editable), collapse CLOSED by default,
    # chevron right (closed state), status
    return (
        system_prompt,
        True,
        False,
        "bi bi-chevron-right me-1",
        _ollama_status_payload(status),
    )


@callback(
    Output("ollama-target-words-hint", "children"),
    Input("ollama-target-words", "value"),
)
def update_target_words_hint(target_words: int | None) -> str:
    """Update helper text to show the effective word target behavior."""
    if not target_words:
        return "25-500: Guides LLM output length"

    if target_words <= 40:
        return f"Exact length: {target_words} words"

    words_low = int(target_words * 0.67)
    words_high = int(target_words * 1.17)
    return f"Range: {words_low}-{words_high} (aim ~{target_words})"


# =============================================================================
# UI Toggle and Seed Control Callbacks
# =============================================================================


@callback(
    Output("ollama-system-prompt-collapse", "is_open", allow_duplicate=True),
    Output("ollama-system-prompt-chevron", "className", allow_duplicate=True),
    Input("ollama-system-prompt-toggle", "n_clicks"),
    State("ollama-system-prompt-collapse", "is_open"),
    prevent_initial_call=True,
)
def toggle_system_prompt_collapse(n_clicks: int, is_open: bool) -> tuple:
    """Toggle the system prompt collapse open/closed."""
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
    """Toggle the parameters section collapse open/closed."""
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
    """Handle seed control interactions (buttons and checkbox)."""
    # Determine which input triggered the callback
    triggered_id = ctx.triggered_id

    # Handle random checkbox changes
    if triggered_id == "ollama-seed-random-check":
        if random_checked:
            # Random mode enabled: set seed to -1
            return -1, True
        # Random mode disabled: set seed to 0 (or keep current if valid)
        if current_seed == -1:
            return 0, False
        return current_seed, False

    # Handle +/- button clicks (only when not in random mode)
    if current_seed == -1:
        # In random mode, buttons don't change the seed
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
