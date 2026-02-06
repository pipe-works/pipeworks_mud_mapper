"""Tests for workspace_callbacks module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import dash_bootstrap_components as dbc
from dash import no_update

from pipeworks_mud_mapper.callbacks import workspace_callbacks as wc
from pipeworks_mud_mapper.models.room import Coords, MapRoom


def test_format_bytes() -> None:
    """_format_bytes should format common sizes."""
    assert wc._format_bytes(512) == "512 B"
    assert wc._format_bytes(1024) == "1.0 KB"
    assert wc._format_bytes(1536) == "1.5 KB"


def test_format_timestamp() -> None:
    """_format_timestamp should normalize ISO timestamps."""
    assert wc._format_timestamp(None) == "—"
    assert wc._format_timestamp("2026-02-06T12:34:56+00:00") == "2026-02-06 12:34:56"
    assert wc._format_timestamp("not-a-date") == "not-a-date"


def test_update_workspace_db_empty() -> None:
    """update_workspace_db should show empty state when no maps exist."""
    stats = {
        "path": Path("data/mapper.db"),
        "size_bytes": 0,
        "map_count": 0,
        "room_count": 0,
        "llm_generation_count": 0,
        "last_updated": None,
    }

    with (
        patch(
            "pipeworks_mud_mapper.callbacks.workspace_callbacks.map_db_service.get_db_stats"
        ) as mock_stats,
        patch(
            "pipeworks_mud_mapper.callbacks.workspace_callbacks.map_db_service.get_map_overview",
            return_value=[],
        ),
    ):
        mock_stats.return_value = stats
        summary, table = wc.update_workspace_db(1, None, None, None, None, None, None)

    assert "DB Path" in str(summary)
    assert "0 maps" in str(summary)
    assert "No maps yet" in str(table)


def test_update_workspace_db_with_overview() -> None:
    """update_workspace_db should render a table when maps exist."""
    stats = {
        "path": Path("data/mapper.db"),
        "size_bytes": 2048,
        "map_count": 1,
        "room_count": 3,
        "llm_generation_count": 2,
        "last_updated": "2026-02-06T12:34:56+00:00",
    }
    overview = [
        {
            "map_id": "alpha",
            "name": "Alpha",
            "map_version": "0",
            "map_revision": 2,
            "updated_at": "2026-02-06T12:34:56+00:00",
            "room_count": 3,
        }
    ]

    with (
        patch(
            "pipeworks_mud_mapper.callbacks.workspace_callbacks.map_db_service.get_db_stats"
        ) as mock_stats,
        patch(
            "pipeworks_mud_mapper.callbacks.workspace_callbacks.map_db_service.get_map_overview",
            return_value=overview,
        ),
    ):
        mock_stats.return_value = stats
        summary, table = wc.update_workspace_db(1, None, None, None, None, None, None)

    assert "1 maps" in str(summary)
    assert isinstance(table, dbc.Table)
    assert "alpha" in str(table)


def test_update_workspace_room_table_no_selection() -> None:
    """update_workspace_room_table should prompt when no map is selected."""
    result = wc.update_workspace_room_table(None, None, None, None, None)
    assert "Select a map" in str(result)


def test_update_workspace_room_table_map_missing() -> None:
    """update_workspace_room_table should handle missing maps gracefully."""
    with patch(
        "pipeworks_mud_mapper.callbacks.workspace_callbacks.map_db_service.load_map",
        side_effect=KeyError("missing"),
    ):
        result = wc.update_workspace_room_table("missing", None, None, None, None)

    assert "not found" in str(result)


def test_update_workspace_room_table_with_rooms() -> None:
    """update_workspace_room_table should render a room table."""
    room_a = MapRoom(
        id="a",
        name="Room A",
        coords=Coords(x=0, y=0, z=0),
        exits={"north": "b"},
    )
    room_b = MapRoom(
        id="b",
        name="Room B",
        coords=Coords(x=1, y=0, z=0),
        exits={},
    )
    map_stub = type("MapStub", (), {"rooms": {"a": room_a, "b": room_b}})()

    with patch(
        "pipeworks_mud_mapper.callbacks.workspace_callbacks.map_db_service.load_map",
        return_value=map_stub,
    ):
        result = wc.update_workspace_room_table("alpha", None, None, None, "b")

    assert isinstance(result, dbc.Table)
    assert "Room A" in str(result)
    assert "Room B" in str(result)


def test_update_workspace_room_table_empty_rooms() -> None:
    """update_workspace_room_table should handle maps with no rooms."""
    map_stub = type("MapStub", (), {"rooms": {}})()
    with patch(
        "pipeworks_mud_mapper.callbacks.workspace_callbacks.map_db_service.load_map",
        return_value=map_stub,
    ):
        result = wc.update_workspace_room_table("alpha", None, None, None, None)

    assert "No rooms" in str(result)


def test_handle_workspace_room_click_toggle() -> None:
    """handle_workspace_room_click should select and toggle rooms."""
    with patch("pipeworks_mud_mapper.callbacks.workspace_callbacks.ctx") as mock_ctx:
        mock_ctx.triggered_id = {"type": "workspace-room-row", "room_id": "room_1"}
        result = wc.handle_workspace_room_click([1], None)
    assert result == "room_1"

    with patch("pipeworks_mud_mapper.callbacks.workspace_callbacks.ctx") as mock_ctx:
        mock_ctx.triggered_id = {"type": "workspace-room-row", "room_id": "room_1"}
        result = wc.handle_workspace_room_click([1], "room_1")
    assert result is None


def test_handle_workspace_room_click_no_clicks() -> None:
    """handle_workspace_room_click should no-op when nothing clicked."""
    result = wc.handle_workspace_room_click([0, 0], None)
    assert result is no_update


def test_handle_workspace_room_click_invalid_trigger() -> None:
    """handle_workspace_room_click should ignore invalid trigger payloads."""
    with patch("pipeworks_mud_mapper.callbacks.workspace_callbacks.ctx") as mock_ctx:
        mock_ctx.triggered_id = "workspace-room-row"
        result = wc.handle_workspace_room_click([1], None)
    assert result is no_update

    with patch("pipeworks_mud_mapper.callbacks.workspace_callbacks.ctx") as mock_ctx:
        mock_ctx.triggered_id = {"type": "workspace-room-row"}
        result = wc.handle_workspace_room_click([1], None)
    assert result is no_update


def test_timestamped_name_has_prefix_and_suffix() -> None:
    """_timestamped_name should generate a name with the requested prefix/suffix."""
    name = wc._timestamped_name("mapper_backup", ".db")

    assert name.startswith("mapper_backup_")
    assert name.endswith(".db")


def test_summarize_export_variants() -> None:
    """_summarize_export should cover empty, single, and multi-file cases."""
    output_dir = Path("exports")

    # Empty export result should be explicit.
    assert "no maps" in wc._summarize_export("Map JSON export", [], output_dir)
    # Single file should print the file path.
    assert "exports/map.json" in wc._summarize_export(
        "Map JSON export",
        ["exports/map.json"],
        output_dir,
    )
    # Multiple files should include a count plus the target directory.
    assert "2 files" in wc._summarize_export(
        "Map JSON export",
        ["exports/a.json", "exports/b.json"],
        output_dir,
    )


def test_direction_helpers() -> None:
    """Direction helpers should format exits cleanly."""
    assert wc._short_direction("north") == "N"
    assert wc._short_direction("Weird") == "W"
    assert wc._short_direction("") == "?"
    assert wc._format_direction_list([]) == "—"
    assert wc._format_direction_list(["D", "N"]) == "D, N"


def test_queue_workspace_db_tool_no_trigger() -> None:
    """queue_workspace_db_tool should no-op when no trigger is present."""
    with patch("pipeworks_mud_mapper.callbacks.workspace_callbacks.ctx") as mock_ctx:
        mock_ctx.triggered_id = None
        jobs, feedback = wc.queue_workspace_db_tool(None, None, None, None, None, None)

    assert jobs is no_update
    assert feedback is no_update


def test_queue_workspace_db_tool_backup() -> None:
    """queue_workspace_db_tool should enqueue backup jobs with feedback."""
    with (
        patch("pipeworks_mud_mapper.callbacks.workspace_callbacks.ctx") as mock_ctx,
        patch(
            "pipeworks_mud_mapper.callbacks.workspace_callbacks._timestamped_name",
            return_value="mapper_backup_test.db",
        ),
        patch("pipeworks_mud_mapper.callbacks.workspace_callbacks.submit_io_job") as mock_submit,
    ):
        mock_ctx.triggered_id = "workspace-db-backup-btn"
        mock_submit.return_value = "job-1"
        jobs, feedback = wc.queue_workspace_db_tool(1, None, None, None, {"jobs": []}, None)

    assert jobs["jobs"][0]["id"] == "job-1"
    assert jobs["jobs"][0]["type"] == "backup"
    assert "mapper_backup_test.db" in jobs["jobs"][0]["path"]
    assert isinstance(feedback, dbc.Alert)
    assert "Backup queued" in str(feedback)


def test_queue_workspace_db_tool_export_map() -> None:
    """queue_workspace_db_tool should enqueue map JSON export jobs."""
    with (
        patch("pipeworks_mud_mapper.callbacks.workspace_callbacks.ctx") as mock_ctx,
        patch("pipeworks_mud_mapper.callbacks.workspace_callbacks.submit_io_job") as mock_submit,
    ):
        mock_ctx.triggered_id = "workspace-db-export-map-btn"
        mock_submit.return_value = "job-2"
        jobs, feedback = wc.queue_workspace_db_tool(1, None, None, None, {"jobs": []}, "alpha")

    job = jobs["jobs"][0]
    assert job["id"] == "job-2"
    assert job["type"] == "export-map"
    assert job["map_id"] == "alpha"
    assert Path(job["output_dir"]).name == "maps"
    assert isinstance(feedback, dbc.Alert)
    assert "Export queued" in str(feedback)


def test_queue_workspace_db_tool_export_zone() -> None:
    """queue_workspace_db_tool should enqueue zone JSON export jobs."""
    with (
        patch("pipeworks_mud_mapper.callbacks.workspace_callbacks.ctx") as mock_ctx,
        patch("pipeworks_mud_mapper.callbacks.workspace_callbacks.submit_io_job") as mock_submit,
    ):
        mock_ctx.triggered_id = "workspace-db-export-zone-btn"
        mock_submit.return_value = "job-3"
        jobs, feedback = wc.queue_workspace_db_tool(1, None, None, None, {"jobs": []}, None)

    job = jobs["jobs"][0]
    assert job["id"] == "job-3"
    assert job["type"] == "export-zone"
    assert job["map_id"] is None
    assert Path(job["output_dir"]).name == "zones"
    assert isinstance(feedback, dbc.Alert)
    assert "Export queued" in str(feedback)


def test_queue_workspace_db_tool_export_sql() -> None:
    """queue_workspace_db_tool should enqueue SQL dump jobs."""
    with (
        patch("pipeworks_mud_mapper.callbacks.workspace_callbacks.ctx") as mock_ctx,
        patch(
            "pipeworks_mud_mapper.callbacks.workspace_callbacks._timestamped_name",
            return_value="mapper_dump_test.sql",
        ),
        patch("pipeworks_mud_mapper.callbacks.workspace_callbacks.submit_io_job") as mock_submit,
    ):
        mock_ctx.triggered_id = "workspace-db-export-sql-btn"
        mock_submit.return_value = "job-4"
        jobs, feedback = wc.queue_workspace_db_tool(1, None, None, None, {"jobs": []}, None)

    job = jobs["jobs"][0]
    assert job["id"] == "job-4"
    assert job["type"] == "export-sql"
    assert "mapper_dump_test.sql" in job["path"]
    assert isinstance(feedback, dbc.Alert)
    assert "SQL dump queued" in str(feedback)


def test_poll_workspace_jobs_pending_no_update() -> None:
    """poll_workspace_jobs should no-op when jobs are still pending."""
    with patch(
        "pipeworks_mud_mapper.callbacks.workspace_callbacks.get_io_job_status",
        return_value={"status": "pending"},
    ):
        jobs, feedback = wc.poll_workspace_jobs(
            1, {"jobs": [{"id": "job-1", "type": "backup", "path": "backup.db"}]}
        )

    assert jobs is no_update
    assert feedback is no_update


def test_poll_workspace_jobs_backup_success() -> None:
    """poll_workspace_jobs should surface success for completed backup jobs."""
    with (
        patch(
            "pipeworks_mud_mapper.callbacks.workspace_callbacks.get_io_job_status",
            return_value={"status": "complete", "result": "backup.db"},
        ),
        patch("pipeworks_mud_mapper.callbacks.workspace_callbacks.forget_io_job") as mock_forget,
    ):
        jobs, feedback = wc.poll_workspace_jobs(
            1, {"jobs": [{"id": "job-1", "type": "backup", "path": "backup.db"}]}
        )

    mock_forget.assert_called_once_with("job-1")
    assert jobs == {"jobs": []}
    assert isinstance(feedback, dbc.Alert)
    assert "Backup created" in str(feedback)


def test_poll_workspace_jobs_export_map_multiple() -> None:
    """poll_workspace_jobs should summarize multi-file exports."""
    with (
        patch(
            "pipeworks_mud_mapper.callbacks.workspace_callbacks.get_io_job_status",
            return_value={"status": "complete", "result": ["a.json", "b.json"]},
        ),
        patch("pipeworks_mud_mapper.callbacks.workspace_callbacks.forget_io_job"),
    ):
        jobs, feedback = wc.poll_workspace_jobs(
            1,
            {
                "jobs": [
                    {
                        "id": "job-2",
                        "type": "export-map",
                        "output_dir": "exports/maps",
                    }
                ]
            },
        )

    assert jobs == {"jobs": []}
    assert isinstance(feedback, dbc.Alert)
    assert "2 files" in str(feedback)


def test_poll_workspace_jobs_error() -> None:
    """poll_workspace_jobs should surface job failures."""
    with (
        patch(
            "pipeworks_mud_mapper.callbacks.workspace_callbacks.get_io_job_status",
            return_value={"status": "error", "error": "boom"},
        ),
        patch("pipeworks_mud_mapper.callbacks.workspace_callbacks.forget_io_job"),
    ):
        jobs, feedback = wc.poll_workspace_jobs(
            1, {"jobs": [{"id": "job-3", "type": "export-sql", "path": "dump.sql"}]}
        )

    assert jobs == {"jobs": []}
    assert isinstance(feedback, dbc.Alert)
    assert "Workspace job failed" in str(feedback)
