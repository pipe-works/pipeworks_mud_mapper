"""Room-related zone state transitions.

These helpers implement the mutations for add/update/delete/undo
room actions. The logic mirrors the prior callback implementations,
while returning a structured ZoneTransition result for the state manager.
"""

from __future__ import annotations

from typing import Any

import dash_bootstrap_components as dbc
from dash import html

from pipeworks_mud_mapper.services.state.types import ZoneTransition


def add_room(
    *,
    zone_data: dict | None,
    room_id: str | None,
    room_name: str | None,
    room_description: str | None,
    coord_x: Any,
    coord_y: Any,
    coord_z: Any,
) -> ZoneTransition:
    """Add a new room to the zone.

    Returns a ZoneTransition with feedback when validation fails.
    """
    if not zone_data:
        feedback = dbc.Alert(
            "No zone loaded. Create or select a zone first.",
            color="warning",
            className="mb-0 py-2",
        )
        return ZoneTransition(zone_data=None, feedback=feedback, changed=False)

    room_id = (room_id or "").strip()
    if not room_id:
        feedback = dbc.Alert(
            "Room ID is required.",
            color="danger",
            className="mb-0 py-2",
        )
        return ZoneTransition(zone_data=None, feedback=feedback, changed=False)

    if not room_id[0].isalpha() or not room_id.replace("_", "").isalnum():
        feedback = dbc.Alert(
            "Room ID must start with a letter and contain only letters, numbers, and underscores.",
            color="danger",
            className="mb-0 py-2",
        )
        return ZoneTransition(zone_data=None, feedback=feedback, changed=False)

    rooms = zone_data.get("rooms", {})
    if room_id in rooms:
        feedback = dbc.Alert(
            f"Room '{room_id}' already exists.",
            color="warning",
            className="mb-0 py-2",
        )
        return ZoneTransition(zone_data=None, feedback=feedback, changed=False)

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
        return ZoneTransition(zone_data=None, feedback=feedback, changed=False)

    new_room = {
        "id": room_id,
        "name": (room_name or "").strip() or room_id,
        "description": (room_description or "").strip(),
        "coords": [x, y, z],
        "exits": {},
        "items": [],
    }

    updated_zone = dict(zone_data)
    updated_zone["rooms"] = dict(zone_data.get("rooms", {}))
    updated_zone["rooms"][room_id] = new_room

    feedback = dbc.Alert(
        f"Room '{room_id}' added at ({x}, {y}, {z})",
        color="success",
        className="mb-0 py-2",
        duration=3000,
    )

    return ZoneTransition(
        zone_data=updated_zone,
        feedback=feedback,
        unsaved=True,
        changed=True,
    )


def update_room(
    *,
    zone_data: dict | None,
    selected_room: str | None,
    room_name: str | None,
    room_description: str | None,
    coord_x: Any,
    coord_y: Any,
    coord_z: Any,
) -> ZoneTransition:
    """Update an existing room's properties."""
    if not zone_data or not selected_room:
        feedback = dbc.Alert(
            "No room selected to update.",
            color="warning",
            className="mb-0 py-2",
        )
        return ZoneTransition(zone_data=None, feedback=feedback, changed=False)

    rooms = zone_data.get("rooms", {})
    if selected_room not in rooms:
        feedback = dbc.Alert(
            f"Room '{selected_room}' not found.",
            color="danger",
            className="mb-0 py-2",
        )
        return ZoneTransition(zone_data=None, feedback=feedback, changed=False)

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
        return ZoneTransition(zone_data=None, feedback=feedback, changed=False)

    updated_zone = dict(zone_data)
    updated_zone["rooms"] = dict(zone_data.get("rooms", {}))
    updated_room = dict(rooms[selected_room])

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

    return ZoneTransition(
        zone_data=updated_zone,
        feedback=feedback,
        unsaved=True,
        changed=True,
    )


def delete_room(
    *,
    zone_data: dict | None,
    selected_room: str | None,
) -> ZoneTransition:
    """Delete a room and collect undo metadata."""
    if not zone_data or not selected_room:
        return ZoneTransition(zone_data=None, changed=False)

    rooms = zone_data.get("rooms", {})
    if selected_room not in rooms:
        return ZoneTransition(zone_data=None, changed=False)

    deleted_room = dict(rooms[selected_room])

    removed_exits: list[dict[str, str]] = []
    for room_id, other_room in rooms.items():
        if room_id == selected_room:
            continue
        for direction, target in list(other_room.get("exits", {}).items()):
            if target == selected_room:
                removed_exits.append(
                    {
                        "room_id": room_id,
                        "direction": direction,
                        "target": selected_room,
                    }
                )

    undo_data = {
        "room_id": selected_room,
        "room_data": deleted_room,
        "removed_exits": removed_exits,
    }

    updated_zone = dict(zone_data)
    updated_zone["rooms"] = dict(zone_data.get("rooms", {}))
    del updated_zone["rooms"][selected_room]

    for exit_info in removed_exits:
        room_id = exit_info["room_id"]
        direction = exit_info["direction"]
        if room_id in updated_zone["rooms"]:
            updated_zone["rooms"][room_id] = dict(updated_zone["rooms"][room_id])
            updated_zone["rooms"][room_id]["exits"] = dict(
                updated_zone["rooms"][room_id].get("exits", {})
            )
            if direction in updated_zone["rooms"][room_id]["exits"]:
                del updated_zone["rooms"][room_id]["exits"][direction]

    feedback = dbc.Alert(
        [
            html.I(className="bi bi-trash me-2"),
            f"Room '{selected_room}' deleted.",
        ],
        color="warning",
        className="mb-0 py-2",
        duration=5000,
    )

    return ZoneTransition(
        zone_data=updated_zone,
        feedback=feedback,
        unsaved=True,
        effects={"undo_data": undo_data},
        changed=True,
    )


def undo_delete(
    *,
    zone_data: dict | None,
    undo_data: dict | None,
) -> ZoneTransition:
    """Restore a deleted room from undo metadata."""
    if not zone_data or not undo_data:
        return ZoneTransition(zone_data=None, changed=False)

    room_id = undo_data.get("room_id")
    room_data = undo_data.get("room_data")
    removed_exits = undo_data.get("removed_exits", [])

    if not room_id or not room_data:
        return ZoneTransition(zone_data=None, changed=False)

    updated_zone = dict(zone_data)
    updated_zone["rooms"] = dict(zone_data.get("rooms", {}))
    updated_zone["rooms"][room_id] = room_data

    for exit_info in removed_exits:
        other_room_id = exit_info["room_id"]
        direction = exit_info["direction"]
        target = exit_info["target"]
        if other_room_id in updated_zone["rooms"]:
            updated_zone["rooms"][other_room_id] = dict(updated_zone["rooms"][other_room_id])
            updated_zone["rooms"][other_room_id]["exits"] = dict(
                updated_zone["rooms"][other_room_id].get("exits", {})
            )
            updated_zone["rooms"][other_room_id]["exits"][direction] = target

    feedback = dbc.Alert(
        [
            html.I(className="bi bi-arrow-counterclockwise me-2"),
            f"Room '{room_id}' restored.",
        ],
        color="success",
        className="mb-0 py-2",
        duration=3000,
    )

    return ZoneTransition(
        zone_data=updated_zone,
        feedback=feedback,
        effects={"cleared_undo": True},
        changed=True,
    )
