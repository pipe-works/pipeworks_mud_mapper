"""
Utility modules for PipeWorks MUD Mapper.

This module provides core utilities for working with MUD zone data,
including file I/O, coordinate system definitions, and spatial queries.

Modules
-------
zone_io
    Zone file loading, saving, and manipulation utilities.
    Defines the coordinate system and direction mappings.

Exported Functions
------------------
auto_layout_rooms(zone_data) -> dict
    Automatically assign coordinates to rooms based on exit directions.

create_blank_zone(zone_id, zone_name, description) -> dict
    Create a new empty zone with a spawn room.

list_zone_files(directory) -> list[Path]
    List all .json zone files in a directory.

load_zone_json(file_path) -> dict
    Load zone data from a JSON file.

save_zone_json(zone_data, file_path) -> None
    Save zone data to a JSON file.

Constants (from zone_io)
------------------------
DIRECTION_OFFSETS : dict[str, tuple[int, int, int]]
    Direction to coordinate offset mapping.

DIRECTION_SHORT : dict[str, str]
    Direction to abbreviation mapping (N, E, S, W, U, D).

SHORT_TO_DIRECTION : dict[str, str]
    Abbreviation to direction mapping.

OPPOSITE_DIRECTION : dict[str, str]
    Direction to opposite direction mapping.

Usage
-----
Import utilities directly from this package::

    from pipeworks_mud_mapper.utils import (
        create_blank_zone,
        save_zone_json,
        load_zone_json,
    )

Or access constants from zone_io::

    from pipeworks_mud_mapper.utils.zone_io import DIRECTION_OFFSETS
"""

from pipeworks_mud_mapper.utils.zone_io import (
    auto_layout_rooms,
    create_blank_zone,
    list_zone_files,
    load_zone_json,
    save_zone_json,
)

__all__ = [
    "auto_layout_rooms",
    "create_blank_zone",
    "list_zone_files",
    "load_zone_json",
    "save_zone_json",
]
