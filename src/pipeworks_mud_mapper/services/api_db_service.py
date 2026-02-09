"""SQLite storage for remote API services and commands.

This module manages a separate SQLite database used to store remote API
service definitions and reusable commands that can be executed from the UI.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pipeworks_mud_mapper.services.app_config import get_path_settings

# ---------------------------------------------------------------------------
# Database connection helpers
# ---------------------------------------------------------------------------


def _resolve_db_path(db_path: Path | None) -> Path:
    """Return the configured API DB path unless an override is provided."""
    if db_path is not None:
        return db_path
    return get_path_settings()["api_db_path"]


@contextmanager
def _connect(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    """Open a SQLite connection with schema ensured."""
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
    # JSON fields are stored as TEXT for portability and easy inspection.
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS api_services (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            base_url TEXT NOT NULL,
            auth_type TEXT NOT NULL DEFAULT 'none',
            auth_secret TEXT,
            default_headers_json TEXT NOT NULL DEFAULT '{}',
            enabled INTEGER NOT NULL DEFAULT 1,
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS api_commands (
            id TEXT PRIMARY KEY,
            service_id TEXT NOT NULL,
            name TEXT NOT NULL,
            method TEXT NOT NULL,
            path TEXT NOT NULL,
            query_json TEXT NOT NULL DEFAULT '{}',
            headers_json TEXT NOT NULL DEFAULT '{}',
            body_json TEXT,
            timeout_seconds INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (service_id) REFERENCES api_services(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_api_commands_service_id
            ON api_commands(service_id);
        """)


# ---------------------------------------------------------------------------
# Row helpers
# ---------------------------------------------------------------------------


def _parse_json(value: str | None, fallback: Any) -> Any:
    """Parse JSON text columns with a safe fallback."""
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _service_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "base_url": row["base_url"],
        "auth_type": row["auth_type"],
        "auth_secret": row["auth_secret"],
        "default_headers": _parse_json(row["default_headers_json"], {}),
        "enabled": bool(row["enabled"]),
        "notes": row["notes"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _command_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "service_id": row["service_id"],
        "name": row["name"],
        "method": row["method"],
        "path": row["path"],
        "query": _parse_json(row["query_json"], {}),
        "headers": _parse_json(row["headers_json"], {}),
        "body": _parse_json(row["body_json"], None),
        "timeout_seconds": row["timeout_seconds"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


# ---------------------------------------------------------------------------
# Service CRUD
# ---------------------------------------------------------------------------


def list_services(
    db_path: Path | None = None,
    *,
    include_disabled: bool = True,
) -> list[dict[str, Any]]:
    """Return API services."""
    # Keep ordering stable for dropdown display.
    query = "SELECT * FROM api_services"
    params: tuple[Any, ...] = ()
    if not include_disabled:
        query += " WHERE enabled = 1"
    query += " ORDER BY name"
    with _connect(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    return [_service_row_to_dict(row) for row in rows]


def get_service(service_id: str, db_path: Path | None = None) -> dict[str, Any]:
    """Return a single API service."""
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM api_services WHERE id = ?",
            (service_id,),
        ).fetchone()
    if row is None:
        raise KeyError(f"API service not found: {service_id}")
    return _service_row_to_dict(row)


def create_service(
    name: str,
    base_url: str,
    *,
    auth_type: str = "none",
    auth_secret: str | None = None,
    default_headers: dict[str, Any] | None = None,
    enabled: bool = True,
    notes: str | None = None,
    db_path: Path | None = None,
) -> str:
    """Create a new API service and return its ID."""
    # Use UUIDs to avoid coordination across clients and manual id entry.
    service_id = str(uuid.uuid4())
    now = _now_iso()
    headers_json = json.dumps(default_headers or {})
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO api_services (
                id, name, base_url, auth_type, auth_secret, default_headers_json,
                enabled, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                service_id,
                name,
                base_url,
                auth_type,
                auth_secret,
                headers_json,
                1 if enabled else 0,
                notes,
                now,
                now,
            ),
        )
    return service_id


def update_service(
    service_id: str,
    *,
    name: str,
    base_url: str,
    auth_type: str = "none",
    auth_secret: str | None = None,
    default_headers: dict[str, Any] | None = None,
    enabled: bool = True,
    notes: str | None = None,
    db_path: Path | None = None,
) -> None:
    """Update an existing API service."""
    # Update timestamps even if only one field changes for auditing.
    now = _now_iso()
    headers_json = json.dumps(default_headers or {})
    with _connect(db_path) as conn:
        result = conn.execute(
            """
            UPDATE api_services
               SET name = ?,
                   base_url = ?,
                   auth_type = ?,
                   auth_secret = ?,
                   default_headers_json = ?,
                   enabled = ?,
                   notes = ?,
                   updated_at = ?
             WHERE id = ?
            """,
            (
                name,
                base_url,
                auth_type,
                auth_secret,
                headers_json,
                1 if enabled else 0,
                notes,
                now,
                service_id,
            ),
        )
    if result.rowcount == 0:
        raise KeyError(f"API service not found: {service_id}")


def delete_service(service_id: str, db_path: Path | None = None) -> None:
    """Delete an API service and cascade its commands."""
    with _connect(db_path) as conn:
        result = conn.execute(
            "DELETE FROM api_services WHERE id = ?",
            (service_id,),
        )
    if result.rowcount == 0:
        raise KeyError(f"API service not found: {service_id}")


# ---------------------------------------------------------------------------
# Command CRUD
# ---------------------------------------------------------------------------


def list_commands(
    service_id: str | None = None,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Return commands for a service (or all commands when service_id is None)."""
    # Commands are ordered by name to keep dropdowns predictable.
    query = "SELECT * FROM api_commands"
    params: tuple[Any, ...] = ()
    if service_id is not None:
        query += " WHERE service_id = ?"
        params = (service_id,)
    query += " ORDER BY name"
    with _connect(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    return [_command_row_to_dict(row) for row in rows]


def get_command(command_id: str, db_path: Path | None = None) -> dict[str, Any]:
    """Return a single command."""
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM api_commands WHERE id = ?",
            (command_id,),
        ).fetchone()
    if row is None:
        raise KeyError(f"API command not found: {command_id}")
    return _command_row_to_dict(row)


def create_command(
    service_id: str,
    name: str,
    method: str,
    path: str,
    *,
    query: dict[str, Any] | None = None,
    headers: dict[str, Any] | None = None,
    body: Any | None = None,
    timeout_seconds: int | None = None,
    db_path: Path | None = None,
) -> str:
    """Create a new API command and return its ID."""
    # Normalize method once on write so callers can pass lower/upper.
    command_id = str(uuid.uuid4())
    now = _now_iso()
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO api_commands (
                id, service_id, name, method, path,
                query_json, headers_json, body_json,
                timeout_seconds, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                command_id,
                service_id,
                name,
                method.upper(),
                path,
                json.dumps(query or {}),
                json.dumps(headers or {}),
                json.dumps(body) if body is not None else None,
                timeout_seconds,
                now,
                now,
            ),
        )
    return command_id


def update_command(
    command_id: str,
    *,
    service_id: str,
    name: str,
    method: str,
    path: str,
    query: dict[str, Any] | None = None,
    headers: dict[str, Any] | None = None,
    body: Any | None = None,
    timeout_seconds: int | None = None,
    db_path: Path | None = None,
) -> None:
    """Update an existing API command."""
    now = _now_iso()
    with _connect(db_path) as conn:
        result = conn.execute(
            """
            UPDATE api_commands
               SET service_id = ?,
                   name = ?,
                   method = ?,
                   path = ?,
                   query_json = ?,
                   headers_json = ?,
                   body_json = ?,
                   timeout_seconds = ?,
                   updated_at = ?
             WHERE id = ?
            """,
            (
                service_id,
                name,
                method.upper(),
                path,
                json.dumps(query or {}),
                json.dumps(headers or {}),
                json.dumps(body) if body is not None else None,
                timeout_seconds,
                now,
                command_id,
            ),
        )
    if result.rowcount == 0:
        raise KeyError(f"API command not found: {command_id}")


def delete_command(command_id: str, db_path: Path | None = None) -> None:
    """Delete a command."""
    with _connect(db_path) as conn:
        result = conn.execute(
            "DELETE FROM api_commands WHERE id = ?",
            (command_id,),
        )
    if result.rowcount == 0:
        raise KeyError(f"API command not found: {command_id}")
