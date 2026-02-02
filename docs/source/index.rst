PipeWorks MUD Mapper Documentation
===================================

.. image:: https://readthedocs.org/projects/pipeworks-mud-mapper/badge/?version=latest
   :target: https://pipeworks-mud-mapper.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

**PipeWorks MUD Mapper** is a procedural MUD world mapping and visualization tool.
It provides a visual zone editor for creating and editing MUD (Multi-User Dungeon)
world files, generating JSON zone files compatible with the PipeWorks MUD Server.

Features
--------

* **Visual Map Editor** - Interactive 2D map with Plotly-based rendering
* **Room Management** - Create, edit, and delete rooms with properties panel
* **Exit System** - Bidirectional exit creation with automatic reverse linking
* **Multi-Level Support** - Z-axis filtering for 3D dungeon visualization
* **Auto-Layout** - Automatic coordinate assignment from exit definitions
* **JSON Export** - Save zones as JSON files for MUD server integration

Quick Start
-----------

Install the mapper::

    pip install pipeworks-mud-mapper

Run the application::

    python -m pipeworks_mud_mapper

Or from code::

    from pipeworks_mud_mapper.app import run_app
    run_app(debug=True, port=8050)

Then open http://127.0.0.1:8050 in your browser.

Coordinate System
-----------------

The mapper uses a 3D Cartesian coordinate system:

* **X-axis**: East (+) / West (-)
* **Y-axis**: North (+) / South (-)
* **Z-axis**: Up (+) / Down (-)

The spawn room is typically placed at origin (0, 0, 0).

Zone File Format
----------------

Zone files are JSON documents with this structure::

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

Contents
--------

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   usage
   zone_format

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   autoapi/index

.. toctree::
   :maxdepth: 1
   :caption: Project

   changelog


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
