"""Exports browser component for the left column.

The left column now focuses on exported game server JSON files. Map
selection is handled from the Workspace table, so the Mapper DB list
is no longer rendered here.

Component Structure
-------------------
::

    ┌────────────────────────┐
    │ Game Server Exports    │  <- CardHeader
    ├────────────────────────┤
    │ 📁 data/zones/         │  <- Export directory
    │   ├── zone1            │  <- Dynamic export list
    │   └── zone2            │
    └────────────────────────┘

Component IDs
-------------
- ``zone-files-list-container``: Container div for exported zone file list
- ``exports-status-indicator``: Text showing latest export status

Notes
-----
Zone files are exported as JSON for the game server and listed separately.

See Also
--------
- ``callbacks/file_callbacks.py``: Callbacks for export list management
"""

import dash_bootstrap_components as dbc
from dash import html

from pipeworks_mud_mapper.services.app_config import (
    format_display_path,
    format_short_path,
    get_path_settings,
)


def create_file_browser() -> dbc.Card:
    """Create the left column exports browser component.

    The exports browser displays the game-ready zone JSON files so
    users can quickly review what has been exported from the mapper.
    """
    paths = get_path_settings()
    zones_label = format_display_path(paths["zones_dir"])
    zones_short = format_short_path(paths["zones_dir"])

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
        [exports],
        className="d-grid gap-2",
    )
