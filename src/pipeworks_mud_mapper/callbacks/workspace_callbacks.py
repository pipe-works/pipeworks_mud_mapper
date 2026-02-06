"""Workspace panel callbacks.

These callbacks keep the Workspace card up to date with SQLite metadata.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import dash_bootstrap_components as dbc
from dash import Input, Output, callback, html

from pipeworks_mud_mapper.services import map_db_service
from pipeworks_mud_mapper.services.app_config import get_path_settings

PATHS = get_path_settings()
DB_PATH = PATHS["db_path"]


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


@callback(
    Output("workspace-db-summary", "children"),
    Output("workspace-db-table", "children"),
    Input("initial-load", "n_intervals"),
    Input("room-feedback-save", "data"),
    Input("room-feedback-export", "data"),
    Input("file-browser-refresh-btn", "n_clicks"),
    Input("workspace-db-refresh", "n_clicks"),
    prevent_initial_call=False,
)
def update_workspace_db(
    _: int,
    __: dict | None,
    ___: dict | None,
    ____: int | None,
    _____: int | None,
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
                html.Tbody(
                    [
                        html.Tr(
                            [
                                html.Td(row["map_id"]),
                                html.Td(row["room_count"]),
                                html.Td(row["map_revision"]),
                                html.Td(row["map_version"]),
                                html.Td(_format_timestamp(row["updated_at"])),
                            ]
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
