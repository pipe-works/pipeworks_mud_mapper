Usage Guide
===========

This guide covers how to use the PipeWorks MUD Mapper to create and edit
zone files for your MUD world.

Starting the Application
------------------------

From the command line::

    python -m pipeworks_mud_mapper

Or with custom settings::

    python -c "from pipeworks_mud_mapper.app import run_app; run_app(debug=False, port=8080)"

The application will be available at http://127.0.0.1:8050 (or your custom port).

Interface Overview
------------------

The mapper has a three-column layout:

**Left Column - File Browser**
    Lists available zone files in the ``data/`` directory. Click a file to
    load it. Use "New Map" to create a new zone.

**Center Column - Map View**
    Interactive Plotly graph showing rooms as nodes and exits as connecting
    lines. Click rooms to select them. Use the Z-level selector below the
    map to view different floors.

**Right Column - Properties Panel**
    Form for editing room properties. Shows room ID, name, description,
    coordinates, and exit checkboxes.

Creating a New Zone
-------------------

1. Click the **New Map** button in the file browser
2. Enter a **Zone ID** (lowercase, no spaces, e.g., ``my_dungeon``)
3. Enter a **Zone Name** (display name, e.g., ``My Dungeon``)
4. Optionally add a **Description**
5. Click **Create**

The new zone file is saved to the ``data/`` directory and appears in the
file browser. Click it to load and start editing.

Adding Rooms
------------

1. Click **New Room** button in the properties panel
2. Enter a unique **Room ID** (e.g., ``hallway_north``)
3. Enter a **Room Name** (e.g., ``Northern Hallway``)
4. Add a **Description** (optional)
5. Set **Coordinates** (X, Y, Z) to position the room on the map
6. Click **Add Room**

The room appears on the map at the specified coordinates.

Editing Rooms
-------------

1. Click a room on the map to select it (turns red)
2. The properties panel fills with the room's current values
3. Modify the name, description, or coordinates
4. Click **Update** to save changes

Note: Room ID cannot be changed after creation.

Managing Exits
--------------

Exits connect rooms together. The mapper creates bidirectional exits by default.

**Adding Exits**

1. Select a room on the map
2. Check the direction checkboxes (N, E, S, W, U, D) in the Exits section
3. The mapper finds the nearest room in that direction and creates:

   - An exit from the current room to the target
   - A reverse exit from the target back to current room

4. If no room exists in that direction, the checkbox unchecks and shows a warning

**Removing Exits**

1. Select a room with exits
2. Uncheck the direction checkbox
3. The exit is removed (but the reverse exit on the other room remains)

To create one-way exits, add the exit, then select the target room and
uncheck the reverse direction.

Saving Changes
--------------

Changes are tracked but not automatically saved. The status indicator at
the bottom shows:

- **Gray dot**: No file loaded
- **Yellow dot**: Unsaved changes
- **Green dot**: All changes saved

Click **Save Map** to save changes to the zone file.

Keyboard Shortcuts
------------------

Currently, the mapper is mouse-driven. Keyboard shortcuts may be added
in future versions.

Tips and Best Practices
-----------------------

**Room Naming**
    Use consistent naming conventions for room IDs. Consider prefixing
    with area names (e.g., ``tavern_common_room``, ``tavern_kitchen``).

**Coordinate Planning**
    Plan your coordinate grid before building. Common approaches:

    - Unit spacing: Each room 1 unit apart
    - Grid spacing: Rooms at 5-unit intervals
    - Logical spacing: Match the "feel" of distances

**Z-Levels**
    Use Z-levels for multi-story buildings, dungeons, or elevation changes.
    Connect levels with "up" and "down" exits.

**Incremental Saving**
    Save frequently to avoid losing work. The mapper doesn't auto-save.
