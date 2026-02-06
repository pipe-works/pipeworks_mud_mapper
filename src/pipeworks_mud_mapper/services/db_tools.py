"""Utility helpers for backing up and exporting the mapper SQLite database."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import IO

from pipeworks_mud_mapper.services import map_db_service, zone_service


def backup_db(db_path: Path, output_path: Path) -> Path:
    """Create a consistent backup of the SQLite database.

    Uses the SQLite backup API so the copy is consistent even while the
    app has the database open.
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as source, sqlite3.connect(output_path) as target:
        source.backup(target)
    return output_path


def dump_db_sql(db_path: Path, output: IO[str]) -> None:
    """Write a SQL dump of the database to the given output stream."""
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    with sqlite3.connect(db_path) as conn:
        for line in conn.iterdump():
            output.write(f"{line}\n")


def export_map_json(db_path: Path, output_dir: Path, map_id: str | None = None) -> list[Path]:
    """Export authoring map JSON files from SQLite."""
    output_dir.mkdir(parents=True, exist_ok=True)
    map_ids = [map_id] if map_id else map_db_service.list_maps(db_path)
    exported: list[Path] = []

    for current_id in map_ids:
        map_file = map_db_service.load_map(current_id, db_path)
        data = map_file.to_dict_with_list_coords()
        path = output_dir / f"{current_id}.map.json"
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        exported.append(path)

    return exported


def export_zone_json(
    db_path: Path,
    output_dir: Path,
    map_id: str | None = None,
) -> list[Path]:
    """Export zone JSON files (game truth) from SQLite."""
    output_dir.mkdir(parents=True, exist_ok=True)
    map_ids = [map_id] if map_id else map_db_service.list_maps(db_path)
    exported: list[Path] = []

    for current_id in map_ids:
        map_file = map_db_service.load_map(current_id, db_path)
        export_map = map_file.model_copy(deep=True)
        updated_map = map_file.model_copy(deep=True)
        updated_map.bump_version()

        path = output_dir / f"{current_id}.json"
        zone_service.export_zone(export_map, path)
        map_db_service.save_map(updated_map, db_path)
        exported.append(path)

    return exported
