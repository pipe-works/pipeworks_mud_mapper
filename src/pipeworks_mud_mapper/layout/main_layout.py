"""Main application layout assembly.

This module assembles all layout components into the complete application
layout. It combines the file browser, map panel, properties panel, and
action bar with the necessary state stores and modal dialogs.

Application Structure
---------------------
::

    ┌─────────────────────────────────────────────────────────────────────┐
    │ 🗺️ PipeWorks MUD Mapper                           Zone: zone_name  │
    ├─────────┬─────────────────────────────────────────────┬─────────────┤
    │  File   │                                             │    Room     │
    │ Browser │              Map Panel                      │ Properties  │
    │  (2/12) │               (7/12)                        │   (3/12)    │
    │         │                                             │             │
    │ 📁 data/│         [Interactive Map]                   │ Room ID: _  │
    │  file1  │                                             │ Name: _____ │
    │  file2  │         Layer (Z): ○-1 ●0 ○+1               │ Coords: XYZ │
    ├─────────┴─────────────────────────────────────────────┴─────────────┤
    │ [Validate] [Export Zone JSON] [Save Map]          ● Status message  │
    └─────────────────────────────────────────────────────────────────────┘

State Stores
------------
The layout includes hidden dcc.Store components for application state:

- ``zone-files-store``: List of available zone file names
- ``current-zone-data``: Currently loaded zone data (dict)
- ``selected-file``: Currently selected file name
- ``selected-room``: Currently selected room ID
- ``has-unsaved-changes``: Boolean flag for save status
- ``delete-undo-data``: Undo data for room deletion (room + removed exits)
- ``validation-report``: Most recent validation report (dict)

Modal Dialogs
-------------
- ``new-map-modal``: Create new map file
- ``delete-confirm-modal``: Confirm room deletion
- ``validation-results-modal``: Display validation results

See Also
--------
- ``file_browser.py``: Left column component
- ``map_panel.py``: Center column component
- ``properties_panel.py``: Right column component
- ``action_bar.py``: Bottom bar component
- ``components/new_map_modal.py``: Zone creation modal
"""

import dash_bootstrap_components as dbc
from dash import dcc, html

from pipeworks_mud_mapper.components.new_map_modal import create_new_map_modal
from pipeworks_mud_mapper.layout.action_bar import create_action_bar
from pipeworks_mud_mapper.layout.file_browser import create_file_browser
from pipeworks_mud_mapper.layout.map_panel import create_map_panel
from pipeworks_mud_mapper.layout.properties_panel import create_properties_panel


def create_app_layout() -> dbc.Container:
    """Create the complete application layout.

    Assembles all layout components into a responsive three-column
    layout with header and action bar.

    Returns
    -------
    dbc.Container
        Bootstrap Container with the complete application layout.

    Layout Structure
    ----------------
    - **State Stores**: Hidden dcc.Store components for app state
    - **Modal Dialogs**: New Map creation modal
    - **Header Row**: App title and current zone name
    - **Three-Column Layout**: File browser, map, properties panel
    - **Action Bar**: Save button and status indicator

    Notes
    -----
    - Uses Bootstrap 12-column grid: 2 + 7 + 3 = 12
    - Container is fluid (full-width) and fills viewport height
    - dcc.Interval triggers initial file list load
    """
    return dbc.Container(
        [
            # -----------------------------------------------------------------
            # State Stores (invisible, hold application state)
            # -----------------------------------------------------------------
            dcc.Store(id="zone-files-store", data=[]),  # List of file names
            dcc.Store(id="current-zone-data", data=None),  # Current zone dict
            dcc.Store(id="selected-file", data=None),  # Selected file name
            dcc.Store(id="selected-room", data=None),  # Selected room ID
            dcc.Store(id="has-unsaved-changes", data=False),  # Unsaved flag
            dcc.Store(id="delete-undo-data", data=None),  # Undo data for delete
            dcc.Store(id="validation-report", data=None),  # Validation report
            # Interval to trigger initial file load
            dcc.Interval(id="initial-load", interval=100, max_intervals=1),
            # -----------------------------------------------------------------
            # Modal Dialogs
            # -----------------------------------------------------------------
            create_new_map_modal(),
            # Delete confirmation modal
            dbc.Modal(
                [
                    dbc.ModalHeader(
                        dbc.ModalTitle(
                            [html.I(className="bi bi-exclamation-triangle me-2"), "Confirm Delete"]
                        ),
                        close_button=True,
                    ),
                    dbc.ModalBody(id="delete-confirm-body"),
                    dbc.ModalFooter(
                        [
                            dbc.Button(
                                "Cancel",
                                id="delete-cancel-btn",
                                color="secondary",
                                outline=True,
                            ),
                            dbc.Button(
                                [html.I(className="bi bi-trash me-2"), "Delete"],
                                id="delete-confirm-btn",
                                color="danger",
                            ),
                        ]
                    ),
                ],
                id="delete-confirm-modal",
                is_open=False,
            ),
            # Validation results modal - displays validation check results
            # with summary counts, categorized warnings, and clickable room links
            dbc.Modal(
                [
                    dbc.ModalHeader(
                        dbc.ModalTitle(
                            [html.I(className="bi bi-check-circle me-2"), "Validation Results"]
                        ),
                        close_button=True,
                    ),
                    # Modal body populated by validation_callbacks.run_validation
                    dbc.ModalBody(id="validation-results-body"),
                    dbc.ModalFooter(
                        [
                            # Close button
                            dbc.Button(
                                "Close",
                                id="validation-close-btn",
                                color="secondary",
                                outline=True,
                            ),
                        ]
                    ),
                ],
                id="validation-results-modal",
                is_open=False,
                size="lg",  # Large modal to show full validation report
                scrollable=True,  # Allow scrolling for long reports
            ),
            # -----------------------------------------------------------------
            # Header Row
            # -----------------------------------------------------------------
            dbc.Row(
                [
                    dbc.Col(
                        html.H4(
                            [
                                html.I(className="bi bi-map me-2"),
                                "PipeWorks MUD Mapper",
                            ],
                            className="mb-0",
                        ),
                        width="auto",
                    ),
                    dbc.Col(
                        html.Span("Zone: (none)", className="text-muted", id="current-zone"),
                        width="auto",
                        className="ms-auto",
                    ),
                ],
                className="py-3 border-bottom mb-3 align-items-center",
            ),
            # -----------------------------------------------------------------
            # Three-Column Layout
            # -----------------------------------------------------------------
            dbc.Row(
                [
                    # Left column - File Browser (2/12 width)
                    dbc.Col(
                        create_file_browser(),
                        width=2,
                        className="pe-2",
                    ),
                    # Center column - Map (7/12 width)
                    dbc.Col(
                        create_map_panel(),
                        width=7,
                        className="px-2",
                    ),
                    # Right column - Properties (3/12 width)
                    dbc.Col(
                        create_properties_panel(),
                        width=3,
                        className="ps-2",
                    ),
                ],
                className="flex-grow-1",
                style={"minHeight": "600px"},
            ),
            # -----------------------------------------------------------------
            # Action Bar (Bottom)
            # -----------------------------------------------------------------
            dbc.Row(
                [
                    dbc.Col(create_action_bar()),
                ],
                className="mt-3",
            ),
        ],
        fluid=True,
        className="vh-100 d-flex flex-column",
    )
