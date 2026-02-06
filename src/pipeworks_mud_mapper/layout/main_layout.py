"""Main application layout assembly.

This module assembles all layout components into the complete application
layout. It combines the file browser, map panel, Ollama panel, properties
panel, and action bar with the necessary state stores and modal dialogs.

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
    │         ├─────────────────────────────────────────────┤             │
    │         │         🤖 LLM Assistant (Ollama)           │             │
    │         │         [Template] [Model] [Generate]       │             │
    ├─────────┴─────────────────────────────────────────────┴─────────────┤
    │ [Validate] [Export Zone JSON] [Save Map]          ● Status message  │
    └─────────────────────────────────────────────────────────────────────┘

State Stores
------------
The layout includes hidden dcc.Store components for application state:

- ``zones-files-store``: List of exported zone file names
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
- ``map_panel.py``: Center column component (map visualization)
- ``ollama_panel.py``: Center column component (LLM Assistant)
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
from pipeworks_mud_mapper.layout.ollama_panel import create_ollama_panel
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
            # Bootstrap theme stylesheet (swapped via theme toggle callback).
            # Using a link tag keeps the toggle fast and avoids rebuilding
            # the Dash app on theme changes.
            html.Link(
                id="theme-link",
                rel="stylesheet",
                href=dbc.themes.BOOTSTRAP,
            ),
            # -----------------------------------------------------------------
            # State Stores (invisible, hold application state)
            # -----------------------------------------------------------------
            dcc.Store(id="zones-files-store", data=[]),  # List of exported zone files
            dcc.Store(id="current-zone-data", data=None),  # Current zone dict
            dcc.Store(id="selected-file", data=None),  # Selected file name
            dcc.Store(id="selected-room", data=None),  # Selected room ID
            dcc.Store(id="has-unsaved-changes", data=False),  # Unsaved flag
            dcc.Store(id="file-delete-pending", data=None),
            # File selection metadata for the File Properties panel.
            dcc.Store(id="selected-zone-file", data=None),
            dcc.Store(id="delete-undo-data", data=None),  # Undo data for delete
            dcc.Store(id="validation-report", data=None),  # Validation report
            # Ollama generation metadata store - holds LLM generation info
            # (model, seed, parameters, prompts) from the most recent generation.
            # This data flows from generate_description() to send_to_description()
            # where it gets attached to the room as llm_generation metadata.
            # Format: dict with keys matching OllamaGenerationInfo fields, or None.
            dcc.Store(id="ollama-last-generation-info", data=None),
            # Latest validator result for the current LLM response.
            dcc.Store(id="ollama-validation-info", data=None),
            # In-memory validator history for the Ollama panel staging area.
            dcc.Store(id="ollama-validation-history", data=[]),
            # Background I/O job tracking for saves/exports.
            dcc.Store(id="io-jobs", data={"jobs": []}),
            # Background job tracking for workspace DB tools.
            dcc.Store(id="workspace-jobs", data={"jobs": []}),
            # Interval to trigger initial file load
            dcc.Interval(id="initial-load", interval=100, max_intervals=1),
            # Interval to poll background I/O jobs.
            dcc.Interval(id="io-job-poll", interval=1000),
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
            # File delete confirmation modal (maps/zones)
            dbc.Modal(
                [
                    dbc.ModalHeader(
                        dbc.ModalTitle(
                            [html.I(className="bi bi-trash me-2"), "Confirm File Delete"]
                        ),
                        close_button=True,
                    ),
                    dbc.ModalBody(id="file-delete-confirm-body"),
                    dbc.ModalFooter(
                        [
                            dbc.Button(
                                "Cancel",
                                id="file-delete-cancel-btn",
                                color="secondary",
                                outline=True,
                            ),
                            dbc.Button(
                                [html.I(className="bi bi-trash me-2"), "Delete File"],
                                id="file-delete-confirm-btn",
                                color="danger",
                            ),
                        ]
                    ),
                ],
                id="file-delete-confirm-modal",
                is_open=False,
            ),
            # Zone JSON modal - shows exported zone files for quick review
            dbc.Modal(
                [
                    dbc.ModalHeader(
                        dbc.ModalTitle(id="zone-json-modal-title"),
                        close_button=True,
                    ),
                    dbc.ModalBody(id="zone-json-modal-body"),
                    dbc.ModalFooter(
                        [
                            dbc.Button(
                                "Close",
                                id="zone-json-close-btn",
                                color="secondary",
                                outline=True,
                            ),
                        ]
                    ),
                ],
                id="zone-json-modal",
                is_open=False,
                size="lg",
                scrollable=True,
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
                        html.Div(
                            [
                                html.Span(
                                    "Zone: (none)",
                                    className="text-muted",
                                    id="current-zone",
                                ),
                                # Theme toggle for light/dark preferences.
                                dbc.Switch(
                                    id="theme-toggle",
                                    label="Dark mode",
                                    value=False,
                                    className="mb-0",
                                ),
                            ],
                            className="d-flex align-items-center gap-3",
                        ),
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
                    # Center column - Map + Ollama (7/12 width)
                    # Contains the map panel at top and LLM Assistant below
                    dbc.Col(
                        html.Div(
                            [
                                create_map_panel(),
                                create_ollama_panel(),
                            ]
                        ),
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
