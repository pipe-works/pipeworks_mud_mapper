"""SQLite storage service for mapper authoring data.

This module replaces map JSON files as the authoring source of truth.
Maps are stored in a single shared SQLite database, while zone exports
remain JSON files for the game server.

Design goals:
- Keep SQLite as the canonical authoring store.
- Preserve existing MapFile/MapRoom models in memory.
- Use clear, explicit SQL (no ORM) to keep dependencies light.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pipeworks_mud_mapper.models import MapFile
from pipeworks_mud_mapper.models.metadata import MapMetadata
from pipeworks_mud_mapper.services.app_config import get_path_settings

# ---------------------------------------------------------------------------
# Database connection helpers
# ---------------------------------------------------------------------------


def _resolve_db_path(db_path: Path | None) -> Path:
    """Return the configured DB path unless an override is provided."""
    if db_path is not None:
        return db_path
    return get_path_settings()["db_path"]


@contextmanager
def _connect(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    """Open a SQLite connection with schema ensured.

    A new connection is created per operation to keep thread usage safe
    (SQLite connections are not thread-safe by default).
    """
    resolved = _resolve_db_path(db_path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(resolved)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        _ensure_schema(conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Create tables if they do not exist."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS maps (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            spawn_room TEXT NOT NULL,
            schema_version TEXT NOT NULL,
            map_version TEXT NOT NULL,
            map_revision INTEGER NOT NULL DEFAULT 0,
            items_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS rooms (
            map_id TEXT NOT NULL,
            id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            x INTEGER NOT NULL,
            y INTEGER NOT NULL,
            z INTEGER NOT NULL,
            exits_json TEXT NOT NULL DEFAULT '{}',
            items_json TEXT NOT NULL DEFAULT '[]',
            llm_generation_json TEXT,
            description_validation_json TEXT,
            PRIMARY KEY (map_id, id),
            FOREIGN KEY (map_id) REFERENCES maps(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_rooms_map_id ON rooms(map_id);
        """
    )


# ---------------------------------------------------------------------------
# CRUD operations
# ---------------------------------------------------------------------------


def list_maps(db_path: Path | None = None) -> list[str]:
    """Return map IDs stored in the database."""
    with _connect(db_path) as conn:
        rows = conn.execute("SELECT id FROM maps ORDER BY id").fetchall()
    return [row["id"] for row in rows]


def map_exists(map_id: str, db_path: Path | None = None) -> bool:
    """Return True if the map ID exists in the database."""
    with _connect(db_path) as conn:
        row = conn.execute("SELECT 1 FROM maps WHERE id = ?", (map_id,)).fetchone()
    return row is not None


def load_map(map_id: str, db_path: Path | None = None) -> MapFile:
    """Load a map from SQLite into a MapFile model."""
    with _connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT id, name, description, spawn_room, schema_version, map_version,
                   map_revision, items_json
              FROM maps
             WHERE id = ?
            """,
            (map_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"Map not found: {map_id}")

        rooms_rows = conn.execute(
            """
            SELECT id, name, description, x, y, z, exits_json, items_json,
                   llm_generation_json, description_validation_json
              FROM rooms
             WHERE map_id = ?
             ORDER BY id
            """,
            (map_id,),
        ).fetchall()

    metadata = MapMetadata(
        schema_version=row["schema_version"],
        map_version=row["map_version"],
        map_revision=row["map_revision"],
    )

    rooms: dict[str, dict[str, Any]] = {}
    for room in rooms_rows:
        rooms[room["id"]] = {
            "id": room["id"],
            "name": room["name"],
            "description": room["description"],
            "coords": [room["x"], room["y"], room["z"]],
            "exits": json.loads(room["exits_json"] or "{}"),
            "items": json.loads(room["items_json"] or "[]"),
            "llm_generation": (
                json.loads(room["llm_generation_json"]) if room["llm_generation_json"] else None
            ),
            "description_validation": (
                json.loads(room["description_validation_json"])
                if room["description_validation_json"]
                else None
            ),
        }

    data = {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "spawn_room": row["spawn_room"],
        "items": json.loads(row["items_json"] or "{}"),
        "metadata": metadata.model_dump(),
        "rooms": rooms,
    }
    return MapFile.from_dict(data)


def save_map(map_file: MapFile, db_path: Path | None = None) -> None:
    """Persist a MapFile to SQLite (upsert + full room refresh)."""
    now = datetime.now(UTC).isoformat()
    payload = map_file.to_dict_with_list_coords()

    with _connect(db_path) as conn:
        # Upsert map row.
        conn.execute(
            """
            INSERT INTO maps (
                id, name, description, spawn_room, schema_version,
                map_version, map_revision, items_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                description = excluded.description,
                spawn_room = excluded.spawn_room,
                schema_version = excluded.schema_version,
                map_version = excluded.map_version,
                map_revision = excluded.map_revision,
                items_json = excluded.items_json,
                updated_at = excluded.updated_at,
                created_at = maps.created_at
            """,
            (
                payload["id"],
                payload["name"],
                payload.get("description", ""),
                payload["spawn_room"],
                payload["metadata"]["schema_version"],
                payload["metadata"]["map_version"],
                payload["metadata"]["map_revision"],
                json.dumps(payload.get("items", {})),
                now,
                now,
            ),
        )

        # Replace rooms for this map. Simpler and safer than diffing.
        conn.execute("DELETE FROM rooms WHERE map_id = ?", (payload["id"],))

        room_rows = []
        for room in payload.get("rooms", {}).values():
            coords = room.get("coords") or [0, 0, 0]
            room_rows.append(
                (
                    payload["id"],
                    room["id"],
                    room["name"],
                    room.get("description", ""),
                    coords[0],
                    coords[1],
                    coords[2],
                    json.dumps(room.get("exits", {})),
                    json.dumps(room.get("items", [])),
                    (
                        json.dumps(room.get("llm_generation"))
                        if room.get("llm_generation") is not None
                        else None
                    ),
                    (
                        json.dumps(room.get("description_validation"))
                        if room.get("description_validation") is not None
                        else None
                    ),
                )
            )

        if room_rows:
            conn.executemany(
                """
                INSERT INTO rooms (
                    map_id, id, name, description, x, y, z,
                    exits_json, items_json, llm_generation_json,
                    description_validation_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                room_rows,
            )


def delete_map(map_id: str, db_path: Path | None = None) -> None:
    """Delete a map and its rooms from SQLite."""
    with _connect(db_path) as conn:
        conn.execute("DELETE FROM maps WHERE id = ?", (map_id,))
