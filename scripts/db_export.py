#!/usr/bin/env python3
"""Export mapper data from SQLite as SQL or JSON."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pipeworks_mud_mapper.services.app_config import get_path_settings
from pipeworks_mud_mapper.services.db_tools import dump_db_sql, export_map_json, export_zone_json


def _default_map_export_dir() -> Path:
    return Path("data/exports/maps")


def _default_zone_export_dir() -> Path:
    return Path("data/zones")


def _write_sql(db_path: Path, output: Path | None) -> None:
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8") as handle:
            dump_db_sql(db_path, handle)
        print(f"SQL dump written: {output}")
    else:
        dump_db_sql(db_path, sys.stdout)


def _write_map_json(db_path: Path, output: Path | None, map_id: str | None) -> None:
    if map_id and output and output.suffix:
        output.parent.mkdir(parents=True, exist_ok=True)
        export_map_json(db_path, output.parent, map_id=map_id)
        renamed = output
        default_path = output.parent / f"{map_id}.map.json"
        if default_path != output:
            default_path.rename(output)
        print(f"Map JSON written: {renamed}")
        return

    export_dir = output or _default_map_export_dir()
    exported = export_map_json(db_path, export_dir, map_id=map_id)
    for path in exported:
        print(f"Map JSON written: {path}")


def _write_zone_json(db_path: Path, output: Path | None, map_id: str | None) -> None:
    export_dir = output or _default_zone_export_dir()
    exported = export_zone_json(db_path, export_dir, map_id=map_id)
    for path in exported:
        print(f"Zone JSON written: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export mapper data from SQLite.")
    parser.add_argument(
        "--db-path",
        type=Path,
        help="Path to the source database (defaults to config db_path).",
    )
    parser.add_argument(
        "--format",
        choices=["sql", "map-json", "zone-json"],
        default="map-json",
        help="Export format (default: map-json).",
    )
    parser.add_argument(
        "--map-id",
        help="Export a single map by ID (default: export all maps).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file or directory (depends on format).",
    )
    args = parser.parse_args()

    db_path = args.db_path or get_path_settings()["db_path"]

    if args.format == "sql":
        _write_sql(db_path, args.output)
        return
    if args.format == "map-json":
        _write_map_json(db_path, args.output, args.map_id)
        return
    if args.format == "zone-json":
        _write_zone_json(db_path, args.output, args.map_id)
        return

    raise SystemExit("Unknown export format.")


if __name__ == "__main__":
    main()
