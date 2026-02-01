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
