"""Tests for world_service helpers."""

import json

from pipeworks_mud_mapper.services.world_service import load_world_zone_ids, load_zone_room_ids


def test_load_world_zone_ids_prefers_world_json(tmp_path):
    zones_dir = tmp_path / "zones"
    zones_dir.mkdir()
    world_path = tmp_path / "world.json"
    world_path.write_text(json.dumps({"zones": ["alpha", "beta"]}), encoding="utf-8")

    # Also create a zone file to ensure world.json wins.
    (zones_dir / "gamma.json").write_text(json.dumps({"rooms": {}}), encoding="utf-8")

    zone_ids = load_world_zone_ids(zones_dir)
    assert zone_ids == ["alpha", "beta"]


def test_load_world_zone_ids_fallback_to_zone_files(tmp_path):
    zones_dir = tmp_path / "zones"
    zones_dir.mkdir()
    (zones_dir / "alpha.json").write_text(json.dumps({"rooms": {}}), encoding="utf-8")
    (zones_dir / "beta.json").write_text(json.dumps({"rooms": {}}), encoding="utf-8")

    zone_ids = load_world_zone_ids(zones_dir)
    assert zone_ids == ["alpha", "beta"]


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
