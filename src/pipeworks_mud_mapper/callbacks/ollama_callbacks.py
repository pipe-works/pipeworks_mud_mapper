"""Ollama callback aggregation module.

This file exists to preserve the historical import path
`pipeworks_mud_mapper.callbacks.ollama_callbacks` while delegating
actual callback definitions to smaller modules. Importing this module
registers all Ollama-related callbacks via the decorators in the
submodules and exposes the functions for tests.
"""

# Re-export callback functions for tests and external imports.
# Each submodule contains the actual @callback-decorated functions.
from pipeworks_mud_mapper.callbacks.ollama_generation_callbacks import (  # noqa: F401
    copy_system_prompt,
    generate_description,
    handle_clipboard_copy,
    populate_prompt_from_description,
    render_ollama_status,
    send_to_description,
)
from pipeworks_mud_mapper.callbacks.ollama_models_callbacks import (  # noqa: F401
    refresh_ollama_models,
)
from pipeworks_mud_mapper.callbacks.ollama_template_callbacks import (  # noqa: F401
    apply_param_preset,
    apply_prompt_prefix,
    handle_seed_controls,
    handle_template_selection,
    load_param_preset_options,
    load_prompt_prefix_options,
    load_template_options,
    toggle_params_collapse,
    toggle_system_prompt_collapse,
    update_target_words_hint,
)
from pipeworks_mud_mapper.callbacks.ollama_validation_callbacks import (  # noqa: F401
    validate_ollama_response,
)

__all__ = [
    "apply_param_preset",
    "apply_prompt_prefix",
    "copy_system_prompt",
    "generate_description",
    "handle_clipboard_copy",
    "handle_seed_controls",
    "handle_template_selection",
    "load_param_preset_options",
    "load_prompt_prefix_options",
    "load_template_options",
    "populate_prompt_from_description",
    "refresh_ollama_models",
    "render_ollama_status",
    "send_to_description",
    "toggle_params_collapse",
    "toggle_system_prompt_collapse",
    "update_target_words_hint",
    "validate_ollama_response",
]
