"""Map panel component for the center column.

The map panel displays the interactive Plotly visualization of rooms
and exits, along with controls for selecting the Z-level (floor).

Component Structure
-------------------
::

    ┌─────────────────────────────────────────┐
    │                                         │
    │        ┌───┐     ┌───┐                  │
    │        │ A │─────│ B │   Plotly map     │
    │        └───┘     └───┘                  │
    │          │                              │
    │        ┌───┐                            │
    │        │ C │                            │
    │        └───┘                            │
    │                                         │
    ├─────────────────────────────────────────┤
    │ Layer (Z): ○ -1 (Down) ● 0 (Ground) ○ +1│
    └─────────────────────────────────────────┘

Component IDs
-------------
- ``map-graph``: Plotly Graph component for room visualization
- ``z-level-selector``: RadioItems for selecting which Z-level to display

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

    - Plotly Graph component for room visualization
    - Z-level selector radio buttons

    Returns
    -------
    dbc.Card
        Bootstrap Card containing the map and layer controls.

    Component IDs
    -------------
    - ``map-graph``: Plotly Graph for map visualization
    - ``z-level-selector``: Radio buttons for Z-level selection

    Notes
    -----
    - Map starts empty and is populated by update_map_with_rooms callback
    - Scroll zoom and pan are enabled via Graph config
    - Lasso and select tools are removed from mode bar
    - Z-level options: -1 (Down), 0 (Ground), 1 (Up)
    """
    return dbc.Card(
        [
            dbc.CardBody(
                [
                    # Plotly map figure
                    dcc.Graph(
                        id="map-graph",
                        figure=create_map_figure(z_level=0),
                        config={
                            "displayModeBar": True,
                            "scrollZoom": True,
                            "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                        },
                    ),
                    # Z-level selector
                    html.Div(
                        [
                            html.Label("Layer (Z):", className="me-3"),
                            dbc.RadioItems(
                                id="z-level-selector",
                                options=[
                                    {"label": "z = -1 (Down)", "value": -1},
                                    {"label": "z = 0 (Ground)", "value": 0},
                                    {"label": "z = +1 (Up)", "value": 1},
                                ],
                                value=0,
                                inline=True,
                            ),
                        ],
                        className="d-flex align-items-center mt-2 p-2 bg-light rounded",
                    ),
                ]
            ),
        ],
        className="h-100",
    )
