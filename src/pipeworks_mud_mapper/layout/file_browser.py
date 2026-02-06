"""File browser component for the left column.

The file browser lists maps from the SQLite authoring database and allows
users to load them or create new maps.

Component Structure
-------------------
::

    ┌─────────────────────┐
    │   File Browser      │  <- CardHeader
    ├─────────────────────┤
    │ 🗄 mapper.db        │  <- Database icon
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
- ``zone-files-list-container``: Container div for exported zone file list
- ``status-indicator``: Text showing current file state (saved/unsaved)
- ``exports-status-indicator``: Text showing latest export status

Notes
-----
Maps are stored in the SQLite database. Zone files are exported as JSON for
the game server and listed separately.

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
    db_path = paths["db_path"]
    # Reuse path formatters for the parent directory, then append filename.
    # This keeps display output consistent with other path chips while
    # avoiding an incorrect trailing slash on the file itself.
    db_label = f"{format_display_path(db_path.parent).rstrip('/')}/{db_path.name}"
    db_short = f"{format_short_path(db_path.parent).rstrip('/')}/{db_path.name}"
    zones_label = format_display_path(paths["zones_dir"])
    zones_short = format_short_path(paths["zones_dir"])

    # Separate cards clarify the three distinct file sources.
    mapper_files = dbc.Card(
        [
            dbc.CardHeader(
                html.Div(
                    [
                        html.Span("Mapper DB", className="me-auto"),
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
                            html.I(className="bi bi-database-fill me-2 text-warning"),
                            html.Span(db_short),
                        ],
                        className="file-path-chip mb-2",
                        title=db_label,
                    ),
                    html.Div(
                        id="file-list-container",
                        className="ms-3 mb-2 file-list-scroll",
                    ),
                    html.Div(
                        id="status-indicator",
                        children="No map loaded",
                        className="text-muted small mt-2",
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
                    html.Div(
                        id="exports-status-indicator",
                        children="No export activity yet",
                        className="text-muted small mt-2",
                    ),
                ],
                className="font-monospace small",
            ),
        ]
    )

    return html.Div(
        [mapper_files, exports],
        className="d-grid gap-2",
    )
