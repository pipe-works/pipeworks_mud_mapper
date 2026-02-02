Usage Guide
===========

This guide covers how to use the PipeWorks MUD Mapper to create and edit
map files for your MUD world.

Two-File Workflow
-----------------

The mapper distinguishes between two file types:

**Map Files** (``data/maps/*.map.json``)
    Authoring source files that include coordinates for visual editing.
    These are your working files. Create and edit maps here.

**Zone Files** (``data/zones/*.json``)
    Game truth files exported without coordinates. These are what the
    MUD server consumes. Coordinates are stripped because the game engine
    operates on topology (connections), not geometry (positions).

Typical workflow::

    1. Create/edit map file  →  data/maps/my_zone.map.json
    2. Save changes          →  Preserves coordinates for future editing
    3. Export Zone JSON      →  data/zones/my_zone.json (coords stripped)

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
    Lists available map files from the ``data/maps/`` directory. Click a file
    to load it. Also contains:

    - **New Map**: Create a new map file
    - **Save Map**: Save authoring file (with coordinates)
    - **Export Zone**: Export game truth file (no coordinates)
    - **Validate Zone**: Check for connectivity and consistency issues
    - **Status**: Shows save state (unsaved/saved)

**Center Column - Map View**
    Interactive Plotly graph showing rooms as nodes and exits as connecting
    lines. Click rooms to select them. Use the Z-level selector below the
    map to view different floors.

**Right Column - Properties Panel**
    Form for editing room properties. Shows room ID, name, description,
    coordinates, and exit checkboxes. Also includes the Ollama LLM integration
    section for generating room descriptions.

Creating a New Map
------------------

1. Click the **New Map** button in the file browser
2. Enter a **Zone ID** (lowercase, no spaces, e.g., ``my_dungeon``)
3. Enter a **Zone Name** (display name, e.g., ``My Dungeon``)
4. Optionally add a **Description**
5. Click **Create**

The new map file is saved to ``data/maps/`` and appears in the file browser.
Click it to load and start editing.

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

Generating Descriptions with Ollama
-----------------------------------

The mapper integrates with a local Ollama server to generate room descriptions
using LLMs.

**Setup**

1. Install Ollama from https://ollama.ai
2. Pull a model (e.g., ``ollama pull llama3.2``)
3. Ensure Ollama is running (default: http://localhost:11434)

**Using the LLM Generator**

1. In the Properties Panel, expand the "LLM Description Generator" section
2. Enter the Ollama server URL (default: http://localhost:11434)
3. Click **Refresh Models** to load available models
4. Select a model from the dropdown
5. Customize the system prompt (optional) and enter a user prompt
6. Click **Generate** to create a description
7. Review the generated text in the response area
8. Click **Send to Description** to apply it to the selected room

**Tips**

- The system prompt sets the tone and style for generated descriptions
- The user prompt should describe what you want (e.g., "A dark cellar with cobwebs")
- You can edit the generated text before sending it to the room
- Generation marks the room as having unsaved changes

Saving and Exporting
--------------------

**Saving Maps**

Changes are tracked but not automatically saved. The status indicator at
the bottom shows:

- **Gray dot**: No file loaded
- **Yellow dot**: Unsaved changes (Save enabled, Export disabled)
- **Green dot**: All changes saved (Save disabled, Export enabled)

Click **Save Map** to save changes to the map file (``data/maps/*.map.json``).

**Exporting Zone Files**

Once your map is saved, click **Export Zone JSON** to create the game truth file:

- Exported to ``data/zones/{zone_id}.json``
- Coordinates are stripped (game engine doesn't need them)
- Room IDs, names, descriptions, and exits are preserved

The exported zone file is what the MUD server consumes.

Validating Your Map
-------------------

The **Validate Zone** button runs comprehensive checks on your map to catch
common issues before export.

**Validation Categories**

*Connectivity*
    - **Broken exits**: Exits pointing to non-existent rooms (ERROR)
    - **Unreachable rooms**: Rooms with no path from spawn (WARNING)
    - **Dead ends**: Rooms with no exits (INFO)

*Exit Consistency*
    - **Asymmetric exits**: Room A→B exists but B→A doesn't (INFO)
    - **Direction mismatch**: Exit says "north" but coordinates suggest "south" (WARNING)

*Language-Direction*
    - **Vertical naming conflicts**: Room named "Upper Landing" not reached via "up" (INFO)

**Severity Levels**

- **ERROR**: Must be fixed before export (e.g., broken references)
- **WARNING**: Should be reviewed but may be intentional
- **INFO**: Informational only (e.g., intentional one-way doors)

**Validation Report**

When you validate, a JSON report is written to ``data/validation/{zone_id}.validation.json``.
This file contains:

- Timestamp of validation
- Summary counts by severity
- Pass/fail status (passes if no errors)
- Detailed list of all warnings

The report file is useful for CI/CD integration or keeping records.

**Using Validation**

1. Load a map file
2. Click **Validate Zone** in the file browser
3. Review the results modal showing any issues
4. Click on room IDs in the modal to select them on the map
5. Fix issues and re-validate as needed
6. Export once validation passes

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

**Export When Ready**
    Export zone files when your map is ready for testing in the MUD server.
    Keep editing the map file; re-export when you make changes.

**Version Control**
    Both map files and zone files are JSON and work well with git.
    Commit map files as your source of truth; zone files are derived.
