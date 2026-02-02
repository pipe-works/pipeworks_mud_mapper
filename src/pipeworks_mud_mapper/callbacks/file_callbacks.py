"""File management callbacks.

This module handles:

- Loading map file list on startup
- Rendering the file browser list
- Loading map data when file is clicked
- New map modal open/close/create
- Save and export functionality
- Status updates

Two-File Workflow
-----------------
The mapper uses two file types:

- **Map files** (``data/maps/*.map.json``): Authoring source with coordinates
- **Zone files** (``data/zones/*.json``): Game truth without coordinates

Authors work with map files. Zone files are exported for game server use.

Component Dependencies
----------------------
**Inputs:**
- ``initial-load``: Interval trigger for startup
- ``zone-files-store``: List of available files
- ``selected-file``: Currently selected file
- ``file-item`` (pattern): Clickable file list items
- ``new-map-btn``: Open new map modal
- ``new-map-cancel-btn``: Close modal
- ``new-map-create-btn``: Create new zone
- ``save-map-btn``: Save current map
- ``export-zone-btn``: Export zone JSON

**Outputs:**
- ``zone-files-store``: Updated file list
- ``file-list-container``: Rendered file list
- ``selected-file``: Selected file name
- ``current-zone-data``: Loaded zone data
- ``current-zone``: Zone name display
- ``new-map-modal``: Modal visibility
- ``has-unsaved-changes``: Unsaved flag
- ``save-map-btn``: Save button state
- ``status-indicator``: Status display
"""

import re
from pathlib import Path
from typing import Any

import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, callback, ctx, html, no_update

from pipeworks_mud_mapper.services import zone_service
from pipeworks_mud_mapper.utils.zone_io import (
    list_map_files,
)

# Directory paths for two-file workflow
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
MAPS_DIR = DATA_DIR / "maps"
ZONES_DIR = DATA_DIR / "zones"


# =============================================================================
# File List Callbacks
# =============================================================================


@callback(
    Output("zone-files-store", "data"),
    Input("initial-load", "n_intervals"),
    prevent_initial_call=False,
)
def load_map_files_list(_: int) -> list[str]:
    """Load list of map files from the maps directory.

    This callback is triggered once on initial page load (via dcc.Interval)
    and populates the zone-files-store with available map file names.

    Parameters
    ----------
    _ : int
        Interval count (ignored, we just need the trigger).

    Returns
    -------
    list[str]
        List of map file names (e.g., ["dungeon.map.json", "town.map.json"]).
    """
    # Ensure maps directory exists
    MAPS_DIR.mkdir(parents=True, exist_ok=True)

    files = list_map_files(MAPS_DIR)
    return [f.name for f in files]


@callback(
    Output("file-list-container", "children"),
    Input("zone-files-store", "data"),
    Input("selected-file", "data"),
)
def render_file_list(files: list[str], selected_file: str | None) -> list:
    """Render the file list in the browser with clickable items.

    Creates a list of clickable div elements, one for each map file.
    The currently selected file is highlighted with different styling.

    Parameters
    ----------
    files : list[str]
        List of map file names from zone-files-store.
    selected_file : str | None
        Currently selected file name, or None.

    Returns
    -------
    list
        List of html.Div elements for each file, or placeholder
        message if no files found.
    """
    if not files:
        return [html.Span("No map files found", className="text-muted fst-italic")]

    items = []
    for filename in files:
        is_selected = filename == selected_file
        icon_class = "bi bi-file-earmark-code me-2"
        if is_selected:
            icon_class += " text-primary"

        # Show shorter display name (without .map.json)
        display_name = filename
        if filename.endswith(".map.json"):
            display_name = filename[:-9]  # Remove .map.json

        items.append(
            html.Div(
                [
                    html.I(className=icon_class),
                    html.Span(display_name, className="fw-bold" if is_selected else ""),
                ],
                id={"type": "file-item", "filename": filename},
                className="mb-1 p-1 rounded file-item"
                + (" bg-primary bg-opacity-10" if is_selected else ""),
                style={"cursor": "pointer"},
                n_clicks=0,
            )
        )
    return items


@callback(
    Output("selected-file", "data"),
    Output("current-zone-data", "data"),
    Output("current-zone", "children"),
    Output("has-unsaved-changes", "data", allow_duplicate=True),
    Input({"type": "file-item", "filename": ALL}, "n_clicks"),
    State("zone-files-store", "data"),
    State("selected-file", "data"),
    prevent_initial_call=True,
)
def handle_file_click(
    n_clicks_list: list[int], files: list[str], current_file: str | None
) -> tuple:
    """Load map data when a file is clicked in the browser.

    Uses Dash pattern-matching callbacks to detect which file was clicked
    from the dynamic file list. Loads the map JSON file.

    Also resets has-unsaved-changes to False when loading a new file.

    Parameters
    ----------
    n_clicks_list : list[int]
        Click counts for all file items (pattern-matching input).
    files : list[str]
        List of file names from zone-files-store.
    current_file : str | None
        Currently selected file (to detect re-clicks on same file).

    Returns
    -------
    tuple
        (selected_file, zone_data, zone_display, has_unsaved) or no_update tuple.
    """
    # Check if any file was actually clicked (before accessing ctx)
    if not any(n_clicks_list):
        print("[DEBUG] handle_file_click: no clicks, returning no_update")
        return no_update, no_update, no_update, no_update

    # Debug logging (only after confirming there was a click)
    print(f"[DEBUG] handle_file_click: n_clicks={n_clicks_list}, current={current_file}")
    print(f"[DEBUG] handle_file_click: triggered_id={ctx.triggered_id}")

    # Get the triggered file from callback context
    triggered = ctx.triggered_id
    if not triggered or not isinstance(triggered, dict):
        print("[DEBUG] handle_file_click: no valid trigger, returning no_update")
        return no_update, no_update, no_update, no_update

    filename = triggered.get("filename")
    if not filename:
        print("[DEBUG] handle_file_click: no filename in trigger, returning no_update")
        return no_update, no_update, no_update, no_update

    # If clicking the same file that's already loaded, don't reload
    if filename == current_file:
        print(f"[DEBUG] handle_file_click: same file {filename}, returning no_update")
        return no_update, no_update, no_update, no_update

    # Load the map file using zone_service
    file_path = MAPS_DIR / filename
    try:
        map_file = zone_service.load_map_file(file_path)
        # Convert to dict for Dash storage
        zone_data = map_file.to_dict_with_list_coords()
        zone_name = zone_data.get("name", filename)
        # Reset unsaved changes when loading a new file
        return filename, zone_data, f"Zone: {zone_name}", False
    except Exception as e:
        print(f"Error loading map: {e}")
        return no_update, no_update, no_update, no_update


# =============================================================================
# New Map Modal Callbacks
# =============================================================================


@callback(
    Output("new-map-modal", "is_open", allow_duplicate=True),
    Input("new-map-btn", "n_clicks"),
    prevent_initial_call=True,
)
def open_new_map_modal(n_clicks: int) -> bool:
    """Open the New Map modal when the button is clicked.

    Parameters
    ----------
    n_clicks : int
        Click count for the "New Map" button.

    Returns
    -------
    bool
        True to open the modal.
    """
    if n_clicks:
        return True
    return False


@callback(
    Output("new-map-modal", "is_open", allow_duplicate=True),
    Input("new-map-cancel-btn", "n_clicks"),
    prevent_initial_call=True,
)
def close_new_map_modal(n_clicks: int) -> Any:
    """Close the New Map modal when Cancel is clicked.

    Parameters
    ----------
    n_clicks : int
        Click count for the Cancel button.

    Returns
    -------
    bool | no_update
        False to close the modal, or no_update if not clicked.
    """
    if n_clicks:
        return False
    return no_update


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
def create_new_map(
    n_clicks: int,
    zone_id: str,
    zone_name: str,
    description: str,
) -> tuple:
    """Create a new map file when the Create button is clicked.

    Validates input, creates the map file structure, saves to data/maps/,
    and refreshes the file list.

    Parameters
    ----------
    n_clicks : int
        Click count for the Create button.
    zone_id : str
        Zone ID input value.
    zone_name : str
        Zone name input value.
    description : str
        Zone description input value.

    Returns
    -------
    tuple
        (modal_open, file_list, feedback, zone_id_val, name_val, desc_val).
        On success: closes modal, updates list, clears form.
        On error: keeps modal open, shows feedback alert.
    """
    if not n_clicks:
        return no_update, no_update, no_update, no_update, no_update, no_update

    # Normalize inputs
    zone_id = (zone_id or "").strip().lower()
    zone_name = (zone_name or "").strip()
    description = (description or "").strip()

    # Validate zone_id
    if not zone_id:
        feedback = dbc.Alert("Zone ID is required.", color="danger", className="mb-0")
        return no_update, no_update, feedback, no_update, no_update, no_update

    if not re.match(r"^[a-z][a-z0-9_]*$", zone_id):
        feedback = dbc.Alert(
            "Zone ID must start with a letter and contain only "
            "lowercase letters, numbers, and underscores.",
            color="danger",
            className="mb-0",
        )
        return no_update, no_update, feedback, no_update, no_update, no_update

    # Validate zone_name
    if not zone_name:
        feedback = dbc.Alert("Zone Name is required.", color="danger", className="mb-0")
        return no_update, no_update, feedback, no_update, no_update, no_update

    # Check if file already exists
    file_path = MAPS_DIR / f"{zone_id}.map.json"
    if file_path.exists():
        feedback = dbc.Alert(
            f"A map with ID '{zone_id}' already exists.",
            color="warning",
            className="mb-0",
        )
        return no_update, no_update, feedback, no_update, no_update, no_update

    # Create and save the map file using zone_service
    map_file = zone_service.create_new_map_file(
        zone_id=zone_id,
        name=zone_name,
        spawn_room_name="Spawn Room",
        description=description,
    )
    zone_service.save_map_file(map_file, file_path)

    # Refresh file list
    files = list_map_files(MAPS_DIR)
    file_names = [f.name for f in files]

    # Close modal and clear form
    return False, file_names, "", "", "", ""


# =============================================================================
# Save/Export/Status Callbacks
# =============================================================================


@callback(
    Output("save-map-btn", "disabled"),
    Output("export-zone-btn", "disabled"),
    Output("status-indicator", "children"),
    Output("debug-btn-state", "children"),
    Input("has-unsaved-changes", "data"),
    Input("selected-file", "data"),
)
def update_save_status(has_unsaved: bool, selected_file: str | None) -> tuple:
    """Update save/export button state and status indicator.

    Shows appropriate status based on current state:

    - No file loaded: disabled buttons
    - Unsaved changes: enabled save, disabled export
    - All saved: disabled save, enabled export

    Parameters
    ----------
    has_unsaved : bool
        Whether there are unsaved changes.
    selected_file : str | None
        Currently selected file name.

    Returns
    -------
    tuple
        (save_disabled, export_disabled, status_text, debug_text).
    """
    print(f"[DEBUG] update_save_status: has_unsaved={has_unsaved}, file={selected_file}")

    if not selected_file:
        print("[DEBUG] update_save_status: no file loaded")
        return True, True, "No file loaded", "no-file"

    # Display name without .map.json
    display_name = selected_file
    if selected_file.endswith(".map.json"):
        display_name = selected_file[:-9]

    if has_unsaved:
        print("[DEBUG] update_save_status: unsaved changes - save=ENABLED")
        return False, True, f"Unsaved: {display_name}", "unsaved"

    print("[DEBUG] update_save_status: saved - export=ENABLED")
    return True, False, f"Saved: {display_name}", "saved"


@callback(
    Output("has-unsaved-changes", "data", allow_duplicate=True),
    Output("room-form-feedback", "children", allow_duplicate=True),
    Input("save-map-btn", "n_clicks"),
    State("current-zone-data", "data"),
    State("selected-file", "data"),
    prevent_initial_call=True,
)
def save_map_to_file(n_clicks: int, zone_data: dict | None, selected_file: str | None) -> tuple:
    """Save the current map data to the file.

    Parameters
    ----------
    n_clicks : int
        Click count for Save button.
    zone_data : dict | None
        Current map data to save.
    selected_file : str | None
        Target file name.

    Returns
    -------
    tuple
        (unsaved_flag, feedback_alert).
        On success: False and success message.
        On error: no_update and error message.
    """
    if not n_clicks or not zone_data or not selected_file:
        return no_update, no_update

    file_path = MAPS_DIR / selected_file
    try:
        # Convert dict to MapFile and save
        from pipeworks_mud_mapper.models import MapFile

        map_file = MapFile.from_dict(zone_data)
        zone_service.save_map_file(map_file, file_path)

        display_name = selected_file
        if selected_file.endswith(".map.json"):
            display_name = selected_file[:-9]

        feedback = dbc.Alert(
            f"Saved: {display_name}",
            color="success",
            className="mb-0 py-2",
            duration=3000,
        )
        return False, feedback
    except Exception as e:
        feedback = dbc.Alert(
            f"Error saving: {e}",
            color="danger",
            className="mb-0 py-2",
        )
        return no_update, feedback


@callback(
    Output("room-form-feedback", "children", allow_duplicate=True),
    Input("export-zone-btn", "n_clicks"),
    State("current-zone-data", "data"),
    State("selected-file", "data"),
    prevent_initial_call=True,
)
def export_zone_to_file(n_clicks: int, zone_data: dict | None, selected_file: str | None) -> Any:
    """Export the current map as a zone file (strips coordinates).

    Exports to data/zones/{name}.json, creating the game truth file
    that the MUD server consumes.

    Parameters
    ----------
    n_clicks : int
        Click count for Export button.
    zone_data : dict | None
        Current map data to export.
    selected_file : str | None
        Source file name (used to derive export name).

    Returns
    -------
    str
        Feedback alert component.
    """
    if not n_clicks or not zone_data or not selected_file:
        return no_update

    # Derive export path from map file name
    map_path = MAPS_DIR / selected_file
    export_path = zone_service.get_suggested_export_path(map_path)

    try:
        # Ensure zones directory exists
        ZONES_DIR.mkdir(parents=True, exist_ok=True)

        # Convert dict to MapFile and export
        from pipeworks_mud_mapper.models import MapFile

        map_file = MapFile.from_dict(zone_data)
        zone_service.export_zone(map_file, export_path)

        feedback = dbc.Alert(
            f"Exported: {export_path.name} (coordinates stripped)",
            color="info",
            className="mb-0 py-2",
            duration=4000,
        )
        return feedback
    except Exception as e:
        feedback = dbc.Alert(
            f"Error exporting: {e}",
            color="danger",
            className="mb-0 py-2",
        )
        return feedback
