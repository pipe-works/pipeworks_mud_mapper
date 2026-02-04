"""Ollama LLM Assistant panel component.

The Ollama panel provides an interface for generating room descriptions
using local LLM models via Ollama. It includes template selection for
pre-configured system prompts, model management, seed control for
reproducible generation, and configurable model parameters.

Component Structure
-------------------
::

    ┌────────────────────────────────────────────────────────────────────┐
    │ 🤖 LLM Assistant (Ollama)                                          │
    ├────────────────────────────────────────────────────────────────────┤
    │ Server: [http://...] [↻]  Model: [dropdown]  Template: [dropdown]  │
    │ ○ Connected                                                        │
    │                                                                    │
    │ ▶ System Prompt              ▶ Parameters                          │
    │                                                                    │
    │ User Prompt: [Preset ▾]                         [Use Description]  │
    │ [________________________]                                         │
    │                                                                    │
    │ [Generate ✨]                                                       │
    │                                                                    │
    │ Response:                                                          │
    │ [________________________]                                         │
    │ [Send to Description] [Copy]                                       │
    └────────────────────────────────────────────────────────────────────┘

Component IDs
-------------
**Server and Model Selection:**

- ``ollama-server-url``: Input for Ollama server URL
- ``ollama-model-dropdown``: Dropdown to select Ollama model
- ``ollama-refresh-models-btn``: Button to refresh model list
- ``ollama-refresh-icon``: Icon inside refresh button (for spinning animation)
- ``ollama-connection-status``: Connection status indicator
- ``ollama-template-dropdown``: Dropdown to select prompt template

**System Prompt Section (collapsible, hidden by default):**

- ``ollama-system-prompt-toggle``: Button to toggle system prompt visibility
- ``ollama-system-prompt-chevron``: Chevron icon for collapse state
- ``ollama-system-prompt-collapse``: Collapsible wrapper for system prompt
- ``ollama-system-prompt``: Textarea for system prompt (read-only when template selected)
- ``ollama-copy-system-prompt-btn``: Clipboard component to copy system prompt

**Parameters Section (collapsible, hidden by default):**

- ``ollama-params-toggle``: Button to toggle parameters visibility
- ``ollama-params-chevron``: Chevron icon for params collapse state
- ``ollama-params-collapse``: Collapsible wrapper for parameters

**Seed Controls:**

- ``ollama-seed-value``: Input for seed value (-1 for random, 0+ for fixed)
- ``ollama-seed-decrease``: Button to decrement seed
- ``ollama-seed-increase``: Button to increment seed
- ``ollama-seed-random-check``: Checkbox for random mode (sets seed to -1)

**Model Parameters:**

- ``ollama-temperature``: Input for temperature (creativity/randomness, 0.0-2.0)
- ``ollama-top-k``: Input for top_k (vocabulary filtering, 1-100)
- ``ollama-top-p``: Input for top_p (nucleus sampling threshold, 0.0-1.0)
- ``ollama-num-ctx``: Input for num_ctx (context window in tokens, 512-8192)
- ``ollama-num-predict``: Input for num_predict (max output tokens, 30-2048)

**User Prompt and Generation:**

- ``ollama-user-prompt``: Textarea for user prompt
- ``ollama-populate-prompt-btn``: Button to populate prompt from room description
- ``ollama-generate-btn``: Button to generate description
- ``ollama-generate-icon``: Icon inside generate button (for loading state)
- ``ollama-generate-text``: Text inside generate button (changes during generation)

**Response and Actions:**

- ``ollama-response``: Textarea for LLM response
- ``ollama-send-to-description-btn``: Button to send response to room description
- ``ollama-clipboard``: Clipboard component for copying response
- ``ollama-clipboard-feedback``: Clipboard copy feedback message
- ``ollama-status``: Status message area

Parameter Defaults
------------------
The following default values are used for model parameters:

+---------------+---------+-----------+----------------------------------------------+
| Parameter     | Default | Range     | Purpose                                      |
+===============+=========+===========+==============================================+
| seed          | -1      | -1 or 0+  | -1 = random seed, 0+ = reproducible          |
+---------------+---------+-----------+----------------------------------------------+
| temperature   | 0.7     | 0.0-2.0   | Controls creativity/randomness of output     |
+---------------+---------+-----------+----------------------------------------------+
| top_k         | 40      | 1-100     | Limits vocabulary to top K probable tokens   |
+---------------+---------+-----------+----------------------------------------------+
| top_p         | 0.9     | 0.0-1.0   | Nucleus sampling threshold (cumulative prob) |
+---------------+---------+-----------+----------------------------------------------+
| num_ctx       | 4096    | 512-8192  | Context window size in tokens                |
+---------------+---------+-----------+----------------------------------------------+
| num_predict   | 512     | 30-2048   | Maximum number of tokens to generate         |
+---------------+---------+-----------+----------------------------------------------+

See Also
--------
- ``callbacks/ollama_callbacks.py``: Callbacks for Ollama LLM integration
- ``services/template_service.py``: Template loading and compilation
- ``models/template.py``: Pydantic models for template validation
"""

# ruff: noqa: E501

import dash_bootstrap_components as dbc
from dash import dcc, html

# Defaults are defined in a service module so UI and callbacks share a single
# source of truth without coupling business logic to layout code.
from pipeworks_mud_mapper.services.ollama_config import (
    DEFAULT_NUM_CTX,
    DEFAULT_NUM_PREDICT,
    DEFAULT_SEED,
    DEFAULT_TARGET_WORDS,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_K,
    DEFAULT_TOP_P,
)

# =============================================================================
# Default Parameter Values
# =============================================================================
# Defaults are imported above from the shared service module.


def create_ollama_panel() -> dbc.Card:
    """Create the Ollama LLM Assistant panel component.

    The Ollama panel provides:

    - Server connection management (URL input, refresh button, status indicator)
    - Model selection dropdown (populated from connected Ollama server)
    - Template selection for pre-configured system prompts
    - Collapsible system prompt viewer (read-only when using templates)
    - Collapsible parameters section with seed control and model parameters
    - User prompt input with "Use Description" button
    - Generate button with loading state feedback
    - Response display with copy and send-to-description actions

    Returns
    -------
    dbc.Card
        Bootstrap Card containing the complete Ollama LLM interface.

    Notes
    -----
    - System prompt and parameters sections are hidden by default for a cleaner UI
    - System prompt is read-only when a template is selected (enforces template integrity)
    - "Custom" template option enables manual system prompt editing
    - Templates are loaded from data/ollama/templates/ directory
    - Uses /api/chat endpoint for proper system/user message separation
    - Seed of -1 means random (uses isolated RNG to avoid poisoning global state)
    - Callback changes button state during generation for user feedback

    Examples
    --------
    The Ollama panel is typically used within the main layout::

        >>> from pipeworks_mud_mapper.layout.ollama_panel import create_ollama_panel
        >>> panel = create_ollama_panel()
        >>> # Panel contains all ollama-* component IDs
    """
    return dbc.Card(
        [
            # =================================================================
            # Card Header with LLM Assistant title
            # =================================================================
            dbc.CardHeader(
                [
                    html.I(className="bi bi-robot me-2"),
                    html.Strong("LLM Assistant"),
                    html.Small(" (Ollama)", className="text-muted"),
                ],
            ),
            dbc.CardBody(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    # ---------------------------------------------------------
                                    # Server, Model, and Template Row (Compact 3-Column Layout)
                                    # ---------------------------------------------------------
                                    # All three controls on one row for a more compact display.
                                    # Server URL takes 5 columns, Model and Template take 3.5 each.
                                    dbc.Row(
                                        [
                                            # Server URL column (with refresh button in input group)
                                            dbc.Col(
                                                [
                                                    dbc.Label(
                                                        "Server",
                                                        html_for="ollama-server-url",
                                                        size="sm",
                                                    ),
                                                    dbc.InputGroup(
                                                        [
                                                            dbc.Input(
                                                                id="ollama-server-url",
                                                                type="text",
                                                                value="http://localhost:11434",
                                                                placeholder="http://localhost:11434",
                                                                size="sm",
                                                            ),
                                                            dbc.Button(
                                                                [
                                                                    html.I(
                                                                        className="bi bi-arrow-clockwise",
                                                                        id="ollama-refresh-icon",
                                                                    ),
                                                                ],
                                                                id="ollama-refresh-models-btn",
                                                                color="secondary",
                                                                outline=True,
                                                                size="sm",
                                                                title="Connect and refresh models",
                                                            ),
                                                        ],
                                                        size="sm",
                                                    ),
                                                ],
                                                width=5,
                                            ),
                                            # Model dropdown column
                                            dbc.Col(
                                                [
                                                    dbc.Label(
                                                        "Model",
                                                        html_for="ollama-model-dropdown",
                                                        size="sm",
                                                    ),
                                                    dcc.Loading(
                                                        id="ollama-model-loading",
                                                        type="dot",
                                                        color="#17a2b8",
                                                        children=dcc.Dropdown(
                                                            id="ollama-model-dropdown",
                                                            options=[],
                                                            placeholder="Connect first",
                                                            style={"fontSize": "0.8rem"},
                                                        ),
                                                    ),
                                                ],
                                                width=4,
                                            ),
                                            # Template dropdown column
                                            dbc.Col(
                                                [
                                                    dbc.Label(
                                                        "Template",
                                                        html_for="ollama-template-dropdown",
                                                        size="sm",
                                                    ),
                                                    dcc.Dropdown(
                                                        id="ollama-template-dropdown",
                                                        options=[],  # Populated by callback on load
                                                        placeholder="Select...",
                                                        style={"fontSize": "0.8rem"},
                                                    ),
                                                ],
                                                width=3,
                                            ),
                                        ],
                                        className="mb-2",
                                    ),
                                    # ---------------------------------------------------------
                                    # Connection Status Indicator
                                    # ---------------------------------------------------------
                                    # Shows current connection state (connected/not connected)
                                    # with appropriate icon color and text.
                                    html.Div(
                                        id="ollama-connection-status",
                                        children=html.Small(
                                            [
                                                html.I(className="bi bi-circle text-muted me-1"),
                                                "Not connected",
                                            ],
                                            className="text-muted",
                                        ),
                                        className="mb-2",
                                    ),
                                    # ---------------------------------------------------------
                                    # Collapsible Section Toggles Row
                                    # ---------------------------------------------------------
                                    # Two buttons side by side to toggle System Prompt and
                                    # Parameters sections. Both are hidden by default.
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                dbc.Button(
                                                    [
                                                        html.I(
                                                            className="bi bi-chevron-right me-1",
                                                            id="ollama-system-prompt-chevron",
                                                        ),
                                                        "System Prompt",
                                                    ],
                                                    id="ollama-system-prompt-toggle",
                                                    color="link",
                                                    size="sm",
                                                    className="p-0 text-muted",
                                                ),
                                                width=6,
                                            ),
                                            dbc.Col(
                                                dbc.Button(
                                                    [
                                                        html.I(
                                                            className="bi bi-chevron-right me-1",
                                                            id="ollama-params-chevron",
                                                        ),
                                                        "Parameters",
                                                    ],
                                                    id="ollama-params-toggle",
                                                    color="link",
                                                    size="sm",
                                                    className="p-0 text-muted",
                                                ),
                                                width=6,
                                            ),
                                        ],
                                        className="mb-2",
                                    ),
                                    # ---------------------------------------------------------
                                    # Collapsible System Prompt Section
                                    # ---------------------------------------------------------
                                    # Contains the full system prompt (read-only when using
                                    # a template) and a copy button for easy extraction.
                                    # Hidden by default (is_open=False).
                                    dbc.Collapse(
                                        [
                                            dbc.Textarea(
                                                id="ollama-system-prompt",
                                                value=(
                                                    "You are a creative writer for a MUD (text-based adventure "
                                                    "game). Write atmospheric, evocative room descriptions. "
                                                    "Keep descriptions concise (2-3 sentences). Focus on "
                                                    "sensory details and mood."
                                                ),
                                                className="mb-1",
                                                style={
                                                    "height": "150px",
                                                    "fontSize": "0.75rem",
                                                    "fontFamily": "monospace",
                                                },
                                            ),
                                            dcc.Clipboard(
                                                id="ollama-copy-system-prompt-btn",
                                                target_id="ollama-system-prompt",
                                                title="Copy system prompt to clipboard",
                                                className="btn btn-outline-secondary btn-sm mb-2",
                                                content="Copy System Prompt",
                                            ),
                                        ],
                                        id="ollama-system-prompt-collapse",
                                        is_open=False,
                                    ),
                                    # ---------------------------------------------------------
                                    # Collapsible Parameters Section
                                    # ---------------------------------------------------------
                                    # Contains seed controls and model parameters. Hidden by
                                    # default (is_open=False) for a cleaner interface.
                                    dbc.Collapse(
                                        [
                                            dbc.Card(
                                                dbc.CardBody(
                                                    [
                                                        # =============================================
                                                        # Seed Controls Row
                                                        # =============================================
                                                        # Seed determines reproducibility. -1 means
                                                        # random (different output each time), while
                                                        # a fixed seed produces the same output.
                                                        dbc.Row(
                                                            [
                                                                dbc.Col(
                                                                    [
                                                                        dbc.Label(
                                                                            [
                                                                                "Seed ",
                                                                                html.Small(
                                                                                    "(reproducibility)",
                                                                                    className="text-muted",
                                                                                ),
                                                                            ],
                                                                            html_for="ollama-seed-value",
                                                                            size="sm",
                                                                        ),
                                                                        dbc.InputGroup(
                                                                            [
                                                                                # Decrement button
                                                                                dbc.Button(
                                                                                    html.I(
                                                                                        className="bi bi-dash"
                                                                                    ),
                                                                                    id="ollama-seed-decrease",
                                                                                    color="secondary",
                                                                                    outline=True,
                                                                                    size="sm",
                                                                                    title="Decrease seed by 1",
                                                                                ),
                                                                                # Seed value input
                                                                                dbc.Input(
                                                                                    id="ollama-seed-value",
                                                                                    type="number",
                                                                                    value=DEFAULT_SEED,
                                                                                    min=-1,
                                                                                    step=1,
                                                                                    size="sm",
                                                                                    style={
                                                                                        "textAlign": "center"
                                                                                    },
                                                                                ),
                                                                                # Increment button
                                                                                dbc.Button(
                                                                                    html.I(
                                                                                        className="bi bi-plus"
                                                                                    ),
                                                                                    id="ollama-seed-increase",
                                                                                    color="secondary",
                                                                                    outline=True,
                                                                                    size="sm",
                                                                                    title="Increase seed by 1",
                                                                                ),
                                                                            ],
                                                                            size="sm",
                                                                        ),
                                                                    ],
                                                                    width=6,
                                                                ),
                                                                dbc.Col(
                                                                    [
                                                                        # Spacer to align checkbox with input
                                                                        html.Div(
                                                                            style={"height": "24px"}
                                                                        ),
                                                                        # Checked by default (seed=-1)
                                                                        dbc.Checkbox(
                                                                            id="ollama-seed-random-check",
                                                                            label="Random each time",
                                                                            value=True,
                                                                            className="small",
                                                                        ),
                                                                    ],
                                                                    width=6,
                                                                    className="d-flex align-items-end",
                                                                ),
                                                            ],
                                                            className="mb-3",
                                                        ),
                                                        # =============================================
                                                        # Model Parameters Row 1: Temperature, Top-K, Top-P
                                                        # =============================================
                                                        dbc.Row(
                                                            [
                                                                # Temperature: Controls randomness
                                                                # (0=deterministic, 2=creative)
                                                                dbc.Col(
                                                                    [
                                                                        dbc.Label(
                                                                            [
                                                                                "Temperature ",
                                                                                html.Small(
                                                                                    "(creativity)",
                                                                                    className="text-muted",
                                                                                ),
                                                                            ],
                                                                            html_for="ollama-temperature",
                                                                            size="sm",
                                                                        ),
                                                                        dbc.Input(
                                                                            id="ollama-temperature",
                                                                            type="number",
                                                                            value=DEFAULT_TEMPERATURE,
                                                                            min=0.0,
                                                                            max=2.0,
                                                                            step=0.05,
                                                                            size="sm",
                                                                        ),
                                                                        html.Small(
                                                                            "0.0-2.0: Low=focused, High=creative",
                                                                            className="text-muted",
                                                                            style={
                                                                                "fontSize": "0.65rem"
                                                                            },
                                                                        ),
                                                                    ],
                                                                    width=4,
                                                                ),
                                                                # Top-K: Limits vocabulary to top K tokens
                                                                dbc.Col(
                                                                    [
                                                                        dbc.Label(
                                                                            [
                                                                                "Top-K ",
                                                                                html.Small(
                                                                                    "(vocab filter)",
                                                                                    className="text-muted",
                                                                                ),
                                                                            ],
                                                                            html_for="ollama-top-k",
                                                                            size="sm",
                                                                        ),
                                                                        dbc.Input(
                                                                            id="ollama-top-k",
                                                                            type="number",
                                                                            value=DEFAULT_TOP_K,
                                                                            min=1,
                                                                            max=100,
                                                                            step=1,
                                                                            size="sm",
                                                                        ),
                                                                        html.Small(
                                                                            "1-100: Smaller=more focused",
                                                                            className="text-muted",
                                                                            style={
                                                                                "fontSize": "0.65rem"
                                                                            },
                                                                        ),
                                                                    ],
                                                                    width=4,
                                                                ),
                                                                # Top-P: Nucleus sampling probability threshold
                                                                dbc.Col(
                                                                    [
                                                                        dbc.Label(
                                                                            [
                                                                                "Top-P ",
                                                                                html.Small(
                                                                                    "(nucleus)",
                                                                                    className="text-muted",
                                                                                ),
                                                                            ],
                                                                            html_for="ollama-top-p",
                                                                            size="sm",
                                                                        ),
                                                                        dbc.Input(
                                                                            id="ollama-top-p",
                                                                            type="number",
                                                                            value=DEFAULT_TOP_P,
                                                                            min=0.0,
                                                                            max=1.0,
                                                                            step=0.05,
                                                                            size="sm",
                                                                        ),
                                                                        html.Small(
                                                                            "0.0-1.0: Cumulative probability",
                                                                            className="text-muted",
                                                                            style={
                                                                                "fontSize": "0.65rem"
                                                                            },
                                                                        ),
                                                                    ],
                                                                    width=4,
                                                                ),
                                                            ],
                                                            className="mb-2",
                                                        ),
                                                        # =============================================
                                                        # Model Parameters Row 2: Context, Max Tokens
                                                        # =============================================
                                                        dbc.Row(
                                                            [
                                                                # Context Window: How many tokens the model can see
                                                                dbc.Col(
                                                                    [
                                                                        dbc.Label(
                                                                            [
                                                                                "Context ",
                                                                                html.Small(
                                                                                    "(memory)",
                                                                                    className="text-muted",
                                                                                ),
                                                                            ],
                                                                            html_for="ollama-num-ctx",
                                                                            size="sm",
                                                                        ),
                                                                        dbc.Input(
                                                                            id="ollama-num-ctx",
                                                                            type="number",
                                                                            value=DEFAULT_NUM_CTX,
                                                                            min=512,
                                                                            max=8192,
                                                                            step=512,
                                                                            size="sm",
                                                                        ),
                                                                        html.Small(
                                                                            "512-8192 tokens: Larger=more context",
                                                                            className="text-muted",
                                                                            style={
                                                                                "fontSize": "0.65rem"
                                                                            },
                                                                        ),
                                                                    ],
                                                                    width=6,
                                                                ),
                                                                # Max Output Tokens: Limit on generated text length
                                                                dbc.Col(
                                                                    [
                                                                        dbc.Label(
                                                                            [
                                                                                "num_predict ",
                                                                                html.Small(
                                                                                    "(max tokens)",
                                                                                    className="text-muted",
                                                                                ),
                                                                            ],
                                                                            html_for="ollama-num-predict",
                                                                            size="sm",
                                                                        ),
                                                                        dbc.Input(
                                                                            id="ollama-num-predict",
                                                                            type="number",
                                                                            value=DEFAULT_NUM_PREDICT,
                                                                            min=30,
                                                                            max=2048,
                                                                            step=1,
                                                                            size="sm",
                                                                        ),
                                                                        html.Small(
                                                                            "30-2048: Max tokens to generate",
                                                                            className="text-muted",
                                                                            style={
                                                                                "fontSize": "0.65rem"
                                                                            },
                                                                        ),
                                                                    ],
                                                                    width=6,
                                                                ),
                                                            ],
                                                        ),
                                                        # =============================================
                                                        # Target Words Row (with explanatory note)
                                                        # =============================================
                                                        dbc.Row(
                                                            [
                                                                # Target Words: Guides LLM on desired output length
                                                                dbc.Col(
                                                                    [
                                                                        dbc.Label(
                                                                            [
                                                                                "Target Words ",
                                                                                html.Small(
                                                                                    "(for template)",
                                                                                    className="text-muted",
                                                                                ),
                                                                                dbc.Button(
                                                                                    [
                                                                                        html.I(
                                                                                            className=(
                                                                                                "bi bi-sliders "
                                                                                                "me-1"
                                                                                            )
                                                                                        ),
                                                                                        "Presets",
                                                                                    ],
                                                                                    id="ollama-params-help-btn",
                                                                                    color="link",
                                                                                    size="sm",
                                                                                    className=(
                                                                                        "p-0 align-baseline"
                                                                                    ),
                                                                                    title=(
                                                                                        "Show parameter examples"
                                                                                    ),
                                                                                ),
                                                                            ],
                                                                            html_for="ollama-target-words",
                                                                            size="sm",
                                                                        ),
                                                                        dbc.Input(
                                                                            id="ollama-target-words",
                                                                            type="number",
                                                                            value=DEFAULT_TARGET_WORDS,
                                                                            min=25,
                                                                            max=500,
                                                                            step=5,
                                                                            size="sm",
                                                                        ),
                                                                        html.Small(
                                                                            id="ollama-target-words-hint",
                                                                            className="text-muted",
                                                                            style={
                                                                                "fontSize": "0.65rem"
                                                                            },
                                                                        ),
                                                                    ],
                                                                    width=6,
                                                                ),
                                                                # Explanatory note about token/word relationship
                                                                dbc.Col(
                                                                    [
                                                                        html.Div(
                                                                            [
                                                                                html.I(
                                                                                    className=(
                                                                                        "bi bi-info-circle "
                                                                                        "text-info me-1"
                                                                                    )
                                                                                ),
                                                                                html.Strong(
                                                                                    "Tokens vs Words",
                                                                                    className="small",
                                                                                ),
                                                                            ],
                                                                            className="mb-1",
                                                                        ),
                                                                        html.Small(
                                                                            [
                                                                                "1 word ≈ 1.3-1.5 tokens. ",
                                                                                "For 300 words, set ",
                                                                                "Max Tokens to ~450+. ",
                                                                                "If too low, output is ",
                                                                                "truncated mid-sentence.",
                                                                            ],
                                                                            className="text-muted",
                                                                            style={
                                                                                "fontSize": "0.65rem",
                                                                                "lineHeight": "1.3",
                                                                            },
                                                                        ),
                                                                    ],
                                                                    width=6,
                                                                    className=(
                                                                        "d-flex flex-column "
                                                                        "justify-content-center"
                                                                    ),
                                                                ),
                                                            ],
                                                            className="mt-2",
                                                        ),
                                                        dbc.Popover(
                                                            [
                                                                dbc.PopoverHeader(
                                                                    "Short Output Baselines"
                                                                ),
                                                                dbc.PopoverBody(
                                                                    [
                                                                        html.Div(
                                                                            "Target 30 words:"
                                                                        ),
                                                                        html.Div(
                                                                            "temp=0.4, top_p=0.7, top_k=20, num_predict=70"
                                                                        ),
                                                                        html.Hr(className="my-2"),
                                                                        html.Div(
                                                                            "If truncation happens:"
                                                                        ),
                                                                        html.Div(
                                                                            "raise num_predict to 80 or reduce prompt length"
                                                                        ),
                                                                        html.Hr(className="my-2"),
                                                                        html.Div(
                                                                            "Longer output (60-80 words):"
                                                                        ),
                                                                        html.Div(
                                                                            "temp=0.7, top_p=0.9, top_k=40, num_predict=140+"
                                                                        ),
                                                                    ]
                                                                ),
                                                            ],
                                                            target="ollama-params-help-btn",
                                                            trigger="click",
                                                            placement="top",
                                                        ),
                                                    ],
                                                    className="py-2",
                                                ),
                                                className="mb-2 bg-light",
                                            ),
                                        ],
                                        id="ollama-params-collapse",
                                        is_open=False,
                                    ),
                                    # ---------------------------------------------------------
                                    # User Prompt Section
                                    # ---------------------------------------------------------
                                    # Input area for the user's prompt with a button to
                                    # automatically populate from the current room description.
                                    html.Div(
                                        [
                                            dbc.Label(
                                                "User Prompt",
                                                html_for="ollama-user-prompt",
                                                size="sm",
                                                className="me-auto",
                                            ),
                                            dcc.Dropdown(
                                                id="ollama-prompt-prefix-dropdown",
                                                options=[],
                                                placeholder="Prompt preset...",
                                                clearable=True,
                                                className="ms-2",
                                                style={
                                                    "minWidth": "220px",
                                                    "fontSize": "0.75rem",
                                                },
                                            ),
                                            dbc.Button(
                                                [
                                                    html.I(
                                                        className="bi bi-arrow-down-circle me-1"
                                                    ),
                                                    "Use Description",
                                                ],
                                                id="ollama-populate-prompt-btn",
                                                color="link",
                                                size="sm",
                                                className="p-0 text-muted",
                                                title="Copy current room description to prompt",
                                            ),
                                        ],
                                        className="d-flex align-items-center mb-1",
                                    ),
                                    dbc.Textarea(
                                        id="ollama-user-prompt",
                                        placeholder="Describe a room called 'The Main Hall'...",
                                        className="mb-2",
                                        style={"height": "60px", "fontSize": "0.8rem"},
                                    ),
                                    # ---------------------------------------------------------
                                    # Generate Button with Loading State
                                    # ---------------------------------------------------------
                                    # Button changes appearance during generation (icon spins,
                                    # text changes to "Generating...") for user feedback.
                                    dbc.Button(
                                        [
                                            html.I(
                                                className="bi bi-magic me-1",
                                                id="ollama-generate-icon",
                                            ),
                                            html.Span("Generate", id="ollama-generate-text"),
                                        ],
                                        id="ollama-generate-btn",
                                        color="info",
                                        size="sm",
                                        className="w-100 mb-2",
                                    ),
                                    # ---------------------------------------------------------
                                    # Status Area
                                    # ---------------------------------------------------------
                                    # Shows feedback messages (success, error, generation status)
                                    html.Div(
                                        id="ollama-status",
                                        className="small mb-2",
                                    ),
                                    # Internal status stores so a single renderer callback
                                    # owns the actual status output.
                                    dcc.Store(id="ollama-status-generation"),
                                    dcc.Store(id="ollama-status-send"),
                                    dcc.Store(id="ollama-status-prompt"),
                                    dcc.Store(id="ollama-status-system"),
                                    dcc.Store(id="ollama-status-template"),
                                    # ---------------------------------------------------------
                                    # Response Section
                                    # ---------------------------------------------------------
                                    # Displays the generated description from Ollama. Read-only
                                    # to prevent accidental edits.
                                    dbc.Label("Response", html_for="ollama-response", size="sm"),
                                    dbc.Textarea(
                                        id="ollama-response",
                                        placeholder="Generated description will appear here...",
                                        className="mb-2",
                                        style={"height": "100px", "fontSize": "0.8rem"},
                                        readOnly=True,
                                    ),
                                    # ---------------------------------------------------------
                                    # Action Buttons Row
                                    # ---------------------------------------------------------
                                    # "Send to Description" copies response to room description
                                    # field. Clipboard button copies response to system clipboard.
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                dbc.Button(
                                                    [
                                                        html.I(
                                                            className="bi bi-arrow-right-circle me-1"
                                                        ),
                                                        "Send to Description",
                                                    ],
                                                    id="ollama-send-to-description-btn",
                                                    color="success",
                                                    outline=True,
                                                    size="sm",
                                                    className="w-100",
                                                ),
                                                width=8,
                                            ),
                                            dbc.Col(
                                                dcc.Clipboard(
                                                    id="ollama-clipboard",
                                                    target_id="ollama-response",
                                                    title="Copy to clipboard",
                                                    className="btn btn-outline-secondary btn-sm w-100",
                                                    style={"height": "31px"},
                                                ),
                                                width=4,
                                            ),
                                        ],
                                        className="mb-2",
                                    ),
                                    # ---------------------------------------------------------
                                    # Clipboard Feedback
                                    # ---------------------------------------------------------
                                    # Shows confirmation when content is copied to clipboard.
                                    html.Div(
                                        id="ollama-clipboard-feedback",
                                        className="small",
                                    ),
                                ],
                                width=7,
                            ),
                            dbc.Col(
                                [
                                    dbc.Card(
                                        dbc.CardBody(
                                            [
                                                html.Div(
                                                    [
                                                        html.I(className="bi bi-shield-check me-2"),
                                                        html.Strong("Validator"),
                                                    ],
                                                    className="mb-2",
                                                ),
                                                html.Div(
                                                    id="ollama-validator-status",
                                                    className="mb-2",
                                                ),
                                                html.Div(
                                                    id="ollama-validator-summary",
                                                    className="small text-muted mb-3",
                                                ),
                                                html.Div(
                                                    [
                                                        html.Small(
                                                            "Rule hits",
                                                            className="text-uppercase text-muted",
                                                        ),
                                                        html.Div(
                                                            id="ollama-validator-hits",
                                                            className="small mt-1",
                                                        ),
                                                    ],
                                                    className="mb-3",
                                                ),
                                                html.Div(
                                                    [
                                                        html.Small(
                                                            "Recent checks",
                                                            className="text-uppercase text-muted",
                                                        ),
                                                        html.Div(
                                                            id="ollama-validator-history",
                                                            className="small mt-1",
                                                        ),
                                                    ]
                                                ),
                                                html.Hr(className="my-2"),
                                                html.Small(
                                                    "Validation is advisory. "
                                                    "Descriptions are not blocked.",
                                                    className="text-muted",
                                                ),
                                            ],
                                        ),
                                        className="bg-light",
                                    )
                                ],
                                width=5,
                            ),
                        ],
                        className="g-2",
                    )
                ]
            ),
        ],
        className="mt-3",  # Margin top to separate from map panel above
    )
