"""
Plotly-based map visualization component for the MUD Mapper.

This module provides the core visualization functions for rendering MUD zone
maps using Plotly. It creates interactive 2D map views that display rooms
as nodes and exits as connecting lines, with support for:

- Multi-level Z-axis filtering (showing one floor at a time)
- Room selection highlighting
- Exit visualization (lines for same-level, indicators for up/down)
- Interactive pan, zoom, and hover tooltips

Design Principles
-----------------
1. **Layer-based Rendering**: Exits drawn first, then rooms (proper z-ordering)
2. **Separation of Concerns**: Base figure creation separate from room rendering
3. **Graceful Degradation**: Handles missing data, empty rooms, invalid exits
4. **Deterministic Output**: Same inputs produce identical figures

Coordinate System
-----------------
The map follows standard cartographic conventions:

- **X-axis**: East (+) / West (-), displayed left-to-right
- **Y-axis**: North (+) / South (-), displayed bottom-to-top
- **Z-axis**: Handled via layer filtering (not shown on 2D map)

The coordinate range is -20 to +20 on both axes, with gridlines every 5 units.

Visual Design
-------------
- **Room nodes**: Blue circles (20px), red when selected
- **Exit lines**: Gray lines connecting rooms on same level
- **Up exits**: Green triangle above room
- **Down exits**: Red triangle below room
- **Crosshair**: Dashed gray lines at origin for orientation

Functions
---------
create_map_figure(z_level) -> go.Figure
    Create empty map canvas with grid and crosshair
create_map_figure_with_rooms(rooms, z_level, selected_room) -> go.Figure
    Create map with rooms and exits rendered
_add_vertical_indicator(fig, x, y, direction) -> None
    Add up/down exit indicator triangle (internal)

Usage
-----
Create an empty map canvas::

    >>> from pipeworks_mud_mapper.components.map_view import create_map_figure
    >>> fig = create_map_figure(z_level=0)
    >>> fig.show()  # Opens in browser

Render rooms on map::

    >>> from pipeworks_mud_mapper.components.map_view import (
    ...     create_map_figure_with_rooms
    ... )
    >>> rooms = {
    ...     "spawn": {"name": "Spawn", "coords": [0, 0, 0], "exits": {"north": "hall"}},
    ...     "hall": {"name": "Hall", "coords": [0, 5, 0], "exits": {"south": "spawn"}},
    ... }
    >>> fig = create_map_figure_with_rooms(rooms, z_level=0, selected_room="spawn")
    >>> fig.show()

Integration with Dash::

    >>> import dash
    >>> from dash import dcc
    >>> fig = create_map_figure_with_rooms(rooms, z_level=0)
    >>> graph = dcc.Graph(figure=fig, id="map-graph")

Architecture
------------
The module uses a two-layer approach:

1. **Base Figure** (create_map_figure)
   - Creates the canvas with grid, crosshair, and axis labels
   - Fixed dimensions (700x650) to prevent layout thrashing
   - Configurable Z-level for title display

2. **Room Overlay** (create_map_figure_with_rooms)
   - Filters rooms to current Z-level
   - Draws exit lines as Scatter traces
   - Draws room nodes as Scatter trace with markers
   - Handles selection highlighting and hover text

This separation allows for efficient re-rendering when only room data
changes (common case) vs. when the base map configuration changes (rare).

Performance Considerations
--------------------------
- Each exit line is a separate Scatter trace (could be optimized)
- Room nodes are batched into a single Scatter trace
- For zones with 100+ rooms, consider pagination by area
- Figure creation is synchronous and typically < 50ms
"""

import plotly.graph_objects as go


def create_map_figure(z_level: int = 0) -> go.Figure:
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
    z_level : int, optional
        Current Z level to display in the title (default: 0).
        Does not affect rendering, only the title text.

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
    Create a ground-level map canvas::

        >>> fig = create_map_figure(z_level=0)
        >>> fig.layout.title.text
        'Layer: z = 0'

    Create an upper-level map canvas::

        >>> fig = create_map_figure(z_level=1)
        >>> fig.layout.title.text
        'Layer: z = 1'

    Notes
    -----
    - The figure uses fixed dimensions (autosize=False) to prevent
      infinite resize loops when embedded in Dash layouts
    - Axis labels show compass directions at the extremes:
      "W 20" at x=-20, "E 20" at x=+20, "S 20" at y=-20, "N 20" at y=+20
    - The scaleanchor constraint ensures 1:1 aspect ratio (square grid)
    - Pan and zoom are enabled (fixedrange=False)
    """
    fig = go.Figure()

    # -------------------------------------------------------------------------
    # Crosshair at Origin
    # -------------------------------------------------------------------------
    # Helps users orient themselves on the map. The spawn room is typically
    # at the origin, so the crosshair marks the "center" of the zone.

    # Vertical line at x=0
    fig.add_shape(
        type="line",
        x0=0,
        y0=-20,
        x1=0,
        y1=20,
        line={"color": "rgba(128, 128, 128, 0.5)", "width": 1, "dash": "dash"},
    )

    # Horizontal line at y=0
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
        # Title showing current Z-level
        title={
            "text": f"Layer: z = {z_level}",
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 14, "color": "gray"},
        },
        # Fixed dimensions prevent Dash resize loops
        autosize=False,
        width=700,
        height=650,
    )

    return fig


def create_map_figure_with_rooms(
    rooms: dict[str, dict] | None = None,
    z_level: int = 0,
    selected_room: str | None = None,
) -> go.Figure:
    """
    Create map figure with room nodes and exit lines.

    Renders a complete zone map by:
    1. Creating the base map canvas
    2. Filtering rooms to the specified Z-level
    3. Drawing exit lines between connected rooms
    4. Drawing room nodes with labels and hover info
    5. Highlighting the selected room (if any)

    Rooms on different Z-levels are not shown, but up/down exits are
    indicated with triangle markers.

    Parameters
    ----------
    rooms : dict[str, dict] | None, optional
        Dictionary mapping room IDs to room data. Each room should have:
        - "coords": [x, y, z] list of coordinates
        - "name": Display name (falls back to room_id)
        - "exits": Dict mapping direction to target room_id
        If None or empty, returns base map only.
    z_level : int, optional
        Z-level to display (default: 0). Only rooms with matching
        Z coordinate are rendered.
    selected_room : str | None, optional
        Room ID to highlight as selected (default: None).
        Selected room appears in red instead of blue.

    Returns
    -------
    go.Figure
        Plotly Figure with rooms rendered as nodes and exits as lines.

    Examples
    --------
    Render a simple two-room zone::

        >>> rooms = {
        ...     "spawn": {
        ...         "name": "Spawn Room",
        ...         "coords": [0, 0, 0],
        ...         "exits": {"north": "hall"}
        ...     },
        ...     "hall": {
        ...         "name": "Great Hall",
        ...         "coords": [0, 5, 0],
        ...         "exits": {"south": "spawn"}
        ...     },
        ... }
        >>> fig = create_map_figure_with_rooms(rooms, z_level=0)

    Highlight a selected room::

        >>> fig = create_map_figure_with_rooms(
        ...     rooms, z_level=0, selected_room="spawn"
        ... )

    Handle empty rooms gracefully::

        >>> fig = create_map_figure_with_rooms(None)  # Returns base map
        >>> fig = create_map_figure_with_rooms({})   # Returns base map

    Notes
    -----
    - Rooms without "coords" key are treated as being at [0, 0, 0]
    - Cross-zone exits (containing ':') are skipped
    - Exit lines are drawn before room nodes (proper z-ordering)
    - Up/down exits show triangle indicators instead of lines
    - Hover text shows room name, ID, and exit directions
    - Room colors: blue (normal), red (selected)
    """
    # Start with base figure
    fig = create_map_figure(z_level=z_level)

    # Handle missing or empty rooms
    if not rooms:
        return fig

    # -------------------------------------------------------------------------
    # Filter Rooms to Current Z-Level
    # -------------------------------------------------------------------------

    rooms_on_level = {
        room_id: room
        for room_id, room in rooms.items()
        if room.get("coords", [0, 0, 0])[2] == z_level
    }

    if not rooms_on_level:
        return fig

    # -------------------------------------------------------------------------
    # Draw Exit Lines (First, so rooms appear on top)
    # -------------------------------------------------------------------------

    for room_id, room in rooms_on_level.items():
        coords = room.get("coords", [0, 0, 0])
        x1, y1 = coords[0], coords[1]

        for direction, target in room.get("exits", {}).items():
            # Skip cross-zone exits (format: "zone_id:room_id")
            if ":" in str(target):
                continue

            # Skip if target room doesn't exist in zone
            if target not in rooms:
                continue

            target_room = rooms[target]
            target_coords = target_room.get("coords", [0, 0, 0])

            # Check if target is on different Z-level
            if target_coords[2] != z_level:
                # Draw triangle indicator for vertical exits
                if direction in ("up", "down"):
                    _add_vertical_indicator(fig, x1, y1, direction)
                continue

            # Draw line connecting rooms on same level
            x2, y2 = target_coords[0], target_coords[1]
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

    # -------------------------------------------------------------------------
    # Draw Room Nodes (Batched into single trace for performance)
    # -------------------------------------------------------------------------

    x_coords = []
    y_coords = []
    labels = []
    colors = []
    hover_texts = []

    for room_id, room in rooms_on_level.items():
        coords = room.get("coords", [0, 0, 0])
        x_coords.append(coords[0])
        y_coords.append(coords[1])
        labels.append(room_id)

        # Color: red for selected, blue for normal
        if room_id == selected_room:
            colors.append("rgba(255, 100, 100, 1)")  # Red
        else:
            colors.append("rgba(70, 130, 180, 1)")  # Steel blue

        # Build hover text with room details
        name = room.get("name", room_id)
        exits = ", ".join(room.get("exits", {}).keys()) or "none"
        hover_texts.append(f"<b>{name}</b><br>ID: {room_id}<br>Exits: {exits}")

    # Add all room nodes as a single trace
    fig.add_trace(
        go.Scatter(
            x=x_coords,
            y=y_coords,
            mode="markers+text",
            marker={
                "size": 20,
                "color": colors,
                "line": {"width": 2, "color": "white"},  # White border
            },
            text=labels,
            textposition="top center",
            textfont={"size": 10},
            hovertext=hover_texts,
            hoverinfo="text",
            showlegend=False,
        )
    )

    return fig


def _add_vertical_indicator(fig: go.Figure, x: int, y: int, direction: str) -> None:
    """
    Add a small triangle indicator for up/down exits.

    Places a colored triangle marker near a room to indicate that an
    exit leads to a different Z-level. This provides visual feedback
    without drawing lines to off-screen rooms.

    Parameters
    ----------
    fig : go.Figure
        The Plotly figure to add the indicator to.
    x : int
        X coordinate of the room (triangle placed nearby).
    y : int
        Y coordinate of the room (triangle placed nearby).
    direction : str
        Exit direction, either "up" or "down".
        Other values are silently ignored.

    Returns
    -------
    None
        Modifies the figure in place.

    Examples
    --------
    Add an "up" indicator::

        >>> fig = create_map_figure()
        >>> _add_vertical_indicator(fig, 0, 0, "up")
        # Adds green triangle above (0, 0)

    Add a "down" indicator::

        >>> _add_vertical_indicator(fig, 5, 5, "down")
        # Adds red triangle below (5, 5)

    Notes
    -----
    - Up exits: Green triangle pointing up, placed above room center
    - Down exits: Red triangle pointing down, placed below room center
    - Offset is 0.3 units to avoid overlapping with room node
    - Hover text shows the exit direction
    - This is an internal function (prefixed with underscore)
    """
    # Offset from room center to avoid overlap with node
    offset = 0.3

    if direction == "up":
        # Green triangle pointing upward
        fig.add_trace(
            go.Scatter(
                x=[x],
                y=[y + offset],
                mode="markers",
                marker={
                    "symbol": "triangle-up",
                    "size": 10,
                    "color": "rgba(100, 180, 100, 0.8)",  # Green
                },
                hovertext=f"Exit: {direction}",
                hoverinfo="text",
                showlegend=False,
            )
        )
    elif direction == "down":
        # Red triangle pointing downward
        fig.add_trace(
            go.Scatter(
                x=[x],
                y=[y - offset],
                mode="markers",
                marker={
                    "symbol": "triangle-down",
                    "size": 10,
                    "color": "rgba(180, 100, 100, 0.8)",  # Red
                },
                hovertext=f"Exit: {direction}",
                hoverinfo="text",
                showlegend=False,
            )
        )
