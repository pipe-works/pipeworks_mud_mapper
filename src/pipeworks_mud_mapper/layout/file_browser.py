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
- ``save-map-btn``: Button to save current map with coordinates
- ``export-zone-btn``: Button to export zone JSON without coordinates
- ``validate-zone-btn``: Button to run validation checks on the map
- ``dev-save-toggle``: Toggle to save snapshots to data/maps/dev_snapshots
- ``status-indicator``: Text showing current file state (saved/unsaved)

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
                        className="w-100 mb-2",
                    ),
                    # Save Map button
                    dbc.Button(
                        [html.I(className="bi bi-save me-2"), "Save Map"],
                        id="save-map-btn",
                        color="success",
                        size="sm",
                        className="w-100 mb-2",
                        disabled=True,
                    ),
                    dbc.Checkbox(
                        id="dev-save-toggle",
                        label="Dev snapshots (maps/dev_snapshots)",
                        value=False,
                        className="small mb-2",
                    ),
                    # Export Zone JSON button
                    dbc.Button(
                        [html.I(className="bi bi-download me-2"), "Export Zone"],
                        id="export-zone-btn",
                        color="primary",
                        size="sm",
                        className="w-100 mb-2",
                        disabled=True,
                    ),
                    # Validate Zone button - runs validation checks and shows results
                    # Disabled until a map file is loaded
                    dbc.Button(
                        [html.I(className="bi bi-check-circle me-2"), "Validate Zone"],
                        id="validate-zone-btn",
                        color="info",
                        size="sm",
                        outline=True,
                        className="w-100 mb-2",
                        disabled=True,
                    ),
                    # Status indicator - shows current file state
                    # Updated by file_callbacks.update_save_status
                    html.Div(
                        id="status-indicator",
                        children="No file loaded",
                        className="text-muted small text-center mt-2",
                    ),
                ],
                className="font-monospace small",
            ),
        ],
        className="h-100",
    )
