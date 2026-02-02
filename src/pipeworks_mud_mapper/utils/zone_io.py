"""
Zone file I/O utilities for the MUD Mapper.

This module provides core utilities for working with MUD zone data files,
including loading, saving, and manipulating zone structures. It also defines
the coordinate system and direction mappings used throughout the mapper.

The module is designed to be the single source of truth for:
1. Zone file format (JSON structure)
2. Coordinate system conventions
3. Direction mappings and relationships
4. Room spatial queries

Design Principles
-----------------
1. **Deterministic**: All operations produce identical results for identical inputs
2. **Non-mutating**: Functions return new data structures, never modify inputs
3. **Fail-fast**: Invalid inputs raise exceptions immediately
4. **Single Responsibility**: Each function does one thing well

Coordinate System
-----------------
The mapper uses a 3D Cartesian coordinate system:

- **X-axis**: East (+) / West (-)
- **Y-axis**: North (+) / South (-)
- **Z-axis**: Up (+) / Down (-)

The spawn room is typically placed at origin (0, 0, 0), with other rooms
positioned relative to it based on exit directions.

Constants
---------
DIRECTION_OFFSETS : dict[str, tuple[int, int, int]]
    Maps direction names to (dx, dy, dz) coordinate offsets
DIRECTION_SHORT : dict[str, str]
    Maps full direction names to single-letter abbreviations (N, E, S, W, U, D)
SHORT_TO_DIRECTION : dict[str, str]
    Reverse mapping from abbreviations to full direction names
OPPOSITE_DIRECTION : dict[str, str]
    Maps each direction to its opposite (north↔south, east↔west, up↔down)

Functions
---------
find_room_by_coords(rooms, coords) -> str | None
    Find a room by exact coordinate match
find_room_in_direction(rooms, from_coords, direction, exclude_room) -> str | None
    Find the nearest room in a cardinal direction
create_blank_zone(zone_id, zone_name, description) -> dict
    Create a new empty zone with a spawn room
save_zone_json(zone_data, file_path) -> None
    Save zone data to a JSON file
load_zone_json(file_path) -> dict
    Load zone data from a JSON file
list_zone_files(directory) -> list[Path]
    List all .json zone files in a directory
auto_layout_rooms(zone_data) -> dict
    Automatically assign coordinates to rooms based on exits

Zone File Format
----------------
Zone files are JSON documents with the following structure::

    {
        "id": "zone_identifier",
        "name": "Human Readable Name",
        "description": "Optional zone description",
        "spawn_room": "room_id_where_players_start",
        "rooms": {
            "room_id": {
                "id": "room_id",
                "name": "Room Name",
                "description": "Room description text",
                "coords": [x, y, z],
                "exits": {"north": "target_room_id", ...},
                "items": []
            },
            ...
        },
        "items": {}
    }

Usage
-----
Create and save a new zone::

    >>> from pathlib import Path
    >>> from pipeworks_mud_mapper.utils.zone_io import (
    ...     create_blank_zone,
    ...     save_zone_json,
    ... )
    >>> zone = create_blank_zone("my_dungeon", "My Dungeon", "A dark place")
    >>> save_zone_json(zone, Path("data/my_dungeon.json"))

Load and explore an existing zone::

    >>> from pipeworks_mud_mapper.utils.zone_io import load_zone_json
    >>> zone = load_zone_json(Path("data/my_dungeon.json"))
    >>> for room_id, room in zone["rooms"].items():
    ...     print(f"{room_id}: {room['name']}")

Find rooms by position::

    >>> from pipeworks_mud_mapper.utils.zone_io import find_room_in_direction
    >>> rooms = zone["rooms"]
    >>> target = find_room_in_direction(rooms, (0, 0, 0), "north")
    >>> if target:
    ...     print(f"Room to the north: {target}")

Auto-layout rooms from exit definitions::

    >>> from pipeworks_mud_mapper.utils.zone_io import auto_layout_rooms
    >>> zone_with_coords = auto_layout_rooms(zone)
    >>> for room_id, room in zone_with_coords["rooms"].items():
    ...     print(f"{room_id}: {room.get('coords')}")
"""

import copy
import json
from collections import deque
from pathlib import Path

# =============================================================================
# Direction Constants
# =============================================================================
#
# These constants define the spatial relationships between rooms in the MUD
# world. They are used consistently throughout the mapper for:
# - Calculating room positions from exits
# - Finding adjacent rooms
# - Creating bidirectional exit connections
# - Displaying direction indicators in the UI

DIRECTION_OFFSETS: dict[str, tuple[int, int, int]] = {
    # Cardinal directions (horizontal plane, z=0)
    "north": (0, 1, 0),  # Y increases going north
    "south": (0, -1, 0),  # Y decreases going south
    "east": (1, 0, 0),  # X increases going east
    "west": (-1, 0, 0),  # X decreases going west
    # Vertical directions
    "up": (0, 0, 1),  # Z increases going up
    "down": (0, 0, -1),  # Z decreases going down
}
"""
Direction name to coordinate offset mapping.

Each direction maps to a (dx, dy, dz) tuple representing the coordinate
change when moving in that direction. Used for:
- Auto-layout room positioning
- Finding adjacent rooms
- Validating exit connections

The coordinate system follows standard cartographic conventions:
- North is "up" on the map (positive Y)
- East is "right" on the map (positive X)
- Up/Down represent vertical movement (Z axis)
"""

DIRECTION_SHORT: dict[str, str] = {
    "north": "N",
    "south": "S",
    "east": "E",
    "west": "W",
    "up": "U",
    "down": "D",
}
"""
Full direction name to single-letter abbreviation mapping.

Used in the UI for compact display of exit directions in checkboxes
and labels. The abbreviations follow standard compass conventions.
"""

SHORT_TO_DIRECTION: dict[str, str] = {v: k for k, v in DIRECTION_SHORT.items()}
"""
Single-letter abbreviation to full direction name mapping.

Reverse of DIRECTION_SHORT, used to convert UI checkbox values back
to full direction names for zone data manipulation.
"""

OPPOSITE_DIRECTION: dict[str, str] = {
    "north": "south",
    "south": "north",
    "east": "west",
    "west": "east",
    "up": "down",
    "down": "up",
}
"""
Direction to opposite direction mapping.

Used for creating bidirectional exits. When an exit is created from
room A to room B going north, we automatically create an exit from
room B to room A going south (the opposite direction).

This mapping is symmetric: OPPOSITE_DIRECTION[OPPOSITE_DIRECTION[d]] == d
"""


# =============================================================================
# Room Spatial Query Functions
# =============================================================================


def find_room_by_coords(
    rooms: dict[str, dict], coords: tuple[int, int, int] | list[int]
) -> str | None:
    """
    Find a room by its exact coordinates.

    Searches through all rooms to find one whose coordinates exactly match
    the specified target coordinates. This is useful for checking if a
    specific grid position is occupied.

    Parameters
    ----------
    rooms : dict[str, dict]
        Dictionary mapping room IDs to room data dictionaries.
        Each room should have a "coords" key with [x, y, z] list.
    coords : tuple[int, int, int] | list[int]
        Target coordinates to search for as (x, y, z) or [x, y, z].

    Returns
    -------
    str | None
        The room ID if a room exists at the exact coordinates,
        None if no room is found at that position.

    Examples
    --------
    Find a room at the origin::

        >>> rooms = {
        ...     "spawn": {"coords": [0, 0, 0]},
        ...     "hallway": {"coords": [1, 0, 0]},
        ... }
        >>> find_room_by_coords(rooms, (0, 0, 0))
        'spawn'

    Return None when no room exists at coordinates::

        >>> find_room_by_coords(rooms, (5, 5, 5))
        None

    Accept coordinates as list::

        >>> find_room_by_coords(rooms, [1, 0, 0])
        'hallway'

    Notes
    -----
    - Coordinates are compared as exact integers (no tolerance)
    - Rooms without a "coords" key are treated as being at [0, 0, 0]
    - If multiple rooms have the same coordinates (invalid state),
      the first one found is returned (dictionary iteration order)
    - This function performs a linear search: O(n) where n = number of rooms
    """
    # Normalize coords to tuple for consistent comparison
    target = tuple(coords) if isinstance(coords, list) else coords

    # Linear search through all rooms
    for room_id, room in rooms.items():
        room_coords = room.get("coords", [0, 0, 0])
        if tuple(room_coords) == target:
            return room_id

    return None


def find_room_in_direction(
    rooms: dict[str, dict],
    from_coords: tuple[int, int, int] | list[int],
    direction: str,
    exclude_room: str | None = None,
) -> str | None:
    """
    Find the nearest room in a cardinal direction.

    Searches for rooms that are strictly in the given direction from the
    starting coordinates. For horizontal directions (N/S/E/W), only rooms
    on the same Z-level are considered. For vertical directions (U/D),
    only rooms at the same X,Y position are considered.

    This function is used when creating exits to find the appropriate
    target room, regardless of the distance between rooms (unlike
    find_room_by_coords which requires exact coordinate matching).

    Parameters
    ----------
    rooms : dict[str, dict]
        Dictionary mapping room IDs to room data dictionaries.
        Each room should have a "coords" key with [x, y, z] list.
    from_coords : tuple[int, int, int] | list[int]
        Starting coordinates as (x, y, z) or [x, y, z].
    direction : str
        Direction to search: "north", "south", "east", "west", "up", or "down".
    exclude_room : str | None, optional
        Room ID to exclude from search results. Typically used to exclude
        the source room when searching from its position.

    Returns
    -------
    str | None
        Room ID of the nearest room in the specified direction,
        None if no room exists in that direction.

    Examples
    --------
    Find room to the east::

        >>> rooms = {
        ...     "origin": {"coords": [0, 0, 0]},
        ...     "east_room": {"coords": [5, 0, 0]},
        ... }
        >>> find_room_in_direction(rooms, (0, 0, 0), "east", exclude_room="origin")
        'east_room'

    Find nearest when multiple rooms in same direction::

        >>> rooms = {
        ...     "origin": {"coords": [0, 0, 0]},
        ...     "near": {"coords": [2, 0, 0]},
        ...     "far": {"coords": [10, 0, 0]},
        ... }
        >>> find_room_in_direction(rooms, (0, 0, 0), "east")
        'near'

    Return None when no room in direction::

        >>> find_room_in_direction(rooms, (0, 0, 0), "west")
        None

    Rooms on different Z-levels are ignored for horizontal directions::

        >>> rooms = {
        ...     "origin": {"coords": [0, 0, 0]},
        ...     "above": {"coords": [5, 0, 1]},  # Different Z
        ... }
        >>> find_room_in_direction(rooms, (0, 0, 0), "east")
        None

    Notes
    -----
    - Direction must be one of the six cardinal directions
    - Invalid direction returns None (no exception raised)
    - Distance is calculated as Manhattan distance in the relevant axis
    - For N/S: rooms must have same X and Z as starting point
    - For E/W: rooms must have same Y and Z as starting point
    - For U/D: rooms must have same X and Y as starting point
    - Rooms at the exact same coordinates are never returned
    - Performance: O(n) where n = number of rooms
    """
    # Validate direction
    if direction not in DIRECTION_OFFSETS:
        return None

    # Normalize starting coordinates to tuple
    fx, fy, fz = tuple(from_coords) if isinstance(from_coords, list) else from_coords

    # Get direction offset (used for determining axis constraints)
    dx, dy, dz = DIRECTION_OFFSETS[direction]

    # Collect candidate rooms with their distances
    candidates: list[tuple[str, int]] = []

    for room_id, room in rooms.items():
        # Skip excluded room (typically the source room)
        if room_id == exclude_room:
            continue

        # Get room coordinates
        rx, ry, rz = room.get("coords", [0, 0, 0])

        # Apply axis constraints based on direction type
        # Horizontal directions require same Z-level
        if direction in ("north", "south", "east", "west"):
            if rz != fz:
                continue

        # Vertical directions require same X,Y position
        if direction in ("up", "down"):
            if rx != fx or ry != fy:
                continue

        # Check if room is strictly in the specified direction
        # and calculate distance if so
        if direction == "north" and ry > fy and rx == fx:
            candidates.append((room_id, ry - fy))
        elif direction == "south" and ry < fy and rx == fx:
            candidates.append((room_id, fy - ry))
        elif direction == "east" and rx > fx and ry == fy:
            candidates.append((room_id, rx - fx))
        elif direction == "west" and rx < fx and ry == fy:
            candidates.append((room_id, fx - rx))
        elif direction == "up" and rz > fz:
            candidates.append((room_id, rz - fz))
        elif direction == "down" and rz < fz:
            candidates.append((room_id, fz - rz))

    # Return None if no candidates found
    if not candidates:
        return None

    # Sort by distance and return the nearest room
    candidates.sort(key=lambda x: x[1])
    return candidates[0][0]


# =============================================================================
# Zone Creation and Manipulation Functions
# =============================================================================


def create_blank_zone(zone_id: str, zone_name: str, description: str = "") -> dict:
    """
    Create a blank zone template with a single spawn room.

    Creates a new zone data structure ready for editing. The zone includes
    a single "spawn" room at the origin which serves as the entry point
    for players and the starting point for auto-layout calculations.

    Parameters
    ----------
    zone_id : str
        Unique identifier for the zone. Should contain only alphanumeric
        characters and underscores. Used as the filename (zone_id.json).
    zone_name : str
        Human-readable display name for the zone. Shown in the UI.
    description : str, optional
        Optional description text for the zone (default: "").

    Returns
    -------
    dict
        A zone data dictionary containing:
        - id: The zone identifier
        - name: The display name
        - description: The description text
        - spawn_room: Set to "spawn"
        - rooms: Contains single "spawn" room at origin
        - items: Empty dict for zone-level items

    Examples
    --------
    Create a basic zone::

        >>> zone = create_blank_zone("my_dungeon", "My Dungeon")
        >>> zone["id"]
        'my_dungeon'
        >>> zone["name"]
        'My Dungeon'
        >>> "spawn" in zone["rooms"]
        True

    Create zone with description::

        >>> zone = create_blank_zone(
        ...     "dark_forest",
        ...     "The Dark Forest",
        ...     "A mysterious forest shrouded in eternal twilight"
        ... )
        >>> zone["description"]
        'A mysterious forest shrouded in eternal twilight'

    Notes
    -----
    - The spawn room is created without coordinates (auto-layout will
      place it at origin)
    - The spawn room has empty exits and items lists
    - Zone ID should match the intended filename for consistency
    - This function does not validate the zone_id format
    """
    return {
        "id": zone_id,
        "name": zone_name,
        "description": description,
        "spawn_room": "spawn",
        "rooms": {
            "spawn": {
                "id": "spawn",
                "name": "Starting Room",
                "description": "An empty room waiting to be defined.",
                "exits": {},
                "items": [],
            }
        },
        "items": {},
    }


# =============================================================================
# File I/O Functions
# =============================================================================


def save_zone_json(zone_data: dict, file_path: Path) -> None:
    """
    Save zone data to a JSON file.

    Writes the zone data dictionary to a JSON file with human-readable
    formatting (2-space indentation). Creates parent directories if they
    don't exist. Overwrites existing files without warning.

    Parameters
    ----------
    zone_data : dict
        The zone data dictionary to save. Should follow the zone file
        format documented in the module docstring.
    file_path : Path
        Path where the JSON file will be written. Can be a string or
        Path object. Parent directories are created automatically.

    Returns
    -------
    None

    Raises
    ------
    PermissionError
        If the file or directory cannot be written to.
    TypeError
        If zone_data contains non-JSON-serializable values.

    Examples
    --------
    Save a zone to file::

        >>> from pathlib import Path
        >>> zone = create_blank_zone("test", "Test Zone")
        >>> save_zone_json(zone, Path("data/test.json"))

    Save to nested directory (created automatically)::

        >>> save_zone_json(zone, Path("data/zones/dungeons/test.json"))

    Notes
    -----
    - Uses UTF-8 encoding for proper Unicode support
    - Adds trailing newline for POSIX compliance
    - ensure_ascii=False preserves Unicode characters in output
    - 2-space indentation for human readability
    - Existing files are overwritten without confirmation
    """
    # Ensure file_path is a Path object
    file_path = Path(file_path)

    # Create parent directories if they don't exist
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Write JSON with human-readable formatting
    with file_path.open("w", encoding="utf-8") as f:
        json.dump(zone_data, f, indent=2, ensure_ascii=False)
        f.write("\n")  # POSIX-compliant trailing newline


def load_zone_json(file_path: Path) -> dict:
    """
    Load zone data from a JSON file.

    Reads and parses a zone JSON file, returning the zone data as a
    dictionary. The file must exist and contain valid JSON.

    Parameters
    ----------
    file_path : Path
        Path to the JSON file to load. Can be a string or Path object.

    Returns
    -------
    dict
        The zone data dictionary parsed from the JSON file.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    json.JSONDecodeError
        If the file contains invalid JSON.
    PermissionError
        If the file cannot be read.

    Examples
    --------
    Load a zone file::

        >>> from pathlib import Path
        >>> zone = load_zone_json(Path("data/my_dungeon.json"))
        >>> zone["name"]
        'My Dungeon'

    Handle missing file::

        >>> try:
        ...     zone = load_zone_json(Path("nonexistent.json"))
        ... except FileNotFoundError:
        ...     print("Zone file not found")
        Zone file not found

    Notes
    -----
    - Uses UTF-8 encoding for proper Unicode support
    - No validation of zone structure is performed
    - Large files are loaded entirely into memory
    """
    # Ensure file_path is a Path object
    file_path = Path(file_path)

    # Read and parse JSON
    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def list_zone_files(directory: Path) -> list[Path]:
    """
    List all .json zone files in a directory.

    Scans the specified directory for JSON files and returns them
    sorted alphabetically by filename. Does not recurse into
    subdirectories.

    Parameters
    ----------
    directory : Path
        Path to the directory to scan. Can be a string or Path object.

    Returns
    -------
    list[Path]
        List of Path objects for each .json file found, sorted by name.
        Returns empty list if directory doesn't exist or contains no
        JSON files.

    Examples
    --------
    List zone files::

        >>> from pathlib import Path
        >>> files = list_zone_files(Path("data"))
        >>> for f in files:
        ...     print(f.name)
        dungeon.json
        forest.json
        town.json

    Handle empty or missing directory::

        >>> list_zone_files(Path("nonexistent"))
        []

    Notes
    -----
    - Only files with .json extension are returned
    - Sorting is case-sensitive (uppercase before lowercase)
    - Does not validate that files contain valid zone data
    - Does not recurse into subdirectories
    """
    # Ensure directory is a Path object
    directory = Path(directory)

    # Return empty list if directory doesn't exist
    if not directory.exists():
        return []

    # Find and sort JSON files
    return sorted(directory.glob("*.json"))


def list_map_files(directory: Path) -> list[Path]:
    """
    List all .map.json map files in a directory.

    Scans the specified directory for map files (*.map.json) and returns
    them sorted alphabetically by filename. Does not recurse into
    subdirectories.

    Parameters
    ----------
    directory : Path
        Path to the directory to scan (typically data/maps/).

    Returns
    -------
    list[Path]
        List of Path objects for each .map.json file found, sorted by name.
        Returns empty list if directory doesn't exist or contains no
        map files.

    Examples
    --------
    List map files::

        >>> from pathlib import Path
        >>> files = list_map_files(Path("data/maps"))
        >>> for f in files:
        ...     print(f.name)
        dungeon.map.json
        forest.map.json

    Notes
    -----
    - Only files ending with .map.json are returned
    - Use list_zone_files() for zone files (*.json without .map)
    - Map files contain coordinates for authoring
    - Zone files are game truth without coordinates
    """
    directory = Path(directory)

    if not directory.exists():
        return []

    return sorted(directory.glob("*.map.json"))


# =============================================================================
# Auto-Layout Functions
# =============================================================================


def auto_layout_rooms(zone_data: dict) -> dict:
    """
    Add coordinates to rooms based on exit directions.

    Performs a breadth-first traversal starting from the spawn room,
    assigning coordinates to each room based on the direction of the
    exit used to reach it. Rooms already having coordinates are preserved.

    This function is useful for:
    - Loading legacy zones that don't have coordinate data
    - Visualizing zones that were defined only by exits
    - Initial placement before manual coordinate adjustment

    Parameters
    ----------
    zone_data : dict
        Zone dictionary containing rooms. Rooms should have "exits"
        dictionaries mapping direction names to target room IDs.

    Returns
    -------
    dict
        A deep copy of zone_data with "coords" added to each room.
        Rooms reachable from spawn get positions based on traversal path.
        Disconnected rooms (not reachable from spawn) are placed at origin.

    Examples
    --------
    Auto-layout a simple linear zone::

        >>> zone = {
        ...     "spawn_room": "start",
        ...     "rooms": {
        ...         "start": {"exits": {"north": "middle"}},
        ...         "middle": {"exits": {"south": "start", "north": "end"}},
        ...         "end": {"exits": {"south": "middle"}},
        ...     }
        ... }
        >>> result = auto_layout_rooms(zone)
        >>> result["rooms"]["start"]["coords"]
        [0, 0, 0]
        >>> result["rooms"]["middle"]["coords"]
        [0, 1, 0]
        >>> result["rooms"]["end"]["coords"]
        [0, 2, 0]

    Preserve existing coordinates::

        >>> zone = {
        ...     "spawn_room": "a",
        ...     "rooms": {
        ...         "a": {"coords": [5, 5, 0], "exits": {"north": "b"}},
        ...         "b": {"exits": {"south": "a"}},
        ...     }
        ... }
        >>> result = auto_layout_rooms(zone)
        >>> result["rooms"]["a"]["coords"]  # Preserved
        [5, 5, 0]

    Notes
    -----
    - Uses BFS traversal for deterministic, shortest-path positioning
    - Cross-zone exits (containing ':') are ignored during traversal
    - Unknown direction names are ignored
    - If spawn_room doesn't exist, the first room in the dict is used
    - Original zone_data is never modified (deep copy is made)
    - Coordinate offsets follow DIRECTION_OFFSETS conventions
    - Disconnected rooms end up at origin (may overlap)
    """
    # Deep copy to avoid mutating original
    zone = copy.deepcopy(zone_data)
    rooms = zone.get("rooms", {})

    # Handle empty zone
    if not rooms:
        return zone

    # Determine starting room for traversal
    spawn_id = zone.get("spawn_room", "spawn")
    if spawn_id not in rooms:
        # Fall back to first room if spawn doesn't exist
        spawn_id = next(iter(rooms))

    # Track visited rooms and their computed coordinates
    visited: dict[str, tuple[int, int, int]] = {}

    # BFS queue: (room_id, x, y, z)
    queue: deque[tuple[str, int, int, int]] = deque()
    queue.append((spawn_id, 0, 0, 0))
    visited[spawn_id] = (0, 0, 0)

    # Traverse zone via BFS
    while queue:
        room_id, x, y, z = queue.popleft()
        room = rooms.get(room_id)
        if not room:
            continue

        # Process each exit from this room
        exits = room.get("exits", {})
        for direction, target in exits.items():
            # Skip cross-zone exits (format: "zone_id:room_id")
            if ":" in str(target):
                continue

            # Skip unknown directions
            if direction not in DIRECTION_OFFSETS:
                continue

            # Skip already visited rooms
            if target in visited:
                continue

            # Skip rooms not in this zone
            if target not in rooms:
                continue

            # Compute new position based on direction offset
            dx, dy, dz = DIRECTION_OFFSETS[direction]
            new_x, new_y, new_z = x + dx, y + dy, z + dz

            # Record position and add to queue
            visited[target] = (new_x, new_y, new_z)
            queue.append((target, new_x, new_y, new_z))

    # Apply computed coordinates to rooms (preserving existing coords)
    for room_id, (rx, ry, rz) in visited.items():
        if room_id in rooms:
            if "coords" not in rooms[room_id]:
                rooms[room_id]["coords"] = [rx, ry, rz]

    # Place any disconnected rooms at origin
    for room_id in rooms:
        if "coords" not in rooms[room_id]:
            rooms[room_id]["coords"] = [0, 0, 0]

    return zone
