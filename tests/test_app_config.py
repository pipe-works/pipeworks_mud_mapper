"""Tests for application configuration helpers."""

from pathlib import Path

import pytest

from pipeworks_mud_mapper.services import app_config


@pytest.fixture(autouse=True)
def clear_app_config_cache():
    """Ensure cached config is cleared between tests."""
    app_config.get_path_settings.cache_clear()
    yield
    app_config.get_path_settings.cache_clear()


def test_get_path_settings_defaults(tmp_path, monkeypatch):
    """get_path_settings should resolve defaults relative to project root."""
    project_root = tmp_path / "project"
    config_dir = project_root / "config"

    monkeypatch.setattr(app_config, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(app_config, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(app_config, "SERVER_CONFIG_PATH", config_dir / "server.ini")

    settings = app_config.get_path_settings()

    assert settings["maps_dir"] == project_root / "data" / "maps"
    assert settings["zones_dir"] == project_root / "data" / "zones"


def test_get_path_settings_from_server_ini(tmp_path, monkeypatch):
    """get_path_settings should honor overrides from server.ini."""
    project_root = tmp_path / "project"
    config_dir = project_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    server_ini = config_dir / "server.ini"

    server_ini.write_text("[paths]\n" "maps_dir = custom/maps\n" "zones_dir = custom/zones\n")

    monkeypatch.setattr(app_config, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(app_config, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(app_config, "SERVER_CONFIG_PATH", server_ini)

    settings = app_config.get_path_settings()

    assert settings["maps_dir"] == project_root / "custom" / "maps"
    assert settings["zones_dir"] == project_root / "custom" / "zones"


def test_format_display_path_relative(tmp_path, monkeypatch):
    """format_display_path should prefer relative paths and trailing slash."""
    project_root = tmp_path / "project"
    nested_path = project_root / "data" / "maps"

    monkeypatch.setattr(app_config, "PROJECT_ROOT", project_root)

    display = app_config.format_display_path(nested_path)

    assert display == "data/maps/"


def test_format_display_path_absolute(tmp_path, monkeypatch):
    """format_display_path should fall back to absolute path."""
    project_root = tmp_path / "project"
    outside_path = tmp_path / "other" / "zones"

    monkeypatch.setattr(app_config, "PROJECT_ROOT", project_root)

    display = app_config.format_display_path(outside_path)

    assert display == f"{outside_path}/"


def test_format_short_path_relative(tmp_path, monkeypatch):
    """format_short_path should prefer relative and keep trailing slash."""
    project_root = tmp_path / "project"
    nested = project_root / "data" / "maps"

    monkeypatch.setattr(app_config, "PROJECT_ROOT", project_root)

    display = app_config.format_short_path(nested)

    assert display == "data/maps/"


def test_format_short_path_absolute(tmp_path, monkeypatch):
    """format_short_path should shorten absolute paths with ellipsis."""
    project_root = tmp_path / "project"
    outside = tmp_path / "alpha" / "beta" / "gamma" / "zones"

    monkeypatch.setattr(app_config, "PROJECT_ROOT", project_root)

    display = app_config.format_short_path(outside, keep_parts=2)

    assert display.startswith("…/")
    assert display.endswith("/gamma/zones/")


def test_format_short_path_absolute_short(tmp_path, monkeypatch):
    """format_short_path should keep short absolute paths intact."""
    project_root = tmp_path / "project"
    outside = Path("/zones")

    monkeypatch.setattr(app_config, "PROJECT_ROOT", project_root)

    display = app_config.format_short_path(outside, keep_parts=5)

    assert display == f"{outside}/"
