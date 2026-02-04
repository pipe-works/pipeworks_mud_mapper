"""Thin client for interacting with a local Ollama server.

This module isolates HTTP communication so callbacks can remain focused
on UI state and response handling. It also provides a central place for
timeouts and request formatting.
"""

from __future__ import annotations

from typing import Any, cast

import httpx

from pipeworks_mud_mapper.services.ollama_config import (
    OLLAMA_MODEL_REFRESH_TIMEOUT_SECONDS,
    OLLAMA_TIMEOUT_SECONDS,
)


def list_models(server_url: str) -> list[dict[str, Any]]:
    """Return the list of models from the Ollama server.

    Parameters
    ----------
    server_url : str
        Base URL for the Ollama server (e.g., http://localhost:11434).

    Returns
    -------
    list[dict[str, Any]]
        Raw model entries from the Ollama /api/tags endpoint.
    """
    # Normalize URL to avoid double slashes when appending endpoints.
    server_url = server_url.rstrip("/")

    with httpx.Client(timeout=OLLAMA_MODEL_REFRESH_TIMEOUT_SECONDS) as client:
        response = client.get(f"{server_url}/api/tags")
        response.raise_for_status()
        data = response.json()

    return cast(list[dict[str, Any]], data.get("models", []))


def chat(
    server_url: str,
    model: str,
    messages: list[dict[str, str]],
    options: dict[str, Any],
) -> dict[str, Any]:
    """Send a chat request to the Ollama /api/chat endpoint.

    Parameters
    ----------
    server_url : str
        Base URL for the Ollama server (e.g., http://localhost:11434).
    model : str
        Ollama model identifier (e.g., "llama3:8b").
    messages : list[dict[str, str]]
        Chat message objects with role/content keys.
    options : dict[str, Any]
        Ollama generation options (seed, temperature, etc.).

    Returns
    -------
    dict[str, Any]
        Parsed JSON response from the Ollama server.
    """
    server_url = server_url.rstrip("/")

    with httpx.Client(timeout=OLLAMA_TIMEOUT_SECONDS) as client:
        response = client.post(
            f"{server_url}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "options": options,
            },
        )
        response.raise_for_status()
        return cast(dict[str, Any], response.json())
