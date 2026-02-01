"""Main Dash application for the MUD Mapper."""

import re
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, callback, ctx, dcc, html, no_update

from pipeworks_mud_mapper.components.map_view import (
    create_map_figure,
    create_map_figure_with_rooms,
)
from pipeworks_mud_mapper.components.new_map_modal import create_new_map_modal
from pipeworks_mud_mapper.utils.zone_io import (
    auto_layout_rooms,
    create_blank_zone,
    list_zone_files,
    load_zone_json,
    save_zone_json,
)

# Data directory for zone files
DATA_DIR = Path(__file__).parent.parent.parent / "data"

# Initialize the Dash app with Bootstrap theme
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="PipeWorks MUD Mapper",
)


def create_file_browser() -> dbc.Card:
    """Create the left column file browser."""
    return dbc.Card(
        [
            dbc.CardHeader("File Browser"),
            dbc.CardBody(
                [
                    html.Div(
                        [
                            html.I(className="bi bi-folder-fill me-2 text-warning"),
                            html.Span("data/"),
                        ],
                        className="mb-2",
                    ),
                    # Dynamic file list container
                    html.Div(id="file-list-container", className="ms-3 mb-3"),
                    html.Hr(),
                    dbc.Button(
                        [html.I(className="bi bi-plus me-2"), "New Map"],
                        id="new-map-btn",
                        color="secondary",
                        size="sm",
                        outline=True,
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
        # State stores
        dcc.Store(id="zone-files-store", data=[]),
        dcc.Store(id="current-zone-data", data=None),
        dcc.Store(id="selected-file", data=None),
        dcc.Interval(id="initial-load", interval=100, max_intervals=1),
        # New Map modal
        create_new_map_modal(),
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


# Callback: Load zone files on initial load and when store updates
@callback(
    Output("zone-files-store", "data"),
    Input("initial-load", "n_intervals"),
    prevent_initial_call=False,
)
def load_zone_files(_: int) -> list[str]:
    """Load list of zone files from working directory."""
    files = list_zone_files(DATA_DIR)
    return [f.name for f in files]


# Callback: Render file list from store
@callback(
    Output("file-list-container", "children"),
    Input("zone-files-store", "data"),
    Input("selected-file", "data"),
)
def render_file_list(files: list[str], selected_file: str | None) -> list:
    """Render the file list in the browser with clickable items."""
    if not files:
        return [html.Span("No zone files found", className="text-muted fst-italic")]

    items = []
    for filename in files:
        is_selected = filename == selected_file
        icon_class = "bi bi-file-earmark-code me-2"
        if is_selected:
            icon_class += " text-primary"
        items.append(
            html.Div(
                [
                    html.I(className=icon_class),
                    html.Span(filename, className="fw-bold" if is_selected else ""),
                ],
                id={"type": "file-item", "filename": filename},
                className="mb-1 p-1 rounded file-item"
                + (" bg-primary bg-opacity-10" if is_selected else ""),
                style={"cursor": "pointer"},
                n_clicks=0,
            )
        )
    return items


# Callback: Handle file click - load zone data
@callback(
    Output("selected-file", "data"),
    Output("current-zone-data", "data"),
    Output("current-zone", "children"),
    Input({"type": "file-item", "filename": ALL}, "n_clicks"),
    State("zone-files-store", "data"),
    prevent_initial_call=True,
)
def handle_file_click(n_clicks_list: list[int], files: list[str]) -> tuple:
    """Load zone data when a file is clicked."""
    # Find which file was clicked
    if not any(n_clicks_list):
        return no_update, no_update, no_update

    # Get the triggered file from context
    triggered = ctx.triggered_id
    if not triggered or not isinstance(triggered, dict):
        return no_update, no_update, no_update

    filename = triggered.get("filename")
    if not filename:
        return no_update, no_update, no_update

    # Load the zone file
    file_path = DATA_DIR / filename
    try:
        zone_data = load_zone_json(file_path)
        # Auto-layout if rooms don't have coords
        zone_data = auto_layout_rooms(zone_data)
        zone_name = zone_data.get("name", filename)
        return filename, zone_data, f"Zone: {zone_name}"
    except Exception as e:
        print(f"Error loading zone: {e}")
        return no_update, no_update, no_update


# Callback: Update map when zone data or Z level changes
@callback(
    Output("map-graph", "figure"),
    Input("current-zone-data", "data"),
    Input("z-level-selector", "value"),
)
def update_map_with_rooms(zone_data: dict | None, z_level: int) -> dict:
    """Update the map figure with loaded zone rooms."""
    if not zone_data:
        return create_map_figure(z_level=z_level)

    rooms = zone_data.get("rooms", {})
    return create_map_figure_with_rooms(rooms=rooms, z_level=z_level)


# Callback: Open New Map modal
@callback(
    Output("new-map-modal", "is_open", allow_duplicate=True),
    Input("new-map-btn", "n_clicks"),
    prevent_initial_call=True,
)
def open_new_map_modal(n_clicks: int) -> bool:
    """Open the New Map modal when button is clicked."""
    if n_clicks:
        return True
    return False


# Callback: Close modal on cancel
@callback(
    Output("new-map-modal", "is_open", allow_duplicate=True),
    Input("new-map-cancel-btn", "n_clicks"),
    prevent_initial_call=True,
)
def close_new_map_modal(n_clicks: int) -> bool:
    """Close the New Map modal when cancel is clicked."""
    if n_clicks:
        return False
    return no_update


# Callback: Create new zone on submit
@callback(
    Output("new-map-modal", "is_open"),
    Output("zone-files-store", "data", allow_duplicate=True),
    Output("new-map-feedback", "children"),
    Output("new-zone-id", "value"),
    Output("new-zone-name", "value"),
    Output("new-zone-description", "value"),
    Input("new-map-create-btn", "n_clicks"),
    State("new-zone-id", "value"),
    State("new-zone-name", "value"),
    State("new-zone-description", "value"),
    prevent_initial_call=True,
)
def create_new_zone(
    n_clicks: int,
    zone_id: str,
    zone_name: str,
    description: str,
) -> tuple:
    """Create a new zone file when Create button is clicked."""
    if not n_clicks:
        return no_update, no_update, no_update, no_update, no_update, no_update

    # Validate zone_id
    zone_id = (zone_id or "").strip()
    zone_name = (zone_name or "").strip()
    description = (description or "").strip()

    if not zone_id:
        feedback = dbc.Alert("Zone ID is required.", color="danger", className="mb-0")
        return no_update, no_update, feedback, no_update, no_update, no_update

    if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", zone_id):
        feedback = dbc.Alert(
            "Zone ID must start with a letter and contain only letters, numbers, and underscores.",
            color="danger",
            className="mb-0",
        )
        return no_update, no_update, feedback, no_update, no_update, no_update

    if not zone_name:
        feedback = dbc.Alert("Zone Name is required.", color="danger", className="mb-0")
        return no_update, no_update, feedback, no_update, no_update, no_update

    # Check if file already exists
    file_path = DATA_DIR / f"{zone_id}.json"
    if file_path.exists():
        feedback = dbc.Alert(
            f"A zone with ID '{zone_id}' already exists.", color="warning", className="mb-0"
        )
        return no_update, no_update, feedback, no_update, no_update, no_update

    # Create and save the zone
    zone_data = create_blank_zone(zone_id, zone_name, description)
    save_zone_json(zone_data, file_path)

    # Refresh file list
    files = list_zone_files(DATA_DIR)
    file_names = [f.name for f in files]

    # Close modal and clear form
    return False, file_names, "", "", "", ""


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
