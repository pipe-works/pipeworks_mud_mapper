"""Exit parsing helpers for local vs cross-zone exits.

This module centralizes the tiny bits of exit parsing logic used by the
UI, validation, and map rendering layers. It keeps the rules for detecting
cross-zone exits ("zone_id:room_id") consistent across the codebase.
"""

from __future__ import annotations

from pipeworks_mud_mapper.models.room import Direction

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

# UI and callback ordering for exit direction widgets.
# This mirrors the visual order used in the properties panel so that
# pattern-matching callbacks can return values in a predictable order.
EXIT_SHORT_ORDER: tuple[str, ...] = ("N", "E", "S", "W", "U", "D")

# ---------------------------------------------------------------------------
# Exit parsing helpers
# ---------------------------------------------------------------------------


def split_exits_by_scope(
    exits: dict[Direction, str] | None,
) -> tuple[dict[Direction, str], dict[Direction, str]]:
    """Split exits into local (same-zone) and zone (cross-zone) mappings.

    Parameters
    ----------
    exits : dict[Direction, str] | None
        Exit mapping from a room. Values that contain ":" are treated as
        cross-zone exits ("zone_id:room_id"). All others are local exits.

    Returns
    -------
    tuple[dict[Direction, str], dict[Direction, str]]
        (local_exits, zone_exits) where each dict is keyed by direction.

    Notes
    -----
    This is deliberately small and conservative: we only treat values as
    cross-zone exits if they include a colon. Any other value is treated
    as local, even if it might be malformed.
    """
    local_exits: dict[Direction, str] = {}
    zone_exits: dict[Direction, str] = {}

    for direction, target in (exits or {}).items():
        # Treat only "zone:room" values as cross-zone exits.
        if ":" in str(target):
            zone_exits[direction] = str(target)
        else:
            local_exits[direction] = str(target)

    return local_exits, zone_exits


def parse_zone_exit(target: str | None) -> tuple[str | None, str | None]:
    """Parse a cross-zone exit target into (zone_id, room_id).

    Parameters
    ----------
    target : str | None
        Exit target string, expected in "zone_id:room_id" format.

    Returns
    -------
    tuple[str | None, str | None]
        (zone_id, room_id). Returns (None, None) if the input is missing
        or does not contain a valid colon-separated pair.
    """
    if not target or ":" not in target:
        return None, None

    zone_id, room_id = target.split(":", 1)
    if not zone_id or not room_id:
        return None, None

    return zone_id, room_id


def format_zone_exit(zone_id: str | None, room_id: str | None) -> str | None:
    """Format a zone + room selection into the stored exit value.

    Parameters
    ----------
    zone_id : str | None
        Selected zone ID.
    room_id : str | None
        Selected room ID.

    Returns
    -------
    str | None
        "zone_id:room_id" if both parts are present; otherwise None.
    """
    if not zone_id or not room_id:
        return None
    return f"{zone_id}:{room_id}"
