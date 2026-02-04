"""Centralized Ollama configuration constants.

This module holds the default values and shared settings for the
Ollama integration. These values used to live in the UI layer
(`layout/ollama_panel.py`), but they are domain defaults rather
than UI concerns. Keeping them here avoids UI→service coupling.
"""

# =============================================================================
# Default Parameter Values
# =============================================================================
# These constants define default values for model parameters. They are used by
# both the UI (as initial input values) and callbacks (as fallbacks when inputs
# are None). Keeping them centralized ensures consistent behavior.

#: Default seed value (-1 means random seed each generation)
DEFAULT_SEED = -1

#: Default temperature for text generation (0.7 is a balanced creative setting)
DEFAULT_TEMPERATURE = 0.7

#: Default top_k value (40 provides good vocabulary diversity)
DEFAULT_TOP_K = 40

#: Default top_p value (0.9 uses nucleus sampling with 90% probability mass)
DEFAULT_TOP_P = 0.9

#: Default context window size in tokens (4096 is common for many models)
DEFAULT_NUM_CTX = 4096

#: Default max tokens to generate (512 is good for room descriptions)
DEFAULT_NUM_PREDICT = 512

#: Default target word count for generated descriptions
DEFAULT_TARGET_WORDS = 300

# =============================================================================
# Networking Defaults
# =============================================================================
# This timeout applies to network calls to the local Ollama server. The timeout
# is intentionally generous to accommodate slower hardware (e.g., Raspberry Pi).

OLLAMA_TIMEOUT_SECONDS = 60.0

# Model list refresh is a lighter call than generation; keep it shorter to
# surface connectivity errors quickly.
OLLAMA_MODEL_REFRESH_TIMEOUT_SECONDS = 10.0
