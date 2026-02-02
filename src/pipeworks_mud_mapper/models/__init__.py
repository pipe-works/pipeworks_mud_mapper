"""Domain models for PipeWorks MUD Mapper.

This module provides Pydantic models that define the core data structures used
throughout the mapper application. These models serve several purposes:

1. **Type Safety**: Catch data errors at validation time rather than runtime
2. **Documentation**: Models serve as executable documentation of the data schema
3. **Serialization**: Automatic JSON serialization/deserialization
4. **IDE Support**: Enable autocompletion and type checking

Architecture
------------
The models are organized to support the two-file workflow defined in
``goblin_cartography.md``:

- **Zone** (game truth): What the MUD server needs - rooms, exits, items.
  No coordinates. This is the "build artifact" that gets deployed.

- **MapFile** (authoring source): What the mapper tool works with - everything
  in Zone plus coordinates and authoring metadata. This is the source of truth
  during map creation.

The key insight is that coordinates are "authoring scaffolding" - they help
humans visualize and validate the map, but the game engine doesn't use them.
Movement in a MUD is purely topological (room A connects to room B via "north"),
not metric.

Model Hierarchy
---------------
::

    MapFile (authoring)
        │
        ├── MapRoom (has coords)
        │   └── exits: dict[Direction, str]
        │
        └── to_zone() ──► Zone (game truth)
                            │
                            └── Room (no coords)
                                └── exits: dict[Direction, str]

Usage
-----
Loading a map file for editing::

    from pipeworks_mud_mapper.models import MapFile

    map_file = MapFile.model_validate_json(path.read_text())
    # Edit rooms, exits, etc.
    path.write_text(map_file.model_dump_json(indent=2))

Exporting to zone file (strips coordinates)::

    zone = map_file.to_zone()
    zone_path.write_text(zone.model_dump_json(indent=2))

See Also
--------
- ``goblin_cartography.md`` Section 2.3: Where Coordinates Live
- ``goblin_cartography.md`` Section 2.5: The Map File Format

Notes
-----
Direction is constrained to the six valid MUD directions: north, south, east,
west, up, down. This matches the decision in ``goblin_cartography.md`` Section
1.7 to use 6 directions (not 4), as up/down are semantically distinct from
north/south - they represent vertical traversal (stairs, ladders, trapdoors).
"""

from pipeworks_mud_mapper.models.map_file import MapFile
from pipeworks_mud_mapper.models.room import Coords, Direction, MapRoom, Room
from pipeworks_mud_mapper.models.zone import Zone

__all__ = [
    "Coords",
    "Direction",
    "MapRoom",
    "Room",
    "Zone",
    "MapFile",
]
