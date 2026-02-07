"""World metadata helpers for cross-zone navigation.

The mapper needs a lightweight way to discover which zones exist and what
rooms they expose so we can build cross-zone exit pickers. The MUD server
stores this information in ``world.json`` alongside the exported zone files.

This module provides best-effort readers that:

- Prefer ``world.json`` when present (authoritative list of zones)
- Fall back to enumerating zone files if the world file is missing
- Gracefully handle missing or malformed data
"""

from __future__ import annotations

import json
from pathlib import Path

from pipeworks_mud_mapper.services import zone_service
from pipeworks_mud_mapper.services.app_config import get_path_settings


def _resolve_zones_dir(zones_dir: Path | None) -> Path:
    """Resolve the zones directory using config defaults when needed."""
    if zones_dir is not None:
        return zones_dir
    return get_path_settings()["zones_dir"]


def _resolve_world_path(world_path: Path | None = None, zones_dir: Path | None = None) -> Path:
    """Derive the ``world.json`` path from config or the zones directory."""
    # Prefer explicit overrides, then zones_dir parent, then config default.
    if world_path is not None:
        return world_path
    if zones_dir is not None:
        resolved_zones = _resolve_zones_dir(zones_dir)
        return resolved_zones.parent / "world.json"
    return get_path_settings()["world_json_path"]


def load_world_json(world_path: Path | None = None, zones_dir: Path | None = None) -> dict | None:
    """Load the world.json payload as a dictionary when available."""
    resolved_path = _resolve_world_path(world_path, zones_dir)
    if not resolved_path.exists():
        return None
    try:
        data = json.loads(resolved_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def load_world_zone_ids(zones_dir: Path | None = None, world_path: Path | None = None) -> list[str]:
    """Return the list of zone IDs known to the world.

    Parameters
    ----------
    zones_dir : Path | None
        Optional override for the zones directory. When omitted, the path
        from ``config/server.ini`` (or defaults) is used.
    world_path : Path | None
        Optional override for the world.json path. Defaults to the configured
        world_json_path, or to the parent of zones_dir when provided.

    Returns
    -------
    list[str]
        Sorted list of zone IDs. Returns an empty list if no zones are found.
    """
    resolved_zones = _resolve_zones_dir(zones_dir)
    world_path = _resolve_world_path(
        world_path,
        resolved_zones if zones_dir is not None else None,
    )
    zone_ids: list[str] = []

    if world_path.exists():
        try:
            data = json.loads(world_path.read_text(encoding="utf-8"))
            raw_zones = data.get("zones", [])
            if isinstance(raw_zones, list):
                zone_ids = [z for z in raw_zones if isinstance(z, str) and z]
        except (OSError, json.JSONDecodeError):
            zone_ids = []

    if not zone_ids:
        zone_ids = [path.stem for path in zone_service.list_zone_files(resolved_zones)]

    return sorted(set(zone_ids))


def load_zone_room_ids(zone_id: str, zones_dir: Path | None = None) -> list[str]:
    """Return room IDs for a specific zone export.

    Parameters
    ----------
    zone_id : str
        Zone ID to read from ``<zones_dir>/<zone_id>.json``.
    zones_dir : Path | None
        Optional override for the zones directory. When omitted, the path
        from ``config/server.ini`` (or defaults) is used.

    Returns
    -------
    list[str]
        Sorted list of room IDs for the zone. Empty if the zone file is
        missing or invalid.
    """
    if not zone_id:
        return []

    resolved_zones = _resolve_zones_dir(zones_dir)
    zone_path = resolved_zones / f"{zone_id}.json"
    if not zone_path.exists():
        return []

    try:
        data = json.loads(zone_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    rooms = data.get("rooms", {})
    if not isinstance(rooms, dict):
        return []

    return sorted([room_id for room_id in rooms.keys() if isinstance(room_id, str)])
