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
- ``services/state``: Room state transitions via the state manager
"""

import time
from typing import Any

from dash import Input, Output, State, callback, html, no_update

from pipeworks_mud_mapper.models.room import DIRECTION_SHORT
from pipeworks_mud_mapper.services.exit_utils import split_exits_by_scope
from pipeworks_mud_mapper.services.state import ZoneAction, apply_zone_action


def _room_feedback_payload(content: Any) -> dict[str, Any]:
    """Build a timestamped payload for room form feedback."""
    return {"content": content, "ts": time.monotonic()}


@callback(
    Output("current-zone-data", "data", allow_duplicate=True),
    Output("room-feedback-add", "data"),
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
    action = ZoneAction(
        type="ADD_ROOM",
        payload={
            "room_id": room_id,
            "room_name": room_name,
            "room_description": room_description,
            "coord_x": coord_x,
            "coord_y": coord_y,
            "coord_z": coord_z,
        },
    )
    transition = apply_zone_action(zone_data, action)

    zone_out = transition.zone_data if transition.zone_data is not None else no_update
    feedback_out = (
        _room_feedback_payload(transition.feedback)
        if transition.feedback is not None
        else no_update
    )
    unsaved_out = transition.unsaved if transition.unsaved is not None else no_update

    if transition.changed:
        return zone_out, feedback_out, "", "", "", 0, 0, 0, unsaved_out

    return (zone_out, feedback_out) + (no_update,) * 7


@callback(
    Output("room-feedback-new", "data"),
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
        return _room_feedback_payload(""), None, "", "", "", 0, 0, 0, True, False, [], ""
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

    # Build exit checkbox values from local (same-zone) exits only.
    # Cross-zone exits are rendered and edited in a separate section.
    exits = room.get("exits", {})
    local_exits, _ = split_exits_by_scope(exits)
    exit_values = [
        DIRECTION_SHORT[direction] for direction in local_exits if direction in DIRECTION_SHORT
    ]

    # Build exit feedback showing targets
    if local_exits:
        exit_info = [
            html.Span(
                [
                    html.Span(DIRECTION_SHORT.get(direction, direction), className="fw-bold"),
                    f"→{target} ",
                ],
                className="me-2",
            )
            for direction, target in local_exits.items()
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
    Output("room-feedback-update", "data"),
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
    action = ZoneAction(
        type="UPDATE_ROOM",
        payload={
            "selected_room": selected_room,
            "room_name": room_name,
            "room_description": room_description,
            "coord_x": coord_x,
            "coord_y": coord_y,
            "coord_z": coord_z,
        },
    )
    transition = apply_zone_action(zone_data, action)

    zone_out = transition.zone_data if transition.zone_data is not None else no_update
    feedback_out = (
        _room_feedback_payload(transition.feedback)
        if transition.feedback is not None
        else no_update
    )
    unsaved_out = transition.unsaved if transition.unsaved is not None else no_update

    if transition.changed:
        print(
            f"[DEBUG] update_room_properties: setting has_unsaved=True for room '{selected_room}'"
        )

    return zone_out, feedback_out, unsaved_out


# =============================================================================
# Delete Room Callbacks
# =============================================================================


@callback(
    Output("delete-room-btn", "disabled"),
    Input("selected-room", "data"),
    State("current-zone-data", "data"),
)
def update_delete_button_state(selected_room: str | None, zone_data: dict | None) -> bool:
    """Enable/disable delete button based on selection.

    Delete is disabled when:
    - No room is selected
    - Selected room is the spawn room

    Parameters
    ----------
    selected_room : str | None
        Currently selected room ID.
    zone_data : dict | None
        Current zone data.

    Returns
    -------
    bool
        True if delete should be disabled.
    """
    if not selected_room or not zone_data:
        return True

    # Can't delete spawn room
    spawn_room = zone_data.get("spawn_room")
    if selected_room == spawn_room:
        return True

    return False


@callback(
    Output("delete-confirm-modal", "is_open", allow_duplicate=True),
    Output("delete-confirm-body", "children"),
    Input("delete-room-btn", "n_clicks"),
    State("selected-room", "data"),
    State("current-zone-data", "data"),
    prevent_initial_call=True,
)
def open_delete_confirmation(
    n_clicks: int, selected_room: str | None, zone_data: dict | None
) -> tuple:
    """Open delete confirmation dialog with details.

    Shows the room name and how many exits from other rooms will be removed.

    Parameters
    ----------
    n_clicks : int
        Click count for delete button.
    selected_room : str | None
        Room to delete.
    zone_data : dict | None
        Current zone data.

    Returns
    -------
    tuple
        (modal_open, body_content).
    """
    if not n_clicks or not selected_room or not zone_data:
        return False, ""

    rooms = zone_data.get("rooms", {})
    room = rooms.get(selected_room, {})
    room_name = room.get("name", selected_room)

    # Count exits from OTHER rooms that point to this room
    incoming_exits = []
    for room_id, other_room in rooms.items():
        if room_id == selected_room:
            continue
        for direction, target in other_room.get("exits", {}).items():
            if target == selected_room:
                incoming_exits.append((room_id, direction))

    # Build confirmation message
    message_parts = [
        html.P(
            [
                "Are you sure you want to delete room ",
                html.Strong(f"'{room_name}'"),
                f" ({selected_room})?",
            ]
        ),
    ]

    if incoming_exits:
        exit_list = [html.Li(f"{room_id} → {direction}") for room_id, direction in incoming_exits]
        message_parts.append(
            html.Div(
                [
                    html.P(
                        f"This will also remove {len(incoming_exits)} exit(s) from other rooms:",
                        className="mb-1 text-warning",
                    ),
                    html.Ul(exit_list, className="small mb-0"),
                ],
                className="mt-2 p-2 bg-light rounded",
            )
        )

    message_parts.append(
        html.P(
            [
                html.I(className="bi bi-info-circle me-1"),
                "You can undo this action before saving.",
            ],
            className="mt-3 mb-0 small text-muted",
        )
    )

    return True, message_parts


@callback(
    Output("delete-confirm-modal", "is_open", allow_duplicate=True),
    Input("delete-cancel-btn", "n_clicks"),
    prevent_initial_call=True,
)
def close_delete_confirmation(n_clicks: int):
    """Close delete confirmation modal on cancel."""
    if n_clicks:
        return False
    return no_update


@callback(
    Output("current-zone-data", "data", allow_duplicate=True),
    Output("selected-room", "data", allow_duplicate=True),
    Output("delete-confirm-modal", "is_open"),
    Output("delete-undo-data", "data"),
    Output("undo-delete-container", "style"),
    Output("has-unsaved-changes", "data", allow_duplicate=True),
    Output("room-feedback-delete", "data"),
    Input("delete-confirm-btn", "n_clicks"),
    State("selected-room", "data"),
    State("current-zone-data", "data"),
    prevent_initial_call=True,
)
def confirm_delete_room(n_clicks: int, selected_room: str | None, zone_data: dict | None) -> tuple:
    """Delete the room and store undo data.

    Parameters
    ----------
    n_clicks : int
        Click count for confirm button.
    selected_room : str | None
        Room to delete.
    zone_data : dict | None
        Current zone data.

    Returns
    -------
    tuple
        Updated zone, cleared selection, modal closed, undo data,
        undo container style, unsaved flag, feedback.
    """
    if not n_clicks:
        return (no_update,) * 7

    action = ZoneAction(
        type="DELETE_ROOM",
        payload={
            "selected_room": selected_room,
        },
    )
    transition = apply_zone_action(zone_data, action)

    if not transition.changed or transition.zone_data is None:
        return (no_update,) * 7

    undo_data = transition.effects.get("undo_data")
    feedback_out = (
        _room_feedback_payload(transition.feedback)
        if transition.feedback is not None
        else no_update
    )

    print(f"[DEBUG] confirm_delete_room: deleted room '{selected_room}'")

    return (
        transition.zone_data,
        None,
        False,
        undo_data,
        {"display": "block"},
        True,
        feedback_out,
    )


@callback(
    Output("current-zone-data", "data", allow_duplicate=True),
    Output("delete-undo-data", "data", allow_duplicate=True),
    Output("undo-delete-container", "style", allow_duplicate=True),
    Output("room-feedback-undo", "data"),
    Input("undo-delete-btn", "n_clicks"),
    State("delete-undo-data", "data"),
    State("current-zone-data", "data"),
    prevent_initial_call=True,
)
def undo_delete_room(n_clicks: int, undo_data: dict | None, zone_data: dict | None) -> tuple:
    """Restore a deleted room from undo data.

    Parameters
    ----------
    n_clicks : int
        Click count for undo button.
    undo_data : dict | None
        Stored undo data with room and exit info.
    zone_data : dict | None
        Current zone data.

    Returns
    -------
    tuple
        Updated zone, cleared undo data, hidden undo container, feedback.
    """
    if not n_clicks:
        return (no_update,) * 4

    action = ZoneAction(
        type="UNDO_DELETE",
        payload={
            "undo_data": undo_data,
        },
    )
    transition = apply_zone_action(zone_data, action)

    if not transition.changed or transition.zone_data is None:
        return (no_update,) * 4

    feedback_out = (
        _room_feedback_payload(transition.feedback)
        if transition.feedback is not None
        else no_update
    )

    restored_id = undo_data.get("room_id") if isinstance(undo_data, dict) else "unknown"
    print(f"[DEBUG] undo_delete_room: restored room '{restored_id}'")

    return (
        transition.zone_data,
        None,
        {"display": "none"},
        feedback_out,
    )


def _latest_room_feedback(payloads: list[dict | None]) -> dict | None:
    """Return the most recent room feedback payload from a list."""
    latest: dict | None = None
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        timestamp = payload.get("ts")
        if timestamp is None:
            continue
        if latest is None or timestamp > latest.get("ts", -1):
            latest = payload
    return latest


@callback(
    Output("room-form-feedback", "children"),
    Input("room-feedback-add", "data"),
    Input("room-feedback-new", "data"),
    Input("room-feedback-update", "data"),
    Input("room-feedback-delete", "data"),
    Input("room-feedback-undo", "data"),
    Input("room-feedback-save", "data"),
    Input("room-feedback-export", "data"),
)
def render_room_form_feedback(*payloads: dict | None) -> Any:
    """Render the latest room feedback payload from any source."""
    latest = _latest_room_feedback(list(payloads))
    if not latest:
        return no_update

    content = latest.get("content")
    if content is None:
        return no_update

    return content
