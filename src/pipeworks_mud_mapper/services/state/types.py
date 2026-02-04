"""Shared types for zone state transitions.

These types define the action payloads and results for the central
zone state manager. Keeping them in one module avoids circular imports
and lets callbacks and action handlers share a stable contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ActionType = Literal[
    "ADD_ROOM",
    "UPDATE_ROOM",
    "DELETE_ROOM",
    "UNDO_DELETE",
    "EXIT_CHANGE",
]


@dataclass(frozen=True)
class ZoneAction:
    """Describe a requested zone mutation.

    Parameters
    ----------
    type : ActionType
        The type of mutation to perform.
    payload : dict[str, Any]
        Action-specific data (room id, coords, exits, etc.).
    """

    type: ActionType
    payload: dict[str, Any]


@dataclass
class ZoneTransition:
    """Result of applying a zone action.

    Attributes
    ----------
    zone_data : dict | None
        Updated zone data if a change occurred. ``None`` means no update.
    feedback : Any | None
        UI feedback payload (e.g., dbc.Alert or html span). ``None`` means no update.
    unsaved : bool | None
        Unsaved flag update. ``None`` means no update.
    effects : dict[str, Any]
        Extra data for callbacks (e.g., exit checkbox values, undo data).
    changed : bool
        Whether the zone data was modified.
    """

    zone_data: dict | None
    feedback: Any | None = None
    unsaved: bool | None = None
    effects: dict[str, Any] = field(default_factory=dict)
    changed: bool = False
