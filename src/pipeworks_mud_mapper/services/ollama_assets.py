"""Asset loading helpers for the Ollama UI.

This module isolates filesystem access for Ollama-related UI assets
(such as prompt prefix presets). Keeping this logic here prevents
callbacks from repeatedly reading files and centralizes error handling.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

# =============================================================================
# Paths
# =============================================================================
# We compute the prompt prefix config path relative to the project root.
# Using a helper keeps the path definition in one place.


def _prompt_prefixes_path() -> Path:
    """Return the absolute path to prompt_prefixes.json.

    Returns
    -------
    Path
        Absolute path to data/ollama/prompt_prefixes.json.
    """
    return Path(__file__).parent.parent.parent.parent / "data" / "ollama" / "prompt_prefixes.json"


def _parameter_presets_dir() -> Path:
    """Return the absolute path to the parameter presets directory.

    Each preset is stored as its own JSON file so authors can add and share
    presets without editing a monolithic registry file.
    """
    return Path(__file__).parent.parent.parent.parent / "data" / "ollama" / "presets"


# =============================================================================
# Loading Functions
# =============================================================================
# We use a small cache so repeated UI interactions don't reread the file
# unnecessarily. The reload flag allows manual refresh when needed.


@lru_cache(maxsize=1)
def _load_prompt_prefixes_cached() -> list[dict[str, Any]]:
    """Load prompt prefixes from disk (cached).

    Returns
    -------
    list[dict[str, Any]]
        Parsed JSON list of prefix objects. Returns empty list on errors.
    """
    config_path = _prompt_prefixes_path()
    try:
        with open(config_path, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

    if not isinstance(data, list):
        return []

    # Ensure only dictionaries are returned for downstream processing.
    return [item for item in data if isinstance(item, dict)]


def load_prompt_prefixes(*, reload: bool = False) -> list[dict[str, Any]]:
    """Return the list of prompt prefix dictionaries.

    Parameters
    ----------
    reload : bool
        When True, clears the cache and reloads from disk.

    Returns
    -------
    list[dict[str, Any]]
        Prompt prefix definitions from prompt_prefixes.json.
    """
    if reload:
        _load_prompt_prefixes_cached.cache_clear()
    return _load_prompt_prefixes_cached()


@lru_cache(maxsize=1)
def _load_parameter_presets_cached() -> list[dict[str, Any]]:
    """Load parameter presets from disk (cached)."""
    presets_dir = _parameter_presets_dir()
    if not presets_dir.exists():
        return []

    presets: list[dict[str, Any]] = []
    # Sort for deterministic UI ordering across platforms.
    for path in sorted(presets_dir.glob("*.preset.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            # Ignore malformed preset files instead of breaking the UI.
            continue
        if isinstance(data, dict):
            presets.append(data)
    return presets


def load_parameter_presets(*, reload: bool = False) -> list[dict[str, Any]]:
    """Return the list of parameter preset dictionaries.

    Parameters
    ----------
    reload : bool
        When True, clears the cache and reloads from disk.
    """
    if reload:
        _load_parameter_presets_cached.cache_clear()
    return _load_parameter_presets_cached()
