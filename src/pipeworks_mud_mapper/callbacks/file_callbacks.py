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
- ``zone-files-store``: List of available map files
- ``zones-files-store``: List of available zone export files
- ``selected-file``: Currently selected file
- ``file-item`` (pattern): Clickable file list items
- ``new-map-btn``: Open new map modal
- ``new-map-cancel-btn``: Close modal
- ``new-map-create-btn``: Create new zone
- ``save-map-btn``: Save current map
- ``export-zone-btn``: Export zone JSON

**Outputs:**
- ``zone-files-store``: Updated file list
- ``file-list-container``: Rendered map file list
- ``zone-files-list-container``: Rendered zone export list
- ``exports-status-indicator``: Export status display
- ``selected-file``: Selected file name
- ``current-zone-data``: Loaded zone data
- ``current-zone``: Zone name display
- ``new-map-modal``: Modal visibility
- ``has-unsaved-changes``: Unsaved flag
- ``save-map-btn``: Save button state
- ``status-indicator``: Status display
"""

import json
import re
import time
from pathlib import Path
from typing import Any

import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, callback, ctx, html, no_update

from pipeworks_mud_mapper.services import zone_service
from pipeworks_mud_mapper.services.app_config import get_path_settings
from pipeworks_mud_mapper.services.io_queue import (
    forget_io_job,
    get_io_job_status,
    submit_io_job,
)
from pipeworks_mud_mapper.services.state import ZoneAction, apply_zone_action

# Directory paths for two-file workflow (user-configurable via config/server.ini)
PATHS = get_path_settings()
MAPS_DIR = PATHS["maps_dir"]
ZONES_DIR = PATHS["zones_dir"]

# =============================================================================
# File Listing Cache
# =============================================================================
# These cache structures reduce repeated filesystem scans when callbacks
# are triggered in quick succession.
# The cache is intentionally short-lived to keep the UI responsive while
# avoiding expensive directory scans on slower disks.

FILE_LIST_CACHE_TTL_SECONDS = 1.0
_FILE_LIST_CACHE: dict[Path, tuple[float, list[Path]]] = {}


def _get_cached_map_files(directory: Path, *, force_refresh: bool = False) -> list[Path]:
    """Return cached file listings with a short TTL.

    Parameters
    ----------
    directory : Path
        Directory to list.
    force_refresh : bool
        When True, bypasses the cache and rescans immediately.

    Returns
    -------
    list[Path]
        List of map file paths.
    """
    # Monotonic clock avoids issues if system time changes.
    now = time.monotonic()
    # Pull cached tuple if we have seen this directory before.
    cached = _FILE_LIST_CACHE.get(directory)

    if cached and not force_refresh:
        last_scan, files = cached
        # Use cached listing if it is still within the TTL window.
        if now - last_scan <= FILE_LIST_CACHE_TTL_SECONDS:
            return files

    # Refresh listing from disk and update cache timestamp.
    files = zone_service.list_map_files(directory)
    _FILE_LIST_CACHE[directory] = (now, files)
    return files


def _room_feedback_payload(content: Any) -> dict[str, Any]:
    """Build a timestamped payload for room form feedback."""
    return {"content": content, "ts": time.monotonic()}


def _save_map_job(map_file: Any, file_path: Path) -> None:
    """Persist a map file in a background thread."""
    zone_service.save_map_file(map_file, file_path)


def _export_zone_job(map_file: Any, export_path: Path) -> None:
    """Export a zone file in a background thread."""
    zone_service.export_zone(map_file, export_path)


# =============================================================================
# File List Callbacks
# =============================================================================


@callback(
    Output("zone-files-store", "data"),
    Input("initial-load", "n_intervals"),
    Input("file-browser-refresh-btn", "n_clicks"),
    prevent_initial_call=False,
)
def load_map_files_list(_: int, __: int | None) -> list[str]:
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

    # Use cached listing to minimize repeated disk reads.
    force_refresh = ctx.triggered_id == "file-browser-refresh-btn"
    files = _get_cached_map_files(MAPS_DIR, force_refresh=force_refresh)
    return [f.name for f in files]


@callback(
    Output("zones-files-store", "data"),
    Input("initial-load", "n_intervals"),
    Input("room-feedback-export", "data"),
    Input("file-browser-refresh-btn", "n_clicks"),
    prevent_initial_call=False,
)
def load_zone_files_list(_: int, __: dict | None, ___: int | None) -> list[str]:
    """Load list of exported zone files from the zones directory.

    This callback is triggered on initial page load and after export
    feedback updates so the list reflects newly exported files.
    """
    # Ensure the export directory exists so the UI list can render consistently.
    ZONES_DIR.mkdir(parents=True, exist_ok=True)
    # Zone files are game-truth JSON (no coordinates), so we list *.json.
    if ctx.triggered_id == "file-browser-refresh-btn":
        # Force refresh on demand.
        _FILE_LIST_CACHE.pop(ZONES_DIR, None)
    files = zone_service.list_zone_files(ZONES_DIR)
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
    Output("zone-files-list-container", "children"),
    Input("zones-files-store", "data"),
)
def render_zone_files_list(files: list[str]) -> list:
    """Render the exported zone file list."""
    # Zones are display-only so users can see what has been exported.
    if not files:
        return [html.Span("No zone exports found", className="text-muted fst-italic")]

    items = []
    for filename in files:
        icon_class = "bi bi-file-earmark-code me-2"

        display_name = filename
        if filename.endswith(".json"):
            display_name = filename[:-5]

        items.append(
            html.Div(
                [
                    html.I(className=icon_class),
                    html.Span(display_name),
                ],
                id={"type": "zone-file-item", "filename": filename},
                className="mb-1 p-1 rounded file-item",
                style={"cursor": "pointer"},
                n_clicks=0,
            )
        )
    return items


@callback(
    Output("exports-status-indicator", "children"),
    Input("room-feedback-export", "data"),
)
def render_export_status(payload: dict | None) -> Any:
    """Render the latest export status feedback in the exports card."""
    if not isinstance(payload, dict):
        return no_update

    content = payload.get("content")
    if content is None:
        return no_update

    return content


@callback(
    Output("zone-json-modal", "is_open"),
    Output("zone-json-modal-title", "children"),
    Output("zone-json-modal-body", "children"),
    Output("selected-zone-file", "data", allow_duplicate=True),
    Input({"type": "zone-file-item", "filename": ALL}, "n_clicks"),
    Input("zone-json-close-btn", "n_clicks"),
    prevent_initial_call=True,
)
def handle_zone_file_click(zone_clicks: list[int], close_clicks: int | None) -> tuple:
    """Open a modal showing the selected zone JSON."""
    trigger = ctx.triggered_id
    if trigger == "zone-json-close-btn":
        return False, no_update, no_update, no_update

    if not any(zone_clicks):
        return no_update, no_update, no_update, no_update

    if not trigger or not isinstance(trigger, dict):
        return no_update, no_update, no_update, no_update

    filename = trigger.get("filename")
    if not filename:
        return no_update, no_update, no_update, no_update

    file_path = ZONES_DIR / filename
    if not file_path.exists():
        feedback = dbc.Alert(
            f"Zone file not found: {filename}",
            color="warning",
            className="mb-0",
        )
        return True, "Zone JSON", feedback, filename

    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        pretty = json.dumps(data, indent=2, sort_keys=True)
        content = html.Pre(pretty, className="mb-0 small")
        return True, f"Zone JSON: {filename}", content, filename
    except json.JSONDecodeError as exc:
        feedback = dbc.Alert(
            f"Invalid JSON in {filename}: {exc}",
            color="danger",
            className="mb-0",
        )
        return True, "Zone JSON", feedback, filename


@callback(
    Output("file-properties-name", "children"),
    Output("file-properties-type", "children"),
    Output("file-properties-delete-btn", "disabled"),
    Input("selected-file", "data"),
    Input("selected-zone-file", "data"),
)
def render_file_properties(
    selected_file: str | None,
    selected_zone_file: str | None,
) -> tuple:
    """Render the file properties summary in the right column."""
    if selected_file:
        name = html.Span(selected_file)
        badge = dbc.Badge("Map file", color="primary", className="me-2")
        return name, html.Div([badge, html.Span("Selected")]), False

    if selected_zone_file:
        name = html.Span(selected_zone_file)
        badge = dbc.Badge("Zone export", color="info", className="me-2")
        return name, html.Div([badge, html.Span("Selected")]), False

    return html.Span("No file selected", className="text-muted"), "", True


@callback(
    Output("file-delete-confirm-modal", "is_open"),
    Output("file-delete-confirm-body", "children"),
    Output("file-delete-pending", "data"),
    Input("file-properties-delete-btn", "n_clicks"),
    Input("file-delete-cancel-btn", "n_clicks"),
    State("selected-file", "data"),
    State("selected-zone-file", "data"),
    prevent_initial_call=True,
)
def request_file_delete(
    delete_clicks: int | None,
    cancel_clicks: int | None,
    selected_file: str | None,
    selected_zone_file: str | None,
) -> tuple:
    """Open confirmation modal when a delete button is clicked."""
    trigger = ctx.triggered_id
    if trigger == "file-delete-cancel-btn":
        return False, no_update, None

    if not delete_clicks:
        return no_update, no_update, no_update

    # Prefer the currently loaded map over a zone export selection.
    if selected_file:
        filename = selected_file
        delete_type = "file-delete-btn"
        label = "map file"
        badge_color = "primary"
        path_hint = MAPS_DIR / filename
    elif selected_zone_file:
        filename = selected_zone_file
        delete_type = "zone-file-delete-btn"
        label = "zone export"
        badge_color = "info"
        path_hint = ZONES_DIR / filename
    else:
        return no_update, no_update, no_update

    body = html.Div(
        [
            html.P("Are you sure you want to delete this file?"),
            html.Div(
                [
                    dbc.Badge(label, color=badge_color, className="me-2"),
                    html.Span(filename, className="fw-bold"),
                ],
                className="mb-1",
            ),
            html.Div(
                [
                    html.Span("Path: ", className="text-muted"),
                    html.Code(str(path_hint)),
                ],
                className="small text-muted",
            ),
        ],
        className="mb-0",
    )
    return True, body, {"type": delete_type, "filename": filename}


@callback(
    Output("zone-files-store", "data", allow_duplicate=True),
    Output("zones-files-store", "data", allow_duplicate=True),
    Output("selected-file", "data", allow_duplicate=True),
    Output("current-zone-data", "data", allow_duplicate=True),
    Output("has-unsaved-changes", "data", allow_duplicate=True),
    Output("file-delete-confirm-modal", "is_open", allow_duplicate=True),
    Input("file-delete-confirm-btn", "n_clicks"),
    State("file-delete-pending", "data"),
    State("selected-file", "data"),
    prevent_initial_call=True,
)
def confirm_file_delete(
    confirm_clicks: int | None,
    pending: dict | None,
    selected_file: str | None,
) -> tuple:
    """Delete a file after confirmation and refresh the relevant list."""
    if not confirm_clicks or not pending:
        return no_update, no_update, no_update, no_update, no_update, no_update

    delete_type = pending.get("type")
    filename = pending.get("filename")
    if not delete_type or not filename:
        return no_update, no_update, no_update, no_update, no_update, no_update

    if delete_type == "file-delete-btn":
        file_path = MAPS_DIR / filename
        list_dir = MAPS_DIR
        list_fn = zone_service.list_map_files
        list_key = "maps"
    else:
        file_path = ZONES_DIR / filename
        list_dir = ZONES_DIR
        list_fn = zone_service.list_zone_files
        list_key = "zones"

    if file_path.exists():
        file_path.unlink()

    files = list_fn(list_dir)
    _FILE_LIST_CACHE[list_dir] = (time.monotonic(), files)
    file_names = [f.name for f in files]

    maps_update = no_update
    zones_update = no_update
    selected_update = no_update
    zone_data_update = no_update
    unsaved_update = no_update

    if list_key == "maps":
        maps_update = file_names
        if filename == selected_file:
            selected_update = None
            zone_data_update = None
            unsaved_update = False
    else:
        zones_update = file_names

    return (
        maps_update,
        zones_update,
        selected_update,
        zone_data_update,
        unsaved_update,
        False,
    )


@callback(
    Output("selected-file", "data"),
    Output("current-zone-data", "data"),
    Output("current-zone", "children"),
    Output("has-unsaved-changes", "data", allow_duplicate=True),
    Output("selected-zone-file", "data", allow_duplicate=True),
    Input({"type": "file-item", "filename": ALL}, "n_clicks"),
    State("selected-file", "data"),
    prevent_initial_call=True,
)
def handle_file_click(
    map_clicks: list[int],
    current_file: str | None,
) -> tuple:
    """Load map data when a map is clicked in the file browser.

    Parameters
    ----------
    map_clicks : list[int]
        Click counts for regular map file items.
    current_file : str | None
        Currently selected file name (used to avoid redundant reloads).

    Returns
    -------
    tuple
        (selected_file, zone_data, zone_display, has_unsaved) or no_update tuple.
    """
    # Bail out early when nothing has been clicked in either list.
    if not any(map_clicks):
        print("[DEBUG] handle_file_click: no clicks, returning no_update")
        return no_update, no_update, no_update, no_update, no_update

    # Log the trigger details so we can trace clicks across both lists.
    print("[DEBUG] handle_file_click: " f"map_clicks={map_clicks}, current={current_file}")
    print(f"[DEBUG] handle_file_click: triggered_id={ctx.triggered_id}")

    # The triggered_id includes the pattern-matching payload with filename/type.
    triggered = ctx.triggered_id
    if not triggered or not isinstance(triggered, dict):
        print("[DEBUG] handle_file_click: no valid trigger, returning no_update")
        return no_update, no_update, no_update, no_update, no_update

    filename = triggered.get("filename")
    if not filename:
        print("[DEBUG] handle_file_click: no filename in trigger, returning no_update")
        return no_update, no_update, no_update, no_update, no_update

    # Avoid reloading the same file if it is already selected.
    if filename == current_file:
        print(f"[DEBUG] handle_file_click: same file {filename}, returning no_update")
        return no_update, no_update, no_update, no_update, no_update

    file_path = MAPS_DIR / filename

    # Load the selected map file and reset unsaved changes.
    action = ZoneAction(type="LOAD_MAP", payload={"file_path": file_path})
    transition = apply_zone_action(None, action)

    if not transition.changed or transition.zone_data is None:
        print(f"Error loading map file {filename}")
        return no_update, no_update, no_update, no_update, no_update

    zone_name = transition.effects.get("zone_name", filename)
    return filename, transition.zone_data, f"Zone: {zone_name}", False, None


# =============================================================================
# New Map Modal Callbacks
# =============================================================================


@callback(
    Output("new-map-modal", "is_open"),
    Output("zone-files-store", "data", allow_duplicate=True),
    Output("new-map-feedback", "children"),
    Output("new-zone-id", "value"),
    Output("new-zone-name", "value"),
    Output("new-zone-description", "value"),
    Input("new-map-btn", "n_clicks"),
    Input("new-map-cancel-btn", "n_clicks"),
    Input("new-map-create-btn", "n_clicks"),
    State("new-zone-id", "value"),
    State("new-zone-name", "value"),
    State("new-zone-description", "value"),
    prevent_initial_call=True,
)
def handle_new_map_modal(
    open_clicks: int,
    cancel_clicks: int,
    create_clicks: int,
    zone_id: str,
    zone_name: str,
    description: str,
) -> tuple:
    """Open, close, and create new maps from a single modal callback.

    This consolidates the previous open/close/create callbacks so only
    one callback owns the modal state. It routes behavior based on the
    triggering input and only runs creation logic for the Create button.
    """
    trigger = ctx.triggered_id

    # Open the modal when the "New Map" button is clicked.
    if trigger == "new-map-btn":
        return True, no_update, no_update, no_update, no_update, no_update

    # Close the modal when Cancel is clicked.
    if trigger == "new-map-cancel-btn":
        return False, no_update, no_update, no_update, no_update, no_update

    # Only the Create button should run creation logic.
    if trigger != "new-map-create-btn" or not create_clicks:
        return no_update, no_update, no_update, no_update, no_update, no_update

    # Normalize inputs to avoid whitespace and casing issues.
    zone_id = (zone_id or "").strip().lower()
    zone_name = (zone_name or "").strip()
    description = (description or "").strip()

    # Validate zone_id.
    if not zone_id:
        feedback = dbc.Alert("Zone ID is required.", color="danger", className="mb-0")
        return True, no_update, feedback, no_update, no_update, no_update

    if not re.match(r"^[a-z][a-z0-9_]*$", zone_id):
        feedback = dbc.Alert(
            "Zone ID must start with a letter and contain only "
            "lowercase letters, numbers, and underscores.",
            color="danger",
            className="mb-0",
        )
        return True, no_update, feedback, no_update, no_update, no_update

    # Validate zone_name.
    if not zone_name:
        feedback = dbc.Alert("Zone Name is required.", color="danger", className="mb-0")
        return True, no_update, feedback, no_update, no_update, no_update

    # Check if file already exists.
    file_path = MAPS_DIR / f"{zone_id}.map.json"
    if file_path.exists():
        feedback = dbc.Alert(
            f"A map with ID '{zone_id}' already exists.",
            color="warning",
            className="mb-0",
        )
        return True, no_update, feedback, no_update, no_update, no_update

    # Create and save the map file using zone_service.
    map_file = zone_service.create_new_map_file(
        zone_id=zone_id,
        name=zone_name,
        spawn_room_name="Spawn Room",
        description=description,
    )
    zone_service.save_map_file(map_file, file_path)

    # Refresh file list after creation.
    files = zone_service.list_map_files(MAPS_DIR)
    file_names = [f.name for f in files]

    # Close modal and clear form on success.
    return False, file_names, "", "", "", ""


# =============================================================================
# Save/Export/Status Callbacks
# =============================================================================


@callback(
    Output("save-map-btn", "disabled"),
    Output("export-zone-btn", "disabled"),
    Output("status-indicator", "children"),
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
        (save_disabled, export_disabled, status_text).
    """
    print(f"[DEBUG] update_save_status: has_unsaved={has_unsaved}, file={selected_file}")

    if not selected_file:
        print("[DEBUG] update_save_status: no file loaded")
        return True, True, "No file loaded"

    # Display full file name for clarity
    display_name = selected_file

    if has_unsaved:
        print("[DEBUG] update_save_status: unsaved changes - save=ENABLED")
        return False, True, f"Unsaved: {display_name}"

    print("[DEBUG] update_save_status: saved - export=ENABLED")
    saved_alert = dbc.Alert(
        f"Saved: {display_name}",
        color="success",
        className="mb-0 py-1",
        duration=3000,
        dismissable=True,
        fade=True,
    )
    return True, False, saved_alert


@callback(
    Output("has-unsaved-changes", "data", allow_duplicate=True),
    Output("room-feedback-save", "data"),
    Output("io-jobs", "data", allow_duplicate=True),
    Input("save-map-btn", "n_clicks"),
    State("current-zone-data", "data"),
    State("selected-file", "data"),
    State("io-jobs", "data"),
    prevent_initial_call=True,
)
def save_map_to_file(
    n_clicks: int,
    zone_data: dict | None,
    selected_file: str | None,
    io_jobs: dict | None,
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
    Returns
    -------
    tuple
        (unsaved_flag, feedback_alert).
        On success: False and success message.
        On error: no_update and error message.
    """
    if not n_clicks or not zone_data or not selected_file:
        return no_update, no_update, no_update

    file_path = MAPS_DIR / selected_file
    try:
        # Convert dict to MapFile and save
        from pipeworks_mud_mapper.models import MapFile

        map_file = MapFile.from_dict(zone_data)

        display_name = selected_file
        if selected_file.endswith(".map.json"):
            display_name = selected_file[:-9]

        job_id = submit_io_job(_save_map_job, map_file, file_path)
        jobs = list((io_jobs or {}).get("jobs", []))
        jobs.append(
            {
                "id": job_id,
                "type": "save",
                "display_name": display_name,
            }
        )

        feedback = dbc.Alert(
            f"Saving: {display_name}",
            color="info",
            className="mb-0 py-2",
            duration=3000,
        )
        return True, _room_feedback_payload(feedback), {"jobs": jobs}
    except Exception as e:
        feedback = dbc.Alert(
            f"Error saving: {e}",
            color="danger",
            className="mb-0 py-2",
        )
        return no_update, _room_feedback_payload(feedback), no_update


@callback(
    Output("room-feedback-export", "data"),
    Output("io-jobs", "data", allow_duplicate=True),
    Input("export-zone-btn", "n_clicks"),
    State("current-zone-data", "data"),
    State("selected-file", "data"),
    State("io-jobs", "data"),
    prevent_initial_call=True,
)
def export_zone_to_file(
    n_clicks: int,
    zone_data: dict | None,
    selected_file: str | None,
    io_jobs: dict | None,
) -> Any:
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
        return no_update, no_update

    # Derive export path from map file name
    map_path = MAPS_DIR / selected_file
    export_path = zone_service.get_suggested_export_path(map_path, zones_dir=ZONES_DIR)

    try:
        # Ensure zones directory exists
        ZONES_DIR.mkdir(parents=True, exist_ok=True)

        # Convert dict to MapFile and export
        from pipeworks_mud_mapper.models import MapFile

        map_file = MapFile.from_dict(zone_data)
        job_id = submit_io_job(_export_zone_job, map_file, export_path)

        jobs = list((io_jobs or {}).get("jobs", []))
        jobs.append(
            {
                "id": job_id,
                "type": "export",
                "display_name": export_path.stem,
            }
        )

        feedback = dbc.Alert(
            f"Export queued: {export_path.name} (coordinates stripped)",
            color="info",
            className="mb-0 py-2",
            duration=4000,
        )
        return _room_feedback_payload(feedback), {"jobs": jobs}
    except Exception as e:
        feedback = dbc.Alert(
            f"Error exporting: {e}",
            color="danger",
            className="mb-0 py-2",
        )
        return _room_feedback_payload(feedback), no_update


@callback(
    Output("io-jobs", "data"),
    Output("room-feedback-save", "data", allow_duplicate=True),
    Output("room-feedback-export", "data", allow_duplicate=True),
    Output("has-unsaved-changes", "data", allow_duplicate=True),
    Input("io-job-poll", "n_intervals"),
    State("io-jobs", "data"),
    prevent_initial_call="initial_duplicate",
)
def poll_io_jobs(n_intervals: int, io_jobs: dict | None) -> tuple:
    """Poll background I/O jobs and surface completion feedback."""
    jobs = list((io_jobs or {}).get("jobs", []))
    if not jobs:
        return no_update, no_update, no_update, no_update

    updated_jobs: list[dict[str, Any]] = []
    save_feedback = no_update
    export_feedback = no_update
    unsaved_update = no_update

    for job in jobs:
        job_id = job.get("id")
        if not job_id:
            continue

        status = get_io_job_status(job_id)
        if status is None or status.get("status") == "pending":
            updated_jobs.append(job)
            continue

        forget_io_job(job_id)
        job_type = job.get("type")

        if status.get("status") == "error":
            error_message = status.get("error", "Unknown error")
            feedback = dbc.Alert(
                f"I/O error: {error_message}",
                color="danger",
                className="mb-0 py-2",
            )
            if job_type == "save":
                save_feedback = _room_feedback_payload(feedback)
                unsaved_update = True
            elif job_type == "export":
                export_feedback = _room_feedback_payload(feedback)
            continue

        if job_type == "save":
            feedback = dbc.Alert(
                f"Saved: {job.get('display_name')}",
                color="success",
                className="mb-0 py-2",
                duration=3000,
            )
            save_feedback = _room_feedback_payload(feedback)
            unsaved_update = False
        elif job_type == "export":
            feedback = dbc.Alert(
                f"Exported: {job.get('display_name')}.json",
                color="success",
                className="mb-0 py-2",
                duration=3000,
            )
            export_feedback = _room_feedback_payload(feedback)

    if updated_jobs == jobs and save_feedback is no_update and export_feedback is no_update:
        return no_update, no_update, no_update, no_update

    return {"jobs": updated_jobs}, save_feedback, export_feedback, unsaved_update
