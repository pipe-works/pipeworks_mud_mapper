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
- ``dev-snapshot-files-store``: List of available dev snapshot files
- ``selected-file``: Currently selected file
- ``file-item`` (pattern): Clickable file list items
- ``dev-snapshot-item`` (pattern): Clickable dev snapshot items
- ``new-map-btn``: Open new map modal
- ``new-map-cancel-btn``: Close modal
- ``new-map-create-btn``: Create new zone
- ``save-map-btn``: Save current map
- ``export-zone-btn``: Export zone JSON

**Outputs:**
- ``zone-files-store``: Updated file list
- ``file-list-container``: Rendered file list
- ``dev-snapshot-files-store``: Updated dev snapshot list
- ``dev-snapshot-list-container``: Rendered dev snapshot list
- ``selected-file``: Selected file name
- ``current-zone-data``: Loaded zone data
- ``current-zone``: Zone name display
- ``new-map-modal``: Modal visibility
- ``has-unsaved-changes``: Unsaved flag
- ``save-map-btn``: Save button state
- ``status-indicator``: Status display
"""

import copy
import re
from datetime import UTC, datetime
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
DEV_MAPS_DIR = MAPS_DIR / "dev_snapshots"


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
    Output("dev-snapshot-files-store", "data"),
    Input("initial-load", "n_intervals"),
    Input("dev-snapshot-status", "data"),
    Input("save-map-btn", "n_clicks"),
    prevent_initial_call=False,
)
def load_dev_snapshot_files_list(_: int, __: dict | None, ___: int | None) -> list[str]:
    """Load list of dev snapshot files from the dev snapshots directory.

    This callback is intentionally triggered by:
    - Initial page load (to populate the list)
    - Dev snapshot status updates (auto snapshot paths)
    - Save button clicks (manual snapshots from Save Map)

    Parameters
    ----------
    _ : int
        Interval count (ignored; the trigger is all we need).
    __ : dict | None
        Latest dev snapshot metadata, used only to trigger refresh.
    ___ : int | None
        Save button click count, used only to trigger refresh.

    Returns
    -------
    list[str]
        List of dev snapshot map file names (e.g., ["zone_20240101.map.json"]).
    """
    # Ensure dev snapshot directory exists so the UI remains stable.
    DEV_MAPS_DIR.mkdir(parents=True, exist_ok=True)

    # Collect dev snapshot map files and return their names for display.
    files = list_map_files(DEV_MAPS_DIR)
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
    Output("dev-snapshot-list-container", "children"),
    Input("dev-snapshot-files-store", "data"),
    Input("selected-file", "data"),
)
def render_dev_snapshot_list(files: list[str], selected_file: str | None) -> list:
    """Render the dev snapshot file list with clickable items.

    Parameters
    ----------
    files : list[str]
        List of dev snapshot file names from dev-snapshot-files-store.
    selected_file : str | None
        Currently selected file name, or None.

    Returns
    -------
    list
        List of html.Div elements for each dev snapshot, or placeholder
        message if no snapshots are found.
    """
    # Empty state to make it clear there are no snapshots yet.
    if not files:
        return [html.Span("No dev snapshots found", className="text-muted fst-italic")]

    items = []
    for filename in files:
        # Reuse selected-file styling so the UI stays consistent.
        is_selected = filename == selected_file
        icon_class = "bi bi-file-earmark-code me-2"
        if is_selected:
            icon_class += " text-primary"

        # Preserve the snapshot filename, but drop ".map.json" for readability.
        display_name = filename
        if filename.endswith(".map.json"):
            display_name = filename[:-9]

        # Pattern-matching ID lets us bind a single callback for all snapshots.
        items.append(
            html.Div(
                [
                    html.I(className=icon_class),
                    html.Span(display_name, className="fw-bold" if is_selected else ""),
                ],
                id={"type": "dev-snapshot-item", "filename": filename},
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
    Input({"type": "dev-snapshot-item", "filename": ALL}, "n_clicks"),
    State("selected-file", "data"),
    prevent_initial_call=True,
)
def handle_file_click(
    map_clicks: list[int],
    snapshot_clicks: list[int],
    current_file: str | None,
) -> tuple:
    """Load map data when a map or dev snapshot is clicked in either browser.

    This single callback handles both file browsers to avoid duplicate output
    errors in Dash. The triggered item tells us whether to read from
    data/maps (authoring files) or data/maps/dev_snapshots (snapshots).

    Parameters
    ----------
    map_clicks : list[int]
        Click counts for regular map file items.
    snapshot_clicks : list[int]
        Click counts for dev snapshot items.
    current_file : str | None
        Currently selected file name (used to avoid redundant reloads).

    Returns
    -------
    tuple
        (selected_file, zone_data, zone_display, has_unsaved) or no_update tuple.
    """
    # Bail out early when nothing has been clicked in either list.
    if not any(map_clicks) and not any(snapshot_clicks):
        print("[DEBUG] handle_file_click: no clicks, returning no_update")
        return no_update, no_update, no_update, no_update

    # Log the trigger details so we can trace clicks across both lists.
    print(
        "[DEBUG] handle_file_click: "
        f"map_clicks={map_clicks}, snapshot_clicks={snapshot_clicks}, current={current_file}"
    )
    print(f"[DEBUG] handle_file_click: triggered_id={ctx.triggered_id}")

    # The triggered_id includes the pattern-matching payload with filename/type.
    triggered = ctx.triggered_id
    if not triggered or not isinstance(triggered, dict):
        print("[DEBUG] handle_file_click: no valid trigger, returning no_update")
        return no_update, no_update, no_update, no_update

    filename = triggered.get("filename")
    if not filename:
        print("[DEBUG] handle_file_click: no filename in trigger, returning no_update")
        return no_update, no_update, no_update, no_update

    # Avoid reloading the same file if it is already selected.
    if filename == current_file:
        print(f"[DEBUG] handle_file_click: same file {filename}, returning no_update")
        return no_update, no_update, no_update, no_update

    # Decide which directory to load from based on which list fired.
    # Default to MAPS_DIR so we always have a safe fallback.
    source_type = triggered.get("type")
    if source_type == "dev-snapshot-item":
        file_path = DEV_MAPS_DIR / filename
    else:
        file_path = MAPS_DIR / filename

    # Load the selected map file and reset unsaved changes.
    try:
        map_file = zone_service.load_map_file(file_path)
        zone_data = map_file.to_dict_with_list_coords()
        zone_name = zone_data.get("name", filename)
        return filename, zone_data, f"Zone: {zone_name}", False
    except Exception as e:
        print(f"Error loading map file {filename}: {e}")
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

    # Display full file name for clarity
    display_name = selected_file

    if has_unsaved:
        print("[DEBUG] update_save_status: unsaved changes - save=ENABLED")
        return False, True, f"Unsaved: {display_name}", "unsaved"

    print("[DEBUG] update_save_status: saved - export=ENABLED")
    saved_alert = dbc.Alert(
        f"Saved: {display_name}",
        color="success",
        className="mb-0 py-1",
        duration=3000,
        dismissable=True,
        fade=True,
    )
    return True, False, saved_alert, "saved"


@callback(
    Output("has-unsaved-changes", "data", allow_duplicate=True),
    Output("room-form-feedback", "children", allow_duplicate=True),
    Input("save-map-btn", "n_clicks"),
    State("current-zone-data", "data"),
    State("selected-file", "data"),
    State("dev-save-toggle", "value"),
    prevent_initial_call=True,
)
def save_map_to_file(
    n_clicks: int,
    zone_data: dict | None,
    selected_file: str | None,
    dev_save_enabled: bool | None,
) -> tuple:
    """Save the current map data to the file.

    Parameters
    ----------
    n_clicks : int
        Click count for Save button.
    zone_data : dict | None
        Current map data to save.
    selected_file : str | None
        Target file name.
    dev_save_enabled : bool | None
        When True, also save a snapshot to data/maps/dev_snapshots.

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

        dev_note = ""
        if isinstance(dev_save_enabled, list):
            dev_enabled = len(dev_save_enabled) > 0
        else:
            dev_enabled = bool(dev_save_enabled)

        if dev_enabled:
            DEV_MAPS_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
            snapshot_name = f"{display_name}_{timestamp}.map.json"
            snapshot_path = DEV_MAPS_DIR / snapshot_name
            zone_service.save_map_file(map_file, snapshot_path)
            dev_note = " (dev snapshot saved)"

        feedback = dbc.Alert(
            f"Saved: {display_name}{dev_note}",
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
    Output("dev-snapshot-status", "data"),
    Input("current-zone-data", "data"),
    Input("dev-save-toggle", "value"),
    State("selected-file", "data"),
    prevent_initial_call=True,
)
def auto_snapshot_map(
    zone_data: dict | None,
    dev_save_enabled: bool | None,
    selected_file: str | None,
) -> Any:
    """Persist dev snapshots on every map change when toggled.

    Parameters
    ----------
    zone_data : dict | None
        Current map data to snapshot.
    selected_file : str | None
        Active map file name (used for snapshot naming).
    dev_save_enabled : bool | None
        Toggle state for dev snapshots.
    Returns
    -------
    dict | None
        Snapshot metadata, or no_update when no snapshot is written.
    """
    # No zone data means there's nothing to snapshot.
    # This can happen during initial load or if a map is cleared.
    if not zone_data:
        return no_update

    if isinstance(dev_save_enabled, list):
        dev_enabled = len(dev_save_enabled) > 0
    else:
        dev_enabled = bool(dev_save_enabled)

    # Toggle is off - dev snapshots are disabled.
    if not dev_enabled:
        return no_update

    from pipeworks_mud_mapper.models import MapFile

    # Snapshot the current map state as-is (authoring truth).
    # This path is used for any map change, not specifically LLM generations.
    map_file = MapFile.from_dict(zone_data)
    display_name = selected_file
    if not display_name:
        display_name = zone_data.get("id") or "unsaved_zone"
    if display_name.endswith(".map.json"):
        display_name = display_name[:-9]

    DEV_MAPS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
    snapshot_name = f"{display_name}_{timestamp}.map.json"
    snapshot_path = DEV_MAPS_DIR / snapshot_name
    zone_service.save_map_file(map_file, snapshot_path)

    return {
        "snapshot": snapshot_name,
        "timestamp": timestamp,
    }


@callback(
    Output("dev-snapshot-status", "data", allow_duplicate=True),
    Input("ollama-last-generation-info", "data"),
    State("ollama-response", "value"),
    State("ollama-validation-info", "data"),
    State("selected-room", "data"),
    State("current-zone-data", "data"),
    State("selected-file", "data"),
    State("dev-save-toggle", "value"),
    prevent_initial_call=True,
)
def auto_snapshot_on_generation(
    generation_info: dict | None,
    response_text: str | None,
    validation_info: dict | None,
    selected_room: str | None,
    zone_data: dict | None,
    selected_file: str | None,
    dev_save_enabled: bool | None,
) -> Any:
    """Persist dev snapshots when a new Ollama generation completes.

    This allows snapshotting even if the user doesn't apply the response
    to a room description (current-zone-data remains unchanged).
    """
    # Require both a generation record and zone data.
    # If a generation occurred but no map is loaded, we cannot snapshot.
    if not generation_info or not zone_data:
        return no_update

    if isinstance(dev_save_enabled, list):
        dev_enabled = len(dev_save_enabled) > 0
    else:
        dev_enabled = bool(dev_save_enabled)

    # Toggle is off - do not write snapshots.
    if not dev_enabled:
        return no_update

    from pipeworks_mud_mapper.models import MapFile

    # Use a copy so we can inject the latest LLM output without mutating live state.
    # The live map should only change when the user explicitly clicks
    # "Send to Description".
    snapshot_zone = copy.deepcopy(zone_data)
    # If a room is selected and we have an LLM response, stage that data
    # into the snapshot so it reflects "what was just generated", even if
    # the author hasn't applied it yet.
    if selected_room and response_text:
        rooms = dict(snapshot_zone.get("rooms", {}))
        if selected_room in rooms:
            updated_room = dict(rooms[selected_room])
            # Inject the freshly generated description for snapshot visibility.
            updated_room["description"] = response_text.strip()
            # Attach generation metadata for reproducibility.
            updated_room["llm_generation"] = generation_info
            # Attach validator output for review; if none, remove any stale value.
            if validation_info:
                updated_room["description_validation"] = validation_info
            else:
                updated_room.pop("description_validation", None)
            rooms[selected_room] = updated_room
            snapshot_zone["rooms"] = rooms

    map_file = MapFile.from_dict(snapshot_zone)
    display_name = selected_file
    if not display_name:
        display_name = zone_data.get("id") or "unsaved_zone"
    if display_name.endswith(".map.json"):
        display_name = display_name[:-9]

    DEV_MAPS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
    snapshot_name = f"{display_name}_{timestamp}.map.json"
    snapshot_path = DEV_MAPS_DIR / snapshot_name
    zone_service.save_map_file(map_file, snapshot_path)

    return {
        "snapshot": snapshot_name,
        "timestamp": timestamp,
        "trigger": "generation",
    }


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
