"""Room editing callbacks.

This module handles:

- Adding new rooms to the zone
- Clearing the form for new room entry
- Populating the form when a room is selected
- Updating existing room properties

Component Dependencies
----------------------
**Inputs:**
- ``add-room-btn``: Add new room button
- ``new-room-btn``: Clear form for new room
- ``selected-room``: Room selection trigger
- ``update-room-btn``: Update existing room

**States:**
- ``current-zone-data``: Current zone data
- ``room-id``, ``room-name``, ``room-description``: Form fields
- ``room-coord-x``, ``room-coord-y``, ``room-coord-z``: Coordinates

**Outputs:**
- ``current-zone-data``: Updated zone data
- ``room-form-feedback``: Validation messages
- Form fields: Populated or cleared values
- ``has-unsaved-changes``: Unsaved flag
- ``exit-checkboxes``: Exit state
- ``exit-feedback``: Exit display

See Also
--------
- ``services/room_service.py``: Room business logic
"""

import re

import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, html, no_update

from pipeworks_mud_mapper.utils.zone_io import DIRECTION_SHORT


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
    """Add a new room to the current zone.

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
            "Room ID must start with a letter and contain only letters, numbers, underscores.",
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
    """Clear the form and deselect room when New Room button is clicked.

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
    """Populate the room form when a room is selected.

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
        exit_info = [html.Span(html.Small("No exits defined", className="text-muted"))]

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
    """Update an existing room's properties.

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
