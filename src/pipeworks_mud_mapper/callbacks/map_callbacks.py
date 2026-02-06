"""Map visualization and interaction callbacks.

This module handles:

- Rendering the flattened map when zone data or visibility filter changes
- Selecting rooms when clicked on the map

The map displays all Z-levels on a single 2D plane with visual differentiation:

- **z=-1 (Down)**: Black filled circles (smallest)
- **z=0 (Ground)**: Blue filled circles (largest)
- **z=+1 (Up)**: White circles with black border (medium)

Component Dependencies
----------------------
**Inputs:**

- ``current-zone-data``: Zone data for rendering
- ``z-level-filter``: List of visible Z-levels (checklist)
- ``selected-room``: Currently selected room
- ``map-graph``: Click events on the map

**Outputs:**

- ``map-graph``: Updated Plotly figure
- ``selected-room``: Room ID from click

Click Selection with Stacked Rooms
----------------------------------
When rooms overlap (same X,Y, different Z), ground level (z=0) receives
clicks first due to render order. To select a lower-level room:

1. Uncheck higher levels in the z-level-filter
2. Click the now-visible lower-level room
3. Re-check levels when done

See Also
--------
- ``components/map_view.py``: Plotly figure creation functions
- ``layout/map_panel.py``: Map panel with filter controls
"""

from typing import Any

from dash import Input, Output, State, callback, ctx, no_update

from pipeworks_mud_mapper.components.map_view import (
    create_map_figure,
    create_map_figure_with_rooms,
)


@callback(
    Output("map-graph", "figure"),
    Input("current-zone-data", "data"),
    Input("z-level-filter", "value"),
    Input("selected-room", "data"),
    Input("z-level-offset-x", "value"),
    Input("z-level-offset-y", "value"),
)
def update_map_with_rooms(
    zone_data: dict | None,
    visible_z_levels: list[int],
    selected_room: str | None,
    visual_offset_x: float | None,
    visual_offset_y: float | None,
) -> Any:
    """Update the map figure when zone data, visibility, or selection changes.

    Re-renders the Plotly figure with rooms from all visible Z-levels,
    displayed on a single 2D plane with visual differentiation by level.

    Parameters
    ----------
    zone_data : dict | None
        Current zone data containing rooms, or None if no zone loaded.
    visible_z_levels : list[int]
        List of Z-levels to display, from the filter checklist.
        Default is all levels: [-1, 0, 1]. Empty list shows base map only.
    selected_room : str | None
        Currently selected room ID, or None. Selected room is highlighted
        in red regardless of its Z-level.
    visual_offset_x : float | None
        X-axis scale factor for Z-level visual offset. Controls horizontal
        separation of stacked rooms.
    visual_offset_y : float | None
        Y-axis scale factor for Z-level visual offset. Controls vertical
        separation of stacked rooms.

    Returns
    -------
    dict
        Plotly figure dictionary for the map graph.

    Rendering Behavior
    ------------------
    - Rooms are rendered in Z-order: z=-1 first, z=+1 second, z=0 last
    - Ground level (z=0) appears on top and receives clicks first
    - Exit lines only connect rooms on the same Z-level
    - Vertical exits (up/down) are shown as "U/D" labels near stacked rooms
    - Hover text includes Z-level information for each room

    Examples
    --------
    Show all levels (default)::

        >>> figure = update_map_with_rooms(zone_data, [-1, 0, 1], None, 1.0)

    Show only ground level::

        >>> figure = update_map_with_rooms(zone_data, [0], None, 1.0)

    Hide ground to select a basement room::

        >>> figure = update_map_with_rooms(zone_data, [-1, 1], "cellar", 1.0)
    """
    # Handle no zone loaded - return empty base map
    if not zone_data:
        return create_map_figure()

    # Get rooms from zone data and render with visibility filter
    rooms = zone_data.get("rooms", {})
    if visual_offset_x is None:
        visual_offset_x = 0.4
    if visual_offset_y is None:
        visual_offset_y = 0.4

    return create_map_figure_with_rooms(
        rooms=rooms,
        visible_z_levels=visible_z_levels,
        selected_room=selected_room,
        visual_offset_x=visual_offset_x,
        visual_offset_y=visual_offset_y,
    )


@callback(
    Output("selected-room", "data"),
    Input("map-graph", "clickData"),
    State("current-zone-data", "data"),
    State("selected-room", "data"),
    prevent_initial_call=True,
)
def handle_map_click(
    click_data: dict | None,
    zone_data: dict | None,
    current_selection: str | None,
) -> Any:
    """Select a room when clicked, or unselect if clicking the same room again.

    Extracts the room ID from the clicked point's text field and
    validates that it exists in the current zone. Clicking on an
    already-selected room toggles the selection off.

    Parameters
    ----------
    click_data : dict | None
        Plotly click event data containing information about the
        clicked point, or None if no click occurred.
    zone_data : dict | None
        Current zone data containing rooms dictionary.
    current_selection : str | None
        Currently selected room ID, used for toggle behavior.

    Returns
    -------
    str | None | no_update
        Room ID if a new room was clicked, None if the same room was clicked
        again (toggle off), or no_update if the click was on a non-room
        element like an exit line.

    Click Handling Details
    ----------------------
    - Room ID is stored in the ``text`` field of Scatter points
    - Clicking an already-selected room clears the selection (toggle)
    - Clicks on exit lines return no_update (hoverinfo="skip")
    - Invalid room IDs (not in zone_data) return no_update

    Stacked Room Selection
    ----------------------
    When rooms are stacked (same X,Y, different Z), the topmost visible
    room receives the click. Due to render order:

    - If z=0 is visible, ground-level room gets the click
    - If z=0 is hidden but z=+1 visible, upper-level room gets the click
    - If only z=-1 is visible, lower-level room gets the click

    To select a specific stacked room, use the z-level-filter to hide
    the levels above it.

    Examples
    --------
    Click data structure from Plotly::

        >>> click_data = {
        ...     "points": [{
        ...         "x": 0,
        ...         "y": 0,
        ...         "text": "spawn",  # Room ID
        ...         "curveNumber": 2,
        ...     }]
        ... }
        >>> handle_map_click(click_data, zone_data, None)
        'spawn'

    Click same room again to unselect::

        >>> handle_map_click(click_data, zone_data, "spawn")
        None
    """
    # Ignore if no click data or no zone loaded
    if not click_data or not zone_data:
        return no_update

    # Extract clicked point information
    points = click_data.get("points", [])
    if not points:
        return no_update

    # Get the first (and typically only) clicked point
    point = points[0]

    # The text field contains the room_id (set in map_view.py _draw_rooms_at_z_level)
    room_id = point.get("text")

    # Validate that this is a real room in the zone
    if room_id and room_id in zone_data.get("rooms", {}):
        # Toggle: if clicking the already-selected room, unselect it
        if room_id == current_selection:
            return None
        return room_id

    # Clicked on something that isn't a room (line, background, etc.)
    return no_update


def _adjust_offset_value(
    triggered_id: str | None,
    current_value: float | None,
    *,
    decrease_id: str,
    increase_id: str,
    step: float = 0.1,
    min_value: float = -5.0,
    max_value: float = 5.0,
) -> float | Any:
    """Adjust an offset value using +/- button identifiers."""
    if current_value is None:
        current_value = 0.4

    if triggered_id == decrease_id:
        new_value = max(min_value, current_value - step)
    elif triggered_id == increase_id:
        new_value = min(max_value, current_value + step)
    else:
        return no_update

    return round(new_value, 1)


@callback(
    Output("z-level-offset-x", "value"),
    Input("z-level-offset-x-decrease", "n_clicks"),
    Input("z-level-offset-x-increase", "n_clicks"),
    State("z-level-offset-x", "value"),
    prevent_initial_call=True,
)
def adjust_z_level_offset_x(
    decrease_clicks: int | None,
    increase_clicks: int | None,
    current_value: float | None,
) -> Any:
    """Adjust the X-axis visual offset via +/- buttons."""
    return _adjust_offset_value(
        ctx.triggered_id,
        current_value,
        decrease_id="z-level-offset-x-decrease",
        increase_id="z-level-offset-x-increase",
    )


@callback(
    Output("z-level-offset-y", "value"),
    Input("z-level-offset-y-decrease", "n_clicks"),
    Input("z-level-offset-y-increase", "n_clicks"),
    State("z-level-offset-y", "value"),
    prevent_initial_call=True,
)
def adjust_z_level_offset_y(
    decrease_clicks: int | None,
    increase_clicks: int | None,
    current_value: float | None,
) -> Any:
    """Adjust the Y-axis visual offset via +/- buttons."""
    return _adjust_offset_value(
        ctx.triggered_id,
        current_value,
        decrease_id="z-level-offset-y-decrease",
        increase_id="z-level-offset-y-increase",
    )
