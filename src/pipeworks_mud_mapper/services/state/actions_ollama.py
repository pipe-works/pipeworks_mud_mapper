"""Ollama-related zone state transitions."""

from __future__ import annotations

from pipeworks_mud_mapper.services.ollama_state import apply_generation_to_room
from pipeworks_mud_mapper.services.state.types import ZoneTransition


def apply_generation(
    *,
    zone_data: dict | None,
    selected_room: str | None,
    response_text: str | None,
    generation_info: dict | None,
    validation_info: dict | None,
) -> ZoneTransition:
    """Apply LLM generation output to the selected room."""
    if not zone_data or not selected_room:
        return ZoneTransition(zone_data=None, changed=False)

    if not response_text:
        return ZoneTransition(zone_data=None, changed=False)

    try:
        updated_zone = apply_generation_to_room(
            zone_data=zone_data,
            room_id=selected_room,
            description=response_text,
            generation_info=generation_info,
            validation_info=validation_info,
        )
    except KeyError:
        return ZoneTransition(zone_data=None, changed=False)

    return ZoneTransition(zone_data=updated_zone, unsaved=True, changed=True)
