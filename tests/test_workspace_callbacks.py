"""Tests for workspace_callbacks module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import dash_bootstrap_components as dbc

from pipeworks_mud_mapper.callbacks import workspace_callbacks as wc


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
        summary, table = wc.update_workspace_db(1, None, None, None, None)

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
        summary, table = wc.update_workspace_db(1, None, None, None, None)

    assert "1 maps" in str(summary)
    assert isinstance(table, dbc.Table)
    assert "alpha" in str(table)
