"""Main Dash application for the MUD Mapper."""

import re
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, callback, ctx, dcc, html, no_update

from pipeworks_mud_mapper.components.map_view import (
    create_map_figure,
    create_map_figure_with_rooms,
)
from pipeworks_mud_mapper.components.new_map_modal import create_new_map_modal
from pipeworks_mud_mapper.utils.zone_io import (
    auto_layout_rooms,
    create_blank_zone,
    list_zone_files,
    load_zone_json,
    save_zone_json,
)

# Data directory for zone files
DATA_DIR = Path(__file__).parent.parent.parent / "data"

# Initialize the Dash app with Bootstrap theme
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="PipeWorks MUD Mapper",
)


def create_file_browser() -> dbc.Card:
    """Create the left column file browser."""
    return dbc.Card(
        [
            dbc.CardHeader("File Browser"),
            dbc.CardBody(
                [
                    html.Div(
                        [
                            html.I(className="bi bi-folder-fill me-2 text-warning"),
                            html.Span("data/"),
                        ],
                        className="mb-2",
                    ),
                    # Dynamic file list container
                    html.Div(id="file-list-container", className="ms-3 mb-3"),
                    html.Hr(),
                    dbc.Button(
                        [html.I(className="bi bi-plus me-2"), "New Map"],
                        id="new-map-btn",
                        color="secondary",
                        size="sm",
                        outline=True,
                    ),
                ],
                className="font-monospace small",
            ),
        ],
        className="h-100",
    )


def create_map_panel() -> dbc.Card:
    """Create the center column map panel."""
    return dbc.Card(
        [
            dbc.CardBody(
                [
                    # Map figure
                    dcc.Graph(
                        id="map-graph",
                        figure=create_map_figure(z_level=0),
                        config={
                            "displayModeBar": True,
                            "scrollZoom": True,
                            "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                        },
                    ),
                    # Layer controls
                    html.Div(
                        [
                            html.Label("Layer (Z):", className="me-3"),
                            dbc.RadioItems(
                                id="z-level-selector",
                                options=[
                                    {"label": "z = -1 (Down)", "value": -1},
                                    {"label": "z = 0 (Ground)", "value": 0},
                                    {"label": "z = +1 (Up)", "value": 1},
                                ],
                                value=0,
                                inline=True,
                            ),
                        ],
                        className="d-flex align-items-center mt-2 p-2 bg-light rounded",
                    ),
                ]
            ),
        ],
        className="h-100",
    )


def create_properties_panel() -> dbc.Card:
    """Create the right column properties panel for adding/editing rooms."""
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
                    # Feedback area
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
                    # Name field
                    dbc.Label("Name", html_for="room-name"),
                    dbc.Input(
                        id="room-name",
                        type="text",
                        placeholder="e.g., The Main Hall",
                        className="mb-3",
                    ),
                    # Description field
                    dbc.Label("Description", html_for="room-description"),
                    dbc.Textarea(
                        id="room-description",
                        placeholder="A spacious hall with stone pillars...",
                        className="mb-3",
                        style={"height": "80px"},
                    ),
                    # Coordinates
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
                    # Add/Update Room buttons
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
                    # Exits section (placeholder for now)
                    dbc.Label("Exits"),
                    html.Div(
                        id="room-exits-display",
                        children=[
                            html.Small(
                                "Add rooms first, then connect exits", className="text-muted"
                            ),
                        ],
                        className="mb-3 p-2 bg-light rounded small",
                    ),
                ]
            ),
        ],
        className="h-100",
    )


def create_action_bar() -> html.Div:
    """Create the bottom action bar."""
    return html.Div(
        [
            dbc.Button(
                [html.I(className="bi bi-check-circle me-2"), "Validate"],
                color="info",
                outline=True,
                className="me-2",
                disabled=True,
            ),
            dbc.Button(
                [html.I(className="bi bi-download me-2"), "Export Zone JSON"],
                color="primary",
                outline=True,
                className="me-2",
                disabled=True,
            ),
            dbc.Button(
                [html.I(className="bi bi-save me-2"), "Save Map"],
                id="save-map-btn",
                color="success",
                outline=True,
                disabled=True,
            ),
            html.Span(
                id="status-indicator",
                children=[
                    html.I(className="bi bi-circle-fill text-secondary me-2"),
                    "No file loaded",
                ],
                className="ms-auto text-muted",
            ),
        ],
        className="d-flex align-items-center p-3 bg-light border-top",
    )


# Main layout
app.layout = dbc.Container(
    [
        # State stores
        dcc.Store(id="zone-files-store", data=[]),
        dcc.Store(id="current-zone-data", data=None),
        dcc.Store(id="selected-file", data=None),
        dcc.Store(id="selected-room", data=None),
        dcc.Store(id="has-unsaved-changes", data=False),
        dcc.Interval(id="initial-load", interval=100, max_intervals=1),
        # New Map modal
        create_new_map_modal(),
        # Header
        dbc.Row(
            [
                dbc.Col(
                    html.H4(
                        [
                            html.I(className="bi bi-map me-2"),
                            "PipeWorks MUD Mapper",
                        ],
                        className="mb-0",
                    ),
                    width="auto",
                ),
                dbc.Col(
                    html.Span("Zone: (none)", className="text-muted", id="current-zone"),
                    width="auto",
                    className="ms-auto",
                ),
            ],
            className="py-3 border-bottom mb-3 align-items-center",
        ),
        # Three-column layout
        dbc.Row(
            [
                # Left column - File Browser (2/12)
                dbc.Col(
                    create_file_browser(),
                    width=2,
                    className="pe-2",
                ),
                # Center column - Map (7/12)
                dbc.Col(
                    create_map_panel(),
                    width=7,
                    className="px-2",
                ),
                # Right column - Properties (3/12)
                dbc.Col(
                    create_properties_panel(),
                    width=3,
                    className="ps-2",
                ),
            ],
            className="flex-grow-1",
            style={"minHeight": "600px"},
        ),
        # Action bar
        dbc.Row(
            [
                dbc.Col(create_action_bar()),
            ],
            className="mt-3",
        ),
    ],
    fluid=True,
    className="vh-100 d-flex flex-column",
)


# Callback: Load zone files on initial load and when store updates
@callback(
    Output("zone-files-store", "data"),
    Input("initial-load", "n_intervals"),
    prevent_initial_call=False,
)
def load_zone_files(_: int) -> list[str]:
    """Load list of zone files from working directory."""
    files = list_zone_files(DATA_DIR)
    return [f.name for f in files]


# Callback: Render file list from store
@callback(
    Output("file-list-container", "children"),
    Input("zone-files-store", "data"),
    Input("selected-file", "data"),
)
def render_file_list(files: list[str], selected_file: str | None) -> list:
    """Render the file list in the browser with clickable items."""
    if not files:
        return [html.Span("No zone files found", className="text-muted fst-italic")]

    items = []
    for filename in files:
        is_selected = filename == selected_file
        icon_class = "bi bi-file-earmark-code me-2"
        if is_selected:
            icon_class += " text-primary"
        items.append(
            html.Div(
                [
                    html.I(className=icon_class),
                    html.Span(filename, className="fw-bold" if is_selected else ""),
                ],
                id={"type": "file-item", "filename": filename},
                className="mb-1 p-1 rounded file-item"
                + (" bg-primary bg-opacity-10" if is_selected else ""),
                style={"cursor": "pointer"},
                n_clicks=0,
            )
        )
    return items


# Callback: Handle file click - load zone data
@callback(
    Output("selected-file", "data"),
    Output("current-zone-data", "data"),
    Output("current-zone", "children"),
    Input({"type": "file-item", "filename": ALL}, "n_clicks"),
    State("zone-files-store", "data"),
    prevent_initial_call=True,
)
def handle_file_click(n_clicks_list: list[int], files: list[str]) -> tuple:
    """Load zone data when a file is clicked."""
    # Find which file was clicked
    if not any(n_clicks_list):
        return no_update, no_update, no_update

    # Get the triggered file from context
    triggered = ctx.triggered_id
    if not triggered or not isinstance(triggered, dict):
        return no_update, no_update, no_update

    filename = triggered.get("filename")
    if not filename:
        return no_update, no_update, no_update

    # Load the zone file
    file_path = DATA_DIR / filename
    try:
        zone_data = load_zone_json(file_path)
        # Auto-layout if rooms don't have coords
        zone_data = auto_layout_rooms(zone_data)
        zone_name = zone_data.get("name", filename)
        return filename, zone_data, f"Zone: {zone_name}"
    except Exception as e:
        print(f"Error loading zone: {e}")
        return no_update, no_update, no_update


# Callback: Update map when zone data, Z level, or selected room changes
@callback(
    Output("map-graph", "figure"),
    Input("current-zone-data", "data"),
    Input("z-level-selector", "value"),
    Input("selected-room", "data"),
)
def update_map_with_rooms(zone_data: dict | None, z_level: int, selected_room: str | None) -> dict:
    """Update the map figure with loaded zone rooms."""
    if not zone_data:
        return create_map_figure(z_level=z_level)

    rooms = zone_data.get("rooms", {})
    return create_map_figure_with_rooms(rooms=rooms, z_level=z_level, selected_room=selected_room)


# Callback: Open New Map modal
@callback(
    Output("new-map-modal", "is_open", allow_duplicate=True),
    Input("new-map-btn", "n_clicks"),
    prevent_initial_call=True,
)
def open_new_map_modal(n_clicks: int) -> bool:
    """Open the New Map modal when button is clicked."""
    if n_clicks:
        return True
    return False


# Callback: Close modal on cancel
@callback(
    Output("new-map-modal", "is_open", allow_duplicate=True),
    Input("new-map-cancel-btn", "n_clicks"),
    prevent_initial_call=True,
)
def close_new_map_modal(n_clicks: int) -> bool:
    """Close the New Map modal when cancel is clicked."""
    if n_clicks:
        return False
    return no_update


# Callback: Create new zone on submit
@callback(
    Output("new-map-modal", "is_open"),
    Output("zone-files-store", "data", allow_duplicate=True),
    Output("new-map-feedback", "children"),
    Output("new-zone-id", "value"),
    Output("new-zone-name", "value"),
    Output("new-zone-description", "value"),
    Input("new-map-create-btn", "n_clicks"),
    State("new-zone-id", "value"),
    State("new-zone-name", "value"),
    State("new-zone-description", "value"),
    prevent_initial_call=True,
)
def create_new_zone(
    n_clicks: int,
    zone_id: str,
    zone_name: str,
    description: str,
) -> tuple:
    """Create a new zone file when Create button is clicked."""
    if not n_clicks:
        return no_update, no_update, no_update, no_update, no_update, no_update

    # Validate zone_id
    zone_id = (zone_id or "").strip()
    zone_name = (zone_name or "").strip()
    description = (description or "").strip()

    if not zone_id:
        feedback = dbc.Alert("Zone ID is required.", color="danger", className="mb-0")
        return no_update, no_update, feedback, no_update, no_update, no_update

    if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", zone_id):
        feedback = dbc.Alert(
            "Zone ID must start with a letter and contain only letters, numbers, and underscores.",
            color="danger",
            className="mb-0",
        )
        return no_update, no_update, feedback, no_update, no_update, no_update

    if not zone_name:
        feedback = dbc.Alert("Zone Name is required.", color="danger", className="mb-0")
        return no_update, no_update, feedback, no_update, no_update, no_update

    # Check if file already exists
    file_path = DATA_DIR / f"{zone_id}.json"
    if file_path.exists():
        feedback = dbc.Alert(
            f"A zone with ID '{zone_id}' already exists.", color="warning", className="mb-0"
        )
        return no_update, no_update, feedback, no_update, no_update, no_update

    # Create and save the zone
    zone_data = create_blank_zone(zone_id, zone_name, description)
    save_zone_json(zone_data, file_path)

    # Refresh file list
    files = list_zone_files(DATA_DIR)
    file_names = [f.name for f in files]

    # Close modal and clear form
    return False, file_names, "", "", "", ""


# Callback: Add new room to current zone
@callback(
    Output("current-zone-data", "data", allow_duplicate=True),
    Output("room-form-feedback", "children"),
    Output("room-id", "value"),
    Output("room-name", "value"),
    Output("room-description", "value"),
    Output("room-coord-x", "value"),
    Output("room-coord-y", "value"),
    Output("room-coord-z", "value"),
    Output("has-unsaved-changes", "data", allow_duplicate=True),
    Input("add-room-btn", "n_clicks"),
    State("current-zone-data", "data"),
    State("room-id", "value"),
    State("room-name", "value"),
    State("room-description", "value"),
    State("room-coord-x", "value"),
    State("room-coord-y", "value"),
    State("room-coord-z", "value"),
    prevent_initial_call=True,
)
def add_room_to_zone(
    n_clicks: int,
    zone_data: dict | None,
    room_id: str,
    room_name: str,
    room_description: str,
    coord_x: int,
    coord_y: int,
    coord_z: int,
) -> tuple:
    """Add a new room to the current zone."""
    if not n_clicks:
        return (no_update,) * 9

    # Validate zone is loaded
    if not zone_data:
        feedback = dbc.Alert(
            "No zone loaded. Create or select a zone first.",
            color="warning",
            className="mb-0 py-2",
        )
        return (no_update, feedback) + (no_update,) * 7

    # Validate room_id
    room_id = (room_id or "").strip()
    if not room_id:
        feedback = dbc.Alert("Room ID is required.", color="danger", className="mb-0 py-2")
        return (no_update, feedback) + (no_update,) * 7

    if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", room_id):
        feedback = dbc.Alert(
            "Room ID must start with a letter and contain only letters, numbers, underscores.",
            color="danger",
            className="mb-0 py-2",
        )
        return (no_update, feedback) + (no_update,) * 7

    # Check if room already exists
    if room_id in zone_data.get("rooms", {}):
        feedback = dbc.Alert(
            f"Room '{room_id}' already exists in this zone.",
            color="warning",
            className="mb-0 py-2",
        )
        return (no_update, feedback) + (no_update,) * 7

    # Validate coordinates
    try:
        x = int(coord_x) if coord_x is not None else 0
        y = int(coord_y) if coord_y is not None else 0
        z = int(coord_z) if coord_z is not None else 0
    except (ValueError, TypeError):
        feedback = dbc.Alert("Coordinates must be integers.", color="danger", className="mb-0 py-2")
        return (no_update, feedback) + (no_update,) * 7

    # Create the new room
    new_room = {
        "id": room_id,
        "name": (room_name or "").strip() or room_id,
        "description": (room_description or "").strip(),
        "coords": [x, y, z],
        "exits": {},
        "items": [],
    }

    # Add to zone data (create a copy to trigger update)
    updated_zone = dict(zone_data)
    updated_zone["rooms"] = dict(zone_data.get("rooms", {}))
    updated_zone["rooms"][room_id] = new_room

    # Success feedback
    feedback = dbc.Alert(
        f"Room '{room_id}' added at ({x}, {y}, {z})",
        color="success",
        className="mb-0 py-2",
        duration=3000,
    )

    # Return updated zone, clear form, and mark unsaved changes
    return updated_zone, feedback, "", "", "", 0, 0, 0, True


# Callback: Clear form and deselect room when New Room button clicked
@callback(
    Output("room-form-feedback", "children", allow_duplicate=True),
    Output("selected-room", "data", allow_duplicate=True),
    Output("room-id", "value", allow_duplicate=True),
    Output("room-name", "value", allow_duplicate=True),
    Output("room-description", "value", allow_duplicate=True),
    Output("room-coord-x", "value", allow_duplicate=True),
    Output("room-coord-y", "value", allow_duplicate=True),
    Output("room-coord-z", "value", allow_duplicate=True),
    Output("update-room-btn", "disabled", allow_duplicate=True),
    Output("room-id", "disabled", allow_duplicate=True),
    Input("new-room-btn", "n_clicks"),
    prevent_initial_call=True,
)
def clear_form_for_new_room(n_clicks: int):
    """Clear form and deselect room when New Room button is clicked."""
    if n_clicks:
        # Clear feedback, deselect room, clear form, disable update, enable room ID
        return "", None, "", "", "", 0, 0, 0, True, False
    return (no_update,) * 10


# Callback: Handle click on map to select a room
@callback(
    Output("selected-room", "data"),
    Input("map-graph", "clickData"),
    State("current-zone-data", "data"),
    prevent_initial_call=True,
)
def handle_map_click(click_data: dict | None, zone_data: dict | None) -> str | None:
    """Select a room when clicked on the map."""
    if not click_data or not zone_data:
        return no_update

    # Get clicked point info
    points = click_data.get("points", [])
    if not points:
        return no_update

    point = points[0]
    # The text field contains the room_id (set in map_view.py)
    room_id = point.get("text")
    if room_id and room_id in zone_data.get("rooms", {}):
        return room_id

    return no_update


# Callback: Populate form when a room is selected
@callback(
    Output("room-id", "value", allow_duplicate=True),
    Output("room-name", "value", allow_duplicate=True),
    Output("room-description", "value", allow_duplicate=True),
    Output("room-coord-x", "value", allow_duplicate=True),
    Output("room-coord-y", "value", allow_duplicate=True),
    Output("room-coord-z", "value", allow_duplicate=True),
    Output("room-exits-display", "children"),
    Output("update-room-btn", "disabled"),
    Output("room-id", "disabled"),
    Input("selected-room", "data"),
    State("current-zone-data", "data"),
    prevent_initial_call=True,
)
def populate_room_form(selected_room: str | None, zone_data: dict | None) -> tuple:
    """Populate the room form when a room is selected."""
    if not selected_room or not zone_data:
        # No room selected - disable update, enable room ID editing
        return (no_update,) * 7 + (True, False)

    rooms = zone_data.get("rooms", {})
    room = rooms.get(selected_room)
    if not room:
        return (no_update,) * 7 + (True, False)

    coords = room.get("coords", [0, 0, 0])

    # Build exits display
    exits = room.get("exits", {})
    if exits:
        exit_items = [
            html.Div(
                [
                    html.Span(direction, className="fw-bold me-2"),
                    html.I(className="bi bi-arrow-right me-2"),
                    html.Span(target),
                ],
                className="mb-1",
            )
            for direction, target in exits.items()
        ]
    else:
        exit_items = [html.Small("No exits defined", className="text-muted")]

    # Room selected - enable update, disable room ID editing (can't change ID)
    return (
        room.get("id", selected_room),
        room.get("name", ""),
        room.get("description", ""),
        coords[0] if len(coords) > 0 else 0,
        coords[1] if len(coords) > 1 else 0,
        coords[2] if len(coords) > 2 else 0,
        exit_items,
        False,  # Enable update button
        True,  # Disable room ID field (can't change ID of existing room)
    )


# Callback: Update existing room properties
@callback(
    Output("current-zone-data", "data", allow_duplicate=True),
    Output("room-form-feedback", "children", allow_duplicate=True),
    Output("has-unsaved-changes", "data", allow_duplicate=True),
    Input("update-room-btn", "n_clicks"),
    State("selected-room", "data"),
    State("current-zone-data", "data"),
    State("room-name", "value"),
    State("room-description", "value"),
    State("room-coord-x", "value"),
    State("room-coord-y", "value"),
    State("room-coord-z", "value"),
    prevent_initial_call=True,
)
def update_room_properties(
    n_clicks: int,
    selected_room: str | None,
    zone_data: dict | None,
    room_name: str,
    room_description: str,
    coord_x: int,
    coord_y: int,
    coord_z: int,
) -> tuple:
    """Update an existing room's properties."""
    if not n_clicks:
        return no_update, no_update, no_update

    if not selected_room or not zone_data:
        feedback = dbc.Alert(
            "No room selected to update.",
            color="warning",
            className="mb-0 py-2",
        )
        return no_update, feedback, no_update

    rooms = zone_data.get("rooms", {})
    if selected_room not in rooms:
        feedback = dbc.Alert(
            f"Room '{selected_room}' not found.",
            color="danger",
            className="mb-0 py-2",
        )
        return no_update, feedback, no_update

    # Validate coordinates
    try:
        x = int(coord_x) if coord_x is not None else 0
        y = int(coord_y) if coord_y is not None else 0
        z = int(coord_z) if coord_z is not None else 0
    except (ValueError, TypeError):
        feedback = dbc.Alert(
            "Coordinates must be integers.",
            color="danger",
            className="mb-0 py-2",
        )
        return no_update, feedback, no_update

    # Create updated zone data
    updated_zone = dict(zone_data)
    updated_zone["rooms"] = dict(zone_data.get("rooms", {}))
    updated_room = dict(rooms[selected_room])

    # Update room properties
    updated_room["name"] = (room_name or "").strip() or selected_room
    updated_room["description"] = (room_description or "").strip()
    updated_room["coords"] = [x, y, z]

    updated_zone["rooms"][selected_room] = updated_room

    feedback = dbc.Alert(
        f"Room '{selected_room}' updated.",
        color="success",
        className="mb-0 py-2",
        duration=3000,
    )

    return updated_zone, feedback, True


# Callback: Reset unsaved changes when file is loaded
@callback(
    Output("has-unsaved-changes", "data", allow_duplicate=True),
    Input("selected-file", "data"),
    prevent_initial_call=True,
)
def reset_unsaved_on_file_load(selected_file: str | None) -> bool:
    """Reset unsaved changes flag when a new file is loaded."""
    return False


# Callback: Update save button and status indicator
@callback(
    Output("save-map-btn", "disabled"),
    Output("status-indicator", "children"),
    Input("has-unsaved-changes", "data"),
    Input("selected-file", "data"),
)
def update_save_status(has_unsaved: bool, selected_file: str | None) -> tuple:
    """Update save button state and status indicator."""
    if not selected_file:
        return True, [
            html.I(className="bi bi-circle-fill text-secondary me-2"),
            "No file loaded",
        ]

    if has_unsaved:
        return False, [
            html.I(className="bi bi-circle-fill text-warning me-2"),
            f"Unsaved changes: {selected_file}",
        ]

    return True, [
        html.I(className="bi bi-circle-fill text-success me-2"),
        f"Saved: {selected_file}",
    ]


# Callback: Save zone to file
@callback(
    Output("has-unsaved-changes", "data", allow_duplicate=True),
    Output("room-form-feedback", "children", allow_duplicate=True),
    Input("save-map-btn", "n_clicks"),
    State("current-zone-data", "data"),
    State("selected-file", "data"),
    prevent_initial_call=True,
)
def save_zone_to_file(n_clicks: int, zone_data: dict | None, selected_file: str | None) -> tuple:
    """Save the current zone data to the file."""
    if not n_clicks or not zone_data or not selected_file:
        return no_update, no_update

    file_path = DATA_DIR / selected_file
    try:
        save_zone_json(zone_data, file_path)
        feedback = dbc.Alert(
            f"Saved to {selected_file}",
            color="success",
            className="mb-0 py-2",
            duration=3000,
        )
        return False, feedback
    except Exception as e:
        feedback = dbc.Alert(
            f"Error saving: {e}",
            color="danger",
            className="mb-0 py-2",
        )
        return no_update, feedback


def run_app(debug: bool = True, port: int = 8050) -> None:
    """Run the Dash application.

    Args:
        debug: Enable debug mode with auto-reload.
        port: Port to run the server on.
    """
    print("\n  PipeWorks MUD Mapper")
    print(f"  Running on http://127.0.0.1:{port}")
    print("  Press Ctrl+C to quit\n")
    app.run(debug=debug, port=port)


if __name__ == "__main__":
    run_app()
