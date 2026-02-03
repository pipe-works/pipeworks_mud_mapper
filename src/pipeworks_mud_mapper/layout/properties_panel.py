"""Properties panel component for the right column.

The properties panel provides the room editing interface, including
fields for room metadata, coordinates, exit management, and LLM-powered
description generation via Ollama.

Component Structure
-------------------
::

    ┌─────────────────────────────┐
    │ Room Properties  [+New Room]│  <- CardHeader
    ├─────────────────────────────┤
    │ [Feedback messages]         │
    │                             │
    │ Room ID: [_______________]  │
    │ Name:    [_______________]  │
    │ Description:                │
    │ [________________________]  │
    │                             │
    │ Coordinates                 │
    │ X[__] Y[__] Z[__]           │
    │                             │
    │ [Add Room] [Update]         │
    │ ─────────────────────────── │
    │ Exits                       │
    │ ☐N ☐E ☐S ☐W ☐U ☐D           │
    │ [Exit status messages]      │
    │ ─────────────────────────── │
    │ 🤖 LLM Assistant (Ollama)   │
    │ Server: [http://...]        │
    │ Model: [dropdown]           │
    │ System Prompt:              │
    │ [________________________]  │
    │ User Prompt:                │
    │ [________________________]  │
    │ [Generate] [Copy]           │
    │ Response:                   │
    │ [________________________]  │
    └─────────────────────────────┘

Component IDs
-------------
- ``new-room-btn``: Button to clear form for creating new room
- ``room-form-feedback``: Container for validation/success messages
- ``room-id``: Input for room identifier
- ``room-name``: Input for room display name
- ``room-description``: Textarea for room description
- ``room-coord-x``, ``room-coord-y``, ``room-coord-z``: Coordinate inputs
- ``add-room-btn``: Button to add new room to zone
- ``update-room-btn``: Button to update existing room
- ``delete-room-btn``: Button to delete selected room (with confirmation)
- ``undo-delete-btn``: Button to undo last room deletion
- ``undo-delete-container``: Container for undo button (hidden/shown)
- ``exit-checkboxes``: Checklist for exit directions (N/E/S/W/U/D)
- ``exit-feedback``: Container for exit status display
- ``ollama-server-url``: Input for Ollama server URL
- ``ollama-model-dropdown``: Dropdown to select Ollama model
- ``ollama-refresh-models-btn``: Button to refresh model list
- ``ollama-refresh-icon``: Icon inside refresh button (for spinning animation)
- ``ollama-template-dropdown``: Dropdown to select prompt template
- ``ollama-system-prompt-toggle``: Button to toggle system prompt visibility
- ``ollama-system-prompt-collapse``: Collapsible wrapper for system prompt
- ``ollama-system-prompt``: Textarea for system prompt (read-only when template selected)
- ``ollama-copy-system-prompt-btn``: Button to copy system prompt to clipboard
- ``ollama-user-prompt``: Textarea for user prompt
- ``ollama-populate-prompt-btn``: Button to populate prompt from room description
- ``ollama-generate-btn``: Button to generate description
- ``ollama-generate-icon``: Icon inside generate button (for loading state)
- ``ollama-generate-text``: Text inside generate button (changes during generation)
- ``ollama-response``: Textarea for LLM response
- ``ollama-send-to-description-btn``: Button to send response to room description
- ``ollama-clipboard``: Clipboard copy component
- ``ollama-clipboard-feedback``: Clipboard copy feedback message
- ``ollama-status``: Status message area

See Also
--------
- ``callbacks/room_callbacks.py``: Callbacks for room editing
- ``callbacks/exit_callbacks.py``: Callbacks for exit management
- ``callbacks/ollama_callbacks.py``: Callbacks for Ollama LLM integration
"""

import dash_bootstrap_components as dbc
from dash import dcc, html


def create_properties_panel() -> dbc.Card:
    """Create the right column properties panel for room editing.

    The properties panel contains:

    - Header with "New Room" button
    - Room ID input (disabled when editing existing room)
    - Room name input
    - Room description textarea
    - Coordinate inputs (X, Y, Z)
    - Add Room / Update buttons
    - Exit checkboxes (N, E, S, W, U, D)

    Returns
    -------
    dbc.Card
        Bootstrap Card containing the room editing form.

    Component IDs
    -------------
    - ``new-room-btn``: Button to clear form for new room
    - ``room-form-feedback``: Container for validation messages
    - ``room-id``: Room ID input field
    - ``room-name``: Room name input field
    - ``room-description``: Room description textarea
    - ``room-coord-x``, ``room-coord-y``, ``room-coord-z``: Coordinate inputs
    - ``add-room-btn``: Button to add new room
    - ``update-room-btn``: Button to update existing room
    - ``exit-checkboxes``: Checklist for exit directions
    - ``exit-feedback``: Container for exit status display

    Notes
    -----
    - Room ID is disabled when editing (cannot change existing ID)
    - Update button is disabled when no room is selected
    - Exit checkboxes show current exits and allow adding/removing
    - Form feedback shows success/error messages temporarily
    """
    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    html.Span("Room Properties", className="me-auto"),
                    dbc.Button(
                        [html.I(className="bi bi-plus-lg me-1"), "New Room"],
                        id="new-room-btn",
                        color="primary",
                        size="sm",
                        outline=True,
                    ),
                ],
                className="d-flex align-items-center",
            ),
            dbc.CardBody(
                [
                    # Feedback area for validation messages
                    html.Div(id="room-form-feedback", className="mb-2"),
                    # Room ID field
                    dbc.Label("Room ID", html_for="room-id"),
                    dbc.Input(
                        id="room-id",
                        type="text",
                        placeholder="e.g., main_hall",
                        className="mb-2",
                    ),
                    dbc.FormText(
                        "Unique identifier (letters, numbers, underscores)",
                        className="mb-3 d-block",
                    ),
                    # Room name field
                    dbc.Label("Name", html_for="room-name"),
                    dbc.Input(
                        id="room-name",
                        type="text",
                        placeholder="e.g., The Main Hall",
                        className="mb-3",
                    ),
                    # Room description field
                    dbc.Label("Description", html_for="room-description"),
                    dbc.Textarea(
                        id="room-description",
                        placeholder="A spacious hall with stone pillars...",
                        className="mb-3",
                        style={"height": "80px"},
                    ),
                    # Coordinate inputs
                    dbc.Label("Coordinates"),
                    dbc.InputGroup(
                        [
                            dbc.InputGroupText("X"),
                            dbc.Input(
                                id="room-coord-x",
                                type="number",
                                value=0,
                                style={"width": "70px"},
                            ),
                            dbc.InputGroupText("Y"),
                            dbc.Input(
                                id="room-coord-y",
                                type="number",
                                value=0,
                                style={"width": "70px"},
                            ),
                            dbc.InputGroupText("Z"),
                            dbc.Input(
                                id="room-coord-z",
                                type="number",
                                value=0,
                                style={"width": "70px"},
                            ),
                        ],
                        className="mb-1",
                        size="sm",
                    ),
                    dbc.FormText(
                        "X: East(+)/West(-), Y: North(+)/South(-), Z: Up(+)/Down(-)",
                        className="mb-3 d-block",
                    ),
                    # Action buttons
                    dbc.Row(
                        [
                            dbc.Col(
                                dbc.Button(
                                    [html.I(className="bi bi-plus-circle me-2"), "Add Room"],
                                    id="add-room-btn",
                                    color="success",
                                    className="w-100",
                                ),
                                width=6,
                            ),
                            dbc.Col(
                                dbc.Button(
                                    [html.I(className="bi bi-pencil me-2"), "Update"],
                                    id="update-room-btn",
                                    color="primary",
                                    className="w-100",
                                    disabled=True,
                                ),
                                width=6,
                            ),
                        ],
                        className="mb-2",
                    ),
                    # Delete button (separate row, danger color)
                    dbc.Button(
                        [html.I(className="bi bi-trash me-2"), "Delete Room"],
                        id="delete-room-btn",
                        color="danger",
                        outline=True,
                        size="sm",
                        className="w-100 mb-3",
                        disabled=True,
                    ),
                    # Undo delete button (hidden by default)
                    html.Div(
                        dbc.Button(
                            [html.I(className="bi bi-arrow-counterclockwise me-2"), "Undo Delete"],
                            id="undo-delete-btn",
                            color="warning",
                            size="sm",
                            className="w-100",
                        ),
                        id="undo-delete-container",
                        style={"display": "none"},
                        className="mb-3",
                    ),
                    html.Hr(),
                    # Exit checkboxes section
                    dbc.Label("Exits"),
                    html.Div(
                        [
                            dbc.Checklist(
                                id="exit-checkboxes",
                                options=[
                                    {"label": "N", "value": "N"},
                                    {"label": "E", "value": "E"},
                                    {"label": "S", "value": "S"},
                                    {"label": "W", "value": "W"},
                                    {"label": "U", "value": "U"},
                                    {"label": "D", "value": "D"},
                                ],
                                value=[],
                                inline=True,
                                className="mb-2",
                            ),
                            html.Div(
                                id="exit-feedback",
                                className="small",
                            ),
                        ],
                        className="mb-3 p-2 bg-light rounded",
                    ),
                    html.Hr(),
                    # =========================================================
                    # Ollama LLM Assistant Section
                    # =========================================================
                    html.Div(
                        [
                            html.I(className="bi bi-robot me-2"),
                            html.Strong("LLM Assistant"),
                            html.Small(" (Ollama)", className="text-muted"),
                        ],
                        className="mb-2",
                    ),
                    # Server URL input with connection status
                    dbc.Label("Server URL", html_for="ollama-server-url", size="sm"),
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
                    # Connection status indicator
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
                    # Model dropdown with loading indicator
                    dbc.Label("Model", html_for="ollama-model-dropdown", size="sm"),
                    dcc.Loading(
                        id="ollama-model-loading",
                        type="dot",
                        color="#17a2b8",
                        children=dcc.Dropdown(
                            id="ollama-model-dropdown",
                            options=[],
                            placeholder="Connect to server first",
                            className="mb-2",
                            style={"fontSize": "0.875rem"},
                        ),
                    ),
                    # Template dropdown
                    dbc.Label("Template", html_for="ollama-template-dropdown", size="sm"),
                    dcc.Dropdown(
                        id="ollama-template-dropdown",
                        options=[],  # Populated by callback
                        placeholder="Select a template...",
                        className="mb-2",
                        style={"fontSize": "0.875rem"},
                    ),
                    # Collapsible system prompt section
                    html.Div(
                        [
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
                        ],
                        className="d-flex align-items-center mb-1",
                    ),
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
                                    "height": "120px",
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
                    # User prompt with populate button
                    html.Div(
                        [
                            dbc.Label(
                                "User Prompt",
                                html_for="ollama-user-prompt",
                                size="sm",
                                className="me-auto",
                            ),
                            dbc.Button(
                                [
                                    html.I(className="bi bi-arrow-down-circle me-1"),
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
                    # Generate button with loading state support
                    dbc.Button(
                        [
                            html.I(className="bi bi-magic me-1", id="ollama-generate-icon"),
                            html.Span("Generate", id="ollama-generate-text"),
                        ],
                        id="ollama-generate-btn",
                        color="info",
                        size="sm",
                        className="w-100 mb-2",
                    ),
                    # Status area
                    html.Div(
                        id="ollama-status",
                        className="small mb-2",
                    ),
                    # Response area
                    dbc.Label("Response", html_for="ollama-response", size="sm"),
                    dbc.Textarea(
                        id="ollama-response",
                        placeholder="Generated description will appear here...",
                        className="mb-2",
                        style={"height": "100px", "fontSize": "0.8rem"},
                        readOnly=True,
                    ),
                    # Action buttons row
                    dbc.Row(
                        [
                            dbc.Col(
                                dbc.Button(
                                    [
                                        html.I(className="bi bi-arrow-right-circle me-1"),
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
                    # Clipboard feedback
                    html.Div(
                        id="ollama-clipboard-feedback",
                        className="small",
                    ),
                ]
            ),
        ],
        className="h-100",
        style={"overflowY": "auto"},
    )
