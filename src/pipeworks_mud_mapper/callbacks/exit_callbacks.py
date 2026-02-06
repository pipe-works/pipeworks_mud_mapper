"""Exit management callbacks.

This module handles both:

- Local exit checkbox changes (bidirectional exits within a zone)
- Cross-zone exit edits via the Workspace table/editor (zone_id:room_id)

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
- ``workspace-zone-exit-direction``: Selected direction for zone exits
- ``workspace-zone-exit-zone``: Selected zone for cross-zone exit
- ``workspace-zone-exit-room``: Selected room for cross-zone exit
- ``workspace-zone-exit-save``: Persist the zone exit selection
- ``workspace-zone-exit-clear``: Remove a zone exit from a direction

**States:**
- ``selected-room``: Currently selected room
- ``current-zone-data``: Zone data for room lookup + mutation

**Outputs:**
- ``current-zone-data``: Updated with new exits
- ``exit-checkboxes``: Corrected values (rejected unchecked)
- ``exit-feedback``: Status display
- ``workspace-zone-exit-table``: Zone exit summary table
- ``workspace-zone-exit-feedback``: Status display for cross-zone exits
- ``has-unsaved-changes``: Unsaved flag

See Also
--------
- ``services/state``: Exit state transitions via the state manager
- ``models/room.py``: Direction constants
"""

import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, callback, ctx, html, no_update

from pipeworks_mud_mapper.models.room import DIRECTION_SHORT, SHORT_TO_DIRECTION, Direction
from pipeworks_mud_mapper.services.exit_utils import (
    EXIT_SHORT_ORDER,
    format_zone_exit,
    parse_zone_exit,
    split_exits_by_scope,
)
from pipeworks_mud_mapper.services.state import ZoneAction, apply_zone_action
from pipeworks_mud_mapper.services.world_service import load_world_zone_ids, load_zone_room_ids


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


def _zone_exit_alert(message: str, color: str = "info") -> dbc.Alert:
    """Build a compact alert for zone exit actions."""
    return dbc.Alert(message, color=color, className="mb-0 py-1", duration=4000)


def _build_zone_exit_rows(exits: dict[Direction, str] | None) -> list[dict[str, str]]:
    """Summarize zone exits into ordered row data for the workspace table."""
    _, zone_exits = split_exits_by_scope(exits or {})
    rows: list[dict[str, str]] = []
    used_directions: set[Direction] = set()

    # Preserve the UI order so authors see a predictable N/E/S/W/U/D list.
    for short_dir in EXIT_SHORT_ORDER:
        direction = SHORT_TO_DIRECTION.get(short_dir)
        if not direction:
            continue
        target = zone_exits.get(direction)
        if not target:
            continue
        zone_id, room_id = parse_zone_exit(target)
        rows.append(
            {
                "direction_short": short_dir,
                "zone_id": zone_id or "—",
                "room_id": room_id or "—",
                "target": target,
            }
        )
        used_directions.add(direction)

    # Append any unexpected directions so malformed data is still visible.
    for direction, target in zone_exits.items():
        if direction in used_directions:
            continue
        short_dir = DIRECTION_SHORT.get(direction, str(direction).upper()[:1])
        zone_id, room_id = parse_zone_exit(target)
        rows.append(
            {
                "direction_short": short_dir,
                "zone_id": zone_id or "—",
                "room_id": room_id or "—",
                "target": target,
            }
        )

    return rows


@callback(
    Output("workspace-zone-exit-zone", "options"),
    Input("initial-load", "n_intervals"),
    prevent_initial_call=True,
)
def load_workspace_zone_exit_zone_options(_: int | None) -> list[dict[str, str]]:
    """Load zone options from world metadata for the workspace editor."""
    zone_ids = load_world_zone_ids()
    return [{"label": zone_id, "value": zone_id} for zone_id in zone_ids]


@callback(
    Output("workspace-zone-exit-room", "options"),
    Output("workspace-zone-exit-room", "disabled"),
    Input("workspace-zone-exit-zone", "value"),
    State("workspace-zone-exit-room", "value"),
)
def update_workspace_zone_exit_room_options(
    zone_id: str | None,
    current_room: str | None,
) -> tuple[list[dict[str, str]], bool]:
    """Update room options when the selected zone changes."""
    if not zone_id:
        return [], True

    rooms = load_zone_room_ids(zone_id)
    options = [{"label": room, "value": room} for room in rooms]

    # Preserve the current room selection if it's missing from options.
    if current_room and all(opt["value"] != current_room for opt in options):
        options.append({"label": f"{current_room} (unlisted)", "value": current_room})

    return options, False


@callback(
    Output("workspace-zone-exit-table", "children"),
    Input("selected-room", "data"),
    Input("current-zone-data", "data"),
    prevent_initial_call=False,
)
def update_workspace_zone_exit_table(
    selected_room: str | None,
    zone_data: dict | None,
) -> html.Div:
    """Render the zone exit table for the selected room."""
    if not selected_room:
        return html.Div(
            "Select a room to inspect zone exits.",
            className="text-muted small",
        )

    if not zone_data:
        return html.Div(
            "Zone data is unavailable.",
            className="text-muted small",
        )

    room = zone_data.get("rooms", {}).get(selected_room)
    if not room:
        return html.Div(
            "Selected room not found in the active map.",
            className="text-muted small",
        )

    rows = _build_zone_exit_rows(room.get("exits", {}))
    if not rows:
        return html.Div(
            "No zone exits defined for this room.",
            className="text-muted small",
        )

    table_rows = []
    for row in rows:
        direction_short = row["direction_short"]
        row_kwargs: dict[str, object] = {}
        if direction_short in EXIT_SHORT_ORDER:
            # Only allow editing standard directions from the table.
            row_kwargs = {
                "id": {"type": "workspace-zone-exit-row", "direction": direction_short},
                "style": {"cursor": "pointer"},
                "n_clicks": 0,
                "title": "Click to edit zone exit",
            }

        table_rows.append(
            html.Tr(
                [
                    html.Td(direction_short),
                    html.Td(row["zone_id"]),
                    html.Td(row["room_id"]),
                    html.Td(row["target"]),
                ],
                **row_kwargs,
            )
        )

    return dbc.Table(
        [
            html.Thead(
                html.Tr(
                    [
                        html.Th("Dir"),
                        html.Th("Zone"),
                        html.Th("Room"),
                        html.Th("Target"),
                    ]
                )
            ),
            html.Tbody(table_rows),
        ],
        bordered=True,
        hover=True,
        size="sm",
        className="small mb-0",
    )


@callback(
    Output("workspace-zone-exit-direction", "value"),
    Output("workspace-zone-exit-zone", "value"),
    Output("workspace-zone-exit-room", "value"),
    Input("selected-room", "data"),
    Input({"type": "workspace-zone-exit-row", "direction": ALL}, "n_clicks"),
    State("current-zone-data", "data"),
    prevent_initial_call=True,
)
def populate_workspace_zone_exit_editor(
    selected_room: str | None,
    row_clicks: list[int],
    zone_data: dict | None,
) -> tuple[str | None, str | None, str | None]:
    """Populate the zone exit editor from table clicks."""
    trigger = ctx.triggered_id

    # When switching rooms, clear the editor to avoid stale selections.
    if trigger == "selected-room":
        return None, None, None

    if not selected_room or not zone_data or not any(row_clicks):
        return no_update, no_update, no_update

    if not isinstance(trigger, dict):
        return no_update, no_update, no_update

    direction_short = trigger.get("direction")
    if direction_short not in EXIT_SHORT_ORDER:
        return no_update, no_update, no_update

    direction = SHORT_TO_DIRECTION.get(direction_short)
    if not direction:
        return no_update, no_update, no_update

    room = zone_data.get("rooms", {}).get(selected_room)
    if not room:
        return no_update, no_update, no_update

    _, zone_exits = split_exits_by_scope(room.get("exits", {}))
    target = zone_exits.get(direction)
    zone_id, room_id = parse_zone_exit(target)

    return direction_short, zone_id, room_id


@callback(
    Output("workspace-zone-exit-feedback", "children", allow_duplicate=True),
    Input("selected-room", "data"),
    prevent_initial_call=True,
)
def clear_workspace_zone_exit_feedback(_: str | None) -> html.Div:
    """Clear action feedback when the selected room changes."""
    return html.Div()


@callback(
    Output("current-zone-data", "data", allow_duplicate=True),
    Output("workspace-zone-exit-feedback", "children", allow_duplicate=True),
    Output("has-unsaved-changes", "data", allow_duplicate=True),
    Input("workspace-zone-exit-save", "n_clicks"),
    Input("workspace-zone-exit-clear", "n_clicks"),
    State("workspace-zone-exit-direction", "value"),
    State("workspace-zone-exit-zone", "value"),
    State("workspace-zone-exit-room", "value"),
    State("selected-room", "data"),
    State("current-zone-data", "data"),
    prevent_initial_call=True,
)
def handle_workspace_zone_exit_action(
    save_clicks: int | None,
    clear_clicks: int | None,
    direction_short: str | None,
    zone_id: str | None,
    room_id: str | None,
    selected_room: str | None,
    zone_data: dict | None,
) -> tuple:
    """Apply workspace zone exit changes to the active map."""
    trigger = ctx.triggered_id
    if trigger not in {"workspace-zone-exit-save", "workspace-zone-exit-clear"}:
        return no_update, no_update, no_update

    if not selected_room or not zone_data:
        return (
            no_update,
            _zone_exit_alert("Select a room before editing zone exits.", "warning"),
            no_update,
        )

    if direction_short not in EXIT_SHORT_ORDER:
        return no_update, _zone_exit_alert("Choose a direction to edit.", "warning"), no_update

    direction = SHORT_TO_DIRECTION.get(direction_short)
    if not direction:
        return no_update, _zone_exit_alert("Invalid direction selection.", "warning"), no_update

    rooms = zone_data.get("rooms", {})
    room = rooms.get(selected_room)
    if not room:
        return no_update, _zone_exit_alert("Selected room not found.", "warning"), no_update

    current_exits = room.get("exits", {})
    local_exits, zone_exits = split_exits_by_scope(current_exits)

    if trigger == "workspace-zone-exit-save":
        if not zone_id or not room_id:
            return (
                no_update,
                _zone_exit_alert("Select both a zone and a room.", "warning"),
                no_update,
            )

        if direction in local_exits:
            return (
                no_update,
                _zone_exit_alert(
                    f"{direction_short}: remove the local exit before adding a zone exit.",
                    "warning",
                ),
                no_update,
            )

        desired_target = format_zone_exit(zone_id, room_id)
        existing_target = zone_exits.get(direction)
        if desired_target == existing_target:
            return (
                no_update,
                _zone_exit_alert("Zone exit already set for that direction.", "info"),
                no_update,
            )

        # Clone zone data before mutation so Dash sees a new object and
        # room state updates remain predictable.
        updated_zone = dict(zone_data)
        updated_zone["rooms"] = {rid: dict(r) for rid, r in rooms.items()}
        updated_room = updated_zone["rooms"][selected_room]
        updated_exits = dict(current_exits)
        updated_exits[direction] = desired_target
        updated_room["exits"] = updated_exits

        return (
            updated_zone,
            _zone_exit_alert(
                f"Saved {direction_short} → {desired_target}",
                "success",
            ),
            True,
        )

    # Clear action removes only zone exits, leaving any local exit intact.
    existing_target = zone_exits.get(direction)
    if not existing_target:
        return (
            no_update,
            _zone_exit_alert("No zone exit set for that direction.", "info"),
            no_update,
        )

    # Clone zone data before mutation so the store updates cleanly.
    updated_zone = dict(zone_data)
    updated_zone["rooms"] = {rid: dict(r) for rid, r in rooms.items()}
    updated_room = updated_zone["rooms"][selected_room]
    updated_exits = dict(current_exits)
    del updated_exits[direction]
    updated_room["exits"] = updated_exits

    return (
        updated_zone,
        _zone_exit_alert(f"Cleared {direction_short} zone exit.", "secondary"),
        True,
    )
