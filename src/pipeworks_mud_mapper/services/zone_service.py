"""Zone service for file I/O operations.

This module handles loading, saving, and exporting zone/map files. It
implements the two-file workflow described in ``goblin_cartography.md``:

- **Map files** (`*.map.json`): Authoring source with coordinates
- **Zone files** (`*.json`): Game truth without coordinates

The Two-File Workflow
---------------------
::

    Author edits:  data/maps/my_zone.map.json   (has coords)
                          │
                          ▼
                   ┌─────────────┐
                   │  MapFile    │  (in memory)
                   └──────┬──────┘
                          │
            ┌─────────────┴─────────────┐
            ▼                           ▼
    save_map_file()              export_zone()
            │                           │
            ▼                           ▼
    data/maps/my_zone.map.json   data/zones/my_zone.json
    (authoring source)           (game truth, no coords)

File Format Detection
---------------------
The service detects file type by:

1. Extension: ``.map.json`` = map file, ``.json`` = zone file
2. Content: presence of ``coords`` in rooms indicates map file

When loading a zone file (no coords), rooms are auto-placed at origin.
A warning is returned to indicate coordinates need assignment.

Examples
--------
Loading a map file::

    from pathlib import Path
    from pipeworks_mud_mapper.services import zone_service

    map_file = zone_service.load_map_file(Path("data/maps/tutorial.map.json"))

Saving changes::

    zone_service.save_map_file(map_file, Path("data/maps/tutorial.map.json"))

Exporting for game server::

    zone_service.export_zone(map_file, Path("data/zones/tutorial.json"))

Creating a new zone::

    map_file = zone_service.create_new_map_file(
        zone_id="new_zone",
        name="New Zone",
        spawn_room_name="Starting Room",
    )

See Also
--------
- ``models/map_file.py``: MapFile model
- ``models/zone.py``: Zone model
- ``goblin_cartography.md`` Section 2.3: Where Coordinates Live
"""

import json
from pathlib import Path
from typing import Any, cast

from pipeworks_mud_mapper.models import Coords, MapFile, MapRoom, Zone


def load_map_file(path: Path) -> MapFile:
    """Load a map file from disk.

    Handles both map files (with coords) and zone files (without coords).
    When loading a zone file, rooms are placed at origin with a warning.

    Parameters
    ----------
    path : Path
        Path to the map or zone file.

    Returns
    -------
    MapFile
        The loaded map file, ready for editing.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    json.JSONDecodeError
        If the file is not valid JSON.
    pydantic.ValidationError
        If the JSON does not match the expected schema.

    Examples
    --------
    >>> map_file = load_map_file(Path("data/maps/tutorial.map.json"))
    >>> len(map_file.rooms)
    5
    """
    content = path.read_text(encoding="utf-8")
    data = json.loads(content)
    return _parse_map_data(data)


def _parse_map_data(data: dict[str, Any]) -> MapFile:
    """Parse raw JSON data into a MapFile.

    Handles legacy format where coords may be lists instead of Coords objects,
    and zone format where coords may be missing entirely.

    Parameters
    ----------
    data : dict
        Raw JSON data from file.

    Returns
    -------
    MapFile
        Parsed map file.
    """
    # Check if this is a zone file (no coords) or map file (has coords)
    has_coords = False
    if "rooms" in data:
        for room_data in data["rooms"].values():
            if "coords" in room_data:
                has_coords = True
                break

    if not has_coords:
        # Zone file - add default coords at origin
        # TODO: Implement auto-layout algorithm (Phase 6)
        for room_id, room_data in data.get("rooms", {}).items():
            if "coords" not in room_data:
                room_data["coords"] = [0, 0, 0]

    return MapFile.from_dict(data)


def save_map_file(map_file: MapFile, path: Path) -> None:
    """Save a map file to disk.

    Saves in the legacy format with coords as [x, y, z] lists for
    compatibility with existing tools and data files.

    Parameters
    ----------
    map_file : MapFile
        The map file to save.
    path : Path
        Destination path. Parent directories are created if needed.

    Examples
    --------
    >>> save_map_file(map_file, Path("data/maps/tutorial.map.json"))
    """
    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dict with list coords for compatibility
    data = map_file.to_dict_with_list_coords()

    # Write with pretty formatting
    content = json.dumps(data, indent=2, ensure_ascii=False)
    path.write_text(content + "\n", encoding="utf-8")


def export_zone(map_file: MapFile, path: Path) -> None:
    """Export a map file as a zone file (strips coordinates and authoring metadata).

    This creates the "game truth" file that the MUD server consumes.
    Coordinates and LLM generation metadata are removed because the game
    engine operates on topology (connections) not geometry (positions),
    and doesn't need authoring provenance data.

    Stripped Fields
    ---------------
    The following "authoring scaffolding" fields are removed during export:

    - **coords**: Room coordinates are visualization aids, not game state.
      Movement in a MUD is topological (room A connects to room B via "north"),
      not metric (room B is at position [1, 0, 0]).

    - **llm_generation**: LLM generation metadata (model, seed, prompts, etc.)
      exists for authoring purposes only - it enables reproducibility and
      provenance tracking during map creation, but has no meaning to the
      game server.

    This separation reflects the pipe-works philosophy that authoring scaffolding
    supports the creation process but is not part of the final game state.

    Parameters
    ----------
    map_file : MapFile
        The map file to export.
    path : Path
        Destination path for the zone file.

    Examples
    --------
    >>> export_zone(map_file, Path("data/zones/tutorial.json"))

    Notes
    -----
    The exported zone file can be loaded back, but coordinates and LLM metadata
    will be lost. Always keep the original map file as the authoring source.

    See Also
    --------
    MapRoom.to_room : Primary stripping mechanism (model conversion).
    OllamaGenerationInfo : The metadata model that gets stripped.
    """
    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to zone (strips coords and llm_generation via MapRoom.to_room())
    # The Room model doesn't have these fields, so they're automatically excluded.
    zone = map_file.to_zone()

    # Serialize without coords
    data = zone.model_dump(exclude_none=True)

    # Belt-and-suspenders: Remove any lingering authoring fields.
    # These should already be gone from the model conversion above,
    # but we explicitly remove them as a safety measure.
    # This guards against:
    #   - Future model changes that might accidentally include these fields
    #   - Serialization edge cases in Pydantic
    #   - Any other unexpected data leakage
    for room_data in data.get("rooms", {}).values():
        room_data.pop("coords", None)
        room_data.pop("llm_generation", None)

    # Write with pretty formatting
    content = json.dumps(data, indent=2, ensure_ascii=False)
    path.write_text(content + "\n", encoding="utf-8")


def create_new_map_file(
    zone_id: str,
    name: str,
    spawn_room_name: str = "Spawn Room",
    description: str = "",
) -> MapFile:
    """Create a new empty map file with a spawn room.

    Parameters
    ----------
    zone_id : str
        Unique identifier for the zone (e.g., "tutorial_area").
    name : str
        Human-readable display name (e.g., "Tutorial Area").
    spawn_room_name : str, default "Spawn Room"
        Display name for the initial spawn room.
    description : str, optional
        Zone description text.

    Returns
    -------
    MapFile
        A new map file with a single spawn room at origin.

    Examples
    --------
    >>> map_file = create_new_map_file(
    ...     zone_id="my_dungeon",
    ...     name="My Dungeon",
    ...     spawn_room_name="Entrance Hall",
    ... )
    >>> map_file.spawn_room
    'spawn'
    >>> map_file.rooms["spawn"].name
    'Entrance Hall'
    """
    spawn_room = MapRoom(
        id="spawn",
        name=spawn_room_name,
        description="",
        coords=Coords(x=0, y=0, z=0),
    )

    return MapFile(
        id=zone_id,
        name=name,
        description=description,
        spawn_room="spawn",
        rooms={"spawn": spawn_room},
        items={},
    )


def load_zone(path: Path) -> Zone:
    """Load a zone file (game truth format).

    This loads a zone file without coordinates. Use this when you need
    to work with the game truth format directly.

    Parameters
    ----------
    path : Path
        Path to the zone file.

    Returns
    -------
    Zone
        The loaded zone.

    Examples
    --------
    >>> zone = load_zone(Path("data/zones/tutorial.json"))
    """
    content = path.read_text(encoding="utf-8")
    data = json.loads(content)
    return cast(Zone, Zone.model_validate(data))


def get_suggested_export_path(map_path: Path) -> Path:
    """Get the suggested zone export path for a map file.

    Converts ``data/maps/foo.map.json`` to ``data/zones/foo.json``.

    Parameters
    ----------
    map_path : Path
        Path to the map file.

    Returns
    -------
    Path
        Suggested path for the exported zone file.

    Examples
    --------
    >>> get_suggested_export_path(Path("data/maps/tutorial.map.json"))
    PosixPath('data/zones/tutorial.json')
    """
    # Remove .map.json or .json extension
    name = map_path.name
    if name.endswith(".map.json"):
        base_name = name[:-9]  # Remove ".map.json"
    elif name.endswith(".json"):
        base_name = name[:-5]  # Remove ".json"
    else:
        base_name = map_path.stem

    # Construct zones path
    # If in data/maps/, put in data/zones/
    # Otherwise put in same directory with .json extension
    if "maps" in map_path.parts:
        parts = list(map_path.parts)
        maps_index = parts.index("maps")
        parts[maps_index] = "zones"
        return Path(*parts[:-1]) / f"{base_name}.json"
    else:
        return map_path.parent / f"{base_name}.json"
