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
- ``services/state``: Exit state transitions via the state manager
- ``models/room.py``: Direction constants
"""

from dash import Input, Output, State, callback, no_update

from pipeworks_mud_mapper.services.state import ZoneAction, apply_zone_action


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
    action = ZoneAction(
        type="EXIT_CHANGE",
        payload={
            "selected_room": selected_room,
            "checked_values": checked_values,
        },
    )
    transition = apply_zone_action(zone_data, action)

    if not transition.changed or transition.zone_data is None:
        return no_update, no_update, no_update, no_update

    final_checked = transition.effects.get("exit_values", no_update)
    exit_info = transition.effects.get("exit_feedback", no_update)

    return transition.zone_data, final_checked, exit_info, True
