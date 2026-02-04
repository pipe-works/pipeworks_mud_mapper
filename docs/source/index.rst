PipeWorks MUD Mapper Documentation
===================================

.. image:: https://readthedocs.org/projects/pipeworks-mud-mapper/badge/?version=latest
   :target: https://pipeworks-mud-mapper.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

**PipeWorks MUD Mapper** is a visual authoring tool for creating and editing
MUD (Multi-User Dungeon) zone files. It provides an interactive map editor
built with Dash and Plotly, generating JSON zone files compatible with the
PipeWorks MUD Server.

Features
--------

* **Visual Map Editor** - Interactive 2D map with Plotly-based rendering
* **Room Management** - Create, edit, and delete rooms with intuitive form
* **Exit System** - Bidirectional exit creation with automatic reverse linking
* **Multi-Level Support** - Z-axis filtering for 3D dungeon visualization
* **Two-File Workflow** - Separate authoring (with coords) and export (without)
* **Validation** - Check for connectivity, consistency, and language-direction issues
* **LLM Integration** - Generate room descriptions using local Ollama server
* **Description Validator** - Advisory checks for LLM prose constraints
* **JSON Schema** - Editor validation support for map files

Two-File Workflow
-----------------

The mapper distinguishes between two file types:

**Map Files** (``data/maps/*.map.json``)
    Authoring source files that include coordinates for visual editing.
    These are your working files.

**Zone Files** (``data/zones/*.json``)
    Game truth files exported without coordinates. These are what the
    MUD server consumes. Coordinates are stripped because the game engine
    operates on topology (connections), not geometry (positions).

Workflow::

    Edit map file  →  Save  →  Export Zone JSON
         ↓              ↓              ↓
    Visual coords   Preserved    Coords stripped
    for authoring   for editing  for game server

Quick Start
-----------

Install the mapper::

    pip install -e ".[dev]"

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

Architecture
------------

The mapper follows a modular architecture::

    src/pipeworks_mud_mapper/
    ├── app.py              # Application entry point
    ├── layout/             # UI structure (Dash components)
    ├── callbacks/          # Interactivity (Dash callbacks)
    ├── services/           # Business logic (pure Python)
    ├── models/             # Domain models (Pydantic)
    ├── components/         # Reusable Plotly components
    └── utils/              # File I/O utilities

This separation enables:

* **Testability** - Services can be tested without Dash
* **Maintainability** - Clear boundaries between concerns
* **Extensibility** - New features can be added in isolation

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
