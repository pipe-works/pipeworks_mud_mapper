File Formats
============

This document describes the JSON formats used by PipeWorks MUD Mapper.
The mapper uses a two-file workflow with distinct formats for authoring
and game deployment.

Two-File Workflow
-----------------

**Map Files** (``data/maps/*.map.json``)
    Authoring source files with coordinates. Used by the mapper for
    visual editing. These are your working files.

**Zone Files** (``data/zones/*.json``)
    Game truth files without coordinates. Exported for the MUD server.
    The game engine operates on topology (connections), not geometry.

::

    data/
    ├── maps/                 # Authoring source (with coords)
    │   ├── dungeon.map.json
    │   └── town.map.json
    │
    └── zones/                # Game truth (exported, no coords)
        ├── dungeon.json
        └── town.json

Map File Format
---------------

Map files are the authoring source and include coordinates for visualization.

**Extension:** ``.map.json``

**Location:** ``data/maps/``

Basic Structure
^^^^^^^^^^^^^^^

.. code-block:: json

    {
        "id": "zone_identifier",
        "name": "Human Readable Name",
        "description": "Optional description text",
        "spawn_room": "starting_room_id",
        "rooms": {
            "room_id": {
                "id": "room_id",
                "name": "Room Name",
                "description": "Room description",
                "coords": [0, 0, 0],
                "exits": {"north": "other_room"},
                "items": []
            }
        },
        "items": {}
    }

**Key difference from zone files:** Rooms include ``coords`` field.

Zone File Format
----------------

Zone files are game truth without coordinates. They are exported from
map files and consumed by the MUD server.

**Extension:** ``.json``

**Location:** ``data/zones/``

Basic Structure
^^^^^^^^^^^^^^^

.. code-block:: json

    {
        "id": "zone_identifier",
        "name": "Human Readable Name",
        "description": "Optional description text",
        "spawn_room": "starting_room_id",
        "rooms": {
            "room_id": {
                "id": "room_id",
                "name": "Room Name",
                "description": "Room description",
                "exits": {"north": "other_room"},
                "items": []
            }
        },
        "items": {}
    }

**Key difference from map files:** No ``coords`` field in rooms.

Top-Level Fields
----------------

These fields are common to both map and zone files:

id
    **Required**. Unique identifier for the zone. Should contain only
    lowercase letters, numbers, and underscores. Used as the filename
    (e.g., ``my_dungeon`` becomes ``my_dungeon.json`` or ``my_dungeon.map.json``).

name
    **Required**. Human-readable display name for the zone.

description
    *Optional*. Description text for the zone.

spawn_room
    **Required**. Room ID where players enter the zone. Must reference
    an existing room in the ``rooms`` dictionary.

rooms
    **Required**. Dictionary mapping room IDs to room objects.

items
    *Optional*. Dictionary of zone-level item definitions (future use).

Room Fields
-----------

id
    **Required**. Unique identifier for the room within this zone.
    Should match the key used in the ``rooms`` dictionary.

name
    **Required**. Human-readable display name for the room.

description
    *Optional*. Description text shown when a player enters the room.

coords
    **Map files only**. Array of three integers ``[x, y, z]``
    representing the room's position in 3D space. Used by the mapper
    for rendering. Stripped when exporting to zone files.

exits
    *Optional*. Dictionary mapping direction names to target room IDs.
    Valid directions: ``north``, ``south``, ``east``, ``west``, ``up``, ``down``.

items
    *Optional*. Array of item IDs present in this room.

Coordinate System
-----------------

The mapper uses a 3D Cartesian coordinate system (map files only):

============  ====================  ====================
Axis          Positive Direction    Negative Direction
============  ====================  ====================
X             East (+X)             West (-X)
Y             North (+Y)            South (-Y)
Z             Up (+Z)               Down (-Z)
============  ====================  ====================

The spawn room is conventionally placed at origin ``[0, 0, 0]``.

Exit Directions
---------------

Standard exit directions and their coordinate implications:

==========  =================
Direction   Typical Offset
==========  =================
north       Y increases
south       Y decreases
east        X increases
west        X decreases
up          Z increases
down        Z decreases
==========  =================

Cross-Zone Exits
----------------

To create exits that lead to other zones, use the format ``zone_id:room_id``:

.. code-block:: json

    {
        "exits": {
            "north": "other_zone:entrance"
        }
    }

Cross-zone exits are not visualized on the map but are preserved in both
map and zone files.

Example Map File
----------------

A complete example of a map file (``data/maps/tutorial_area.map.json``):

.. code-block:: json

    {
        "id": "tutorial_area",
        "name": "Tutorial Area",
        "description": "A small area for new players to learn the basics.",
        "spawn_room": "spawn",
        "rooms": {
            "spawn": {
                "id": "spawn",
                "name": "Arrival Chamber",
                "description": "You find yourself in a dimly lit stone chamber.",
                "coords": [0, 0, 0],
                "exits": {
                    "north": "hallway"
                },
                "items": []
            },
            "hallway": {
                "id": "hallway",
                "name": "Long Hallway",
                "description": "A narrow hallway stretches before you.",
                "coords": [0, 1, 0],
                "exits": {
                    "south": "spawn",
                    "north": "exit_room"
                },
                "items": []
            },
            "exit_room": {
                "id": "exit_room",
                "name": "Exit Portal",
                "description": "A shimmering portal leads to the main world.",
                "coords": [0, 2, 0],
                "exits": {
                    "south": "hallway",
                    "north": "main_world:entrance"
                },
                "items": []
            }
        },
        "items": {}
    }

Example Zone File
-----------------

The same zone exported (``data/zones/tutorial_area.json``):

.. code-block:: json

    {
        "id": "tutorial_area",
        "name": "Tutorial Area",
        "description": "A small area for new players to learn the basics.",
        "spawn_room": "spawn",
        "rooms": {
            "spawn": {
                "id": "spawn",
                "name": "Arrival Chamber",
                "description": "You find yourself in a dimly lit stone chamber.",
                "exits": {
                    "north": "hallway"
                },
                "items": []
            },
            "hallway": {
                "id": "hallway",
                "name": "Long Hallway",
                "description": "A narrow hallway stretches before you.",
                "exits": {
                    "south": "spawn",
                    "north": "exit_room"
                },
                "items": []
            },
            "exit_room": {
                "id": "exit_room",
                "name": "Exit Portal",
                "description": "A shimmering portal leads to the main world.",
                "exits": {
                    "south": "hallway",
                    "north": "main_world:entrance"
                },
                "items": []
            }
        },
        "items": {}
    }

Note: The only difference is the absence of ``coords`` fields.

Validation Rules
----------------

When creating zones, ensure:

1. All room IDs are unique within the zone
2. All exit targets reference existing rooms (or valid cross-zone references)
3. The spawn_room references an existing room
4. Room IDs start with a letter and contain only alphanumeric characters and underscores
5. Coordinates are integers (not floats) - map files only

The mapper validates these rules when saving and shows errors for violations.
