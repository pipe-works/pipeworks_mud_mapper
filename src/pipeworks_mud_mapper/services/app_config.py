"""Application configuration helpers.

This module centralizes user-configurable settings loaded from config/server.ini.
Defaults are used when the file is missing so the app remains runnable out of the box.
"""

from __future__ import annotations

from configparser import ConfigParser
from functools import lru_cache
from pathlib import Path
from typing import Final

PROJECT_ROOT: Final[Path] = Path(__file__).parent.parent.parent.parent
CONFIG_DIR: Final[Path] = PROJECT_ROOT / "config"
SERVER_CONFIG_PATH: Final[Path] = CONFIG_DIR / "server.ini"

DEFAULTS: Final[dict[str, dict[str, str]]] = {
    "paths": {
        "db_path": "data/mapper.db",
        "api_db_path": "data/api_services.db",
        "zones_dir": "data/zones",
        "world_json_path": "data/world.json",
    },
    "server": {
        "port": "8050",
    },
}


def _resolve_path(value: str) -> Path:
    """Resolve a path from config, relative to the project root when needed."""
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def _load_config() -> ConfigParser:
    """Load server.ini configuration with defaults applied."""
    config = ConfigParser()
    config.read_dict(DEFAULTS)
    if SERVER_CONFIG_PATH.exists():
        config.read(SERVER_CONFIG_PATH)
    return config


@lru_cache
def get_path_settings() -> dict[str, Path]:
    """Return configured filesystem paths used by the app.

    Note: changes to config/server.ini require an app restart to take effect.
    """
    config = _load_config()
    db_path = _resolve_path(config.get("paths", "db_path"))
    api_db_path = _resolve_path(config.get("paths", "api_db_path"))
    zones_dir = _resolve_path(config.get("paths", "zones_dir"))
    world_json_path = _resolve_path(config.get("paths", "world_json_path"))
    return {
        "db_path": db_path,
        "api_db_path": api_db_path,
        "zones_dir": zones_dir,
        "world_json_path": world_json_path,
    }


@lru_cache
def get_server_settings() -> dict[str, int]:
    """Return server settings used by the app (for example, the default port)."""
    config = _load_config()
    port_value = config.get("server", "port", fallback=DEFAULTS["server"]["port"])
    try:
        port = int(port_value)
    except ValueError:
        port = int(DEFAULTS["server"]["port"])
    return {"port": port}


def format_display_path(path: Path) -> str:
    """Format a path for UI display (relative when possible, trailing slash)."""
    try:
        display = str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        display = str(path)
    if not display.endswith("/"):
        display = f"{display}/"
    return display


def format_short_path(path: Path, *, keep_parts: int = 3) -> str:
    """Return a shortened path for compact UI labels.

    Uses relative path when possible; otherwise keeps the last few segments
    with an ellipsis prefix to avoid overly wide labels.
    """
    try:
        display = str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        parts = path.parts
        if len(parts) <= keep_parts:
            display = str(path)
        else:
            display = "…/" + "/".join(parts[-keep_parts:])
    if not display.endswith("/"):
        display = f"{display}/"
    return display
