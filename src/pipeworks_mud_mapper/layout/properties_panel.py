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
- ``exit-checkboxes``: Checklist for exit directions (N/E/S/W/U/D)
- ``exit-feedback``: Container for exit status display

See Also
--------
- ``callbacks/room_callbacks.py``: Callbacks for room editing
- ``callbacks/exit_callbacks.py``: Callbacks for exit management
"""

import dash_bootstrap_components as dbc
from dash import html


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
                ]
            ),
        ],
        className="h-100",
    )
