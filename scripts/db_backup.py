#!/usr/bin/env python3
"""Create a timestamped backup of the mapper SQLite database."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from pipeworks_mud_mapper.services.app_config import get_path_settings
from pipeworks_mud_mapper.services.db_tools import backup_db


def _default_backup_path() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path("data/backups") / f"mapper_backup_{timestamp}.db"


def main() -> None:
    parser = argparse.ArgumentParser(description="Backup the mapper SQLite database.")
    parser.add_argument(
        "--db-path",
        type=Path,
        help="Path to the source database (defaults to config db_path).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output path for the backup file (defaults to data/backups).",
    )
    args = parser.parse_args()

    db_path = args.db_path or get_path_settings()["db_path"]
    output_path = args.output or _default_backup_path()

    backup_db(db_path, output_path)
    print(f"Backup created: {output_path}")


if __name__ == "__main__":
    main()
