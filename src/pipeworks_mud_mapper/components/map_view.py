"""
Plotly-based map visualization component for the MUD Mapper.

This module provides the core visualization functions for rendering MUD zone
maps using Plotly. It creates interactive 2D map views that display rooms
as nodes and exits as connecting lines, with support for:

- **Flattened multi-level display**: All Z-levels shown on a single 2D plane
- **Visual Z-level differentiation**: Size and color distinguish floor levels
- **Room selection highlighting**: Selected room shown in red
- **Exit visualization**: Lines for cardinal directions, labels for up/down
- **Interactive pan, zoom, and hover tooltips**

Design Principles
-----------------
1. **Flattened View**: All rooms rendered on one plane regardless of Z
2. **Z-Ordered Rendering**: Rooms drawn back-to-front so ground level is clickable
3. **Separation of Concerns**: Base figure creation separate from room rendering
4. **Graceful Degradation**: Handles missing data, empty rooms, invalid exits
5. **Deterministic Output**: Same inputs produce identical figures

Coordinate System
-----------------
The map follows standard cartographic conventions:

- **X-axis**: East (+) / West (-), displayed left-to-right
- **Y-axis**: North (+) / South (-), displayed bottom-to-top
- **Z-axis**: Represented by visual styling (size/color), not position

The coordinate range is -20 to +20 on both axes, with gridlines every 5 units.

Visual Design
-------------
Rooms are styled by Z-level for easy identification:

- **z=-1 (Down)**: Black filled, 14px (smallest) - cellars, basements
- **z=+1 (Up)**: White with black border, 18px (medium) - towers, attics
- **z=0 (Ground)**: Blue filled, 20px (largest) - main floor
- **Selected**: Red, regardless of Z-level

Exit connections:

- **Cardinal exits (N/E/S/W)**: Gray lines between rooms on same Z-level
- **Vertical exits (U/D)**: Text labels ("U", "D", or "U/D") near stacked rooms
- **Crosshair**: Dashed gray lines at origin for orientation

Constants
---------
Z_LEVEL_STYLES : dict[int, dict]
    Visual styling for each Z-level (size, color, border)
Z_RENDER_ORDER : list[int]
    Order in which Z-levels are rendered (back to front)
SELECTED_ROOM_COLOR : str
    Color for highlighted/selected rooms

Functions
---------
create_map_figure(title) -> go.Figure
    Create empty map canvas with grid and crosshair
create_map_figure_with_rooms(rooms, visible_z_levels, selected_room) -> go.Figure
    Create map with rooms and exits rendered across multiple Z-levels

Internal Functions
------------------
_group_rooms_by_z_level(rooms, visible_z_levels) -> dict
    Group rooms into buckets by their Z coordinate
_find_stacked_positions(rooms, visible_z_levels) -> dict
    Find X,Y positions with rooms at multiple Z-levels
_draw_all_exit_lines(fig, rooms, visible_z_levels) -> None
    Draw connecting lines for cardinal exits
_draw_rooms_at_z_level(fig, rooms_at_level, z_level, selected_room) -> None
    Render rooms for a single Z-level as a Scatter trace
_add_vertical_exit_labels(fig, stacked_positions, rooms) -> None
    Add "U/D" labels near stacked rooms with vertical exits

Usage
-----
Create an empty map canvas::

    >>> from pipeworks_mud_mapper.components.map_view import create_map_figure
    >>> fig = create_map_figure()
    >>> fig.show()  # Opens in browser

Render rooms from all Z-levels::

    >>> from pipeworks_mud_mapper.components.map_view import (
    ...     create_map_figure_with_rooms
    ... )
    >>> rooms = {
    ...     "ground": {"name": "Ground", "coords": [0, 0, 0], "exits": {"down": "cellar"}},
    ...     "cellar": {"name": "Cellar", "coords": [0, 0, -1], "exits": {"up": "ground"}},
    ... }
    >>> fig = create_map_figure_with_rooms(rooms, selected_room="ground")
    >>> fig.show()

Filter to specific Z-levels::

    >>> fig = create_map_figure_with_rooms(rooms, visible_z_levels=[0])  # Ground only

Integration with Dash::

    >>> import dash
    >>> from dash import dcc
    >>> fig = create_map_figure_with_rooms(rooms)
    >>> graph = dcc.Graph(figure=fig, id="map-graph")

Architecture
------------
The module uses a layered rendering approach:

1. **Base Figure** (create_map_figure)
   - Creates the canvas with grid, crosshair, and axis labels
   - Fixed dimensions (700x650) to prevent layout thrashing

2. **Exit Lines** (_draw_all_exit_lines)
   - Drawn first so rooms appear on top
   - Only cardinal directions on same Z-level

3. **Room Nodes** (_draw_rooms_at_z_level)
   - Rendered in Z-order: z=-1 first, z=+1 second, z=0 last
   - Ground level on top ensures it receives clicks

4. **Vertical Labels** (_add_vertical_exit_labels)
   - Added last as annotations
   - Show U/D for stacked rooms with vertical exits

Performance Considerations
--------------------------
- Rooms batched into single Scatter trace per Z-level
- Exit lines deduplicated (bidirectional exits draw once)
- For zones with 100+ rooms, consider filter controls
- Figure creation is synchronous and typically < 50ms
"""

import plotly.graph_objects as go

# =============================================================================
# Z-Level Visual Configuration
# =============================================================================
#
# These constants define how rooms at different Z-levels are displayed.
# The design philosophy is:
#
# 1. Ground level (z=0) is most common and should be most prominent/clickable
# 2. Below ground (z=-1) uses dark colors suggesting depth/underground
# 3. Above ground (z=+1) uses light/hollow style suggesting elevation
# 4. Render order ensures ground is on top for click selection

Z_LEVEL_STYLES: dict[int, dict] = {
    -1: {
        # Below ground level (cellars, basements, underground)
        # Smallest size, black fill - suggests depth and darkness
        "size": 14,
        "color": "rgba(40, 40, 40, 1)",  # Black/dark gray filled
        "border_color": "rgba(40, 40, 40, 1)",  # Same as fill (no visible border)
        "border_width": 1,
        "label": "Down (z=-1)",
    },
    0: {
        # Ground level (main floor, streets, ground-level rooms)
        # Largest size, blue fill - the default and most prominent
        "size": 20,
        "color": "rgba(70, 130, 180, 1)",  # Steel blue (familiar from original)
        "border_color": "white",  # White border for contrast
        "border_width": 2,
        "label": "Ground (z=0)",
    },
    1: {
        # Above ground level (towers, attics, upper floors)
        # Medium size, white with black border - suggests elevation/openness
        "size": 18,
        "color": "white",  # White/hollow fill
        "border_color": "rgba(40, 40, 40, 1)",  # Black border for visibility
        "border_width": 2,
        "label": "Up (z=+1)",
    },
}
"""
Visual styling configuration for each Z-level.

Each Z-level maps to a dictionary containing:

- **size**: Marker diameter in pixels
- **color**: Fill color (rgba string)
- **border_color**: Marker outline color
- **border_width**: Marker outline width in pixels
- **label**: Human-readable label for legends/tooltips

The size hierarchy (14 < 18 < 20) ensures that when rooms overlap at the
same X,Y position, the ground-level room (largest) is most visible and
receives clicks first due to render order.
"""

Z_RENDER_ORDER: list[int] = [-1, 1, 0]
"""
Order in which Z-levels are rendered (back to front).

Rooms are drawn in this order, meaning:

1. z=-1 (Down) is drawn first, appearing at the back
2. z=+1 (Up) is drawn second
3. z=0 (Ground) is drawn last, appearing on top

This ensures that when rooms overlap at the same X,Y position (stacked
vertically), the ground-level room is on top and receives mouse clicks.
Users can use the Z-level filter to hide ground level when they need to
select a room below or above.
"""

SELECTED_ROOM_COLOR: str = "rgba(255, 100, 100, 1)"
"""
Color used for the currently selected room.

This red color overrides the Z-level-based color when a room is selected,
providing clear visual feedback regardless of which floor the selected
room is on. The color is intentionally bright and distinct from all
Z-level colors.
"""

Z_LEVEL_VISUAL_OFFSET: dict[int, tuple[float, float]] = {
    -1: (-0.4, -0.4),  # Down: offset left and down (appears "behind")
    0: (0.0, 0.0),  # Ground: no offset (reference level)
    1: (0.4, 0.4),  # Up: offset right and up (appears "in front")
}
"""
Visual X,Y offset applied to rooms based on Z-level.

When rooms are stacked at the same logical X,Y position but different Z-levels,
this offset separates them visually so they don't overlap. The diagonal offset
creates an intuitive "stacking" effect:

- z=-1 (Down): Shifted left and down, appearing "behind"
- z=0 (Ground): No offset, the reference position
- z=+1 (Up): Shifted right and up, appearing "in front"

The offset value (0.4) is small enough that stacked rooms are clearly at the
"same position" but large enough to be visually distinct and separately clickable.

Note: This is purely visual. The logical coordinates used for U/D connections
remain unchanged.
"""


# =============================================================================
# Public API Functions
# =============================================================================


def create_map_figure(title: str | None = None) -> go.Figure:
    """
    Create the base map figure with crosshair and grid.

    Creates an empty Plotly figure configured as a 2D map canvas with:

    - Cartesian grid with 5-unit spacing
    - Crosshair at origin for orientation
    - Compass-labeled axes (N/S/E/W at extremes)
    - Fixed dimensions to prevent resize loops in Dash

    This function creates only the canvas - use create_map_figure_with_rooms
    to add room visualizations.

    Parameters
    ----------
    title : str | None, optional
        Title text to display above the map (default: None).
        If None, no title is shown. This is the default for flattened
        views where a Z-level title would be misleading.

    Returns
    -------
    go.Figure
        Plotly Figure configured as an interactive map canvas.
        The figure has:

        - Range: -20 to +20 on both axes
        - Grid: 5-unit spacing with light gray lines
        - Crosshair: Dashed gray lines at x=0 and y=0
        - Dimensions: 700x650 pixels (fixed)

    Examples
    --------
    Create a map canvas with no title (default)::

        >>> fig = create_map_figure()
        >>> fig.layout.title is None or fig.layout.title.text is None
        True

    Create a map canvas with a custom title::

        >>> fig = create_map_figure(title="Crooked Pipe District")
        >>> fig.layout.title.text
        'Crooked Pipe District'

    Notes
    -----
    - The figure uses fixed dimensions (autosize=False) to prevent
      infinite resize loops when embedded in Dash layouts
    - Axis labels show compass directions at the extremes:
      "W 20" at x=-20, "E 20" at x=+20, "S 20" at y=-20, "N 20" at y=+20
    - The scaleanchor constraint ensures 1:1 aspect ratio (square grid)
    - Pan and zoom are enabled (fixedrange=False)

    See Also
    --------
    create_map_figure_with_rooms : Add rooms to the map canvas
    """
    fig = go.Figure()

    # -------------------------------------------------------------------------
    # Crosshair at Origin
    # -------------------------------------------------------------------------
    # Helps users orient themselves on the map. The spawn room is typically
    # at the origin, so the crosshair marks the "center" of the zone.

    # Vertical line at x=0 (runs north-south through origin)
    fig.add_shape(
        type="line",
        x0=0,
        y0=-20,
        x1=0,
        y1=20,
        line={"color": "rgba(128, 128, 128, 0.5)", "width": 1, "dash": "dash"},
    )

    # Horizontal line at y=0 (runs east-west through origin)
    fig.add_shape(
        type="line",
        x0=-20,
        y0=0,
        x1=20,
        y1=0,
        line={"color": "rgba(128, 128, 128, 0.5)", "width": 1, "dash": "dash"},
    )

    # -------------------------------------------------------------------------
    # Layout Configuration
    # -------------------------------------------------------------------------
    # Configure axes, grid, dimensions, and optional title.

    # Build title configuration - only include if title provided
    title_config = None
    if title is not None:
        title_config = {
            "text": title,
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 14, "color": "gray"},
        }

    fig.update_layout(
        # X-axis: East/West
        xaxis={
            "range": [-21, 21],  # Slight padding beyond grid
            "dtick": 5,  # Grid line spacing
            "gridcolor": "rgba(200, 200, 200, 0.3)",
            "zeroline": False,  # We use custom crosshair instead
            "title": None,
            "showticklabels": True,
            "tickmode": "array",
            "tickvals": [-20, -15, -10, -5, 0, 5, 10, 15, 20],
            "ticktext": [
                "W 20",  # West at negative X
                "15",
                "10",
                "5",
                "0",
                "5",
                "10",
                "15",
                "E 20",  # East at positive X
            ],
            "fixedrange": False,  # Allow pan/zoom
        },
        # Y-axis: North/South
        yaxis={
            "range": [-21, 21],  # Slight padding beyond grid
            "dtick": 5,  # Grid line spacing
            "gridcolor": "rgba(200, 200, 200, 0.3)",
            "zeroline": False,  # We use custom crosshair instead
            "scaleanchor": "x",  # Lock to X-axis for square aspect
            "scaleratio": 1,  # 1:1 ratio
            "title": None,
            "showticklabels": True,
            "tickmode": "array",
            "tickvals": [-20, -15, -10, -5, 0, 5, 10, 15, 20],
            "ticktext": [
                "S 20",  # South at negative Y
                "15",
                "10",
                "5",
                "0",
                "5",
                "10",
                "15",
                "N 20",  # North at positive Y
            ],
            "fixedrange": False,  # Allow pan/zoom
        },
        # Visual appearance
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin={"l": 50, "r": 20, "t": 40, "b": 50},
        # Title (None for flattened view, or custom text)
        title=title_config,
        # Fixed dimensions prevent Dash resize loops
        autosize=False,
        width=700,
        height=650,
    )

    return fig


def create_map_figure_with_rooms(
    rooms: dict[str, dict] | None = None,
    visible_z_levels: list[int] | None = None,
    selected_room: str | None = None,
    visual_offset: float = 1.0,
) -> go.Figure:
    """
    Create map figure with all rooms flattened onto a single 2D plane.

    Renders a complete zone map showing rooms from multiple Z-levels
    simultaneously. Rooms are visually differentiated by Z-level using
    size and color, with the selected room highlighted in red.

    The rendering order ensures that ground-level rooms (z=0) appear on
    top and receive clicks first when rooms overlap at the same X,Y
    position.

    Parameters
    ----------
    rooms : dict[str, dict] | None, optional
        Dictionary mapping room IDs to room data. Each room should have:

        - "coords": [x, y, z] list of coordinates
        - "name": Display name (falls back to room_id if missing)
        - "exits": Dict mapping direction to target room_id

        If None or empty, returns base map only.

    visible_z_levels : list[int] | None, optional
        List of Z-levels to display (default: None, which shows all).
        Pass ``[-1, 0, 1]`` explicitly for all levels, or a subset like
        ``[0]`` to show only ground level, ``[-1, 0]`` to hide upper level.

    selected_room : str | None, optional
        Room ID to highlight as selected (default: None).
        Selected room appears in red regardless of its Z-level.

    visual_offset : float, optional
        Scale factor for Z-level visual offset (default: 1.0). Controls how
        much stacked rooms are visually separated. Use 0.0 for no offset
        (rooms overlap at same position), or higher values like 2.5 for
        more separation.

    Returns
    -------
    go.Figure
        Plotly Figure with rooms rendered in Z-order.

    Visual Styling
    --------------
    Rooms are styled based on their Z coordinate:

    - **z=-1 (Down)**: Black filled, 14px - smallest, drawn first (back)
    - **z=+1 (Up)**: White with black border, 18px - medium, drawn second
    - **z=0 (Ground)**: Blue filled, 20px - largest, drawn last (front)
    - **Selected**: Always red, regardless of Z-level

    Exit connections:

    - **Cardinal (N/E/S/W)**: Gray lines between rooms on same Z-level
    - **Vertical (U/D)**: "U", "D", or "U/D" labels near stacked rooms

    Examples
    --------
    Render all rooms from a zone::

        >>> rooms = {
        ...     "ground": {
        ...         "name": "Ground Floor",
        ...         "coords": [0, 0, 0],
        ...         "exits": {"down": "cellar", "north": "hall"}
        ...     },
        ...     "cellar": {
        ...         "name": "The Cellar",
        ...         "coords": [0, 0, -1],
        ...         "exits": {"up": "ground"}
        ...     },
        ...     "hall": {
        ...         "name": "Great Hall",
        ...         "coords": [0, 5, 0],
        ...         "exits": {"south": "ground"}
        ...     },
        ... }
        >>> fig = create_map_figure_with_rooms(rooms)

    Filter to ground level only::

        >>> fig = create_map_figure_with_rooms(rooms, visible_z_levels=[0])

    Highlight a selected room::

        >>> fig = create_map_figure_with_rooms(
        ...     rooms, selected_room="cellar"
        ... )

    Handle empty rooms gracefully::

        >>> fig = create_map_figure_with_rooms(None)  # Returns base map
        >>> fig = create_map_figure_with_rooms({})   # Returns base map

    Notes
    -----
    - Rooms without "coords" key are treated as being at [0, 0, 0]
    - Cross-zone exits (containing ':') are skipped during line drawing
    - Exit lines are drawn before room nodes (proper layering)
    - Vertical exits show text labels instead of lines
    - Hover text shows room name, ID, Z-level, and exit directions
    - When rooms overlap (stacked vertically), ground level is on top

    Click Selection with Stacked Rooms
    ----------------------------------
    When rooms share the same X,Y but different Z, they overlap visually.
    Due to render order, ground level (z=0) receives clicks first. To
    select a lower-level room:

    1. Uncheck "Ground (z=0)" in the layer filter
    2. Click the now-visible lower-level room
    3. Re-check ground level when done

    See Also
    --------
    create_map_figure : Create empty map canvas
    Z_LEVEL_STYLES : Visual configuration for each Z-level
    Z_RENDER_ORDER : Rendering order for Z-levels
    """
    # Start with base figure (no title for flattened view)
    fig = create_map_figure(title=None)

    # Handle missing or empty rooms - return base map
    if not rooms:
        return fig

    # Default to showing all Z-levels if not specified
    if visible_z_levels is None:
        visible_z_levels = [-1, 0, 1]

    # Handle empty filter (show no rooms, just base map)
    if not visible_z_levels:
        return fig

    # -------------------------------------------------------------------------
    # Prepare Room Data
    # -------------------------------------------------------------------------
    # Group rooms by Z-level for ordered rendering, and identify stacked
    # positions where multiple rooms share the same X,Y coordinates.

    rooms_by_z = _group_rooms_by_z_level(rooms, visible_z_levels)
    stacked_positions = _find_stacked_positions(rooms, visible_z_levels)

    # -------------------------------------------------------------------------
    # Draw Exit Lines (First Layer)
    # -------------------------------------------------------------------------
    # Exit lines are drawn first so that room nodes appear on top. Only
    # cardinal directions (N/E/S/W) on the same Z-level get lines.

    _draw_all_exit_lines(fig, rooms, visible_z_levels, visual_offset)

    # -------------------------------------------------------------------------
    # Draw Room Nodes (Second Layer, Z-Ordered)
    # -------------------------------------------------------------------------
    # Rooms are drawn in Z_RENDER_ORDER so that ground level appears on top
    # and receives clicks when rooms overlap at the same X,Y position.

    for z_level in Z_RENDER_ORDER:
        # Skip Z-levels not in the visible filter
        if z_level not in visible_z_levels:
            continue
        # Skip Z-levels with no rooms
        if z_level not in rooms_by_z:
            continue
        # Draw all rooms at this Z-level as a single Scatter trace
        _draw_rooms_at_z_level(fig, rooms_by_z[z_level], z_level, selected_room, visual_offset)

    # -------------------------------------------------------------------------
    # Add Vertical Exit Labels (Third Layer)
    # -------------------------------------------------------------------------
    # For stacked rooms (same X,Y, different Z) with up/down exits, add
    # text labels to indicate vertical connections.

    _add_vertical_exit_labels(fig, stacked_positions, rooms)

    return fig


# =============================================================================
# Internal Helper Functions
# =============================================================================


def _get_visual_coords(
    x: float, y: float, z: int, offset_scale: float = 1.0
) -> tuple[float, float]:
    """
    Apply visual offset to coordinates based on Z-level.

    Stacked rooms (same X,Y, different Z) are offset visually so they don't
    overlap on the 2D display. This keeps them clickable and distinguishable.

    Parameters
    ----------
    x : float
        Logical X coordinate.
    y : float
        Logical Y coordinate.
    z : int
        Z-level (determines the offset to apply).
    offset_scale : float, optional
        Multiplier for the offset (default: 1.0). Set to 0.0 for no offset,
        or higher values for more separation. The base offset is 0.4 units.

    Returns
    -------
    tuple[float, float]
        Visual (x, y) coordinates with offset applied.

    Examples
    --------
    Ground level has no offset::

        >>> _get_visual_coords(5, 10, 0)
        (5.0, 10.0)

    Below ground shifts left and down::

        >>> _get_visual_coords(5, 10, -1)
        (4.6, 9.6)

    Above ground shifts right and up::

        >>> _get_visual_coords(5, 10, 1)
        (5.4, 10.4)

    Custom offset scale::

        >>> _get_visual_coords(5, 10, -1, offset_scale=2.5)
        (4.0, 9.0)
    """
    base_offset = Z_LEVEL_VISUAL_OFFSET.get(z, (0.0, 0.0))
    return (x + base_offset[0] * offset_scale, y + base_offset[1] * offset_scale)


def _group_rooms_by_z_level(
    rooms: dict[str, dict],
    visible_z_levels: list[int],
) -> dict[int, dict[str, dict]]:
    """
    Group rooms by their Z-level coordinate.

    Partitions rooms into buckets based on Z coordinate, filtering to
    only include rooms at visible Z-levels.

    Parameters
    ----------
    rooms : dict[str, dict]
        All rooms in the zone, keyed by room ID.
    visible_z_levels : list[int]
        Z-levels to include in the result.

    Returns
    -------
    dict[int, dict[str, dict]]
        Mapping of z_level -> {room_id: room_data} for visible levels only.
        Z-levels with no rooms are not included in the result.

    Examples
    --------
    Group rooms from a multi-level zone::

        >>> rooms = {
        ...     "cellar": {"coords": [0, 0, -1]},
        ...     "hall": {"coords": [0, 0, 0]},
        ...     "tower": {"coords": [0, 0, 1]},
        ... }
        >>> result = _group_rooms_by_z_level(rooms, [-1, 0, 1])
        >>> list(result.keys())
        [-1, 0, 1]
        >>> result[0]
        {'hall': {'coords': [0, 0, 0]}}

    Filter to specific levels::

        >>> result = _group_rooms_by_z_level(rooms, [0])
        >>> list(result.keys())
        [0]

    Notes
    -----
    - Rooms without "coords" key are treated as z=0
    - The result only contains Z-levels that have at least one room
    - This function is O(n) where n = number of rooms
    """
    result: dict[int, dict[str, dict]] = {}

    for room_id, room in rooms.items():
        # Extract Z coordinate, defaulting to 0 if coords missing
        coords = room.get("coords", [0, 0, 0])
        z = coords[2] if len(coords) > 2 else 0

        # Skip rooms not on a visible Z-level
        if z not in visible_z_levels:
            continue

        # Initialize bucket for this Z-level if needed
        if z not in result:
            result[z] = {}

        # Add room to its Z-level bucket
        result[z][room_id] = room

    return result


def _find_stacked_positions(
    rooms: dict[str, dict],
    visible_z_levels: list[int],
) -> dict[tuple[int, int], list[tuple[str, int]]]:
    """
    Find X,Y positions that have rooms at multiple Z-levels.

    Identifies positions where rooms are "stacked" vertically, meaning
    they share the same X,Y coordinates but have different Z coordinates.
    These positions are candidates for up/down exit labels.

    Parameters
    ----------
    rooms : dict[str, dict]
        All rooms in the zone, keyed by room ID.
    visible_z_levels : list[int]
        Z-levels being displayed (rooms outside these are ignored).

    Returns
    -------
    dict[tuple[int, int], list[tuple[str, int]]]
        Mapping of (x, y) position to list of (room_id, z_level) tuples.
        Only includes positions with 2 or more rooms (actual stacks).

    Examples
    --------
    Find stacked positions in a vertical tower::

        >>> rooms = {
        ...     "base": {"coords": [5, 5, -1]},
        ...     "ground": {"coords": [5, 5, 0]},
        ...     "top": {"coords": [5, 5, 1]},
        ...     "other": {"coords": [10, 10, 0]},
        ... }
        >>> stacked = _find_stacked_positions(rooms, [-1, 0, 1])
        >>> (5, 5) in stacked
        True
        >>> len(stacked[(5, 5)])
        3
        >>> (10, 10) in stacked  # Only one room, not stacked
        False

    Notes
    -----
    - Positions with only 1 room are not considered "stacked"
    - The room list for each position includes all visible Z-levels
    - This is used to determine where to place U/D labels
    """
    # Collect all rooms at each X,Y position
    positions: dict[tuple[int, int], list[tuple[str, int]]] = {}

    for room_id, room in rooms.items():
        coords = room.get("coords", [0, 0, 0])
        z = coords[2] if len(coords) > 2 else 0

        # Skip rooms not on a visible Z-level
        if z not in visible_z_levels:
            continue

        # Use (x, y) tuple as position key
        xy = (coords[0], coords[1])

        # Initialize list for this position if needed
        if xy not in positions:
            positions[xy] = []

        # Record room and its Z-level
        positions[xy].append((room_id, z))

    # Filter to only positions with multiple rooms (actual stacks)
    return {xy: room_list for xy, room_list in positions.items() if len(room_list) > 1}


def _draw_all_exit_lines(
    fig: go.Figure,
    rooms: dict[str, dict],
    visible_z_levels: list[int],
    visual_offset: float = 1.0,
) -> None:
    """
    Draw exit lines for cardinal directions (N/E/S/W).

    Adds Scatter traces to the figure for each exit connection. Only
    draws lines for cardinal directions between rooms on the same Z-level.
    Vertical exits (up/down) are handled separately via labels.

    Parameters
    ----------
    fig : go.Figure
        Plotly figure to add traces to (modified in place).
    rooms : dict[str, dict]
        All rooms in the zone, keyed by room ID.
    visible_z_levels : list[int]
        Z-levels being displayed.
    visual_offset : float, optional
        Scale factor for Z-level visual offset (default: 1.0).

    Returns
    -------
    None
        Modifies the figure in place.

    Notes
    -----
    - Cross-zone exits (containing ':') are skipped
    - Vertical exits (up/down) are skipped (handled by labels)
    - Bidirectional exits only draw one line (deduplication)
    - Lines are gray with slight transparency for visual clarity
    - Exit lines to rooms outside visible_z_levels are not drawn
    """
    # Track drawn connections to avoid duplicates
    # (bidirectional exits would otherwise draw twice)
    drawn_pairs: set[tuple[str, str]] = set()

    for room_id, room in rooms.items():
        coords = room.get("coords", [0, 0, 0])
        z = coords[2] if len(coords) > 2 else 0

        # Skip rooms not on a visible Z-level
        if z not in visible_z_levels:
            continue

        # Apply visual offset for stacked room separation
        x1, y1 = _get_visual_coords(coords[0], coords[1], z, visual_offset)

        # Process each exit from this room
        for direction, target in room.get("exits", {}).items():
            # Skip cross-zone exits (format: "zone_id:room_id")
            if ":" in str(target):
                continue

            # Skip vertical exits (handled by labels)
            if direction in ("up", "down"):
                continue

            # Skip exits to non-existent rooms
            if target not in rooms:
                continue

            # Skip if we've already drawn this connection
            # (handles bidirectional exits)
            pair = tuple(sorted([room_id, target]))
            if pair in drawn_pairs:
                continue
            drawn_pairs.add(pair)

            # Get target room coordinates
            target_room = rooms[target]
            target_coords = target_room.get("coords", [0, 0, 0])
            target_z = target_coords[2] if len(target_coords) > 2 else 0

            # Only draw line if target is on same Z-level and visible
            if target_z != z or target_z not in visible_z_levels:
                continue

            # Apply visual offset for stacked room separation
            x2, y2 = _get_visual_coords(target_coords[0], target_coords[1], target_z, visual_offset)

            # Add line trace connecting the rooms
            fig.add_trace(
                go.Scatter(
                    x=[x1, x2],
                    y=[y1, y2],
                    mode="lines",
                    line={"color": "rgba(100, 100, 100, 0.6)", "width": 2},
                    hoverinfo="skip",  # Don't show hover on lines
                    showlegend=False,
                )
            )


def _draw_rooms_at_z_level(
    fig: go.Figure,
    rooms_at_level: dict[str, dict],
    z_level: int,
    selected_room: str | None,
    visual_offset: float = 1.0,
) -> None:
    """
    Draw all rooms at a specific Z-level as a single Scatter trace.

    Renders rooms with Z-level-specific styling (size, color, border).
    The selected room (if any) is colored red regardless of Z-level.

    Parameters
    ----------
    fig : go.Figure
        Plotly figure to add the trace to (modified in place).
    rooms_at_level : dict[str, dict]
        Rooms to draw, already filtered to this Z-level.
    z_level : int
        The Z-level being drawn (used for styling lookup).
    selected_room : str | None
        ID of the selected room (will be colored red).
    visual_offset : float, optional
        Scale factor for Z-level visual offset (default: 1.0).

    Returns
    -------
    None
        Modifies the figure in place.

    Notes
    -----
    - Rooms are batched into a single Scatter trace for performance
    - Styling is determined by Z_LEVEL_STYLES constant
    - Selected room color overrides Z-level color
    - Hover text includes Z-level information
    - Room ID is stored in text field for click handling
    """
    # Early exit if no rooms at this level
    if not rooms_at_level:
        return

    # Get visual styling for this Z-level (default to ground if unknown)
    style = Z_LEVEL_STYLES.get(z_level, Z_LEVEL_STYLES[0])

    # Prepare arrays for batch rendering
    x_coords: list[float] = []
    y_coords: list[float] = []
    labels: list[str] = []
    colors: list[str] = []
    hover_texts: list[str] = []

    for room_id, room in rooms_at_level.items():
        coords = room.get("coords", [0, 0, 0])
        # Apply visual offset based on Z-level so stacked rooms don't overlap
        visual_x, visual_y = _get_visual_coords(coords[0], coords[1], z_level, visual_offset)
        x_coords.append(visual_x)
        y_coords.append(visual_y)

        # Room ID is used as the label (displayed above node)
        # and stored for click handling
        labels.append(room_id)

        # Color: red for selected, otherwise use Z-level style
        if room_id == selected_room:
            colors.append(SELECTED_ROOM_COLOR)
        else:
            colors.append(style["color"])

        # Build hover text with room details including Z-level
        name = room.get("name", room_id)
        exits = ", ".join(room.get("exits", {}).keys()) or "none"
        hover_texts.append(
            f"<b>{name}</b><br>" f"ID: {room_id}<br>" f"Z-level: {z_level}<br>" f"Exits: {exits}"
        )

    # Add all rooms at this Z-level as a single Scatter trace
    fig.add_trace(
        go.Scatter(
            x=x_coords,
            y=y_coords,
            mode="markers+text",
            marker={
                "size": style["size"],
                "color": colors,
                "line": {
                    "width": style["border_width"],
                    "color": style["border_color"],
                },
            },
            text=labels,  # Room IDs for display and click handling
            textposition="top center",
            textfont={"size": 10},
            hovertext=hover_texts,
            hoverinfo="text",
            showlegend=False,
            name=style["label"],  # For potential legend use
        )
    )


def _add_vertical_exit_labels(
    fig: go.Figure,
    stacked_positions: dict[tuple[int, int], list[tuple[str, int]]],
    rooms: dict[str, dict],
) -> None:
    """
    Add "U", "D", or "U/D" labels near stacked rooms with vertical exits.

    For positions where rooms are stacked (same X,Y, different Z), checks
    if any room has up or down exits. If so, adds a text annotation to
    indicate the vertical connection.

    Parameters
    ----------
    fig : go.Figure
        Plotly figure to add annotations to (modified in place).
    stacked_positions : dict[tuple[int, int], list[tuple[str, int]]]
        Mapping of (x, y) to list of (room_id, z_level) at that position.
        Only includes positions with 2+ rooms.
    rooms : dict[str, dict]
        All rooms in the zone (for checking exit data).

    Returns
    -------
    None
        Modifies the figure in place by adding annotations.

    Label Logic
    -----------
    - **"U/D"**: At least one room has "up" AND at least one has "down"
    - **"U"**: At least one room has "up", none have "down"
    - **"D"**: At least one room has "down", none have "up"
    - **No label**: No rooms at this position have vertical exits

    Notes
    -----
    - Labels are offset to the lower-right of the room center
    - Small semi-transparent background for readability
    - Only shown when actual up/down exits exist (not just stacking)
    """
    for (x, y), room_list in stacked_positions.items():
        # Check which vertical exits exist at this position
        has_up = False
        has_down = False

        for room_id, _z_level in room_list:
            room = rooms.get(room_id, {})
            exits = room.get("exits", {})

            if "up" in exits:
                has_up = True
            if "down" in exits:
                has_down = True

        # Skip if no vertical exits at this position
        if not has_up and not has_down:
            continue

        # Determine label text based on which exits exist
        if has_up and has_down:
            label = "U/D"
        elif has_up:
            label = "U"
        else:
            label = "D"

        # Position label offset from room center to avoid overlap
        # Offset to lower-right where it's less likely to conflict
        fig.add_annotation(
            x=x + 0.8,
            y=y - 0.8,
            text=label,
            showarrow=False,
            font={
                "size": 9,
                "color": "rgba(80, 80, 80, 1)",
            },
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor="rgba(100, 100, 100, 0.5)",
            borderwidth=1,
            borderpad=2,
        )
