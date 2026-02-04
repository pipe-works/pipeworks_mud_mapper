"""Exit-related zone state transitions.

These helpers encapsulate the exit checkbox logic so callbacks can delegate
all zone mutations to the state manager.
"""

from __future__ import annotations

from typing import Any

from dash import html

from pipeworks_mud_mapper.services.state.types import ZoneTransition
from pipeworks_mud_mapper.utils.zone_io import (
    DIRECTION_SHORT,
    OPPOSITE_DIRECTION,
    SHORT_TO_DIRECTION,
    find_room_in_direction,
)


def apply_exit_changes(
    *,
    zone_data: dict | None,
    selected_room: str | None,
    checked_values: list[str],
) -> ZoneTransition:
    """Apply exit checkbox changes to the zone.

    Returns a ZoneTransition with extra effects for checkbox values and feedback UI.
    """
    if not selected_room or not zone_data:
        return ZoneTransition(zone_data=None, changed=False)

    rooms = zone_data.get("rooms", {})
    room = rooms.get(selected_room)
    if not room:
        return ZoneTransition(zone_data=None, changed=False)

    coords = room.get("coords", [0, 0, 0])
    current_exits = room.get("exits", {})

    current_checked = {DIRECTION_SHORT[d] for d in current_exits if d in DIRECTION_SHORT}
    new_checked = set(checked_values)

    added = new_checked - current_checked
    removed = current_checked - new_checked

    if not added and not removed:
        return ZoneTransition(zone_data=None, changed=False)

    updated_zone = dict(zone_data)
    updated_zone["rooms"] = {rid: dict(r) for rid, r in zone_data.get("rooms", {}).items()}
    updated_room = updated_zone["rooms"][selected_room]
    updated_exits = dict(current_exits)

    feedback_messages: list[str] = []
    rejected_directions: list[str] = []

    for short_dir in removed:
        direction = SHORT_TO_DIRECTION.get(short_dir)
        if direction and direction in updated_exits:
            del updated_exits[direction]
            feedback_messages.append(f"Removed {short_dir}")

    for short_dir in added:
        direction = SHORT_TO_DIRECTION.get(short_dir)
        if not direction:
            continue

        target_room_id = find_room_in_direction(
            rooms, coords, direction, exclude_room=selected_room
        )

        if target_room_id:
            updated_exits[direction] = target_room_id
            feedback_messages.append(f"{short_dir}→{target_room_id}")

            opposite_dir = OPPOSITE_DIRECTION.get(direction)
            if opposite_dir:
                target_room_data = updated_zone["rooms"][target_room_id]
                target_exits = dict(target_room_data.get("exits", {}))
                if opposite_dir not in target_exits:
                    target_exits[opposite_dir] = selected_room
                    target_room_data["exits"] = target_exits
        else:
            rejected_directions.append(short_dir)
            feedback_messages.append(f"⚠️ {short_dir}: no room")

    updated_room["exits"] = updated_exits

    final_checked = [v for v in checked_values if v not in rejected_directions]

    exit_info: list[Any] = []
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

    return ZoneTransition(
        zone_data=updated_zone,
        feedback=None,
        unsaved=True,
        effects={
            "exit_values": final_checked,
            "exit_feedback": exit_info,
        },
        changed=True,
    )
