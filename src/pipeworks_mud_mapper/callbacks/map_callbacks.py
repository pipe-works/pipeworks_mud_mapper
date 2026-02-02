"""Map visualization and interaction callbacks.

This module handles:

- Rendering the map when zone data or Z-level changes
- Selecting rooms when clicked on the map

Component Dependencies
----------------------
**Inputs:**
- ``current-zone-data``: Zone data for rendering
- ``z-level-selector``: Current Z-level filter
- ``selected-room``: Currently selected room
- ``map-graph``: Click events on the map

**Outputs:**
- ``map-graph``: Updated Plotly figure
- ``selected-room``: Room ID from click

See Also
--------
- ``components/map_view.py``: Plotly figure creation functions
"""

from typing import Any

from dash import Input, Output, State, callback, no_update

from pipeworks_mud_mapper.components.map_view import (
    create_map_figure,
    create_map_figure_with_rooms,
)


@callback(
    Output("map-graph", "figure"),
    Input("current-zone-data", "data"),
    Input("z-level-selector", "value"),
    Input("selected-room", "data"),
)
def update_map_with_rooms(zone_data: dict | None, z_level: int, selected_room: str | None) -> Any:
    """Update the map figure when zone data, Z-level, or selection changes.

    Re-renders the Plotly figure with current rooms filtered to the
    selected Z-level, highlighting the selected room if any.

    Parameters
    ----------
    zone_data : dict | None
        Current zone data, or None if no zone loaded.
    z_level : int
        Currently selected Z-level (-1, 0, or 1).
    selected_room : str | None
        Currently selected room ID, or None.

    Returns
    -------
    dict
        Plotly figure dictionary for the map graph.
    """
    if not zone_data:
        return create_map_figure(z_level=z_level)

    rooms = zone_data.get("rooms", {})
    return create_map_figure_with_rooms(rooms=rooms, z_level=z_level, selected_room=selected_room)


@callback(
    Output("selected-room", "data"),
    Input("map-graph", "clickData"),
    State("current-zone-data", "data"),
    prevent_initial_call=True,
)
def handle_map_click(click_data: dict | None, zone_data: dict | None) -> Any:
    """Select a room when it is clicked on the map.

    Extracts the room ID from the clicked point's text field and
    validates that it exists in the current zone.

    Parameters
    ----------
    click_data : dict | None
        Plotly click event data.
    zone_data : dict | None
        Current zone data.

    Returns
    -------
    str | None
        Room ID if valid room clicked, or no_update.

    Notes
    -----
    - Room ID is stored in the text field of Scatter points
    - Clicks on non-room elements (lines, empty space) are ignored
    """
    if not click_data or not zone_data:
        return no_update

    # Get clicked point info
    points = click_data.get("points", [])
    if not points:
        return no_update

    point = points[0]
    # The text field contains the room_id (set in map_view.py)
    room_id = point.get("text")
    if room_id and room_id in zone_data.get("rooms", {}):
        return room_id

    return no_update
