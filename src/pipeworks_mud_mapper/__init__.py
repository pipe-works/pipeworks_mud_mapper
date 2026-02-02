"""
PipeWorks MUD Mapper - Procedural MUD world mapping and visualization tool.

This package provides a visual zone editor for creating and editing MUD
(Multi-User Dungeon) world files. It generates JSON zone files compatible
with the PipeWorks MUD Server.

Features
--------
- Visual 2D map editor with Plotly-based rendering
- Room creation and editing with properties panel
- Exit management with bidirectional connection support
- Multi-level Z-axis support for 3D dungeons
- Auto-layout from exit definitions
- JSON zone file I/O

Architecture
------------
The package is organized into:

- **app**: Main Dash application and callbacks
- **components**: Reusable UI components (map view, modals)
- **utils**: Zone file I/O and spatial utilities

Quick Start
-----------
Run the mapper from the command line::

    python -m pipeworks_mud_mapper

Or import and run programmatically::

    from pipeworks_mud_mapper.app import run_app
    run_app(debug=True, port=8050)

Zone File Format
----------------
Zone files are JSON documents with the following structure::

    {
        "id": "zone_id",
        "name": "Zone Name",
        "description": "Description text",
        "spawn_room": "room_id",
        "rooms": {
            "room_id": {
                "id": "room_id",
                "name": "Room Name",
                "description": "Room description",
                "coords": [x, y, z],
                "exits": {"direction": "target_room_id"},
                "items": []
            }
        },
        "items": {}
    }

License
-------
GPL-3.0-or-later

See Also
--------
- PipeWorks MUD Server: https://github.com/pipe-works/pipeworks_mud_server
- Pipe-Works Organization: https://github.com/pipe-works
"""

__version__ = "0.0.3"
