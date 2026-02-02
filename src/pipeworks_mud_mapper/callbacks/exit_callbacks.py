"""Exit management callbacks.

This module handles exit checkbox changes, implementing bidirectional
exit creation when connecting rooms.

Design Decisions
----------------
**Bidirectional by default**: When an exit checkbox is checked and a
target room is found, both the forward and reverse exits are created.
This matches player expectations in MUDs.

**No room = rejected**: If no room exists in the checked direction,
the checkbox is automatically unchecked and a warning is shown.

**Removal is one-way**: When unchecking an exit, only the exit from
the current room is removed. The reverse exit on the target room
remains (can be manually removed if needed).

Component Dependencies
----------------------
**Inputs:**
- ``exit-checkboxes``: Checklist of direction abbreviations

**States:**
- ``selected-room``: Currently selected room
- ``current-zone-data``: Zone data for room lookup

**Outputs:**
- ``current-zone-data``: Updated with new exits
- ``exit-checkboxes``: Corrected values (rejected unchecked)
- ``exit-feedback``: Status display
- ``has-unsaved-changes``: Unsaved flag

See Also
--------
- ``services/room_service.py``: Exit business logic
- ``utils/zone_io.py``: Direction constants
"""

from dash import Input, Output, State, callback, html, no_update

from pipeworks_mud_mapper.utils.zone_io import (
    DIRECTION_SHORT,
    OPPOSITE_DIRECTION,
    SHORT_TO_DIRECTION,
    find_room_in_direction,
)


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
    """Handle exit checkbox changes - add or remove exits.

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
