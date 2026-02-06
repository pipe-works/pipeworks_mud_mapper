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
- ``dev-snapshot-list-container``: Container div for dev snapshot file list
- ``zone-files-list-container``: Container div for exported zone file list
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

from pipeworks_mud_mapper.services.app_config import (
    format_display_path,
    format_short_path,
    get_path_settings,
)


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
    paths = get_path_settings()
    maps_label = format_display_path(paths["maps_dir"])
    dev_snapshots_label = format_display_path(paths["dev_snapshots_dir"])
    zones_label = format_display_path(paths["zones_dir"])
    maps_short = format_short_path(paths["maps_dir"])
    dev_snapshots_short = format_short_path(paths["dev_snapshots_dir"])
    zones_short = format_short_path(paths["zones_dir"])
    dev_snapshots_toggle_label = f"Dev snapshots ({dev_snapshots_label.rstrip('/')})"

    # Separate cards clarify the three distinct file sources.
    mapper_files = dbc.Card(
        [
            dbc.CardHeader(
                html.Div(
                    [
                        html.Span("Mapper Files", className="me-auto"),
                        dbc.Button(
                            [
                                html.Span("Refresh All"),
                                html.Span("↻", className="ms-1"),
                            ],
                            id="file-browser-refresh-btn",
                            color="link",
                            className="file-browser-refresh",
                            size="sm",
                            title="Refresh all file lists",
                        ),
                    ],
                    className="d-flex align-items-center",
                )
            ),
            dbc.CardBody(
                [
                    html.Div(
                        [
                            html.I(className="bi bi-folder-fill me-2 text-warning"),
                            html.Span(maps_short),
                        ],
                        className="file-path-chip mb-2",
                        title=maps_label,
                    ),
                    html.Div(
                        id="file-list-container",
                        className="ms-3 mb-2 file-list-scroll",
                    ),
                    html.Div(
                        id="status-indicator",
                        children="No file loaded",
                        className="text-muted small mt-2",
                    ),
                ],
                className="font-monospace small",
            ),
        ]
    )

    dev_snapshots = dbc.Card(
        [
            dbc.CardHeader("Dev Snapshots"),
            dbc.CardBody(
                [
                    html.Div(
                        [
                            html.I(className="bi bi-folder-fill me-2 text-warning"),
                            html.Span(dev_snapshots_short),
                        ],
                        className="file-path-chip mb-2",
                        title=dev_snapshots_label,
                    ),
                    html.Div(
                        id="dev-snapshot-list-container",
                        className="ms-3 mb-2 file-list-scroll",
                    ),
                    dbc.Checkbox(
                        id="dev-save-toggle",
                        label=dev_snapshots_toggle_label,
                        value=False,
                        className="small",
                    ),
                ],
                className="font-monospace small",
            ),
        ]
    )

    exports = dbc.Card(
        [
            dbc.CardHeader("Game Server Exports"),
            dbc.CardBody(
                [
                    html.Div(
                        [
                            html.I(className="bi bi-folder-fill me-2 text-warning"),
                            html.Span(zones_short),
                        ],
                        className="file-path-chip mb-2",
                        title=zones_label,
                    ),
                    html.Div(
                        id="zone-files-list-container",
                        className="ms-3 mb-2 file-list-scroll",
                    ),
                ],
                className="font-monospace small",
            ),
        ]
    )

    return html.Div(
        [mapper_files, dev_snapshots, exports],
        className="d-grid gap-2",
    )
