# PipeWorks MUD Mapper

> A visual authoring tool for creating and editing MUD zone files with an interactive map editor.

[![CI](https://github.com/pipe-works/pipeworks_mud_mapper/actions/workflows/ci.yml/badge.svg)](https://github.com/pipe-works/pipeworks_mud_mapper/actions/workflows/ci.yml)
[![Documentation](https://readthedocs.org/projects/pipeworks-mud-mapper/badge/?version=latest)](https://pipeworks-mud-mapper.readthedocs.io/en/latest/?badge=latest)
[![codecov](https://codecov.io/gh/pipe-works/pipeworks_mud_mapper/branch/main/graph/badge.svg)](https://codecov.io/gh/pipe-works/pipeworks_mud_mapper)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

---

## What is PipeWorks MUD Mapper?

An interactive map editor built with Dash and Plotly for creating MUD (Multi-User Dungeon) zone files. It generates JSON zone files compatible with the [PipeWorks MUD Server](https://github.com/pipe-works/pipeworks_mud_server).

**Features:**

- **Visual Map Editor** - Interactive 2D map with Plotly-based rendering
- **Room Management** - Create, edit, and delete rooms with intuitive forms
- **Exit System** - Bidirectional exit creation with automatic reverse linking
- **Multi-Level Support** - Z-axis filtering for 3D dungeon visualization
- **Two-File Workflow** - Separate authoring (with coords) and export (without)

---

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Run
python -m pipeworks_mud_mapper
```

Open http://127.0.0.1:8050 in your browser.

---

## Two-File Workflow

The mapper distinguishes between authoring files and game files:

| File Type | Location | Purpose |
|-----------|----------|---------|
| **Map Files** | `data/maps/*.map.json` | Authoring source with coordinates |
| **Zone Files** | `data/zones/*.json` | Game truth without coordinates |

```
Edit map file  →  Save  →  Export Zone JSON
     ↓              ↓              ↓
Visual coords   Preserved    Coords stripped
for authoring   for editing  for game server
```

Zone files are what the MUD server consumes. Coordinates are stripped because the game engine operates on topology (connections), not geometry (positions).

---

## Interface

The mapper has a three-column layout:

| Column | Purpose |
|--------|---------|
| **Left** | File browser - load maps from `data/maps/` |
| **Center** | Interactive map view with Z-level selector |
| **Right** | Properties panel for room editing |
| **Bottom** | Action bar with Save/Export and status |

### Creating a Zone

1. Click **New Map** in the file browser
2. Enter Zone ID (e.g., `my_dungeon`) and Name
3. Click **Create** - spawns with one room at origin
4. Add rooms, connect with exits
5. **Save Map** to preserve your work
6. **Export Zone JSON** when ready for the MUD server

---

## Documentation

Full documentation: **[pipeworks-mud-mapper.readthedocs.io](https://pipeworks-mud-mapper.readthedocs.io/)**

- [Usage Guide](https://pipeworks-mud-mapper.readthedocs.io/en/latest/usage.html)
- [File Formats](https://pipeworks-mud-mapper.readthedocs.io/en/latest/zone_format.html)
- [API Reference](https://pipeworks-mud-mapper.readthedocs.io/en/latest/autoapi/index.html)

---

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint and format
ruff check src/ tests/
black src/ tests/
```

### Architecture

```
src/pipeworks_mud_mapper/
├── app.py              # Application entry point (~120 lines)
├── models/             # Domain models (Pydantic)
├── services/           # Business logic (pure Python, no Dash)
├── layout/             # UI structure (Dash components)
├── callbacks/          # Interactivity (Dash callbacks)
├── components/         # Reusable Plotly components
└── utils/              # File I/O utilities
```

The architecture separates concerns for testability: services contain all business logic and can be tested without Dash.

---

## License

GPL-3.0-or-later. See [LICENSE](LICENSE) for details.

---

## Related Projects

- **[pipeworks_mud_server](https://github.com/pipe-works/pipeworks_mud_server)** - The Undertaking MUD server
- **[pipe-works](https://github.com/pipe-works/pipe-works)** - Main project hub
