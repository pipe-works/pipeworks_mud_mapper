"""Exit-related zone state transitions.

These helpers encapsulate the exit checkbox logic so callbacks can delegate
all zone mutations to the state manager.
"""

from __future__ import annotations

from typing import Any

from dash import html

from pipeworks_mud_mapper.models.room import (
    DIRECTION_OFFSETS,
    DIRECTION_SHORT,
    OPPOSITE_DIRECTION,
    SHORT_TO_DIRECTION,
    Direction,
)
from pipeworks_mud_mapper.services.state.types import ZoneTransition


def _find_room_in_direction(
    rooms: dict[str, dict],
    from_coords: list[int],
    direction: Direction,
    *,
    exclude_room: str | None = None,
) -> str | None:
    """Find the nearest room ID in a cardinal direction from coordinates."""
    dx, dy, dz = DIRECTION_OFFSETS[direction]
    fx, fy, fz = from_coords

    candidates: list[tuple[int, str]] = []
    for room_id, room_data in rooms.items():
        if exclude_room and room_id == exclude_room:
            continue

        coords = room_data.get("coords", [0, 0, 0])
        if not isinstance(coords, list) or len(coords) < 3:
            continue

        rx, ry, rz = coords[0], coords[1], coords[2]

        in_direction = True
        if dx != 0:
            if dx > 0 and rx <= fx:
                in_direction = False
            elif dx < 0 and rx >= fx:
                in_direction = False
            elif ry != fy or rz != fz:
                in_direction = False
        elif dy != 0:
            if dy > 0 and ry <= fy:
                in_direction = False
            elif dy < 0 and ry >= fy:
                in_direction = False
            elif rx != fx or rz != fz:
                in_direction = False
        elif dz != 0:
            if dz > 0 and rz <= fz:
                in_direction = False
            elif dz < 0 and rz >= fz:
                in_direction = False
            elif rx != fx or ry != fy:
                in_direction = False

        if in_direction:
            distance = abs(rx - fx) + abs(ry - fy) + abs(rz - fz)
            candidates.append((distance, room_id))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


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

        target_room_id = _find_room_in_direction(
            rooms,
            coords,
            direction,
            exclude_room=selected_room,
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
