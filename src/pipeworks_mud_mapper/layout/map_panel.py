"""Map panel component for the center column.

The map panel displays the interactive Plotly visualization of rooms
and exits, along with filter controls for showing/hiding Z-levels.

The flattened view displays all rooms on a single 2D plane regardless
of their Z coordinate, with visual differentiation by level:

- **z=-1 (Down)**: Black filled circles (smallest)
- **z=0 (Ground)**: Blue filled circles (largest)
- **z=+1 (Up)**: White circles with black border (medium)

Component Structure
-------------------
::

    ┌─────────────────────────────────────────┐
    │                                         │
    │        ●───────●     ◐                  │
    │        │       │     │                  │
    │        ●───────●─────●   Plotly map     │
    │                ⬤                        │
    │                                         │
    ├─────────────────────────────────────────┤
    │ Show Layers: ☑ Down  ☑ Ground  ☑ Up   │
    └─────────────────────────────────────────┘

Component IDs
-------------
- ``map-graph``: Plotly Graph component for room visualization
- ``z-level-filter``: Checklist for filtering which Z-levels to display

Filter Behavior
---------------
All levels are shown by default (all checkboxes checked). Unchecking a
level hides rooms at that Z coordinate. This is useful for:

- Reducing visual clutter when working on a single floor
- Selecting stacked rooms (hide upper levels to click lower ones)
- Focusing on specific areas of the map

See Also
--------
- ``components/map_view.py``: Plotly figure creation functions
- ``callbacks/map_callbacks.py``: Callbacks for map interaction
"""

import dash_bootstrap_components as dbc
from dash import dcc, html

from pipeworks_mud_mapper.components.map_view import create_map_figure


def create_map_panel() -> dbc.Card:
    """Create the center column map panel component.

    The map panel contains:

    - Plotly Graph component for room visualization (flattened multi-level view)
    - Z-level filter checkboxes for showing/hiding each level

    Returns
    -------
    dbc.Card
        Bootstrap Card containing the map and layer filter controls.

    Component IDs
    -------------
    - ``map-graph``: Plotly Graph for map visualization
    - ``z-level-filter``: Checklist for filtering visible Z-levels

    Visual Indicators
    -----------------
    The filter checkboxes include colored circles matching the room styling:

    - **Down (z=-1)**: Small black circle
    - **Ground (z=0)**: Medium blue circle
    - **Up (z=+1)**: Medium white circle with black border

    Notes
    -----
    - Map displays all Z-levels by default (flattened view)
    - Uncheck a level to hide rooms at that Z coordinate
    - Rooms are rendered in Z-order: down first, then up, then ground on top
    - Ground level rooms receive clicks first when stacked
    - To select a lower-level room, temporarily uncheck higher levels
    - Scroll zoom and pan are enabled via Graph config
    - Lasso and select tools are removed from mode bar

    Examples
    --------
    The map panel is typically used within the main layout::

        >>> from pipeworks_mud_mapper.layout.map_panel import create_map_panel
        >>> panel = create_map_panel()
        >>> # Panel contains 'map-graph' and 'z-level-filter' components
    """
    return dbc.Card(
        [
            dbc.CardBody(
                [
                    # ---------------------------------------------------------
                    # Plotly Map Figure
                    # ---------------------------------------------------------
                    # Interactive map showing rooms as nodes and exits as lines.
                    # Displays all Z-levels simultaneously (flattened view).
                    dcc.Graph(
                        id="map-graph",
                        figure=create_map_figure(),  # No title for flattened view
                        config={
                            "displayModeBar": True,
                            "scrollZoom": True,
                            "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                        },
                    ),
                    # ---------------------------------------------------------
                    # Z-Level Filter Checkboxes
                    # ---------------------------------------------------------
                    # Allow users to show/hide specific Z-levels. All are shown
                    # by default. Colored indicators match room styling.
                    html.Div(
                        [
                            html.Label("Show Layers:", className="me-3"),
                            dbc.Checklist(
                                id="z-level-filter",
                                options=[
                                    # Down level: black circle indicator
                                    {
                                        "label": html.Span(
                                            [
                                                html.Span(
                                                    "",
                                                    style={
                                                        "display": "inline-block",
                                                        "width": "10px",
                                                        "height": "10px",
                                                        "backgroundColor": "#282828",
                                                        "borderRadius": "50%",
                                                        "marginRight": "4px",
                                                        "verticalAlign": "middle",
                                                    },
                                                ),
                                                "Down (z=-1)",
                                            ]
                                        ),
                                        "value": -1,
                                    },
                                    # Ground level: blue circle indicator
                                    {
                                        "label": html.Span(
                                            [
                                                html.Span(
                                                    "",
                                                    style={
                                                        "display": "inline-block",
                                                        "width": "12px",
                                                        "height": "12px",
                                                        "backgroundColor": "#4682B4",
                                                        "borderRadius": "50%",
                                                        "marginRight": "4px",
                                                        "verticalAlign": "middle",
                                                    },
                                                ),
                                                "Ground (z=0)",
                                            ]
                                        ),
                                        "value": 0,
                                    },
                                    # Up level: white circle with black border
                                    {
                                        "label": html.Span(
                                            [
                                                html.Span(
                                                    "",
                                                    style={
                                                        "display": "inline-block",
                                                        "width": "11px",
                                                        "height": "11px",
                                                        "backgroundColor": "white",
                                                        "border": "2px solid #282828",
                                                        "borderRadius": "50%",
                                                        "marginRight": "4px",
                                                        "verticalAlign": "middle",
                                                    },
                                                ),
                                                "Up (z=+1)",
                                            ]
                                        ),
                                        "value": 1,
                                    },
                                ],
                                # All levels checked by default (show all rooms)
                                value=[-1, 0, 1],
                                inline=True,
                            ),
                            # ---------------------------------------------------------
                            # Z-Level Visual Offset Control
                            # ---------------------------------------------------------
                            # Allows users to adjust how much stacked rooms are
                            # visually separated. 0 = no offset (overlap), higher
                            # values = more separation. Uses -/+/input for easy control.
                            html.Div(
                                [
                                    html.Label(
                                        "Stack Offset:",
                                        className="ms-4 me-2",
                                        style={"whiteSpace": "nowrap"},
                                    ),
                                    dbc.InputGroup(
                                        [
                                            dbc.Button(
                                                "-",
                                                id="z-level-offset-decrease",
                                                color="secondary",
                                                size="sm",
                                                style={"width": "32px"},
                                            ),
                                            dbc.Input(
                                                id="z-level-offset",
                                                type="number",
                                                value=0.4,
                                                min=0,
                                                max=5,
                                                step=0.1,
                                                size="sm",
                                                style={"width": "70px", "textAlign": "center"},
                                            ),
                                            dbc.Button(
                                                "+",
                                                id="z-level-offset-increase",
                                                color="secondary",
                                                size="sm",
                                                style={"width": "32px"},
                                            ),
                                        ],
                                        size="sm",
                                    ),
                                ],
                                className="d-flex align-items-center",
                            ),
                        ],
                        className="d-flex align-items-center mt-2 p-2 bg-light rounded",
                    ),
                ]
            ),
        ],
        className="h-100",
    )
