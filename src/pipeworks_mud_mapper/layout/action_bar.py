"""Action bar component for the bottom of the application.

The action bar provides save/export controls and displays the current
status of the zone file (unsaved changes, etc.).

Component Structure
-------------------
::

    ┌───────────────────────────────────────────────────────────────────┐
    │ [Validate] [Export Zone JSON] [Save Map]         ● Unsaved changes│
    └───────────────────────────────────────────────────────────────────┘

Component IDs
-------------
- ``save-map-btn``: Button to save current map to file
- ``export-zone-btn``: Button to export zone JSON (strips coordinates)
- ``status-indicator``: Span showing save state (colored dot + message)

Status Indicator States
-----------------------
- **Gray dot**: No file loaded
- **Yellow dot**: Unsaved changes exist (save enabled, export disabled)
- **Green dot**: All changes saved (save disabled, export enabled)

See Also
--------
- ``callbacks/file_callbacks.py``: Callbacks for save operations
"""

import dash_bootstrap_components as dbc
from dash import html


def create_action_bar() -> html.Div:
    """Create the bottom action bar with save/export and status controls.

    The action bar contains:

    - Validate button (placeholder for Phase 6)
    - Export Zone JSON button (exports without coordinates)
    - Save Map button (saves with coordinates)
    - Status indicator showing current file and save state

    Returns
    -------
    html.Div
        Container with action buttons and status indicator.

    Component IDs
    -------------
    - ``save-map-btn``: Button to save current map to file
    - ``export-zone-btn``: Button to export zone JSON
    - ``status-indicator``: Span showing current status

    Notes
    -----
    - Validate button is placeholder for Phase 6
    - Export is enabled when file is saved (no unsaved changes)
    - Save is enabled when there are unsaved changes
    - Status indicator shows colored dot and message:

      - Gray: No file loaded
      - Yellow: Unsaved changes
      - Green: Saved successfully
    """
    return html.Div(
        [
            # Validate button (placeholder)
            dbc.Button(
                [html.I(className="bi bi-check-circle me-2"), "Validate"],
                color="info",
                outline=True,
                className="me-2",
                disabled=True,
            ),
            # Export button
            dbc.Button(
                [html.I(className="bi bi-download me-2"), "Export Zone JSON"],
                id="export-zone-btn",
                color="primary",
                outline=True,
                className="me-2",
                disabled=True,
            ),
            # Save button
            dbc.Button(
                [html.I(className="bi bi-save me-2"), "Save Map"],
                id="save-map-btn",
                color="success",
                outline=True,
                disabled=True,
            ),
            # Status indicator (pushed to right with ms-auto)
            html.Span(
                id="status-indicator",
                children=[
                    html.I(className="bi bi-circle-fill text-secondary me-2"),
                    "No file loaded",
                ],
                className="ms-auto text-muted",
            ),
        ],
        className="d-flex align-items-center p-3 bg-light border-top",
    )
