"""Tests for SQLite map storage service."""

from pipeworks_mud_mapper.models import Coords, MapFile, MapRoom
from pipeworks_mud_mapper.services import map_db_service, zone_service


def test_list_maps_empty(tmp_path):
    """list_maps should return empty list for a fresh database."""
    db_path = tmp_path / "mapper.db"
    assert map_db_service.list_maps(db_path) == []


def test_save_and_load_map_round_trip(tmp_path):
    """save_map/load_map should preserve map metadata and rooms."""
    db_path = tmp_path / "mapper.db"
    map_file = zone_service.create_new_map_file(
        zone_id="test_zone",
        name="Test Zone",
        spawn_room_name="Spawn Room",
        description="A test zone.",
    )
    map_file.metadata.map_version = "2"
    map_file.metadata.map_revision = 5
    map_file.rooms["spawn"].description = "Spawn description."
    map_file.rooms["spawn"].coords = Coords(x=10, y=20, z=0)
    map_file.rooms["spawn"].exits = {"north": "hall"}
    map_file.rooms["spawn"].items = ["item_1"]

    map_db_service.save_map(map_file, db_path)
    loaded = map_db_service.load_map("test_zone", db_path)

    assert loaded.id == "test_zone"
    assert loaded.name == "Test Zone"
    assert loaded.description == "A test zone."
    assert loaded.metadata.map_version == "2"
    assert loaded.metadata.map_revision == 5
    assert loaded.spawn_room == "spawn"
    assert loaded.rooms["spawn"].description == "Spawn description."
    assert loaded.rooms["spawn"].coords == Coords(x=10, y=20, z=0)
    assert loaded.rooms["spawn"].exits == {"north": "hall"}
    assert loaded.rooms["spawn"].items == ["item_1"]


def test_map_exists_and_delete(tmp_path):
    """map_exists should reflect inserts and deletes."""
    db_path = tmp_path / "mapper.db"
    map_file = MapFile(
        id="alpha",
        name="Alpha",
        spawn_room="spawn",
        rooms={"spawn": MapRoom(id="spawn", name="Spawn")},
    )

    assert map_db_service.map_exists("alpha", db_path) is False

    map_db_service.save_map(map_file, db_path)
    assert map_db_service.map_exists("alpha", db_path) is True

    map_db_service.delete_map("alpha", db_path)
    assert map_db_service.map_exists("alpha", db_path) is False


def test_get_db_stats_empty(tmp_path):
    """get_db_stats should return zero counts for empty DB."""
    db_path = tmp_path / "mapper.db"
    stats = map_db_service.get_db_stats(db_path)

    assert stats["map_count"] == 0
    assert stats["room_count"] == 0
    assert stats["llm_generation_count"] == 0
    assert stats["last_updated"] is None


def test_get_map_overview_counts_rooms(tmp_path):
    """get_map_overview should include room counts per map."""
    db_path = tmp_path / "mapper.db"
    map_file = MapFile(
        id="alpha",
        name="Alpha",
        spawn_room="spawn",
        rooms={
            "spawn": MapRoom(id="spawn", name="Spawn"),
            "hall": MapRoom(id="hall", name="Hall"),
        },
    )

    map_db_service.save_map(map_file, db_path)
    overview = map_db_service.get_map_overview(db_path)

    assert len(overview) == 1
    assert overview[0]["map_id"] == "alpha"
    assert overview[0]["room_count"] == 2
