"""Main Dash application for the MUD Mapper."""

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, callback, dcc, html

from pipeworks_mud_mapper.components.map_view import create_map_figure

# Initialize the Dash app with Bootstrap theme
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="PipeWorks MUD Mapper",
)


def create_file_browser() -> dbc.Card:
    """Create the left column file browser placeholder."""
    return dbc.Card(
        [
            dbc.CardHeader("File Browser"),
            dbc.CardBody(
                [
                    html.Div(
                        [
                            html.I(className="bi bi-folder me-2"),
                            html.Span("data/"),
                        ],
                        className="mb-2",
                    ),
                    html.Div(
                        [
                            html.Span("  ", style={"whiteSpace": "pre"}),
                            html.I(className="bi bi-folder me-2"),
                            html.Span("maps/"),
                        ],
                        className="mb-2 ms-3",
                    ),
                    html.Div(
                        [
                            html.Span("    ", style={"whiteSpace": "pre"}),
                            html.I(className="bi bi-file-earmark me-2"),
                            html.Span("crooked_pipe.map.json", className="text-muted"),
                        ],
                        className="mb-2 ms-4",
                    ),
                    html.Div(
                        [
                            html.Span("    ", style={"whiteSpace": "pre"}),
                            html.I(className="bi bi-file-earmark me-2"),
                            html.Span("cobbled_street.map.json", className="text-muted"),
                        ],
                        className="mb-2 ms-4",
                    ),
                    html.Hr(),
                    dbc.Button(
                        [html.I(className="bi bi-plus me-2"), "New Map"],
                        color="secondary",
                        size="sm",
                        outline=True,
                        disabled=True,
                    ),
                ],
                className="font-monospace small",
            ),
        ],
        className="h-100",
    )


def create_map_panel() -> dbc.Card:
    """Create the center column map panel."""
    return dbc.Card(
        [
            dbc.CardBody(
                [
                    # Map figure
                    dcc.Graph(
                        id="map-graph",
                        figure=create_map_figure(z_level=0),
                        config={
                            "displayModeBar": True,
                            "scrollZoom": True,
                            "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                        },
                    ),
                    # Layer controls
                    html.Div(
                        [
                            html.Label("Layer (Z):", className="me-3"),
                            dbc.RadioItems(
                                id="z-level-selector",
                                options=[
                                    {"label": "z = -1 (Down)", "value": -1},
                                    {"label": "z = 0 (Ground)", "value": 0},
                                    {"label": "z = +1 (Up)", "value": 1},
                                ],
                                value=0,
                                inline=True,
                            ),
                        ],
                        className="d-flex align-items-center mt-2 p-2 bg-light rounded",
                    ),
                ]
            ),
        ],
        className="h-100",
    )


def create_properties_panel() -> dbc.Card:
    """Create the right column properties panel placeholder."""
    return dbc.Card(
        [
            dbc.CardHeader("Properties"),
            dbc.CardBody(
                [
                    html.P(
                        "Select a room to edit its properties.",
                        className="text-muted fst-italic",
                    ),
                    html.Hr(),
                    # Placeholder form fields
                    dbc.Label("Room ID", html_for="room-id"),
                    dbc.Input(
                        id="room-id",
                        type="text",
                        placeholder="spawn",
                        disabled=True,
                        className="mb-3",
                    ),
                    dbc.Label("Name", html_for="room-name"),
                    dbc.Input(
                        id="room-name",
                        type="text",
                        placeholder="The Crooked Pipe",
                        disabled=True,
                        className="mb-3",
                    ),
                    dbc.Label("Description", html_for="room-description"),
                    dbc.Textarea(
                        id="room-description",
                        placeholder="A low-ceilinged goblin pub...",
                        disabled=True,
                        className="mb-3",
                        style={"height": "100px"},
                    ),
                    dbc.Label("Coordinates", html_for="room-coords"),
                    dbc.InputGroup(
                        [
                            dbc.InputGroupText("X"),
                            dbc.Input(
                                type="number", value=0, disabled=True, style={"width": "60px"}
                            ),
                            dbc.InputGroupText("Y"),
                            dbc.Input(
                                type="number", value=0, disabled=True, style={"width": "60px"}
                            ),
                            dbc.InputGroupText("Z"),
                            dbc.Input(
                                type="number", value=0, disabled=True, style={"width": "60px"}
                            ),
                        ],
                        className="mb-3",
                    ),
                    html.Hr(),
                    dbc.Label("Exits"),
                    html.Div(
                        [
                            html.Small("No exits defined", className="text-muted"),
                        ],
                        className="mb-3 p-2 bg-light rounded",
                    ),
                    dbc.Label("Items"),
                    html.Div(
                        [
                            html.Small("No items", className="text-muted"),
                        ],
                        className="mb-3 p-2 bg-light rounded",
                    ),
                ]
            ),
        ],
        className="h-100",
    )


def create_action_bar() -> html.Div:
    """Create the bottom action bar."""
    return html.Div(
        [
            dbc.Button(
                [html.I(className="bi bi-check-circle me-2"), "Validate"],
                color="info",
                outline=True,
                className="me-2",
                disabled=True,
            ),
            dbc.Button(
                [html.I(className="bi bi-download me-2"), "Export Zone JSON"],
                color="primary",
                outline=True,
                className="me-2",
                disabled=True,
            ),
            dbc.Button(
                [html.I(className="bi bi-save me-2"), "Save Map"],
                color="success",
                outline=True,
                disabled=True,
            ),
            html.Span(
                [html.I(className="bi bi-circle-fill text-secondary me-2"), "No file loaded"],
                className="ms-auto text-muted",
            ),
        ],
        className="d-flex align-items-center p-3 bg-light border-top",
    )


# Main layout
app.layout = dbc.Container(
    [
        # Header
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
        # Three-column layout
        dbc.Row(
            [
                # Left column - File Browser (2/12)
                dbc.Col(
                    create_file_browser(),
                    width=2,
                    className="pe-2",
                ),
                # Center column - Map (7/12)
                dbc.Col(
                    create_map_panel(),
                    width=7,
                    className="px-2",
                ),
                # Right column - Properties (3/12)
                dbc.Col(
                    create_properties_panel(),
                    width=3,
                    className="ps-2",
                ),
            ],
            className="flex-grow-1",
            style={"minHeight": "600px"},
        ),
        # Action bar
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


# Callback: Update map when Z level changes
@callback(
    Output("map-graph", "figure"),
    Input("z-level-selector", "value"),
)
def update_map_layer(z_level: int) -> dict:
    """Update the map figure when Z level selector changes."""
    return create_map_figure(z_level=z_level)


def run_app(debug: bool = True, port: int = 8050) -> None:
    """Run the Dash application.

    Args:
        debug: Enable debug mode with auto-reload.
        port: Port to run the server on.
    """
    print("\n  PipeWorks MUD Mapper")
    print(f"  Running on http://127.0.0.1:{port}")
    print("  Press Ctrl+C to quit\n")
    app.run(debug=debug, port=port)


if __name__ == "__main__":
    run_app()
