"""Properties panel component for the right column.

The properties panel provides the room editing interface, including
fields for room metadata, coordinates, and exit management.

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

See Also
--------
- ``callbacks/room_callbacks.py``: Callbacks for room editing
- ``callbacks/exit_callbacks.py``: Callbacks for exit management
- ``layout/ollama_panel.py``: LLM Assistant panel (separate component)
"""

import dash_bootstrap_components as dbc
from dash import dcc, html

from pipeworks_mud_mapper.services.exit_utils import EXIT_SHORT_ORDER


def create_properties_panel() -> html.Div:
    """Create the right column properties panels for file + room editing.

    The properties panel contains:

    - File Properties card (selected file + delete action)
    - Action row (New/Save/Validate/Export)
    - Header with "New Room" button
    - Room ID input (disabled when editing existing room)
    - Room name input
    - Room description textarea
    - Coordinate inputs (X, Y, Z)
    - Add Room / Update buttons
    - Exit checkboxes (N, E, S, W, U, D)

    Returns
    -------
    html.Div
        Container with the File Properties card, action row, and Room Properties card.

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
    # File Properties are kept separate so file actions feel distinct from room edits.
    file_properties = dbc.Card(
        [
            dbc.CardHeader(
                [
                    html.Span("File Properties", className="me-auto"),
                    dbc.Button(
                        [html.I(className="bi bi-trash me-1"), "Delete File"],
                        id="file-properties-delete-btn",
                        color="danger",
                        outline=True,
                        size="sm",
                        disabled=True,
                    ),
                ],
                className="d-flex align-items-center",
            ),
            dbc.CardBody(
                [
                    html.Div(id="file-properties-name", className="fw-bold mb-1"),
                    html.Div(id="file-properties-type", className="text-muted small"),
                ],
                className="small",
            ),
        ],
        className="mb-3",
    )

    room_properties = dbc.Card(
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
                    # Internal feedback stores so a single renderer owns the output.
                    dcc.Store(id="room-feedback-add"),
                    dcc.Store(id="room-feedback-new"),
                    dcc.Store(id="room-feedback-update"),
                    dcc.Store(id="room-feedback-delete"),
                    dcc.Store(id="room-feedback-undo"),
                    dcc.Store(id="room-feedback-save"),
                    dcc.Store(id="room-feedback-export"),
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
                    # Exit checkboxes section (local exits only).
                    dbc.Label("Exits"),
                    html.Div(
                        [
                            dbc.Checklist(
                                id="exit-checkboxes",
                                options=[
                                    {"label": direction, "value": direction}
                                    for direction in EXIT_SHORT_ORDER
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
                        className="mb-3 p-2 bg-body-tertiary rounded",
                    ),
                ]
            ),
        ],
        className="h-100",
        style={"overflowY": "auto"},
    )

    # Compact one-line action row keeps file actions visible without dominating the UI.
    action_row = dbc.Row(
        [
            dbc.Col(
                dbc.Button(
                    [html.I(className="bi bi-plus me-1"), "New Map"],
                    id="new-map-btn",
                    color="secondary",
                    size="sm",
                    outline=True,
                    className="w-100",
                ),
                width=3,
            ),
            dbc.Col(
                dbc.Button(
                    [html.I(className="bi bi-save me-1"), "Save"],
                    id="save-map-btn",
                    color="success",
                    size="sm",
                    className="w-100",
                    disabled=True,
                ),
                width=3,
            ),
            dbc.Col(
                dbc.Button(
                    [html.I(className="bi bi-check-circle me-1"), "Validate"],
                    id="validate-zone-btn",
                    color="info",
                    size="sm",
                    outline=True,
                    className="w-100",
                    disabled=True,
                ),
                width=3,
            ),
            dbc.Col(
                dbc.Button(
                    [html.I(className="bi bi-download me-1"), "Export"],
                    id="export-zone-btn",
                    color="primary",
                    size="sm",
                    className="w-100",
                    disabled=True,
                ),
                width=3,
            ),
        ],
        className="g-2 mb-3",
    )

    # Status indicator now lives near the action row for quick visibility.
    status_indicator = html.Div(id="status-indicator", className="small mb-2")

    return html.Div([file_properties, action_row, status_indicator, room_properties])
