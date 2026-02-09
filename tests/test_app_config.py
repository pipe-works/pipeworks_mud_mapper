"""Tests for app configuration helpers."""

from __future__ import annotations

from pathlib import Path

from pipeworks_mud_mapper.services import app_config


def _write_config(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_get_server_settings_defaults(tmp_path, monkeypatch):
    """Missing server.ini should fall back to defaults."""
    config_path = tmp_path / "server.ini"
    monkeypatch.setattr(app_config, "SERVER_CONFIG_PATH", config_path)
    app_config.get_server_settings.cache_clear()

    settings = app_config.get_server_settings()
    assert settings["port"] == 8050


def test_get_server_settings_invalid_port(tmp_path, monkeypatch):
    """Invalid port values should fall back to defaults."""
    config_path = tmp_path / "server.ini"
    _write_config(config_path, "[server]\nport = not-a-number\n")
    monkeypatch.setattr(app_config, "SERVER_CONFIG_PATH", config_path)
    app_config.get_server_settings.cache_clear()

    settings = app_config.get_server_settings()
    assert settings["port"] == 8050


def test_get_server_settings_valid_port(tmp_path, monkeypatch):
    """Valid port values should be parsed as integers."""
    config_path = tmp_path / "server.ini"
    _write_config(config_path, "[server]\nport = 9001\n")
    monkeypatch.setattr(app_config, "SERVER_CONFIG_PATH", config_path)
    app_config.get_server_settings.cache_clear()

    settings = app_config.get_server_settings()
    assert settings["port"] == 9001
