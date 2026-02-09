"""Tests for the API HTTP client."""

from datetime import timedelta

import httpx

from pipeworks_mud_mapper.services import api_client


def test_build_url_handles_absolute_paths():
    """Absolute URLs should pass through unchanged."""
    assert api_client._build_url("http://example.com", "https://api.test/v1") == (
        "https://api.test/v1"
    )


def test_build_url_joins_base_and_path():
    """Base URLs should join cleanly with paths."""
    assert api_client._build_url("http://example.com/", "/api/test") == (
        "http://example.com/api/test"
    )


def test_merge_headers_overrides_case_insensitive():
    """Headers with the same name should be overridden regardless of case."""
    merged = api_client._merge_headers({"X-Token": "old"}, {"x-token": "new"})
    assert merged == {"x-token": "new"}


def test_apply_auth_sets_bearer_header():
    """Bearer auth should populate the Authorization header."""
    headers, auth = api_client._apply_auth({}, "bearer", "token")
    assert headers["Authorization"] == "Bearer token"
    assert auth is None


def test_apply_auth_sets_basic_auth():
    """Basic auth should return an httpx.BasicAuth object."""
    headers, auth = api_client._apply_auth({}, "basic", "user:pass")
    assert isinstance(auth, httpx.BasicAuth)
    assert headers == {}


def test_execute_api_request_success(monkeypatch):
    """execute_api_request should return structured response data."""

    class DummyResponse:
        def __init__(self) -> None:
            self.is_success = True
            self.status_code = 200
            self.reason_phrase = "OK"
            self.url = httpx.URL("http://example.com/api")
            self.elapsed = timedelta(milliseconds=15)
            self.headers = {"content-type": "application/json"}
            self.text = '{"ok": true}'

        def json(self):  # type: ignore[override]
            return {"ok": True}

    class DummyClient:
        last_request: dict | None = None

        def __init__(self, *args, **kwargs) -> None:
            self.kwargs = kwargs

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def request(self, *args, **kwargs):
            DummyClient.last_request = kwargs
            return DummyResponse()

    monkeypatch.setattr(api_client.httpx, "Client", DummyClient)

    result = api_client.execute_api_request(
        base_url="http://example.com",
        path="/api",
        method="GET",
        headers={"X-Token": "123"},
        query={"q": "test"},
        body=None,
        auth_type="none",
        auth_secret=None,
        timeout_seconds=5,
    )

    assert result["ok"] is True
    assert result["status_code"] == 200
    assert result["json"] == {"ok": True}
    assert DummyClient.last_request is not None
    assert DummyClient.last_request["headers"]["X-Token"] == "123"


def test_execute_api_request_handles_errors(monkeypatch):
    """execute_api_request should surface request errors."""

    class DummyClient:
        def __init__(self, *args, **kwargs) -> None:
            self.kwargs = kwargs

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def request(self, *args, **kwargs):
            raise httpx.RequestError("boom", request=httpx.Request("GET", "http://x"))

    monkeypatch.setattr(api_client.httpx, "Client", DummyClient)

    result = api_client.execute_api_request(
        base_url="http://example.com",
        path="/api",
        method="GET",
    )

    assert result["ok"] is False
    assert result["status_code"] is None
    assert "boom" in result["error"]
