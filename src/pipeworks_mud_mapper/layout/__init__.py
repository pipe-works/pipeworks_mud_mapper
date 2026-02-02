"""Layout components for PipeWorks MUD Mapper.

This module provides the UI structure (Dash components) for the mapper
application. Layout modules define the visual structure while callbacks
in the callbacks/ module handle interactivity.

Architecture
------------
The application uses a three-column layout plus action bar:

::

    ┌─────────┬─────────────────────────┬───────────┐
    │  File   │                         │  Room     │
    │ Browser │       Map Panel         │Properties │
    │  (2/12) │        (7/12)           │  (3/12)   │
    └─────────┴─────────────────────────┴───────────┘
    │             Action Bar (Save, Status)         │
    └───────────────────────────────────────────────┘

Module Layout
-------------
**file_browser**
    Left column file list and "New Map" button.

**map_panel**
    Center column with Plotly map and Z-level selector.

**properties_panel**
    Right column room editing form with coordinates and exits.

**action_bar**
    Bottom bar with Validate, Export, Save buttons and status indicator.

**main_layout**
    Assembles all components into the complete application layout.

Usage
-----
Import and use in app.py::

    from pipeworks_mud_mapper.layout import create_app_layout

    app.layout = create_app_layout()

Or import individual components::

    from pipeworks_mud_mapper.layout import (
        create_file_browser,
        create_map_panel,
        create_properties_panel,
        create_action_bar,
    )

See Also
--------
- ``callbacks/``: Dash callbacks for interactivity
- ``components/``: Reusable Plotly/Dash components
- ``refactor_01.md``: Architecture decisions and rationale
"""

from pipeworks_mud_mapper.layout.action_bar import create_action_bar
from pipeworks_mud_mapper.layout.file_browser import create_file_browser
from pipeworks_mud_mapper.layout.main_layout import create_app_layout
from pipeworks_mud_mapper.layout.map_panel import create_map_panel
from pipeworks_mud_mapper.layout.properties_panel import create_properties_panel

__all__ = [
    "create_app_layout",
    "create_file_browser",
    "create_map_panel",
    "create_properties_panel",
    "create_action_bar",
]
