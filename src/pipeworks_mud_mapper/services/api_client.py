"""HTTP client for executing remote API commands."""

from __future__ import annotations

from typing import Any

import httpx

DEFAULT_TIMEOUT_SECONDS = 30


def _build_url(base_url: str, path: str) -> str:
    """Join base URL and path, preserving absolute URLs."""
    if path.startswith(("http://", "https://")):
        return path
    base_url = base_url.rstrip("/")
    path = path.lstrip("/")
    if not path:
        return base_url
    return f"{base_url}/{path}"


def _merge_headers(
    base_headers: dict[str, Any] | None,
    override_headers: dict[str, Any] | None,
) -> dict[str, str]:
    """Merge headers with case-insensitive override semantics."""
    merged: dict[str, str] = {}
    for headers in (base_headers or {}, override_headers or {}):
        for key, value in headers.items():
            if value is None:
                continue
            lower_key = str(key).lower()
            for existing in list(merged.keys()):
                if existing.lower() == lower_key:
                    merged.pop(existing)
                    break
            merged[str(key)] = str(value)
    return merged


def _header_present(headers: dict[str, str], name: str) -> bool:
    target = name.lower()
    return any(key.lower() == target for key in headers.keys())


def _apply_auth(
    headers: dict[str, str],
    auth_type: str,
    auth_secret: str | None,
) -> tuple[dict[str, str], httpx.Auth | None]:
    """Inject auth headers or return an httpx auth object."""
    if not auth_secret:
        return headers, None

    auth_type = auth_type.lower().strip()
    if auth_type == "bearer":
        if not _header_present(headers, "Authorization"):
            headers["Authorization"] = f"Bearer {auth_secret}"
        return headers, None
    if auth_type == "api_key":
        if not (_header_present(headers, "X-API-Key") or _header_present(headers, "Api-Key")):
            headers["X-API-Key"] = auth_secret
        return headers, None
    if auth_type == "basic":
        if _header_present(headers, "Authorization"):
            return headers, None
        if ":" in auth_secret:
            username, password = auth_secret.split(":", 1)
        else:
            username, password = auth_secret, ""
        # Basic auth is handled via httpx helper to avoid manual header encoding.
        return headers, httpx.BasicAuth(username, password)

    return headers, None


def execute_api_request(
    *,
    base_url: str,
    path: str,
    method: str,
    headers: dict[str, Any] | None = None,
    query: dict[str, Any] | None = None,
    body: Any | None = None,
    auth_type: str = "none",
    auth_secret: str | None = None,
    timeout_seconds: int | None = None,
) -> dict[str, Any]:
    """Execute a single API request and return a structured response."""
    method = method.upper().strip() or "GET"
    url = _build_url(base_url, path)
    merged_headers = _merge_headers({}, headers or {})
    # Apply auth after merging headers so auth can override any user-provided values.
    merged_headers, auth = _apply_auth(merged_headers, auth_type, auth_secret)
    timeout = timeout_seconds if timeout_seconds is not None else DEFAULT_TIMEOUT_SECONDS

    request_kwargs: dict[str, Any] = {
        "method": method,
        "url": url,
        "headers": merged_headers,
        "params": query or {},
    }
    if body is not None:
        request_kwargs["json"] = body

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.request(auth=auth, **request_kwargs)
        result: dict[str, Any] = {
            "ok": response.is_success,
            "status_code": response.status_code,
            "reason": response.reason_phrase,
            "url": str(response.url),
            "method": method,
            "elapsed_ms": int(response.elapsed.total_seconds() * 1000),
            "headers": dict(response.headers),
            "text": response.text,
        }
        try:
            result["json"] = response.json()
        except ValueError:
            result["json"] = None
        return result
    except httpx.RequestError as exc:
        return {
            "ok": False,
            "status_code": None,
            "reason": "request_error",
            "url": url,
            "method": method,
            "elapsed_ms": None,
            "headers": {},
            "text": "",
            "json": None,
            "error": str(exc),
        }
