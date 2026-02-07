"""Tests for world_service helpers."""

import json

from pipeworks_mud_mapper.services.world_service import (
    load_world_json,
    load_world_zone_ids,
    load_zone_room_ids,
)


def test_load_world_zone_ids_prefers_world_json(tmp_path):
    zones_dir = tmp_path / "zones"
    zones_dir.mkdir()
    world_path = tmp_path / "world.json"
    world_path.write_text(json.dumps({"zones": ["alpha", "beta"]}), encoding="utf-8")

    # Also create a zone file to ensure world.json wins.
    (zones_dir / "gamma.json").write_text(json.dumps({"rooms": {}}), encoding="utf-8")

    zone_ids = load_world_zone_ids(zones_dir)
    assert zone_ids == ["alpha", "beta"]


def test_load_world_json_reads_payload(tmp_path):
    zones_dir = tmp_path / "zones"
    zones_dir.mkdir()
    world_path = tmp_path / "world.json"
    world_path.write_text(json.dumps({"zones": ["alpha"]}), encoding="utf-8")

    payload = load_world_json(world_path=world_path, zones_dir=zones_dir)

    assert payload == {"zones": ["alpha"]}


def test_load_world_json_uses_config_path(tmp_path, monkeypatch):
    zones_dir = tmp_path / "zones"
    zones_dir.mkdir()
    world_path = tmp_path / "world.json"
    world_path.write_text(json.dumps({"zones": ["alpha"]}), encoding="utf-8")

    monkeypatch.setattr(
        "pipeworks_mud_mapper.services.world_service.get_path_settings",
        lambda: {"world_json_path": world_path, "zones_dir": zones_dir},
    )

    payload = load_world_json()

    assert payload == {"zones": ["alpha"]}


def test_load_world_json_missing_file(tmp_path):
    zones_dir = tmp_path / "zones"
    zones_dir.mkdir()

    payload = load_world_json(zones_dir=zones_dir)

    assert payload is None


def test_load_world_json_invalid_payload(tmp_path):
    zones_dir = tmp_path / "zones"
    zones_dir.mkdir()
    world_path = tmp_path / "world.json"
    world_path.write_text("[]", encoding="utf-8")

    payload = load_world_json(world_path=world_path, zones_dir=zones_dir)

    assert payload is None


def test_load_world_zone_ids_fallback_to_zone_files(tmp_path):
    zones_dir = tmp_path / "zones"
    zones_dir.mkdir()
    (zones_dir / "alpha.json").write_text(json.dumps({"rooms": {}}), encoding="utf-8")
    (zones_dir / "beta.json").write_text(json.dumps({"rooms": {}}), encoding="utf-8")

    zone_ids = load_world_zone_ids(zones_dir)
    assert zone_ids == ["alpha", "beta"]


def test_load_world_zone_ids_uses_config_defaults(tmp_path, monkeypatch):
    zones_dir = tmp_path / "zones"
    zones_dir.mkdir()
    world_path = tmp_path / "world.json"
    world_path.write_text(json.dumps({"zones": ["alpha"]}), encoding="utf-8")

    monkeypatch.setattr(
        "pipeworks_mud_mapper.services.world_service.get_path_settings",
        lambda: {"world_json_path": world_path, "zones_dir": zones_dir},
    )

    zone_ids = load_world_zone_ids()
    assert zone_ids == ["alpha"]


def test_load_world_zone_ids_invalid_world_json_fallback(tmp_path):
    zones_dir = tmp_path / "zones"
    zones_dir.mkdir()
    world_path = tmp_path / "world.json"
    world_path.write_text("{bad json", encoding="utf-8")
    (zones_dir / "alpha.json").write_text(json.dumps({"rooms": {}}), encoding="utf-8")

    zone_ids = load_world_zone_ids(zones_dir)
    assert zone_ids == ["alpha"]


def test_load_world_zone_ids_filters_non_strings(tmp_path):
    zones_dir = tmp_path / "zones"
    zones_dir.mkdir()
    world_path = tmp_path / "world.json"
    world_path.write_text(json.dumps({"zones": ["alpha", "", 123]}), encoding="utf-8")

    zone_ids = load_world_zone_ids(zones_dir)
    assert zone_ids == ["alpha"]


def test_load_zone_room_ids(tmp_path):
    zones_dir = tmp_path / "zones"
    zones_dir.mkdir()
    zone_path = zones_dir / "alpha.json"
    zone_path.write_text(
        json.dumps({"rooms": {"spawn": {}, "hall": {}, "kitchen": {}}}),
        encoding="utf-8",
    )

    room_ids = load_zone_room_ids("alpha", zones_dir)
    assert room_ids == ["hall", "kitchen", "spawn"]


def test_load_zone_room_ids_missing_zone(tmp_path):
    zones_dir = tmp_path / "zones"
    zones_dir.mkdir()

    assert load_zone_room_ids("", zones_dir) == []
    assert load_zone_room_ids("missing", zones_dir) == []


def test_load_zone_room_ids_invalid_json(tmp_path):
    zones_dir = tmp_path / "zones"
    zones_dir.mkdir()
    zone_path = zones_dir / "alpha.json"
    zone_path.write_text("{bad json", encoding="utf-8")

    assert load_zone_room_ids("alpha", zones_dir) == []


def test_load_zone_room_ids_rooms_not_dict(tmp_path):
    zones_dir = tmp_path / "zones"
    zones_dir.mkdir()
    zone_path = zones_dir / "alpha.json"
    zone_path.write_text(json.dumps({"rooms": []}), encoding="utf-8")

    assert load_zone_room_ids("alpha", zones_dir) == []
