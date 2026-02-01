"""Plotly map view component."""

import plotly.graph_objects as go


def create_map_figure(z_level: int = 0) -> go.Figure:
    """Create the map figure with crosshair and grid.

    Args:
        z_level: Current Z level to display (for future layer filtering).

    Returns:
        Plotly Figure configured as a map canvas.
    """
    fig = go.Figure()

    # Crosshair - vertical line at x=0
    fig.add_shape(
        type="line",
        x0=0,
        y0=-20,
        x1=0,
        y1=20,
        line={"color": "rgba(128, 128, 128, 0.5)", "width": 1, "dash": "dash"},
    )

    # Crosshair - horizontal line at y=0
    fig.add_shape(
        type="line",
        x0=-20,
        y0=0,
        x1=20,
        y1=0,
        line={"color": "rgba(128, 128, 128, 0.5)", "width": 1, "dash": "dash"},
    )

    # Configure layout
    fig.update_layout(
        # Grid range
        xaxis={
            "range": [-21, 21],
            "dtick": 5,
            "gridcolor": "rgba(200, 200, 200, 0.3)",
            "zeroline": False,
            "title": None,
            "showticklabels": True,
            "tickmode": "array",
            "tickvals": [-20, -15, -10, -5, 0, 5, 10, 15, 20],
            "ticktext": [
                "W 20",
                "15",
                "10",
                "5",
                "0",
                "5",
                "10",
                "15",
                "E 20",
            ],
            "fixedrange": False,
        },
        yaxis={
            "range": [-21, 21],
            "dtick": 5,
            "gridcolor": "rgba(200, 200, 200, 0.3)",
            "zeroline": False,
            "scaleanchor": "x",
            "scaleratio": 1,
            "title": None,
            "showticklabels": True,
            "tickmode": "array",
            "tickvals": [-20, -15, -10, -5, 0, 5, 10, 15, 20],
            "ticktext": [
                "S 20",
                "15",
                "10",
                "5",
                "0",
                "5",
                "10",
                "15",
                "N 20",
            ],
            "fixedrange": False,
        },
        # Appearance
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin={"l": 50, "r": 20, "t": 40, "b": 50},
        # Title showing current layer
        title={
            "text": f"Layer: z = {z_level}",
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 14, "color": "gray"},
        },
        # Fixed size to prevent resize loops
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
    """Create map figure with room nodes and exit lines.

    Args:
        rooms: Dict of room_id -> room data (must include 'coords' key).
        z_level: Current Z level to filter rooms by.
        selected_room: Room ID to highlight as selected.

    Returns:
        Plotly Figure with rooms rendered as nodes and exits as lines.
    """
    # Start with base figure
    fig = create_map_figure(z_level=z_level)

    if not rooms:
        return fig

    # Filter rooms on this z-level
    rooms_on_level = {
        room_id: room
        for room_id, room in rooms.items()
        if room.get("coords", [0, 0, 0])[2] == z_level
    }

    if not rooms_on_level:
        return fig

    # Draw exit lines first (so nodes are on top)
    for room_id, room in rooms_on_level.items():
        coords = room.get("coords", [0, 0, 0])
        x1, y1 = coords[0], coords[1]

        for direction, target in room.get("exits", {}).items():
            # Skip cross-zone exits
            if ":" in str(target):
                continue

            # Skip if target not in rooms or not on this level
            if target not in rooms:
                continue

            target_room = rooms[target]
            target_coords = target_room.get("coords", [0, 0, 0])

            # Only draw line if target is on same z-level
            if target_coords[2] != z_level:
                # Draw indicator for up/down exits
                if direction in ("up", "down"):
                    _add_vertical_indicator(fig, x1, y1, direction)
                continue

            x2, y2 = target_coords[0], target_coords[1]

            # Draw line
            fig.add_trace(
                go.Scatter(
                    x=[x1, x2],
                    y=[y1, y2],
                    mode="lines",
                    line={"color": "rgba(100, 100, 100, 0.6)", "width": 2},
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

    # Draw room nodes
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

        # Highlight selected room
        if room_id == selected_room:
            colors.append("rgba(255, 100, 100, 1)")
        else:
            colors.append("rgba(70, 130, 180, 1)")

        # Hover text with room details
        name = room.get("name", room_id)
        exits = ", ".join(room.get("exits", {}).keys()) or "none"
        hover_texts.append(f"<b>{name}</b><br>ID: {room_id}<br>Exits: {exits}")

    fig.add_trace(
        go.Scatter(
            x=x_coords,
            y=y_coords,
            mode="markers+text",
            marker={
                "size": 20,
                "color": colors,
                "line": {"width": 2, "color": "white"},
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
    """Add a small triangle indicator for up/down exits.

    Args:
        fig: The figure to add the indicator to.
        x: X coordinate of the room.
        y: Y coordinate of the room.
        direction: Either 'up' or 'down'.
    """
    # Small offset from room center
    offset = 0.3
    if direction == "up":
        # Triangle pointing up
        fig.add_trace(
            go.Scatter(
                x=[x],
                y=[y + offset],
                mode="markers",
                marker={
                    "symbol": "triangle-up",
                    "size": 10,
                    "color": "rgba(100, 180, 100, 0.8)",
                },
                hovertext=f"Exit: {direction}",
                hoverinfo="text",
                showlegend=False,
            )
        )
    elif direction == "down":
        # Triangle pointing down
        fig.add_trace(
            go.Scatter(
                x=[x],
                y=[y - offset],
                mode="markers",
                marker={
                    "symbol": "triangle-down",
                    "size": 10,
                    "color": "rgba(180, 100, 100, 0.8)",
                },
                hovertext=f"Exit: {direction}",
                hoverinfo="text",
                showlegend=False,
            )
        )
