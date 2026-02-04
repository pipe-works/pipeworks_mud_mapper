"""Zone state manager entry point.

This module routes high-level zone actions to specialized handlers.
Callbacks should use `apply_zone_action` as the single entrypoint for
mutating `current-zone-data`.
"""

from __future__ import annotations

from pipeworks_mud_mapper.services.state import (
    actions_exit,
    actions_load,
    actions_ollama,
    actions_room,
)
from pipeworks_mud_mapper.services.state.types import ZoneAction, ZoneTransition


def apply_zone_action(zone_data: dict | None, action: ZoneAction) -> ZoneTransition:
    """Apply a zone action using the appropriate handler.

    Parameters
    ----------
    zone_data : dict | None
        Current zone data to mutate.
    action : ZoneAction
        Action describing the desired mutation.

    Returns
    -------
    ZoneTransition
        The result of the action, including updated zone data and effects.
    """
    action_type = action.type
    payload = action.payload

    if action_type == "ADD_ROOM":
        return actions_room.add_room(zone_data=zone_data, **payload)
    if action_type == "UPDATE_ROOM":
        return actions_room.update_room(zone_data=zone_data, **payload)
    if action_type == "DELETE_ROOM":
        return actions_room.delete_room(zone_data=zone_data, **payload)
    if action_type == "UNDO_DELETE":
        return actions_room.undo_delete(zone_data=zone_data, **payload)
    if action_type == "EXIT_CHANGE":
        return actions_exit.apply_exit_changes(zone_data=zone_data, **payload)
    if action_type == "LOAD_MAP":
        return actions_load.load_map(**payload)
    if action_type == "APPLY_GENERATION":
        return actions_ollama.apply_generation(zone_data=zone_data, **payload)

    raise ValueError(f"Unknown zone action: {action_type}")
