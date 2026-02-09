"""Tests for the app entrypoint helper."""

from __future__ import annotations

from pipeworks_mud_mapper import app as mapper_app


def test_run_app_uses_config_port(monkeypatch):
    """run_app should pull the configured port when port is None."""
    captured: dict[str, int | bool] = {}

    monkeypatch.setattr(mapper_app, "get_server_settings", lambda: {"port": 9005})
    monkeypatch.setattr(mapper_app.app, "run", lambda **kwargs: captured.update(kwargs))

    mapper_app.run_app(debug=False, port=None)

    assert captured["port"] == 9005
    assert captured["debug"] is False


def test_run_app_uses_explicit_port(monkeypatch):
    """run_app should respect explicit port arguments."""
    captured: dict[str, int | bool] = {}

    def _fail():
        raise AssertionError("get_server_settings should not be called")

    monkeypatch.setattr(mapper_app, "get_server_settings", _fail)
    monkeypatch.setattr(mapper_app.app, "run", lambda **kwargs: captured.update(kwargs))

    mapper_app.run_app(debug=True, port=8123)

    assert captured["port"] == 8123
    assert captured["debug"] is True
