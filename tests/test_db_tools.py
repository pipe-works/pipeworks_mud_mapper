"""Tests for db_tools helpers."""

from __future__ import annotations

import json
from pathlib import Path

from pipeworks_mud_mapper.models import MapFile, MapRoom
from pipeworks_mud_mapper.services import db_tools, map_db_service


def test_backup_db_creates_copy(tmp_path: Path) -> None:
    """backup_db should create a new SQLite file."""
    db_path = tmp_path / "mapper.db"
    backup_path = tmp_path / "backup.db"

    map_file = MapFile(
        id="alpha",
        name="Alpha",
        spawn_room="spawn",
        rooms={"spawn": MapRoom(id="spawn", name="Spawn")},
    )
    map_db_service.save_map(map_file, db_path)

    db_tools.backup_db(db_path, backup_path)
    assert backup_path.exists()


def test_dump_db_sql(tmp_path: Path) -> None:
    """dump_db_sql should write SQL statements."""
    db_path = tmp_path / "mapper.db"
    map_file = MapFile(
        id="alpha",
        name="Alpha",
        spawn_room="spawn",
        rooms={"spawn": MapRoom(id="spawn", name="Spawn")},
    )
    map_db_service.save_map(map_file, db_path)

    sql_path = tmp_path / "dump.sql"
    with sql_path.open("w", encoding="utf-8") as handle:
        db_tools.dump_db_sql(db_path, handle)

    content = sql_path.read_text(encoding="utf-8")
    assert "CREATE TABLE" in content
    assert "maps" in content


def test_export_map_json(tmp_path: Path) -> None:
    """export_map_json should write map JSON files."""
    db_path = tmp_path / "mapper.db"
    output_dir = tmp_path / "exports"

    map_file = MapFile(
        id="alpha",
        name="Alpha",
        spawn_room="spawn",
        rooms={"spawn": MapRoom(id="spawn", name="Spawn")},
    )
    map_db_service.save_map(map_file, db_path)

    paths = db_tools.export_map_json(db_path, output_dir)
    assert len(paths) == 1
    assert paths[0].name == "alpha.map.json"

    payload = json.loads(paths[0].read_text(encoding="utf-8"))
    assert payload["id"] == "alpha"
    assert payload["rooms"]["spawn"]["coords"] == [0, 0, 0]


def test_export_zone_json(tmp_path: Path) -> None:
    """export_zone_json should write zone JSON files without coords."""
    db_path = tmp_path / "mapper.db"
    output_dir = tmp_path / "zones"

    map_file = MapFile(
        id="alpha",
        name="Alpha",
        spawn_room="spawn",
        rooms={"spawn": MapRoom(id="spawn", name="Spawn")},
    )
    map_db_service.save_map(map_file, db_path)

    paths = db_tools.export_zone_json(db_path, output_dir)
    assert len(paths) == 1
    assert paths[0].name == "alpha.json"

    payload = json.loads(paths[0].read_text(encoding="utf-8"))
    assert payload["id"] == "alpha"
    assert "coords" not in payload["rooms"]["spawn"]
    assert "exported_from" in payload["metadata"]
