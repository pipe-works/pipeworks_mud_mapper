"""
UI components for the PipeWorks MUD Mapper.

This module provides reusable UI components for the mapper application,
built using Dash and Plotly for interactive visualization.

Components
----------
map_view
    Plotly-based map visualization with room nodes and exit lines.
    Supports multi-level Z-axis filtering and room selection.

new_map_modal
    Bootstrap modal dialog for creating new zone files.
    Collects zone ID, name, and description from user.

Exported Functions
------------------
create_map_figure(z_level) -> go.Figure
    Create an empty map canvas with grid and crosshair.

create_map_figure_with_rooms(rooms, z_level, selected_room) -> go.Figure
    Create a map with rooms and exits rendered.

create_new_map_modal() -> dbc.Modal
    Create the "New Map" modal dialog component.

Usage
-----
Import components directly from this package::

    from pipeworks_mud_mapper.components import (
        create_map_figure,
        create_map_figure_with_rooms,
        create_new_map_modal,
    )

Or import the specific module::

    from pipeworks_mud_mapper.components.map_view import create_map_figure
"""

from pipeworks_mud_mapper.components.map_view import (
    create_map_figure,
    create_map_figure_with_rooms,
)
from pipeworks_mud_mapper.components.new_map_modal import create_new_map_modal

__all__ = ["create_map_figure", "create_map_figure_with_rooms", "create_new_map_modal"]
