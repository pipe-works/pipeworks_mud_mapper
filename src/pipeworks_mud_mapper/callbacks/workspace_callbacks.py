"""Workspace panel callbacks.

These callbacks keep the Workspace card up to date with SQLite metadata.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, cast

import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, callback, ctx, html, no_update

from pipeworks_mud_mapper.models.room import DIRECTION_SHORT, Direction
from pipeworks_mud_mapper.services import db_tools, map_db_service
from pipeworks_mud_mapper.services.app_config import get_path_settings
from pipeworks_mud_mapper.services.io_queue import (
    forget_io_job,
    get_io_job_status,
    submit_io_job,
)

PATHS = get_path_settings()
DB_PATH = PATHS["db_path"]

# Workspace export locations live alongside the DB by default. This keeps all
# mapper-local artifacts in one place, even if db_path is customized. The
# subdirectories are split by artifact type so backups, exports, and SQL dumps
# stay discoverable even as the workspace grows.
DATA_DIR = DB_PATH.parent
BACKUP_DIR = DATA_DIR / "backups"
EXPORT_DIR = DATA_DIR / "exports"
EXPORT_MAP_DIR = EXPORT_DIR / "maps"
EXPORT_ZONE_DIR = EXPORT_DIR / "zones"
EXPORT_SQL_DIR = EXPORT_DIR / "sql"


def _format_bytes(size: int) -> str:
    """Format byte counts into human-readable strings."""
    if size < 1024:
        return f"{size} B"
    size_float = float(size)
    for unit in ["KB", "MB", "GB", "TB"]:
        size_float /= 1024
        if size_float < 1024:
            return f"{size_float:.1f} {unit}"
    return f"{size_float:.1f} PB"


def _format_timestamp(value: str | None) -> str:
    """Normalize timestamps for display."""
    if not value:
        return "—"
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return value


def _summary_row(label: str, value: Any) -> html.Div:
    """Build a consistent label/value row."""
    return html.Div(
        [
            html.Span(label, className="text-muted me-2"),
            html.Span(value),
        ],
        className="mb-1",
    )


# NOTE: The I/O queue executes callables in a background thread. Keep these
# helpers module-level and return simple, serializable values for UI feedback.


def _backup_db_job(db_path: Path, output_path: Path) -> str:
    """Background job to create a DB backup.

    Returns the final output path so the UI can confirm where the backup lives.
    """
    result = db_tools.backup_db(db_path, output_path)
    return str(result)


def _export_map_json_job(db_path: Path, output_dir: Path, map_id: str | None) -> list[str]:
    """Background job to export authoring JSON.

    Returns the list of exported file paths to summarize in the Workspace UI.
    """
    exported = db_tools.export_map_json(db_path, output_dir, map_id=map_id)
    return [str(path) for path in exported]


def _export_zone_json_job(db_path: Path, output_dir: Path, map_id: str | None) -> list[str]:
    """Background job to export zone JSON.

    Zone JSON is the game-ready export, so we report back with exported files.
    """
    exported = db_tools.export_zone_json(db_path, output_dir, map_id=map_id)
    return [str(path) for path in exported]


def _dump_sql_job(db_path: Path, output_path: Path) -> str:
    """Background job to dump SQL to a file.

    A SQL dump is useful for migrations/debugging, so we write directly to disk
    and return the final file path for confirmation.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        db_tools.dump_db_sql(db_path, handle)
    return str(output_path)


def _timestamped_name(prefix: str, suffix: str) -> str:
    """Generate a timestamped filename."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}{suffix}"


def _summarize_export(kind: str, result: list[str], output_dir: Path) -> str:
    """Format export results for display."""
    if not result:
        return f"{kind}: no maps to export."
    if len(result) == 1:
        return f"{kind}: {result[0]}"
    return f"{kind}: {len(result)} files in {output_dir}"


def _short_direction(direction: str) -> str:
    """Convert a full direction label into its short UI form."""
    if not direction:
        return "?"
    key = str(direction).lower()
    if key in DIRECTION_SHORT:
        return DIRECTION_SHORT[cast(Direction, key)]
    return key[:1].upper()


def _format_direction_list(directions: list[str]) -> str:
    """Format a direction list for the room table."""
    if not directions:
        return "—"
    return ", ".join(sorted(directions))


def _build_entrance_map(rooms: dict[str, Any]) -> dict[str, list[str]]:
    """Build an entrance lookup for each room based on other rooms' exits."""
    entrances: dict[str, list[str]] = {room_id: [] for room_id in rooms}

    # Walk every exit edge and record the direction on the target room.
    for room in rooms.values():
        for direction, target in room.exits.items():
            if target in entrances:
                entrances[target].append(_short_direction(direction))

    for room_id, directions in entrances.items():
        directions.sort()
        entrances[room_id] = directions

    return entrances


@callback(
    Output("workspace-db-summary", "children"),
    Output("workspace-db-table", "children"),
    Input("initial-load", "n_intervals"),
    Input("room-feedback-save", "data"),
    Input("room-feedback-export", "data"),
    Input("new-map-create-btn", "n_clicks"),
    Input("file-delete-confirm-btn", "n_clicks"),
    Input("workspace-db-refresh", "n_clicks"),
    Input("selected-file", "data"),
    prevent_initial_call=False,
)
def update_workspace_db(
    _: int,
    __: dict | None,
    ___: dict | None,
    ____: int | None,
    _____: int | None,
    ______: int | None,
    selected_file: str | None,
) -> tuple[Any, Any]:
    """Refresh SQLite DB summary and map overview table."""
    stats = map_db_service.get_db_stats(DB_PATH)
    overview = map_db_service.get_map_overview(DB_PATH)

    db_path = stats["path"]
    summary = html.Div(
        [
            _summary_row("DB Path:", html.Code(str(db_path))),
            _summary_row("DB Size:", _format_bytes(stats["size_bytes"])),
            html.Div(
                [
                    dbc.Badge(f"{stats['map_count']} maps", color="primary", className="me-2"),
                    dbc.Badge(
                        f"{stats['room_count']} rooms",
                        color="info",
                        className="me-2",
                    ),
                    dbc.Badge(
                        f"{stats['llm_generation_count']} LLM",
                        color="secondary",
                    ),
                ],
                className="mb-1",
            ),
            _summary_row("Last Updated:", _format_timestamp(stats["last_updated"])),
        ],
        className="mb-2",
    )

    if not overview:
        table = html.Div(
            "No maps yet. Create one to populate the database.",
            className="text-muted small",
        )
    else:
        table = dbc.Table(
            [
                html.Thead(
                    html.Tr(
                        [
                            html.Th("Map"),
                            html.Th("Rooms"),
                            html.Th("Revision"),
                            html.Th("Version"),
                            html.Th("Updated"),
                        ]
                    )
                ),
                # Rows are clickable to load maps; the active map is highlighted.
                html.Tbody(
                    [
                        html.Tr(
                            [
                                html.Td(row["map_id"]),
                                html.Td(row["room_count"]),
                                html.Td(row["map_revision"]),
                                html.Td(row["map_version"]),
                                html.Td(_format_timestamp(row["updated_at"])),
                            ],
                            id={"type": "workspace-map-row", "map_id": row["map_id"]},
                            className="table-primary" if row["map_id"] == selected_file else None,
                            style={"cursor": "pointer"},
                            n_clicks=0,
                            title="Click to load map",
                        )
                        for row in overview
                    ]
                ),
            ],
            bordered=True,
            hover=True,
            size="sm",
            className="small mb-0",
        )

    return summary, table


@callback(
    Output("workspace-room-table", "children"),
    Input("selected-file", "data"),
    Input("room-feedback-save", "data"),
    Input("new-map-create-btn", "n_clicks"),
    Input("file-delete-confirm-btn", "n_clicks"),
    Input("selected-room", "data"),
    prevent_initial_call=False,
)
def update_workspace_room_table(
    selected_file: str | None,
    _: dict | None,
    __: int | None,
    ___: int | None,
    selected_room: str | None,
) -> Any:
    """Render a table of rooms for the selected map in the Workspace tab."""
    if not selected_file:
        return html.Div(
            "Select a map to inspect its rooms.",
            className="text-muted small",
        )

    try:
        map_file = map_db_service.load_map(selected_file, db_path=DB_PATH)
    except KeyError:
        return html.Div(
            "Selected map not found in the database.",
            className="text-muted small",
        )

    rooms = map_file.rooms
    if not rooms:
        return html.Div(
            "No rooms saved for this map yet.",
            className="text-muted small",
        )

    # Build entrance directions so each room shows both outgoing and incoming links.
    entrances = _build_entrance_map(rooms)
    rows = []

    for room_id in sorted(rooms):
        room = rooms[room_id]
        coords = room.coords
        exits = _format_direction_list(
            [_short_direction(direction) for direction in room.exits.keys()]
        )
        incoming = _format_direction_list(entrances.get(room_id, []))

        rows.append(
            html.Tr(
                [
                    html.Td(room_id),
                    html.Td(room.name),
                    html.Td(coords.x),
                    html.Td(coords.y),
                    html.Td(coords.z),
                    html.Td(exits),
                    html.Td(incoming),
                ],
                id={"type": "workspace-room-row", "room_id": room_id},
                className="table-primary" if room_id == selected_room else None,
                style={"cursor": "pointer"},
                n_clicks=0,
                title="Click to select room",
            )
        )

    return dbc.Table(
        [
            html.Thead(
                html.Tr(
                    [
                        html.Th("Room"),
                        html.Th("Name"),
                        html.Th("X"),
                        html.Th("Y"),
                        html.Th("Z"),
                        html.Th("Exits"),
                        html.Th("Entrances"),
                    ]
                )
            ),
            html.Tbody(rows),
        ],
        bordered=True,
        hover=True,
        size="sm",
        className="small mb-0",
    )


@callback(
    Output("selected-room", "data", allow_duplicate=True),
    Input({"type": "workspace-room-row", "room_id": ALL}, "n_clicks"),
    State("selected-room", "data"),
    prevent_initial_call=True,
)
def handle_workspace_room_click(
    room_clicks: list[int],
    current_room: str | None,
) -> Any:
    """Select a room when a Workspace table row is clicked."""
    if not any(room_clicks):
        return no_update

    trigger = ctx.triggered_id
    if not trigger or not isinstance(trigger, dict):
        return no_update

    room_id = trigger.get("room_id")
    if not room_id:
        return no_update

    if room_id == current_room:
        return None

    return room_id


@callback(
    Output("workspace-jobs", "data", allow_duplicate=True),
    Output("workspace-db-feedback", "children", allow_duplicate=True),
    Input("workspace-db-backup-btn", "n_clicks"),
    Input("workspace-db-export-map-btn", "n_clicks"),
    Input("workspace-db-export-zone-btn", "n_clicks"),
    Input("workspace-db-export-sql-btn", "n_clicks"),
    State("workspace-jobs", "data"),
    State("selected-file", "data"),
    prevent_initial_call=True,
)
def queue_workspace_db_tool(
    backup_clicks: int | None,
    export_map_clicks: int | None,
    export_zone_clicks: int | None,
    export_sql_clicks: int | None,
    workspace_jobs: dict | None,
    selected_map: str | None,
) -> tuple[Any, Any]:
    """Queue a workspace DB tool job and surface immediate feedback.

    Each button click spawns an asynchronous job so the UI stays responsive
    while backups/exports run. A short alert confirms the action immediately.
    """
    trigger = ctx.triggered_id
    if not trigger:
        return no_update, no_update

    jobs = list((workspace_jobs or {}).get("jobs", []))
    feedback = None

    if trigger == "workspace-db-backup-btn":
        # Backup jobs write a timestamped copy under data/backups/.
        output_path = BACKUP_DIR / _timestamped_name("mapper_backup", ".db")
        job_id = submit_io_job(_backup_db_job, DB_PATH, output_path)
        jobs.append({"id": job_id, "type": "backup", "path": str(output_path)})
        feedback = dbc.Alert(
            f"Backup queued: {output_path.name}",
            color="info",
            className="mb-0 py-1",
            duration=3000,
        )
    elif trigger == "workspace-db-export-map-btn":
        # Map JSON exports represent the authoring format.
        job_id = submit_io_job(_export_map_json_job, DB_PATH, EXPORT_MAP_DIR, selected_map)
        jobs.append(
            {
                "id": job_id,
                "type": "export-map",
                "map_id": selected_map,
                "output_dir": str(EXPORT_MAP_DIR),
            }
        )
        feedback = dbc.Alert(
            "Export queued: map JSON",
            color="info",
            className="mb-0 py-1",
            duration=3000,
        )
    elif trigger == "workspace-db-export-zone-btn":
        # Zone JSON exports represent the game-ready format.
        job_id = submit_io_job(_export_zone_json_job, DB_PATH, EXPORT_ZONE_DIR, selected_map)
        jobs.append(
            {
                "id": job_id,
                "type": "export-zone",
                "map_id": selected_map,
                "output_dir": str(EXPORT_ZONE_DIR),
            }
        )
        feedback = dbc.Alert(
            "Export queued: zone JSON",
            color="info",
            className="mb-0 py-1",
            duration=3000,
        )
    elif trigger == "workspace-db-export-sql-btn":
        # SQL dumps capture schema + data for debugging/migrations.
        output_path = EXPORT_SQL_DIR / _timestamped_name("mapper_dump", ".sql")
        job_id = submit_io_job(_dump_sql_job, DB_PATH, output_path)
        jobs.append({"id": job_id, "type": "export-sql", "path": str(output_path)})
        feedback = dbc.Alert(
            f"SQL dump queued: {output_path.name}",
            color="info",
            className="mb-0 py-1",
            duration=3000,
        )
    else:
        return no_update, no_update

    return {"jobs": jobs}, feedback


@callback(
    Output("workspace-jobs", "data", allow_duplicate=True),
    Output("workspace-db-feedback", "children", allow_duplicate=True),
    Input("io-job-poll", "n_intervals"),
    State("workspace-jobs", "data"),
    prevent_initial_call="initial_duplicate",
)
def poll_workspace_jobs(n_intervals: int, workspace_jobs: dict | None) -> tuple[Any, Any]:
    """Poll background workspace jobs and surface completion feedback.

    Completed jobs are removed from the store, pending jobs are kept, and the
    newest alert is shown in the Workspace tab.
    """
    jobs = list((workspace_jobs or {}).get("jobs", []))
    if not jobs:
        return no_update, no_update

    updated_jobs: list[dict[str, Any]] = []
    feedback = no_update

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
            feedback = dbc.Alert(
                f"Workspace job failed: {status.get('error', 'Unknown error')}",
                color="danger",
                className="mb-0 py-1",
            )
            continue

        result = status.get("result")
        if job_type == "backup":
            feedback = dbc.Alert(
                f"Backup created: {result}",
                color="success",
                className="mb-0 py-1",
                duration=4000,
            )
        elif job_type == "export-map":
            feedback = dbc.Alert(
                _summarize_export("Map JSON export", result or [], Path(job["output_dir"])),
                color="success",
                className="mb-0 py-1",
                duration=4000,
            )
        elif job_type == "export-zone":
            feedback = dbc.Alert(
                _summarize_export("Zone JSON export", result or [], Path(job["output_dir"])),
                color="success",
                className="mb-0 py-1",
                duration=4000,
            )
        elif job_type == "export-sql":
            feedback = dbc.Alert(
                f"SQL dump created: {result}",
                color="success",
                className="mb-0 py-1",
                duration=4000,
            )

    if updated_jobs == jobs and feedback is no_update:
        return no_update, no_update

    return {"jobs": updated_jobs}, feedback
