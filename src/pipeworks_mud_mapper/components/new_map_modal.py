"""
New Map modal dialog component for creating zone files.

This module provides the modal dialog used to create new zone files.
The modal collects the zone ID, display name, and optional description
from the user before creating a new zone file.

Design Principles
-----------------
1. **Stateless Component**: The modal returns only UI structure, no state
2. **Validation Deferred**: Input validation handled by app callbacks
3. **Consistent IDs**: All input IDs prefixed with "new-" for namespacing
4. **Accessible**: Proper labels and form structure for screen readers

Modal Structure
---------------
The modal contains:

1. **Header**: Title with icon, close button
2. **Body**: Form with three fields:
   - Zone ID (required): Unique identifier, alphanumeric + underscore
   - Zone Name (required): Human-readable display name
   - Description (optional): Zone description text
   - Feedback area: For validation messages
3. **Footer**: Cancel and Create buttons

Component IDs
-------------
The following IDs are used by app callbacks:

- ``new-map-modal``: The modal container (is_open state)
- ``new-zone-id``: Zone ID input field
- ``new-zone-name``: Zone name input field
- ``new-zone-description``: Description textarea
- ``new-map-feedback``: Validation feedback container
- ``new-map-cancel-btn``: Cancel button
- ``new-map-create-btn``: Create button

Functions
---------
create_new_map_modal() -> dbc.Modal
    Create the modal dialog component.

Usage
-----
Include the modal in your app layout::

    from pipeworks_mud_mapper.components.new_map_modal import create_new_map_modal

    app.layout = html.Div([
        create_new_map_modal(),
        # ... rest of layout
    ])

Control modal visibility with callbacks::

    @callback(
        Output("new-map-modal", "is_open"),
        Input("open-modal-btn", "n_clicks"),
    )
    def open_modal(n_clicks):
        return True if n_clicks else False

Handle form submission::

    @callback(
        Output("new-map-modal", "is_open"),
        Output("new-map-feedback", "children"),
        Input("new-map-create-btn", "n_clicks"),
        State("new-zone-id", "value"),
        State("new-zone-name", "value"),
        State("new-zone-description", "value"),
    )
    def create_zone(n_clicks, zone_id, zone_name, description):
        # Validate and create zone...
        pass
"""

import dash_bootstrap_components as dbc
from dash import html


def create_new_map_modal() -> dbc.Modal:
    """
    Create the New Map modal dialog component.

    Constructs a Bootstrap modal dialog with a form for entering new
    zone details. The modal is initially closed and must be opened
    by setting its ``is_open`` property to True via a callback.

    The modal does not contain any logic - all validation and zone
    creation is handled by app callbacks that reference the component
    IDs defined in this modal.

    Returns
    -------
    dbc.Modal
        A Bootstrap modal component containing:
        - Header with title and close button
        - Body with zone creation form
        - Footer with Cancel and Create buttons

    Examples
    --------
    Add to app layout::

        >>> from pipeworks_mud_mapper.components.new_map_modal import (
        ...     create_new_map_modal
        ... )
        >>> modal = create_new_map_modal()
        >>> modal.id
        'new-map-modal'

    Notes
    -----
    - Modal starts closed (is_open=False)
    - Modal is centered on screen (centered=True)
    - Close button in header allows dismissal
    - All form inputs have associated labels for accessibility
    - Zone ID field includes format hint in form text
    - Description field is a textarea for longer text
    """
    return dbc.Modal(
        [
            # -----------------------------------------------------------------
            # Modal Header
            # -----------------------------------------------------------------
            dbc.ModalHeader(
                dbc.ModalTitle(
                    [
                        html.I(className="bi bi-plus-circle me-2"),  # Icon
                        "Create New Map",
                    ]
                ),
                close_button=True,  # X button to dismiss
            ),
            # -----------------------------------------------------------------
            # Modal Body - Zone Creation Form
            # -----------------------------------------------------------------
            dbc.ModalBody(
                [
                    dbc.Form(
                        [
                            # Zone ID field (required, used as filename)
                            dbc.Label("Zone ID", html_for="new-zone-id"),
                            dbc.Input(
                                id="new-zone-id",
                                type="text",
                                placeholder="my_zone",
                                className="mb-2",
                            ),
                            dbc.FormText(
                                "Unique identifier (letters, numbers, underscores only)",
                                className="mb-3 d-block",
                            ),
                            # Zone Name field (required, display name)
                            dbc.Label("Zone Name", html_for="new-zone-name"),
                            dbc.Input(
                                id="new-zone-name",
                                type="text",
                                placeholder="My Zone",
                                className="mb-3",
                            ),
                            # Description field (optional, textarea for longer text)
                            dbc.Label("Description", html_for="new-zone-description"),
                            dbc.Textarea(
                                id="new-zone-description",
                                placeholder="A brief description of this zone...",
                                className="mb-3",
                                style={"height": "80px"},
                            ),
                            # Validation feedback container (populated by callbacks)
                            html.Div(id="new-map-feedback", className="mb-2"),
                        ]
                    ),
                ]
            ),
            # -----------------------------------------------------------------
            # Modal Footer - Action Buttons
            # -----------------------------------------------------------------
            dbc.ModalFooter(
                [
                    # Cancel button - closes modal without action
                    dbc.Button(
                        "Cancel",
                        id="new-map-cancel-btn",
                        color="secondary",
                        outline=True,
                        className="me-2",
                    ),
                    # Create button - triggers zone creation
                    dbc.Button(
                        [
                            html.I(className="bi bi-check-lg me-2"),  # Checkmark icon
                            "Create",
                        ],
                        id="new-map-create-btn",
                        color="success",
                    ),
                ]
            ),
        ],
        id="new-map-modal",
        is_open=False,  # Start closed
        centered=True,  # Center on screen
    )
