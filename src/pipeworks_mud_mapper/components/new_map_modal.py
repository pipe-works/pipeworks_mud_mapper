"""New Map modal dialog component."""

import dash_bootstrap_components as dbc
from dash import html


def create_new_map_modal() -> dbc.Modal:
    """Create the New Map modal dialog.

    Returns:
        A Bootstrap modal with form fields for creating a new zone.
    """
    return dbc.Modal(
        [
            dbc.ModalHeader(
                dbc.ModalTitle([html.I(className="bi bi-plus-circle me-2"), "Create New Map"]),
                close_button=True,
            ),
            dbc.ModalBody(
                [
                    dbc.Form(
                        [
                            # Zone ID field
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
                            # Zone Name field
                            dbc.Label("Zone Name", html_for="new-zone-name"),
                            dbc.Input(
                                id="new-zone-name",
                                type="text",
                                placeholder="My Zone",
                                className="mb-3",
                            ),
                            # Description field
                            dbc.Label("Description", html_for="new-zone-description"),
                            dbc.Textarea(
                                id="new-zone-description",
                                placeholder="A brief description of this zone...",
                                className="mb-3",
                                style={"height": "80px"},
                            ),
                            # Validation feedback
                            html.Div(id="new-map-feedback", className="mb-2"),
                        ]
                    ),
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button(
                        "Cancel",
                        id="new-map-cancel-btn",
                        color="secondary",
                        outline=True,
                        className="me-2",
                    ),
                    dbc.Button(
                        [html.I(className="bi bi-check-lg me-2"), "Create"],
                        id="new-map-create-btn",
                        color="success",
                    ),
                ]
            ),
        ],
        id="new-map-modal",
        is_open=False,
        centered=True,
    )
