"""State helpers for applying Ollama outputs to map data.

This module centralizes the domain logic for:
- building generation metadata
- applying generated descriptions to rooms
- attaching or clearing validation metadata

Keeping these operations here allows callbacks to remain thin and
makes unit testing easier.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

# =============================================================================
# Metadata Builders
# =============================================================================


def build_generation_metadata(
    *,
    model: str,
    actual_seed: int,
    template_id: str,
    temperature: float,
    top_k: int,
    top_p: float,
    num_ctx: int,
    num_predict: int,
    target_words: int,
    system_prompt: str | None,
    user_prompt: str,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build a metadata dictionary matching OllamaGenerationInfo fields.

    Parameters
    ----------
    model : str
        Ollama model identifier used for generation.
    actual_seed : int
        Seed that was actually used (>= 0).
    template_id : str
        Template ID used for generation.
    temperature : float
        Temperature parameter used for generation.
    top_k : int
        Top-K sampling parameter.
    top_p : float
        Top-P sampling parameter.
    num_ctx : int
        Context window size used for generation.
    num_predict : int
        Maximum output tokens requested.
    target_words : int
        Target word count used in the system prompt.
    system_prompt : str | None
        Full system prompt (compiled or custom).
    user_prompt : str
        User prompt entered by the author.
    generated_at : str | None
        Optional ISO timestamp; if None, uses current UTC.

    Returns
    -------
    dict[str, Any]
        Metadata dictionary for storage in map files.
    """
    return {
        "model": model,
        "actual_seed": actual_seed,
        "template_id": template_id,
        "temperature": float(temperature),
        "top_k": int(top_k),
        "top_p": float(top_p),
        "num_ctx": int(num_ctx),
        "num_predict": int(num_predict),
        "target_words": int(target_words),
        "system_prompt": system_prompt or "",
        "user_prompt": user_prompt,
        "generated_at": generated_at or datetime.now(UTC).isoformat(),
    }


# =============================================================================
# Room Update Helpers
# =============================================================================


def apply_generation_to_room(
    *,
    zone_data: dict,
    room_id: str,
    description: str,
    generation_info: dict[str, Any] | None,
    validation_info: dict[str, Any] | None,
) -> dict:
    """Return updated zone data with the generated description applied.

    Parameters
    ----------
    zone_data : dict
        Current zone data object.
    room_id : str
        Room ID to update.
    description : str
        Generated description text to apply.
    generation_info : dict[str, Any] | None
        Metadata about the LLM generation; when None, metadata is cleared.
    validation_info : dict[str, Any] | None
        Validator metadata to attach; when None, validation info is cleared.

    Returns
    -------
    dict
        Updated zone data with modified room data.

    Raises
    ------
    KeyError
        If room_id is not in the zone data.
    """
    rooms = zone_data.get("rooms", {})
    if room_id not in rooms:
        raise KeyError(f"Room '{room_id}' not found")

    # Create new dicts so Dash recognizes changes.
    updated_zone = dict(zone_data)
    updated_zone["rooms"] = dict(rooms)
    updated_room = dict(rooms[room_id])

    # Apply description text.
    updated_room["description"] = description.strip()

    # Attach or clear generation metadata.
    if generation_info:
        updated_room["llm_generation"] = generation_info
    else:
        updated_room.pop("llm_generation", None)

    # Attach or clear validation metadata.
    if validation_info:
        updated_room["description_validation"] = validation_info
    else:
        updated_room.pop("description_validation", None)

    updated_zone["rooms"][room_id] = updated_room
    return updated_zone
