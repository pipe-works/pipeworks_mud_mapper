"""File browser component for the left column.

The file browser displays available map files from the data/maps/ directory
and allows users to load them or create new maps.

Component Structure
-------------------
::

    ┌─────────────────────┐
    │   File Browser      │  <- CardHeader
    ├─────────────────────┤
    │ 📁 maps/            │  <- Folder icon
    │   ├── zone1         │  <- Dynamic file list
    │   └── zone2         │     (rendered by callback)
    │ ──────────────────  │
    │ [+ New Map]         │  <- New Map button
    └─────────────────────┘

Component IDs
-------------
- ``file-list-container``: Container div populated by render_file_list callback
- ``new-map-btn``: Button that opens the New Map modal

Notes
-----
Files are stored as ``*.map.json`` but displayed without the extension.
The two-file workflow separates:

- Map files (data/maps/*.map.json) - authoring with coordinates
- Zone files (data/zones/*.json) - game truth without coordinates

See Also
--------
- ``callbacks/file_callbacks.py``: Callbacks for file loading and creation
- ``components/new_map_modal.py``: Modal dialog for creating new maps
"""

import dash_bootstrap_components as dbc
from dash import html


def create_file_browser() -> dbc.Card:
    """Create the left column file browser component.

    The file browser displays:

    - A folder icon with "data/" label
    - Dynamic list of zone files (rendered by callback)
    - "New Map" button to open creation modal

    Returns
    -------
    dbc.Card
        Bootstrap Card containing the file browser UI.
        The file list is populated by the render_file_list callback.

    Component IDs
    -------------
    - ``file-list-container``: Container for dynamic file list
    - ``new-map-btn``: Button to open New Map modal

    Notes
    -----
    - Files are rendered as clickable divs with pattern-matching IDs
    - Selected file is highlighted with different styling
    - Uses monospace font for code-like appearance
    """
    return dbc.Card(
        [
            dbc.CardHeader("File Browser"),
            dbc.CardBody(
                [
                    # Folder header
                    html.Div(
                        [
                            html.I(className="bi bi-folder-fill me-2 text-warning"),
                            html.Span("maps/"),
                        ],
                        className="mb-2",
                    ),
                    # Dynamic file list (populated by callback)
                    html.Div(id="file-list-container", className="ms-3 mb-3"),
                    html.Hr(),
                    # New Map button
                    dbc.Button(
                        [html.I(className="bi bi-plus me-2"), "New Map"],
                        id="new-map-btn",
                        color="secondary",
                        size="sm",
                        outline=True,
                    ),
                ],
                className="font-monospace small",
            ),
        ],
        className="h-100",
    )
