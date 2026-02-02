Zone File Format
================

This document describes the JSON format used by PipeWorks MUD Mapper for
zone files. These files are compatible with the PipeWorks MUD Server.

Overview
--------

Zone files are JSON documents that define a collection of connected rooms.
Each zone has a unique identifier, metadata, and a dictionary of rooms.

Basic Structure
---------------

.. code-block:: json

    {
        "id": "zone_identifier",
        "name": "Human Readable Name",
        "description": "Optional description text",
        "spawn_room": "starting_room_id",
        "rooms": {
            "room_id": {}
        },
        "items": {}
    }

Top-Level Fields
----------------

id
    **Required**. Unique identifier for the zone. Should contain only
    lowercase letters, numbers, and underscores. Used as the filename
    (e.g., ``my_dungeon`` becomes ``my_dungeon.json``).

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

Room Structure
--------------

Each room is a JSON object with the following fields:

.. code-block:: json

    {
        "id": "room_identifier",
        "name": "Room Name",
        "description": "Room description text",
        "coords": [0, 0, 0],
        "exits": {
            "north": "target_room_id",
            "east": "another_room_id"
        },
        "items": []
    }

Room Fields
^^^^^^^^^^^

id
    **Required**. Unique identifier for the room within this zone.
    Should match the key used in the ``rooms`` dictionary.

name
    **Required**. Human-readable display name for the room.

description
    *Optional*. Description text shown when a player enters the room.

coords
    **Required** for visualization. Array of three integers ``[x, y, z]``
    representing the room's position in 3D space. Used by the mapper for
    rendering but not required by the MUD server.

exits
    *Optional*. Dictionary mapping direction names to target room IDs.
    Valid directions: ``north``, ``south``, ``east``, ``west``, ``up``, ``down``.

items
    *Optional*. Array of item IDs present in this room.

Coordinate System
-----------------

The mapper uses a 3D Cartesian coordinate system:

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

Cross-zone exits are not visualized on the map but are preserved in the
zone file.

Example Zone
------------

A complete example of a small zone:

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

Validation Rules
----------------

When creating zones, ensure:

1. All room IDs are unique within the zone
2. All exit targets reference existing rooms (or valid cross-zone references)
3. The spawn_room references an existing room
4. Room IDs start with a letter and contain only alphanumeric characters and underscores
5. Coordinates are integers (not floats)

The mapper validates these rules when saving and shows errors for violations.
