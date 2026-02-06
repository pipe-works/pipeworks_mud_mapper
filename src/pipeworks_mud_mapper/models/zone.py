"""Zone model for game truth representation.

This module defines the Zone model - the "game truth" format that the MUD
server consumes. Zone files contain everything the game engine needs to run:
rooms, exits, items, and metadata. They explicitly exclude coordinates because
the engine operates on topology (connections) not geometry (positions).

The Two-File Philosophy
-----------------------
As described in ``goblin_cartography.md`` Section 2.3, there's a deliberate
separation between:

1. **Zone files** (game truth): What the server needs. Pure topology.
2. **Map files** (authoring source): What humans need. Includes coordinates.

Zone files are "build artifacts" - they're generated from map files by stripping
coordinates. This separation ensures:

- The server never sees or depends on visual layout
- Authors can freely rearrange map layouts without affecting gameplay
- Zone files remain clean and focused on game logic

Zone Structure
--------------
A zone is a self-contained region of the MUD world::

    {
        "id": "crooked_pipe",
        "name": "Crooked Pipe District",
        "description": "A warren of goblin pubs...",
        "spawn_room": "spawn",
        "rooms": {
            "spawn": { ... },
            "front_parlour": { ... }
        },
        "items": {
            "ale_mug": { ... }
        }
    }

Cross-Zone Exits
----------------
Exits can reference rooms in other zones using the format ``zone:room``::

    "exits": {
        "north": "front_parlour",          # Same zone
        "west": "cobbled_street:market"    # Cross-zone
    }

The engine parses the ``:`` delimiter and loads the target zone if needed.

Examples
--------
Creating a zone programmatically::

    zone = Zone(
        id="tutorial",
        name="Tutorial Area",
        spawn_room="spawn",
        rooms={
            "spawn": Room(id="spawn", name="Arrival Chamber", exits={"north": "hall"}),
            "hall": Room(id="hall", name="Main Hall", exits={"south": "spawn"}),
        },
    )

Serializing to JSON::

    json_str = zone.model_dump_json(indent=2, exclude_none=True)

See Also
--------
MapFile : Authoring format that includes coordinates.
Room : Individual room within a zone.
"""

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from pipeworks_mud_mapper.models.metadata import ZoneMetadata
from pipeworks_mud_mapper.models.room import Room


class Zone(BaseModel):
    """A zone in game truth format (no coordinates).

    Zones are self-contained regions of the MUD world. Each zone has its own
    spawn point, rooms, and items. Zones connect to each other through
    cross-zone exits.

    This model represents the format consumed by the MUD server. It excludes
    coordinates because the game engine operates on topology, not geometry.

    Attributes
    ----------
    id : str
        Unique zone identifier. Used in cross-zone references and as filename.
        Should be lowercase with underscores (e.g., "crooked_pipe").
    name : str
        Human-readable display name (e.g., "Crooked Pipe District").
    metadata : ZoneMetadata
        Versioning metadata that accompanies exported zone files.
    description : str
        Optional zone description for authoring reference.
    spawn_room : str
        Room ID where players enter this zone. Must exist in rooms dict.
    rooms : dict[str, Room]
        Mapping of room ID to Room objects.
    items : dict[str, dict]
        Mapping of item ID to item definitions. Item structure is flexible
        to support future item system expansion.

    Examples
    --------
    >>> zone = Zone(
    ...     id="tutorial",
    ...     name="Tutorial Area",
    ...     spawn_room="spawn",
    ...     rooms={"spawn": Room(id="spawn", name="Start")},
    ... )

    Validation ensures spawn_room exists::

        >>> Zone(
        ...     id="bad",
        ...     name="Bad Zone",
        ...     spawn_room="nonexistent",
        ...     rooms={},
        ... )
        Traceback (most recent call last):
        ...
        pydantic_core._pydantic_core.ValidationError: ...

    See Also
    --------
    MapFile : Authoring format with coordinates.
    Room : Individual room model.
    """

    id: str = Field(..., min_length=1, description="Unique zone identifier")
    name: str = Field(..., min_length=1, description="Display name")
    metadata: ZoneMetadata = Field(
        default_factory=ZoneMetadata,
        description="Versioning metadata for exported zone files",
    )
    description: str = Field(default="", description="Zone description")
    spawn_room: str = Field(..., min_length=1, description="Entry room ID")
    rooms: dict[str, Room] = Field(default_factory=dict, description="Room ID to Room mapping")
    items: dict[str, dict[str, Any]] = Field(
        default_factory=dict, description="Item ID to item definition mapping"
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate zone ID format.

        Zone IDs must start with a letter and contain only lowercase letters,
        numbers, and underscores.
        """
        if not v[0].isalpha():
            raise ValueError("Zone ID must start with a letter")
        if not v.replace("_", "").isalnum():
            raise ValueError("Zone ID must contain only letters, numbers, and underscores")
        if v != v.lower():
            raise ValueError("Zone ID must be lowercase")
        return v

    @model_validator(mode="after")
    def validate_spawn_room_exists(self) -> "Zone":
        """Ensure spawn_room references an existing room.

        Returns
        -------
        Zone
            The validated zone instance.

        Raises
        ------
        ValueError
            If spawn_room is not in the rooms dictionary.
        """
        if self.spawn_room not in self.rooms:
            raise ValueError(
                f"spawn_room '{self.spawn_room}' does not exist in rooms. "
                f"Available rooms: {list(self.rooms.keys())}"
            )
        return self

    @model_validator(mode="after")
    def validate_room_ids_match_keys(self) -> "Zone":
        """Ensure room IDs match their dictionary keys.

        Returns
        -------
        Zone
            The validated zone instance.

        Raises
        ------
        ValueError
            If any room's ID doesn't match its dictionary key.
        """
        for key, room in self.rooms.items():
            if room.id != key:
                raise ValueError(f"Room ID mismatch: key '{key}' but room.id is '{room.id}'")
        return self

    def get_room(self, room_id: str) -> Room | None:
        """Get a room by ID.

        Parameters
        ----------
        room_id : str
            The room ID to look up.

        Returns
        -------
        Room or None
            The room if found, None otherwise.

        Examples
        --------
        >>> zone.get_room("spawn")
        Room(id='spawn', ...)
        >>> zone.get_room("nonexistent")
        None
        """
        return self.rooms.get(room_id)

    def validate_exits(self) -> list[str]:
        """Validate all exit targets exist (within this zone).

        Cross-zone exits (containing `:`) are skipped as they reference
        other zones that may not be loaded.

        Returns
        -------
        list[str]
            List of warning messages for invalid exit targets.

        Examples
        --------
        >>> zone.validate_exits()
        ["Room 'spawn' has exit 'north' to nonexistent room 'bad_room'"]
        """
        warnings = []
        for room_id, room in self.rooms.items():
            for direction, target in room.exits.items():
                # Skip cross-zone exits
                if ":" in target:
                    continue
                if target not in self.rooms:
                    warnings.append(
                        f"Room '{room_id}' has exit '{direction}' to "
                        f"nonexistent room '{target}'"
                    )
        return warnings

    def find_unreachable_rooms(self) -> list[str]:
        """Find rooms that cannot be reached from the spawn room.

        Uses breadth-first search from spawn_room to find all reachable rooms,
        then returns any rooms not in that set.

        Returns
        -------
        list[str]
            List of room IDs that are unreachable from spawn.

        Examples
        --------
        >>> zone.find_unreachable_rooms()
        ['isolated_room', 'another_orphan']
        """
        if not self.rooms:
            return []

        reachable: set[str] = set()
        queue = [self.spawn_room]

        while queue:
            current = queue.pop(0)
            if current in reachable:
                continue
            reachable.add(current)

            room = self.rooms.get(current)
            if room:
                for target in room.exits.values():
                    # Handle cross-zone exits - only follow same-zone
                    if ":" not in target and target not in reachable:
                        queue.append(target)

        all_rooms = set(self.rooms.keys())
        return sorted(all_rooms - reachable)

    def find_dead_ends(self) -> list[str]:
        """Find rooms with no outgoing exits.

        Note: Dead ends are not always errors - some rooms are intentionally
        terminal (treasure rooms, trap rooms, etc.).

        Returns
        -------
        list[str]
            List of room IDs with no exits.

        Examples
        --------
        >>> zone.find_dead_ends()
        ['treasure_room', 'pit_of_doom']
        """
        return sorted(room_id for room_id, room in self.rooms.items() if not room.exits)
