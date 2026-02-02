"""
Main Dash application for the PipeWorks MUD Mapper.

This module provides the complete web-based zone editor application,
built using Dash and Plotly for interactive visualization and editing.
The application allows users to create, edit, and save MUD zone files
through a visual interface.

Design Principles
-----------------
1. **Reactive Updates**: All UI changes flow through Dash callbacks
2. **State Isolation**: Application state stored in dcc.Store components
3. **Bidirectional Exits**: Exit creation automatically creates reverse exits
4. **Non-destructive**: Original files untouched until explicit save

Application Architecture
------------------------
The application uses a three-column layout:

1. **Left Column (File Browser)**
   - Lists zone files in data/ directory
   - Click to load a zone file
   - "New Map" button opens creation modal

2. **Center Column (Map View)**
   - Interactive Plotly graph showing rooms and exits
   - Z-level selector for multi-floor zones
   - Click rooms to select them

3. **Right Column (Properties Panel)**
   - Room creation/editing form
   - Coordinate input fields
   - Exit checkboxes with bidirectional support

State Management
----------------
The application maintains state in the following dcc.Store components:

- ``zone-files-store``: List of available zone file names
- ``current-zone-data``: Currently loaded zone data (dict)
- ``selected-file``: Currently selected file name
- ``selected-room``: Currently selected room ID
- ``has-unsaved-changes``: Boolean flag for save status

Layout Components
-----------------
create_file_browser() -> dbc.Card
    Left column file browser with zone list and "New Map" button

create_map_panel() -> dbc.Card
    Center column with Plotly map and Z-level selector

create_properties_panel() -> dbc.Card
    Right column room editing form with exits

create_action_bar() -> html.Div
    Bottom bar with save button and status indicator

Callbacks
---------
The application uses numerous Dash callbacks for reactivity:

**File Management**
- load_zone_files: Load zone file list on startup
- render_file_list: Render clickable file list
- handle_file_click: Load zone when file clicked
- create_new_zone: Create new zone from modal

**Map Interaction**
- update_map_with_rooms: Re-render map when data changes
- handle_map_click: Select room when clicked on map

**Room Editing**
- populate_room_form: Fill form when room selected
- add_room_to_zone: Add new room to zone
- update_room_properties: Update existing room
- clear_form_for_new_room: Reset form for new room

**Exit Management**
- handle_exit_changes: Process exit checkbox changes
  (includes bidirectional exit creation)

**Save/Status**
- update_save_status: Update save button and indicator
- save_zone_to_file: Save zone data to file
- reset_unsaved_on_file_load: Reset flag when file loaded

Module Constants
----------------
DATA_DIR : Path
    Directory containing zone JSON files (../data relative to this file)

app : dash.Dash
    The Dash application instance

Usage
-----
Run the application from command line::

    python -m pipeworks_mud_mapper

Or import and run programmatically::

    from pipeworks_mud_mapper.app import run_app
    run_app(debug=True, port=8050)

Access the application at http://127.0.0.1:8050 in your browser.

Workflow Example
----------------
1. Click "New Map" to create a zone
2. Enter zone ID, name, description
3. Click "Create" - zone file saved to data/
4. Click the new file to load it
5. Use "Add Room" to create rooms at coordinates
6. Select rooms by clicking on map
7. Check exit checkboxes to connect rooms
8. Click "Save Map" to persist changes

Technical Notes
---------------
- The application uses Bootstrap 5 via dash-bootstrap-components
- Bootstrap Icons are used throughout the UI
- Pattern-matching callbacks (ALL) are used for dynamic file list
- Callback outputs use allow_duplicate=True for multiple callbacks
  targeting the same component

See Also
--------
- pipeworks_mud_mapper.components.map_view : Map visualization
- pipeworks_mud_mapper.components.new_map_modal : Zone creation modal
- pipeworks_mud_mapper.utils.zone_io : Zone file I/O utilities
"""

import re
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, callback, ctx, html, no_update

from pipeworks_mud_mapper.components.map_view import (
    create_map_figure,
    create_map_figure_with_rooms,
)
from pipeworks_mud_mapper.layout import create_app_layout
from pipeworks_mud_mapper.utils.zone_io import (
    DIRECTION_SHORT,
    OPPOSITE_DIRECTION,
    SHORT_TO_DIRECTION,
    auto_layout_rooms,
    create_blank_zone,
    find_room_in_direction,
    list_zone_files,
    load_zone_json,
    save_zone_json,
)

# =============================================================================
# Module Constants
# =============================================================================

DATA_DIR = Path(__file__).parent.parent.parent / "data"
"""
Path to the data directory containing zone JSON files.

This is calculated relative to the app.py location:
- app.py is in: src/pipeworks_mud_mapper/app.py
- data is in: data/
- So we go up 3 levels (parent.parent.parent) then into "data"
"""

# =============================================================================
# Application Initialization
# =============================================================================

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="PipeWorks MUD Mapper",
)
"""
The main Dash application instance.

Configured with:
- Bootstrap theme for consistent styling
- Custom title shown in browser tab
- Serves the Flask app on run()
"""


# =============================================================================
# Application Layout (see layout/ modules for component definitions)
# =============================================================================

app.layout = create_app_layout()


# NOTE: Layout component functions have been moved to layout/ modules:
# - create_file_browser -> layout/file_browser.py
# - create_map_panel -> layout/map_panel.py
# - create_properties_panel -> layout/properties_panel.py
# - create_action_bar -> layout/action_bar.py


# =============================================================================
# File Management Callbacks
# =============================================================================


@callback(
    Output("zone-files-store", "data"),
    Input("initial-load", "n_intervals"),
    prevent_initial_call=False,
)
def load_zone_files(_: int) -> list[str]:
    """
    Load list of zone files from the data directory.

    This callback is triggered once on initial page load (via dcc.Interval)
    and populates the zone-files-store with available zone file names.

    Parameters
    ----------
    _ : int
        Interval count (ignored, we just need the trigger).

    Returns
    -------
    list[str]
        List of zone file names (e.g., ["dungeon.json", "town.json"]).
    """
    files = list_zone_files(DATA_DIR)
    return [f.name for f in files]


@callback(
    Output("file-list-container", "children"),
    Input("zone-files-store", "data"),
    Input("selected-file", "data"),
)
def render_file_list(files: list[str], selected_file: str | None) -> list:
    """
    Render the file list in the browser with clickable items.

    Creates a list of clickable div elements, one for each zone file.
    The currently selected file is highlighted with different styling.

    Parameters
    ----------
    files : list[str]
        List of zone file names from zone-files-store.
    selected_file : str | None
        Currently selected file name, or None.

    Returns
    -------
    list
        List of html.Div elements for each file, or placeholder
        message if no files found.

    Notes
    -----
    - Each file item has a pattern-matching ID: {"type": "file-item", "filename": name}
    - Selected file gets bg-primary highlight and bold text
    - Items are styled as clickable with cursor: pointer
    """
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


@callback(
    Output("selected-file", "data"),
    Output("current-zone-data", "data"),
    Output("current-zone", "children"),
    Input({"type": "file-item", "filename": ALL}, "n_clicks"),
    State("zone-files-store", "data"),
    prevent_initial_call=True,
)
def handle_file_click(n_clicks_list: list[int], files: list[str]) -> tuple:
    """
    Load zone data when a file is clicked in the browser.

    Uses Dash pattern-matching callbacks to detect which file was clicked
    from the dynamic file list. Loads the zone JSON and applies auto-layout
    to ensure all rooms have coordinates.

    Parameters
    ----------
    n_clicks_list : list[int]
        Click counts for all file items (pattern-matching input).
    files : list[str]
        List of file names from zone-files-store.

    Returns
    -------
    tuple
        (selected_file, zone_data, zone_display) or no_update tuple.

    Notes
    -----
    - Uses ctx.triggered_id to determine which file was clicked
    - Applies auto_layout_rooms to ensure coords exist for visualization
    - Errors are printed to console (could be improved)
    """
    # Check if any file was actually clicked
    if not any(n_clicks_list):
        return no_update, no_update, no_update

    # Get the triggered file from callback context
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
        # Auto-layout ensures all rooms have coordinates for display
        zone_data = auto_layout_rooms(zone_data)
        zone_name = zone_data.get("name", filename)
        return filename, zone_data, f"Zone: {zone_name}"
    except Exception as e:
        print(f"Error loading zone: {e}")
        return no_update, no_update, no_update


# =============================================================================
# Map Visualization Callbacks
# =============================================================================


@callback(
    Output("map-graph", "figure"),
    Input("current-zone-data", "data"),
    Input("z-level-selector", "value"),
    Input("selected-room", "data"),
)
def update_map_with_rooms(zone_data: dict | None, z_level: int, selected_room: str | None) -> dict:
    """
    Update the map figure when zone data, Z-level, or selection changes.

    Re-renders the Plotly figure with current rooms filtered to the
    selected Z-level, highlighting the selected room if any.

    Parameters
    ----------
    zone_data : dict | None
        Current zone data, or None if no zone loaded.
    z_level : int
        Currently selected Z-level (-1, 0, or 1).
    selected_room : str | None
        Currently selected room ID, or None.

    Returns
    -------
    dict
        Plotly figure dictionary for the map graph.
    """
    if not zone_data:
        return create_map_figure(z_level=z_level)

    rooms = zone_data.get("rooms", {})
    return create_map_figure_with_rooms(rooms=rooms, z_level=z_level, selected_room=selected_room)


# =============================================================================
# New Map Modal Callbacks
# =============================================================================


@callback(
    Output("new-map-modal", "is_open", allow_duplicate=True),
    Input("new-map-btn", "n_clicks"),
    prevent_initial_call=True,
)
def open_new_map_modal(n_clicks: int) -> bool:
    """
    Open the New Map modal when the button is clicked.

    Parameters
    ----------
    n_clicks : int
        Click count for the "New Map" button.

    Returns
    -------
    bool
        True to open the modal.
    """
    if n_clicks:
        return True
    return False


@callback(
    Output("new-map-modal", "is_open", allow_duplicate=True),
    Input("new-map-cancel-btn", "n_clicks"),
    prevent_initial_call=True,
)
def close_new_map_modal(n_clicks: int) -> bool:
    """
    Close the New Map modal when Cancel is clicked.

    Parameters
    ----------
    n_clicks : int
        Click count for the Cancel button.

    Returns
    -------
    bool | no_update
        False to close the modal, or no_update if not clicked.
    """
    if n_clicks:
        return False
    return no_update


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
    """
    Create a new zone file when the Create button is clicked.

    Validates input, creates the zone data structure, saves to file,
    and refreshes the file list.

    Parameters
    ----------
    n_clicks : int
        Click count for the Create button.
    zone_id : str
        Zone ID input value.
    zone_name : str
        Zone name input value.
    description : str
        Zone description input value.

    Returns
    -------
    tuple
        (modal_open, file_list, feedback, zone_id_val, name_val, desc_val).
        On success: closes modal, updates list, clears form.
        On error: keeps modal open, shows feedback alert.

    Notes
    -----
    - Zone ID must start with letter, contain only alphanumeric + underscore
    - Zone name is required
    - File is saved as {zone_id}.json in DATA_DIR
    - Existing files are not overwritten (error shown instead)
    """
    if not n_clicks:
        return no_update, no_update, no_update, no_update, no_update, no_update

    # Normalize inputs
    zone_id = (zone_id or "").strip()
    zone_name = (zone_name or "").strip()
    description = (description or "").strip()

    # Validate zone_id
    if not zone_id:
        feedback = dbc.Alert("Zone ID is required.", color="danger", className="mb-0")
        return no_update, no_update, feedback, no_update, no_update, no_update

    if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", zone_id):
        feedback = dbc.Alert(
            "Zone ID must start with a letter and contain only "
            "letters, numbers, and underscores.",
            color="danger",
            className="mb-0",
        )
        return no_update, no_update, feedback, no_update, no_update, no_update

    # Validate zone_name
    if not zone_name:
        feedback = dbc.Alert("Zone Name is required.", color="danger", className="mb-0")
        return no_update, no_update, feedback, no_update, no_update, no_update

    # Check if file already exists
    file_path = DATA_DIR / f"{zone_id}.json"
    if file_path.exists():
        feedback = dbc.Alert(
            f"A zone with ID '{zone_id}' already exists.",
            color="warning",
            className="mb-0",
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


# =============================================================================
# Room Editing Callbacks
# =============================================================================


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
    """
    Add a new room to the current zone.

    Validates input, creates the room data structure, and adds it to
    the zone. Clears the form on success.

    Parameters
    ----------
    n_clicks : int
        Click count for the Add Room button.
    zone_data : dict | None
        Current zone data.
    room_id : str
        Room ID input value.
    room_name : str
        Room name input value.
    room_description : str
        Room description input value.
    coord_x, coord_y, coord_z : int
        Coordinate input values.

    Returns
    -------
    tuple
        Updated zone data, feedback, cleared form values, unsaved flag.

    Notes
    -----
    - Room ID must be unique within the zone
    - Room ID format: start with letter, alphanumeric + underscore
    - Coordinates must be valid integers
    - Name defaults to room_id if not provided
    """
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
            "Room ID must start with a letter and contain only " "letters, numbers, underscores.",
            color="danger",
            className="mb-0 py-2",
        )
        return (no_update, feedback) + (no_update,) * 7

    # Check for duplicate room ID
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

    # Add to zone data (create copies to trigger Dash update)
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

    # Return updated zone, clear form, mark unsaved
    return updated_zone, feedback, "", "", "", 0, 0, 0, True


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
    Output("exit-checkboxes", "value", allow_duplicate=True),
    Output("exit-feedback", "children", allow_duplicate=True),
    Input("new-room-btn", "n_clicks"),
    prevent_initial_call=True,
)
def clear_form_for_new_room(n_clicks: int):
    """
    Clear the form and deselect room when New Room button is clicked.

    Resets the properties panel to create a new room:
    - Clears all form fields
    - Deselects any selected room
    - Disables Update button
    - Enables Room ID field
    - Clears exit checkboxes

    Parameters
    ----------
    n_clicks : int
        Click count for the New Room button.

    Returns
    -------
    tuple
        Reset values for all form components.
    """
    if n_clicks:
        return "", None, "", "", "", 0, 0, 0, True, False, [], ""
    return (no_update,) * 12


@callback(
    Output("selected-room", "data"),
    Input("map-graph", "clickData"),
    State("current-zone-data", "data"),
    prevent_initial_call=True,
)
def handle_map_click(click_data: dict | None, zone_data: dict | None) -> str | None:
    """
    Select a room when it is clicked on the map.

    Extracts the room ID from the clicked point's text field and
    validates that it exists in the current zone.

    Parameters
    ----------
    click_data : dict | None
        Plotly click event data.
    zone_data : dict | None
        Current zone data.

    Returns
    -------
    str | None
        Room ID if valid room clicked, or no_update.

    Notes
    -----
    - Room ID is stored in the text field of Scatter points
    - Clicks on non-room elements (lines, empty space) are ignored
    """
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


@callback(
    Output("room-id", "value", allow_duplicate=True),
    Output("room-name", "value", allow_duplicate=True),
    Output("room-description", "value", allow_duplicate=True),
    Output("room-coord-x", "value", allow_duplicate=True),
    Output("room-coord-y", "value", allow_duplicate=True),
    Output("room-coord-z", "value", allow_duplicate=True),
    Output("exit-checkboxes", "value"),
    Output("exit-feedback", "children"),
    Output("update-room-btn", "disabled"),
    Output("room-id", "disabled"),
    Input("selected-room", "data"),
    State("current-zone-data", "data"),
    prevent_initial_call=True,
)
def populate_room_form(selected_room: str | None, zone_data: dict | None) -> tuple:
    """
    Populate the room form when a room is selected.

    Fills all form fields with the selected room's data:
    - Room ID, name, description
    - Coordinates
    - Exit checkboxes reflecting current exits
    - Exit feedback showing exit targets

    Parameters
    ----------
    selected_room : str | None
        Selected room ID, or None.
    zone_data : dict | None
        Current zone data.

    Returns
    -------
    tuple
        Form field values, checkbox values, button states.

    Notes
    -----
    - When a room is selected, Room ID is disabled (can't change ID)
    - Update button is enabled when a room is selected
    - Exit checkboxes show which directions have exits
    - Exit feedback shows "direction→target" for each exit
    """
    if not selected_room or not zone_data:
        # No room selected - reset to default state
        return (no_update,) * 6 + ([], "", True, False)

    rooms = zone_data.get("rooms", {})
    room = rooms.get(selected_room)
    if not room:
        return (no_update,) * 6 + ([], "", True, False)

    coords = room.get("coords", [0, 0, 0])

    # Build exit checkbox values from current exits
    exits = room.get("exits", {})
    exit_values = [
        DIRECTION_SHORT[direction] for direction in exits if direction in DIRECTION_SHORT
    ]

    # Build exit feedback showing targets
    if exits:
        exit_info = [
            html.Span(
                [
                    html.Span(DIRECTION_SHORT.get(direction, direction), className="fw-bold"),
                    f"→{target} ",
                ],
                className="me-2",
            )
            for direction, target in exits.items()
        ]
    else:
        exit_info = [html.Small("No exits defined", className="text-muted")]

    # Return populated form (room ID disabled, update enabled)
    return (
        room.get("id", selected_room),
        room.get("name", ""),
        room.get("description", ""),
        coords[0] if len(coords) > 0 else 0,
        coords[1] if len(coords) > 1 else 0,
        coords[2] if len(coords) > 2 else 0,
        exit_values,
        exit_info,
        False,  # Enable update button
        True,  # Disable room ID field
    )


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
    """
    Update an existing room's properties.

    Modifies the selected room's name, description, and coordinates.
    Room ID cannot be changed.

    Parameters
    ----------
    n_clicks : int
        Click count for the Update button.
    selected_room : str | None
        Selected room ID.
    zone_data : dict | None
        Current zone data.
    room_name : str
        New room name value.
    room_description : str
        New room description value.
    coord_x, coord_y, coord_z : int
        New coordinate values.

    Returns
    -------
    tuple
        Updated zone data, feedback alert, unsaved flag.
    """
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

    # Create updated zone data (copies for Dash reactivity)
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


# =============================================================================
# Exit Management Callbacks
# =============================================================================


@callback(
    Output("current-zone-data", "data", allow_duplicate=True),
    Output("exit-checkboxes", "value", allow_duplicate=True),
    Output("exit-feedback", "children", allow_duplicate=True),
    Output("has-unsaved-changes", "data", allow_duplicate=True),
    Input("exit-checkboxes", "value"),
    State("selected-room", "data"),
    State("current-zone-data", "data"),
    prevent_initial_call=True,
)
def handle_exit_changes(
    checked_values: list[str],
    selected_room: str | None,
    zone_data: dict | None,
) -> tuple:
    """
    Handle exit checkbox changes - add or remove exits.

    When an exit checkbox is checked:
    1. Find the nearest room in that direction
    2. If found, create exit and reverse exit (bidirectional)
    3. If not found, reject and show warning

    When an exit checkbox is unchecked:
    1. Remove the exit from current room only
    2. Reverse exit on target room is NOT removed (can be done manually)

    Parameters
    ----------
    checked_values : list[str]
        List of checked direction abbreviations (e.g., ["N", "E"]).
    selected_room : str | None
        Currently selected room ID.
    zone_data : dict | None
        Current zone data.

    Returns
    -------
    tuple
        Updated zone data, corrected checkbox values, feedback, unsaved flag.

    Notes
    -----
    - Uses find_room_in_direction to locate nearest room
    - OPPOSITE_DIRECTION maps direction to its reverse
    - Rejected directions (no room found) are unchecked automatically
    - Feedback shows current exits and any warnings
    """
    if not selected_room or not zone_data:
        return no_update, no_update, no_update, no_update

    rooms = zone_data.get("rooms", {})
    room = rooms.get(selected_room)
    if not room:
        return no_update, no_update, no_update, no_update

    coords = room.get("coords", [0, 0, 0])
    current_exits = room.get("exits", {})

    # Determine current checked directions from existing exits
    current_checked = {DIRECTION_SHORT[d] for d in current_exits if d in DIRECTION_SHORT}
    new_checked = set(checked_values)

    # Find what was added and removed
    added = new_checked - current_checked
    removed = current_checked - new_checked

    # If no changes, skip
    if not added and not removed:
        return no_update, no_update, no_update, no_update

    # Create updated zone data - deep copy all rooms we might modify
    updated_zone = dict(zone_data)
    updated_zone["rooms"] = {rid: dict(r) for rid, r in zone_data.get("rooms", {}).items()}
    updated_room = updated_zone["rooms"][selected_room]
    updated_exits = dict(current_exits)

    feedback_messages = []
    rejected_directions = []

    # Process removals (only remove from current room, not reverse)
    for short_dir in removed:
        direction = SHORT_TO_DIRECTION.get(short_dir)
        if direction and direction in updated_exits:
            del updated_exits[direction]
            feedback_messages.append(f"Removed {short_dir}")

    # Process additions
    for short_dir in added:
        direction = SHORT_TO_DIRECTION.get(short_dir)
        if not direction:
            continue

        # Find nearest room in that direction
        target_room_id = find_room_in_direction(
            rooms, coords, direction, exclude_room=selected_room
        )

        if target_room_id:
            # Valid exit - add it to current room
            updated_exits[direction] = target_room_id
            feedback_messages.append(f"{short_dir}→{target_room_id}")

            # Add reverse exit to target room (bidirectional by default)
            opposite_dir = OPPOSITE_DIRECTION.get(direction)
            if opposite_dir:
                target_room_data = updated_zone["rooms"][target_room_id]
                target_exits = dict(target_room_data.get("exits", {}))
                if opposite_dir not in target_exits:
                    target_exits[opposite_dir] = selected_room
                    target_room_data["exits"] = target_exits
        else:
            # No room in that direction - reject the checkbox
            rejected_directions.append(short_dir)
            feedback_messages.append(
                html.Span(
                    f"⚠️ {short_dir}: no room",
                    className="text-warning",
                )
            )

    # Update room with new exits
    updated_room["exits"] = updated_exits

    # Build final checkbox values (exclude rejected)
    final_checked = [v for v in checked_values if v not in rejected_directions]

    # Build feedback display
    if updated_exits:
        exit_info = [
            html.Span(
                [
                    html.Span(DIRECTION_SHORT.get(d, d), className="fw-bold"),
                    f"→{t} ",
                ],
                className="me-2",
            )
            for d, t in updated_exits.items()
        ]
        if rejected_directions:
            exit_info.append(html.Br())
            exit_info.extend(
                [
                    html.Span(
                        f"⚠️ No room {d} ",
                        className="text-warning small",
                    )
                    for d in rejected_directions
                ]
            )
    else:
        if rejected_directions:
            exit_info = [
                html.Span(
                    f"⚠️ No room {d} ",
                    className="text-warning small",
                )
                for d in rejected_directions
            ]
        else:
            exit_info = [html.Small("No exits defined", className="text-muted")]

    return updated_zone, final_checked, exit_info, True


# =============================================================================
# Save/Status Callbacks
# =============================================================================


@callback(
    Output("has-unsaved-changes", "data", allow_duplicate=True),
    Input("selected-file", "data"),
    prevent_initial_call=True,
)
def reset_unsaved_on_file_load(selected_file: str | None) -> bool:
    """
    Reset unsaved changes flag when a new file is loaded.

    Parameters
    ----------
    selected_file : str | None
        Newly selected file name.

    Returns
    -------
    bool
        False to indicate no unsaved changes.
    """
    return False


@callback(
    Output("save-map-btn", "disabled"),
    Output("status-indicator", "children"),
    Input("has-unsaved-changes", "data"),
    Input("selected-file", "data"),
)
def update_save_status(has_unsaved: bool, selected_file: str | None) -> tuple:
    """
    Update save button state and status indicator.

    Shows appropriate status based on current state:
    - No file loaded: gray dot, disabled save
    - Unsaved changes: yellow dot, enabled save
    - All saved: green dot, disabled save

    Parameters
    ----------
    has_unsaved : bool
        Whether there are unsaved changes.
    selected_file : str | None
        Currently selected file name.

    Returns
    -------
    tuple
        (save_disabled, status_children).
    """
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


@callback(
    Output("has-unsaved-changes", "data", allow_duplicate=True),
    Output("room-form-feedback", "children", allow_duplicate=True),
    Input("save-map-btn", "n_clicks"),
    State("current-zone-data", "data"),
    State("selected-file", "data"),
    prevent_initial_call=True,
)
def save_zone_to_file(n_clicks: int, zone_data: dict | None, selected_file: str | None) -> tuple:
    """
    Save the current zone data to the file.

    Parameters
    ----------
    n_clicks : int
        Click count for Save button.
    zone_data : dict | None
        Current zone data to save.
    selected_file : str | None
        Target file name.

    Returns
    -------
    tuple
        (unsaved_flag, feedback_alert).
        On success: False and success message.
        On error: no_update and error message.
    """
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


# =============================================================================
# Application Entry Point
# =============================================================================


def run_app(debug: bool = True, port: int = 8050) -> None:
    """
    Run the Dash application.

    Starts the Flask development server and opens the mapper
    application in the browser.

    Parameters
    ----------
    debug : bool, optional
        Enable debug mode with auto-reload (default: True).
        Set to False for production deployments.
    port : int, optional
        Port to run the server on (default: 8050).

    Examples
    --------
    Run with defaults::

        >>> from pipeworks_mud_mapper.app import run_app
        >>> run_app()

    Run on different port::

        >>> run_app(debug=False, port=8080)

    Notes
    -----
    - In debug mode, the server auto-reloads on code changes
    - Access the application at http://127.0.0.1:{port}
    - Press Ctrl+C to stop the server
    """
    print("\n  PipeWorks MUD Mapper")
    print(f"  Running on http://127.0.0.1:{port}")
    print("  Press Ctrl+C to quit\n")
    app.run(debug=debug, port=port)


if __name__ == "__main__":
    run_app()
