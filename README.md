# PipeWorks MUD Mapper

Visual authoring tool for creating and editing MUD zone files. Part of the pipe-works ecosystem.

[![Documentation Status](https://readthedocs.org/projects/pipeworks-mud-mapper/badge/?version=latest)](https://pipeworks-mud-mapper.readthedocs.io/en/latest/?badge=latest)

## Overview

**PipeWorks MUD Mapper** provides an interactive map editor built with Dash and Plotly for creating MUD (Multi-User Dungeon) zone files. It generates JSON zone files compatible with the PipeWorks MUD Server.

### Features

- **Visual Map Editor** - Interactive 2D map with Plotly-based rendering
- **Room Management** - Create, edit, and delete rooms with intuitive form
- **Exit System** - Bidirectional exit creation with automatic reverse linking
- **Multi-Level Support** - Z-axis filtering for 3D dungeon visualization
- **Two-File Workflow** - Separate authoring (with coords) and export (without)

### Two-File Workflow

The mapper uses two file types:

- **Map Files** (`data/maps/*.map.json`) - Authoring source with coordinates for visual editing
- **Zone Files** (`data/zones/*.json`) - Game truth without coordinates for MUD server

```
Edit map file  →  Save  →  Export Zone JSON
     ↓              ↓              ↓
Visual coords   Preserved    Coords stripped
for authoring   for editing  for game server
```

## Installation

```bash
pip install -e ".[dev]"
```

## Usage

Run the application:

```bash
python -m pipeworks_mud_mapper
```

Or from code:

```python
from pipeworks_mud_mapper.app import run_app
run_app(debug=True, port=8050)
```

Then open http://127.0.0.1:8050 in your browser.

### Interface

The mapper has a three-column layout:

| Column | Purpose |
|--------|---------|
| Left | File browser - load maps from `data/maps/` |
| Center | Interactive map view with Z-level selector |
| Right | Properties panel for room editing |
| Bottom | Action bar with Save/Export and status |

### Creating a Zone

1. Click **New Map** in the file browser
2. Enter Zone ID (e.g., `my_dungeon`) and Name
3. Click **Create** - spawns with one room at origin
4. Add rooms, connect with exits
5. **Save Map** to preserve your work
6. **Export Zone JSON** when ready for the MUD server

## Documentation

Full documentation: https://pipeworks-mud-mapper.readthedocs.io/

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest

# Run linting
ruff check src/ tests/
black --check src/ tests/

# Format code
black src/ tests/
ruff check --fix src/ tests/
```

### Architecture

```
src/pipeworks_mud_mapper/
├── app.py              # Application entry point
├── layout/             # UI structure (Dash components)
├── callbacks/          # Interactivity (Dash callbacks)
├── services/           # Business logic (pure Python)
├── models/             # Domain models (Pydantic)
├── components/         # Reusable Plotly components
└── utils/              # File I/O utilities
```

## License

GPL-3.0-or-later. See [LICENSE](LICENSE) for details.

## Related Projects

- [pipeworks_mud_server](https://github.com/pipe-works/pipeworks_mud_server) - The Undertaking MUD server
- [pipe-works](https://github.com/pipe-works/pipe-works) - Main project hub
