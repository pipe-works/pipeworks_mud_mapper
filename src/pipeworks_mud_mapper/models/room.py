"""Room and coordinate models for PipeWorks MUD Mapper.

This module defines the core room-related data structures used by the mapper.
Two room types exist to support the two-file workflow:

- **Room**: Game truth representation (no coordinates)
- **MapRoom**: Authoring representation (includes coordinates)

The separation reflects the principle that coordinates are "authoring scaffolding"
- they help humans visualize the map but are not part of the game state.

Direction System
----------------
MUDs traditionally use cardinal directions for navigation. This mapper supports
six directions as decided in ``goblin_cartography.md`` Section 1.7:

============  ===================  ====================
Direction     Axis                 Typical Use
============  ===================  ====================
north         +Y                   Horizontal movement
south         -Y                   Horizontal movement
east          +X                   Horizontal movement
west          -X                   Horizontal movement
up            +Z                   Vertical (stairs, ladders)
down          -Z                   Vertical (trapdoors, basements)
============  ===================  ====================

The decision to use 6 directions (not 4) allows rooms to have both a "south"
exit AND a "down" exit going to different places - essential for multi-story
structures like The Crooked Pipe pub.

Coordinate System
-----------------
The mapper uses a 3D Cartesian coordinate system::

           +Y (North)
              │
              │
    -X ───────┼─────── +X
   (West)     │       (East)
              │
           -Y (South)

    Z: +Z (Up) / -Z (Down)

The origin ``[0, 0, 0]`` is conventionally the zone's spawn room.

Examples
--------
Creating a room for game truth (Zone export)::

    room = Room(
        id="spawn",
        name="The Crooked Pipe",
        description="A low-ceilinged goblin pub...",
        exits={"north": "front_parlour", "down": "cellar"},
        items=["ale_mug", "chalk"],
    )

Creating a room for authoring (MapFile)::

    map_room = MapRoom(
        id="spawn",
        name="The Crooked Pipe",
        description="A low-ceilinged goblin pub...",
        coords=Coords(x=0, y=0, z=0),
        exits={"north": "front_parlour", "down": "cellar"},
        items=["ale_mug", "chalk"],
    )

Converting MapRoom to Room (strips coordinates)::

    room = map_room.to_room()

See Also
--------
- ``goblin_cartography.md`` Section 1.7: Cardinal Points and Movement
- ``goblin_cartography.md`` Section 2.2: The Coordinate Paradox
"""

from __future__ import annotations

from typing import Literal, cast

from pydantic import BaseModel, Field, field_validator

from pipeworks_mud_mapper.models.description_validation import DescriptionValidationInfo

# Import OllamaGenerationInfo for Pydantic field type.
# This is imported directly (not under TYPE_CHECKING) because Pydantic needs
# the actual class at runtime for field validation and serialization.
# The import is placed here (after BaseModel) to avoid potential circular imports.
from pipeworks_mud_mapper.models.ollama_generation import OllamaGenerationInfo

# =============================================================================
# Type Definitions
# =============================================================================

Direction = Literal["north", "south", "east", "west", "up", "down"]
"""Valid MUD movement directions.

Constrained to six values matching the decision in goblin_cartography.md:
- Horizontal: north, south, east, west
- Vertical: up, down

Up/Down are semantically distinct from North/South - they represent vertical
traversal (stairs, ladders, trapdoors) rather than horizontal movement on a
conceptual map.
"""

# Direction constants for programmatic use
DIRECTIONS: tuple[Direction, ...] = ("north", "south", "east", "west", "up", "down")
"""All valid directions as a tuple for iteration."""

OPPOSITE_DIRECTION: dict[Direction, Direction] = {
    "north": "south",
    "south": "north",
    "east": "west",
    "west": "east",
    "up": "down",
    "down": "up",
}
"""Mapping of each direction to its opposite.

Used for bidirectional exit creation - when creating an exit from A to B,
the opposite direction is used for the return exit from B to A.
"""

DIRECTION_OFFSETS: dict[Direction, tuple[int, int, int]] = {
    "north": (0, 1, 0),
    "south": (0, -1, 0),
    "east": (1, 0, 0),
    "west": (-1, 0, 0),
    "up": (0, 0, 1),
    "down": (0, 0, -1),
}
"""Coordinate offsets for each direction.

These represent the unit vector for movement in each direction:
- X axis: East (+1) / West (-1)
- Y axis: North (+1) / South (-1)
- Z axis: Up (+1) / Down (-1)

Note: Actual room spacing may vary. These offsets indicate direction only,
not distance. Use for determining which direction a target room lies relative
to a source room.
"""


# =============================================================================
# Coordinate Model
# =============================================================================


class Coords(BaseModel):
    """Three-dimensional coordinates for room placement.

    Coordinates are authoring metadata - they help humans visualize and validate
    the map layout but are not used by the game engine. The MUD server operates
    on pure topology (room connections) not geometry.

    Attributes
    ----------
    x : int
        East/West position. Positive = East, Negative = West.
    y : int
        North/South position. Positive = North, Negative = South.
    z : int
        Up/Down level. Positive = Up (upper floors), Negative = Down (basements).

    Examples
    --------
    >>> coords = Coords(x=0, y=0, z=0)  # Origin (typically spawn room)
    >>> coords = Coords(x=5, y=-5, z=0)  # 5 units east, 5 units south
    >>> coords = Coords(x=0, y=0, z=-1)  # One level below origin (basement)

    Notes
    -----
    The coordinate system follows standard mathematical conventions:
    - Origin at (0, 0, 0)
    - Right-hand rule for axis orientation
    - Integers only (no fractional positions)
    """

    x: int = Field(default=0, description="East (+) / West (-) position")
    y: int = Field(default=0, description="North (+) / South (-) position")
    z: int = Field(default=0, description="Up (+) / Down (-) level")

    def to_tuple(self) -> tuple[int, int, int]:
        """Convert coordinates to a tuple.

        Returns
        -------
        tuple[int, int, int]
            Coordinates as (x, y, z) tuple.

        Examples
        --------
        >>> Coords(x=1, y=2, z=3).to_tuple()
        (1, 2, 3)
        """
        return (self.x, self.y, self.z)

    def to_list(self) -> list[int]:
        """Convert coordinates to a list.

        This format matches the JSON serialization used in map files.

        Returns
        -------
        list[int]
            Coordinates as [x, y, z] list.

        Examples
        --------
        >>> Coords(x=1, y=2, z=3).to_list()
        [1, 2, 3]
        """
        return [self.x, self.y, self.z]

    @classmethod
    def from_list(cls, coords: list[int]) -> Coords:
        """Create Coords from a list.

        Parameters
        ----------
        coords : list[int]
            Coordinates as [x, y, z] list.

        Returns
        -------
        Coords
            New Coords instance.

        Raises
        ------
        ValueError
            If coords does not have exactly 3 elements.

        Examples
        --------
        >>> Coords.from_list([1, 2, 3])
        Coords(x=1, y=2, z=3)
        """
        if len(coords) != 3:
            raise ValueError(f"Coords must have 3 elements, got {len(coords)}")
        return cls(x=coords[0], y=coords[1], z=coords[2])

    def offset(self, direction: Direction) -> Coords:
        """Return new coordinates offset in the given direction.

        Parameters
        ----------
        direction : Direction
            The direction to offset towards.

        Returns
        -------
        Coords
            New Coords offset by one unit in the given direction.

        Examples
        --------
        >>> origin = Coords(x=0, y=0, z=0)
        >>> origin.offset("north")
        Coords(x=0, y=1, z=0)
        >>> origin.offset("down")
        Coords(x=0, y=0, z=-1)
        """
        dx, dy, dz = DIRECTION_OFFSETS[direction]
        return Coords(x=self.x + dx, y=self.y + dy, z=self.z + dz)


# =============================================================================
# Room Models
# =============================================================================


class Room(BaseModel):
    """A room in game truth format (no coordinates).

    This model represents a room as it appears in exported zone files - the
    format consumed by the MUD server. Coordinates are excluded because the
    game engine operates on topology (connections) not geometry (positions).

    Attributes
    ----------
    id : str
        Unique identifier within the zone. Used as dictionary key and in exit
        references. Should be lowercase with underscores (e.g., "front_parlour").
    name : str
        Human-readable display name shown to players (e.g., "Front Parlour").
    description : str
        Room description shown when a player enters or looks. Can be multiple
        sentences. Defaults to empty string.
    exits : dict[Direction, str]
        Mapping of direction to target room ID. Target can be same-zone
        (e.g., "front_parlour") or cross-zone (e.g., "docks:east_pier").
    items : list[str]
        List of item IDs present in this room. Items must be defined in the
        zone's items dictionary.

    Examples
    --------
    >>> room = Room(
    ...     id="spawn",
    ...     name="The Crooked Pipe",
    ...     description="A low-ceilinged goblin pub with sticky floors.",
    ...     exits={"north": "front_parlour", "down": "cellar"},
    ...     items=["ale_mug"],
    ... )

    See Also
    --------
    MapRoom : Room with coordinates for authoring.
    Zone : Container for rooms in game truth format.
    """

    id: str = Field(..., min_length=1, description="Unique room identifier")
    name: str = Field(..., min_length=1, description="Display name")
    description: str = Field(default="", description="Room description text")
    exits: dict[Direction, str] = Field(
        default_factory=dict, description="Direction to target room mapping"
    )
    items: list[str] = Field(default_factory=list, description="Item IDs in this room")

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate room ID format.

        Room IDs must start with a letter and contain only lowercase letters,
        numbers, and underscores.

        Parameters
        ----------
        v : str
            The room ID to validate.

        Returns
        -------
        str
            The validated room ID.

        Raises
        ------
        ValueError
            If the ID format is invalid.
        """
        if not v[0].isalpha():
            raise ValueError("Room ID must start with a letter")
        if not v.replace("_", "").isalnum():
            raise ValueError("Room ID must contain only letters, numbers, and underscores")
        if v != v.lower():
            raise ValueError("Room ID must be lowercase")
        return v


class MapRoom(BaseModel):
    """A room in authoring format (includes coordinates and LLM metadata).

    This model represents a room as it appears in map files - the format used
    by the mapper tool during authoring. It extends the game truth Room with:

    - **Coordinates**: Position in 3D space for visualization
    - **LLM generation metadata**: Provenance info for AI-generated descriptions
    - **Description validation metadata**: Latest validator output for the description

    Both fields are "authoring scaffolding" - they help humans create and
    understand the map but are not part of the game state. When exporting
    to a zone file, both are stripped using ``to_room()``.

    Attributes
    ----------
    id : str
        Unique identifier within the zone.
    name : str
        Human-readable display name.
    description : str
        Room description text.
    coords : Coords
        Position in 3D space (x, y, z). Used for visualization only.
    exits : dict[Direction, str]
        Mapping of direction to target room ID.
    items : list[str]
        List of item IDs present in this room.
    llm_generation : OllamaGenerationInfo | None
        Metadata about the last LLM generation for this room's description.
        Only present if the description was generated by Ollama. Contains
        model name, seed, parameters, and prompts for reproducibility.
        Stripped during zone export (like coords).
    description_validation : DescriptionValidationInfo | None
        Metadata about the last validator run for this description.
        Stripped during zone export (like coords).

    Examples
    --------
    >>> map_room = MapRoom(
    ...     id="spawn",
    ...     name="The Crooked Pipe",
    ...     description="A low-ceilinged goblin pub.",
    ...     coords=Coords(x=0, y=0, z=0),
    ...     exits={"north": "front_parlour"},
    ...     items=["ale_mug"],
    ... )

    Converting to game truth format (strips coords and llm_generation)::

        >>> room = map_room.to_room()
        >>> hasattr(room, 'coords')  # False - stripped
        False
        >>> hasattr(room, 'llm_generation')  # Also stripped
        False

    See Also
    --------
    Room : Game truth format (no coordinates or LLM metadata).
    MapFile : Container for MapRooms.
    OllamaGenerationInfo : LLM generation metadata model.
    """

    id: str = Field(..., min_length=1, description="Unique room identifier")
    name: str = Field(..., min_length=1, description="Display name")
    description: str = Field(default="", description="Room description text")
    coords: Coords = Field(default_factory=Coords, description="Position in 3D space")
    exits: dict[Direction, str] = Field(
        default_factory=dict, description="Direction to target room mapping"
    )
    items: list[str] = Field(default_factory=list, description="Item IDs in this room")

    # =========================================================================
    # LLM Generation Metadata (Authoring Scaffolding)
    # =========================================================================
    # This field stores provenance information for AI-generated descriptions.
    # It enables reproducibility (same seed + params = same output) and helps
    # authors understand how a description was created.
    #
    # Like coords, this is stripped when exporting to zone files because it's
    # authoring metadata, not game state.

    llm_generation: OllamaGenerationInfo | None = Field(
        default=None,
        description="LLM generation metadata (stripped on zone export)",
    )
    description_validation: DescriptionValidationInfo | None = Field(
        default=None,
        description="Description validation metadata (stripped on zone export)",
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate room ID format.

        Room IDs must start with a letter and contain only lowercase letters,
        numbers, and underscores.
        """
        if not v[0].isalpha():
            raise ValueError("Room ID must start with a letter")
        if not v.replace("_", "").isalnum():
            raise ValueError("Room ID must contain only letters, numbers, and underscores")
        if v != v.lower():
            raise ValueError("Room ID must be lowercase")
        return v

    def to_room(self) -> Room:
        """Convert to game truth format by stripping authoring metadata.

        Removes coordinates and LLM generation metadata, producing a Room
        suitable for zone export. The MUD server only needs topology (room
        connections) and content (description, items), not authoring aids.

        Returns
        -------
        Room
            A Room instance without coordinates or LLM metadata.

        Notes
        -----
        The following fields are intentionally NOT copied to the output:

        - ``coords``: Visualization aid, not game state
        - ``llm_generation``: Provenance tracking, not game state
        - ``description_validation``: Validator output, not game state

        Examples
        --------
        >>> map_room = MapRoom(
        ...     id="spawn",
        ...     name="Spawn",
        ...     coords=Coords(x=0, y=0, z=0),
        ... )
        >>> room = map_room.to_room()
        >>> hasattr(room, 'coords')
        False
        """
        # Only copy fields that are part of game truth.
        # coords, llm_generation, and description_validation are intentionally excluded.
        return Room(
            id=self.id,
            name=self.name,
            description=self.description,
            exits=self.exits.copy(),
            items=self.items.copy(),
        )

    @classmethod
    def from_dict(cls, data: dict) -> MapRoom:
        """Create MapRoom from a dictionary (legacy format support).

        This method handles various input formats:

        - Legacy coords as ``[x, y, z]`` list (converted to Coords object)
        - Files without ``llm_generation`` field (defaults to None)
        - Files with ``llm_generation`` as dict (validated by Pydantic)

        Parameters
        ----------
        data : dict
            Room data dictionary. May contain:

            - ``coords`` as ``[x, y, z]`` list or ``Coords`` object
            - ``llm_generation`` as dict, ``None``, or missing entirely

        Returns
        -------
        MapRoom
            New MapRoom instance with all fields properly typed.

        Examples
        --------
        Basic room without LLM metadata (legacy format)::

            >>> data = {
            ...     "id": "spawn",
            ...     "name": "Spawn",
            ...     "coords": [0, 0, 0],
            ...     "exits": {},
            ...     "items": [],
            ... }
            >>> room = MapRoom.from_dict(data)
            >>> room.coords
            Coords(x=0, y=0, z=0)
            >>> room.llm_generation is None
            True

        Room with LLM generation metadata::

            >>> data = {
            ...     "id": "spawn",
            ...     "name": "Spawn",
            ...     "coords": [0, 0, 0],
            ...     "exits": {},
            ...     "items": [],
            ...     "llm_generation": {
            ...         "model": "gemma2:2b",
            ...         "actual_seed": 12345,
            ...         "template_id": "custom",
            ...         "temperature": 0.7,
            ...         "top_k": 40,
            ...         "top_p": 0.9,
            ...         "num_ctx": 4096,
            ...         "num_predict": 512,
            ...         "system_prompt": "...",
            ...         "user_prompt": "...",
            ...         "generated_at": "2024-01-15T10:30:00Z",
            ...     },
            ... }
            >>> room = MapRoom.from_dict(data)
            >>> room.llm_generation.model
            'gemma2:2b'
        """
        data = data.copy()

        # Handle legacy coords format: [x, y, z] list -> Coords object
        if "coords" in data and isinstance(data["coords"], list):
            data["coords"] = Coords.from_list(data["coords"])

        # llm_generation is optional and may be missing in legacy files.
        # Pydantic handles None/missing gracefully with the default=None.
        # If present as a dict, Pydantic will validate it against OllamaGenerationInfo.

        return cast("MapRoom", cls.model_validate(data))
