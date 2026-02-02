"""Tests for zone I/O utilities."""

import json
from pathlib import Path

import pytest

from pipeworks_mud_mapper.utils.zone_io import (
    DIRECTION_OFFSETS,
    DIRECTION_SHORT,
    OPPOSITE_DIRECTION,
    SHORT_TO_DIRECTION,
    auto_layout_rooms,
    create_blank_zone,
    find_room_by_coords,
    find_room_in_direction,
    list_zone_files,
    load_zone_json,
    save_zone_json,
)


class TestCreateBlankZone:
    """Tests for create_blank_zone function."""

    def test_returns_dict_with_required_fields(self) -> None:
        """Blank zone should have all required top-level fields."""
        zone = create_blank_zone("test_zone", "Test Zone")

        assert zone["id"] == "test_zone"
        assert zone["name"] == "Test Zone"
        assert zone["description"] == ""
        assert zone["spawn_room"] == "spawn"
        assert "rooms" in zone
        assert "items" in zone

    def test_includes_spawn_room(self) -> None:
        """Blank zone should include a spawn room."""
        zone = create_blank_zone("test_zone", "Test Zone")

        assert "spawn" in zone["rooms"]
        spawn = zone["rooms"]["spawn"]
        assert spawn["id"] == "spawn"
        assert spawn["name"] == "Starting Room"
        assert spawn["exits"] == {}
        assert spawn["items"] == []

    def test_includes_description(self) -> None:
        """Blank zone should include provided description."""
        zone = create_blank_zone("test_zone", "Test Zone", "A test description")

        assert zone["description"] == "A test description"

    def test_items_dict_is_empty(self) -> None:
        """Blank zone should have empty items dict."""
        zone = create_blank_zone("test_zone", "Test Zone")

        assert zone["items"] == {}


class TestSaveAndLoadZoneJson:
    """Tests for save_zone_json and load_zone_json functions."""

    def test_save_creates_file(self, tmp_path: Path) -> None:
        """save_zone_json should create a JSON file."""
        zone = create_blank_zone("test_zone", "Test Zone")
        file_path = tmp_path / "test_zone.json"

        save_zone_json(zone, file_path)

        assert file_path.exists()

    def test_save_writes_valid_json(self, tmp_path: Path) -> None:
        """save_zone_json should write valid JSON."""
        zone = create_blank_zone("test_zone", "Test Zone")
        file_path = tmp_path / "test_zone.json"

        save_zone_json(zone, file_path)

        content = file_path.read_text()
        parsed = json.loads(content)
        assert parsed["id"] == "test_zone"

    def test_save_creates_parent_directories(self, tmp_path: Path) -> None:
        """save_zone_json should create parent directories if needed."""
        zone = create_blank_zone("test_zone", "Test Zone")
        file_path = tmp_path / "subdir" / "nested" / "test_zone.json"

        save_zone_json(zone, file_path)

        assert file_path.exists()

    def test_load_reads_saved_file(self, tmp_path: Path) -> None:
        """load_zone_json should read a saved zone file."""
        zone = create_blank_zone("test_zone", "Test Zone", "Description")
        file_path = tmp_path / "test_zone.json"
        save_zone_json(zone, file_path)

        loaded = load_zone_json(file_path)

        assert loaded == zone

    def test_load_raises_on_missing_file(self, tmp_path: Path) -> None:
        """load_zone_json should raise FileNotFoundError for missing file."""
        file_path = tmp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError):
            load_zone_json(file_path)

    def test_load_raises_on_invalid_json(self, tmp_path: Path) -> None:
        """load_zone_json should raise JSONDecodeError for invalid JSON."""
        file_path = tmp_path / "invalid.json"
        file_path.write_text("not valid json")

        with pytest.raises(json.JSONDecodeError):
            load_zone_json(file_path)


class TestListZoneFiles:
    """Tests for list_zone_files function."""

    def test_returns_empty_list_for_missing_directory(self, tmp_path: Path) -> None:
        """list_zone_files should return empty list for nonexistent directory."""
        result = list_zone_files(tmp_path / "nonexistent")

        assert result == []

    def test_returns_empty_list_for_empty_directory(self, tmp_path: Path) -> None:
        """list_zone_files should return empty list for empty directory."""
        result = list_zone_files(tmp_path)

        assert result == []

    def test_finds_json_files(self, tmp_path: Path) -> None:
        """list_zone_files should find .json files."""
        (tmp_path / "zone1.json").write_text("{}")
        (tmp_path / "zone2.json").write_text("{}")

        result = list_zone_files(tmp_path)

        assert len(result) == 2
        names = [f.name for f in result]
        assert "zone1.json" in names
        assert "zone2.json" in names

    def test_ignores_non_json_files(self, tmp_path: Path) -> None:
        """list_zone_files should ignore non-.json files."""
        (tmp_path / "zone1.json").write_text("{}")
        (tmp_path / "readme.txt").write_text("text")
        (tmp_path / "config.yaml").write_text("yaml: true")

        result = list_zone_files(tmp_path)

        assert len(result) == 1
        assert result[0].name == "zone1.json"

    def test_returns_sorted_list(self, tmp_path: Path) -> None:
        """list_zone_files should return files sorted by name."""
        (tmp_path / "c_zone.json").write_text("{}")
        (tmp_path / "a_zone.json").write_text("{}")
        (tmp_path / "b_zone.json").write_text("{}")

        result = list_zone_files(tmp_path)

        names = [f.name for f in result]
        assert names == ["a_zone.json", "b_zone.json", "c_zone.json"]


class TestAutoLayoutRooms:
    """Tests for auto_layout_rooms function."""

    def test_single_room_at_origin(self) -> None:
        """Single room zone should place spawn at origin."""
        zone = {
            "spawn_room": "spawn",
            "rooms": {
                "spawn": {"id": "spawn", "exits": {}},
            },
        }

        result = auto_layout_rooms(zone)

        assert result["rooms"]["spawn"]["coords"] == [0, 0, 0]

    def test_north_exit_increases_y(self) -> None:
        """Room north of spawn should have y+1."""
        zone = {
            "spawn_room": "spawn",
            "rooms": {
                "spawn": {"id": "spawn", "exits": {"north": "north_room"}},
                "north_room": {"id": "north_room", "exits": {"south": "spawn"}},
            },
        }

        result = auto_layout_rooms(zone)

        assert result["rooms"]["spawn"]["coords"] == [0, 0, 0]
        assert result["rooms"]["north_room"]["coords"] == [0, 1, 0]

    def test_east_exit_increases_x(self) -> None:
        """Room east of spawn should have x+1."""
        zone = {
            "spawn_room": "spawn",
            "rooms": {
                "spawn": {"id": "spawn", "exits": {"east": "east_room"}},
                "east_room": {"id": "east_room", "exits": {"west": "spawn"}},
            },
        }

        result = auto_layout_rooms(zone)

        assert result["rooms"]["spawn"]["coords"] == [0, 0, 0]
        assert result["rooms"]["east_room"]["coords"] == [1, 0, 0]

    def test_down_exit_decreases_z(self) -> None:
        """Room below spawn should have z-1."""
        zone = {
            "spawn_room": "spawn",
            "rooms": {
                "spawn": {"id": "spawn", "exits": {"down": "cellar"}},
                "cellar": {"id": "cellar", "exits": {"up": "spawn"}},
            },
        }

        result = auto_layout_rooms(zone)

        assert result["rooms"]["spawn"]["coords"] == [0, 0, 0]
        assert result["rooms"]["cellar"]["coords"] == [0, 0, -1]

    def test_chain_of_rooms(self) -> None:
        """Chain of rooms should accumulate offsets."""
        zone = {
            "spawn_room": "a",
            "rooms": {
                "a": {"id": "a", "exits": {"north": "b"}},
                "b": {"id": "b", "exits": {"north": "c", "south": "a"}},
                "c": {"id": "c", "exits": {"south": "b"}},
            },
        }

        result = auto_layout_rooms(zone)

        assert result["rooms"]["a"]["coords"] == [0, 0, 0]
        assert result["rooms"]["b"]["coords"] == [0, 1, 0]
        assert result["rooms"]["c"]["coords"] == [0, 2, 0]

    def test_preserves_existing_coords(self) -> None:
        """Rooms with existing coords should not be overwritten."""
        zone = {
            "spawn_room": "spawn",
            "rooms": {
                "spawn": {"id": "spawn", "coords": [5, 5, 0], "exits": {"north": "north_room"}},
                "north_room": {"id": "north_room", "exits": {"south": "spawn"}},
            },
        }

        result = auto_layout_rooms(zone)

        # Spawn keeps its original coords
        assert result["rooms"]["spawn"]["coords"] == [5, 5, 0]
        # North room gets computed coords (spawn is still at origin for BFS)
        assert result["rooms"]["north_room"]["coords"] == [0, 1, 0]

    def test_skips_cross_zone_exits(self) -> None:
        """Cross-zone exits (with ':') should be skipped."""
        zone = {
            "spawn_room": "spawn",
            "rooms": {
                "spawn": {"id": "spawn", "exits": {"west": "other_zone:room"}},
            },
        }

        result = auto_layout_rooms(zone)

        # Only spawn should have coords
        assert result["rooms"]["spawn"]["coords"] == [0, 0, 0]

    def test_disconnected_rooms_placed_at_origin(self) -> None:
        """Rooms not reachable from spawn should be placed at origin."""
        zone = {
            "spawn_room": "spawn",
            "rooms": {
                "spawn": {"id": "spawn", "exits": {}},
                "island": {"id": "island", "exits": {}},
            },
        }

        result = auto_layout_rooms(zone)

        assert result["rooms"]["spawn"]["coords"] == [0, 0, 0]
        assert result["rooms"]["island"]["coords"] == [0, 0, 0]

    def test_empty_zone(self) -> None:
        """Empty zone should return unchanged."""
        zone = {"rooms": {}}

        result = auto_layout_rooms(zone)

        assert result["rooms"] == {}

    def test_does_not_mutate_original(self) -> None:
        """auto_layout_rooms should not mutate the original zone."""
        zone = {
            "spawn_room": "spawn",
            "rooms": {
                "spawn": {"id": "spawn", "exits": {}},
            },
        }

        auto_layout_rooms(zone)

        assert "coords" not in zone["rooms"]["spawn"]


class TestDirectionMappings:
    """Tests for direction mapping constants."""

    def test_direction_offsets_has_six_directions(self) -> None:
        """DIRECTION_OFFSETS should have all 6 cardinal directions."""
        assert len(DIRECTION_OFFSETS) == 6
        assert set(DIRECTION_OFFSETS.keys()) == {
            "north",
            "south",
            "east",
            "west",
            "up",
            "down",
        }

    def test_direction_short_maps_all_directions(self) -> None:
        """DIRECTION_SHORT should map all directions to short labels."""
        assert DIRECTION_SHORT["north"] == "N"
        assert DIRECTION_SHORT["south"] == "S"
        assert DIRECTION_SHORT["east"] == "E"
        assert DIRECTION_SHORT["west"] == "W"
        assert DIRECTION_SHORT["up"] == "U"
        assert DIRECTION_SHORT["down"] == "D"

    def test_short_to_direction_is_reverse_mapping(self) -> None:
        """SHORT_TO_DIRECTION should be reverse of DIRECTION_SHORT."""
        for direction, short in DIRECTION_SHORT.items():
            assert SHORT_TO_DIRECTION[short] == direction

    def test_opposite_direction_maps_all_directions(self) -> None:
        """OPPOSITE_DIRECTION should map all directions to their opposites."""
        assert OPPOSITE_DIRECTION["north"] == "south"
        assert OPPOSITE_DIRECTION["south"] == "north"
        assert OPPOSITE_DIRECTION["east"] == "west"
        assert OPPOSITE_DIRECTION["west"] == "east"
        assert OPPOSITE_DIRECTION["up"] == "down"
        assert OPPOSITE_DIRECTION["down"] == "up"

    def test_opposite_direction_is_symmetric(self) -> None:
        """Applying opposite twice should return original direction."""
        for direction in DIRECTION_OFFSETS:
            opposite = OPPOSITE_DIRECTION[direction]
            assert OPPOSITE_DIRECTION[opposite] == direction


class TestFindRoomByCoords:
    """Tests for find_room_by_coords function."""

    def test_finds_room_at_coordinates(self) -> None:
        """Should find room matching given coordinates."""
        rooms = {
            "room_a": {"coords": [0, 0, 0]},
            "room_b": {"coords": [5, -5, 0]},
            "room_c": {"coords": [1, 2, 3]},
        }

        result = find_room_by_coords(rooms, (5, -5, 0))

        assert result == "room_b"

    def test_returns_none_when_no_match(self) -> None:
        """Should return None when no room at coordinates."""
        rooms = {
            "room_a": {"coords": [0, 0, 0]},
            "room_b": {"coords": [5, 0, 0]},
        }

        result = find_room_by_coords(rooms, (10, 10, 10))

        assert result is None

    def test_accepts_list_coordinates(self) -> None:
        """Should accept coordinates as list."""
        rooms = {
            "room_a": {"coords": [3, 4, 5]},
        }

        result = find_room_by_coords(rooms, [3, 4, 5])

        assert result == "room_a"

    def test_empty_rooms_returns_none(self) -> None:
        """Should return None for empty rooms dict."""
        result = find_room_by_coords({}, (0, 0, 0))

        assert result is None

    def test_room_without_coords_skipped(self) -> None:
        """Rooms without coords key should use default [0,0,0]."""
        rooms = {
            "room_no_coords": {},
            "room_at_origin": {"coords": [0, 0, 0]},
        }

        # Both should match origin, but room_no_coords comes first alphabetically
        result = find_room_by_coords(rooms, (0, 0, 0))

        # Should find one of them (dict ordering)
        assert result in ["room_no_coords", "room_at_origin"]


class TestFindRoomInDirection:
    """Tests for find_room_in_direction function."""

    def test_finds_room_to_east(self) -> None:
        """Should find room that is east (higher x, same y/z)."""
        rooms = {
            "origin": {"coords": [0, 0, 0]},
            "east_room": {"coords": [5, 0, 0]},
        }

        result = find_room_in_direction(rooms, (0, 0, 0), "east", exclude_room="origin")

        assert result == "east_room"

    def test_finds_room_to_north(self) -> None:
        """Should find room that is north (higher y, same x/z)."""
        rooms = {
            "origin": {"coords": [0, 0, 0]},
            "north_room": {"coords": [0, 10, 0]},
        }

        result = find_room_in_direction(rooms, (0, 0, 0), "north", exclude_room="origin")

        assert result == "north_room"

    def test_finds_nearest_room(self) -> None:
        """Should find the nearest room when multiple exist in direction."""
        rooms = {
            "origin": {"coords": [0, 0, 0]},
            "near_east": {"coords": [3, 0, 0]},
            "far_east": {"coords": [10, 0, 0]},
        }

        result = find_room_in_direction(rooms, (0, 0, 0), "east", exclude_room="origin")

        assert result == "near_east"

    def test_returns_none_when_no_room_in_direction(self) -> None:
        """Should return None when no room exists in that direction."""
        rooms = {
            "origin": {"coords": [0, 0, 0]},
            "west_room": {"coords": [-5, 0, 0]},
        }

        result = find_room_in_direction(rooms, (0, 0, 0), "east", exclude_room="origin")

        assert result is None

    def test_ignores_rooms_on_different_z_level(self) -> None:
        """Horizontal directions should only find rooms on same z-level."""
        rooms = {
            "origin": {"coords": [0, 0, 0]},
            "east_different_z": {"coords": [5, 0, 1]},
        }

        result = find_room_in_direction(rooms, (0, 0, 0), "east", exclude_room="origin")

        assert result is None

    def test_finds_room_up(self) -> None:
        """Should find room that is up (higher z, same x/y)."""
        rooms = {
            "ground": {"coords": [0, 0, 0]},
            "upstairs": {"coords": [0, 0, 1]},
        }

        result = find_room_in_direction(rooms, (0, 0, 0), "up", exclude_room="ground")

        assert result == "upstairs"

    def test_finds_room_down(self) -> None:
        """Should find room that is down (lower z, same x/y)."""
        rooms = {
            "ground": {"coords": [0, 0, 0]},
            "basement": {"coords": [0, 0, -1]},
        }

        result = find_room_in_direction(rooms, (0, 0, 0), "down", exclude_room="ground")

        assert result == "basement"

    def test_excludes_specified_room(self) -> None:
        """Should not return the excluded room."""
        rooms = {
            "origin": {"coords": [0, 0, 0]},
        }

        result = find_room_in_direction(rooms, (0, 0, 0), "east", exclude_room="origin")

        assert result is None

    def test_invalid_direction_returns_none(self) -> None:
        """Should return None for invalid direction."""
        rooms = {
            "origin": {"coords": [0, 0, 0]},
            "other": {"coords": [5, 0, 0]},
        }

        result = find_room_in_direction(rooms, (0, 0, 0), "invalid")

        assert result is None

    def test_diagonal_room_not_found(self) -> None:
        """Should not find rooms that are diagonal (both x and y differ)."""
        rooms = {
            "origin": {"coords": [0, 0, 0]},
            "diagonal": {"coords": [5, 5, 0]},
        }

        result = find_room_in_direction(rooms, (0, 0, 0), "east", exclude_room="origin")

        assert result is None

    def test_ledgerfall_alley_layout(self) -> None:
        """Should work with the ledgerfall_alley room layout."""
        # Reproduce the actual test data layout
        rooms = {
            "spawn": {"coords": [0, 0, 0]},
            "broken_door": {"coords": [5, 0, 0]},
            "locked_door": {"coords": [0, -5, 0]},
            "dark_hallway": {"coords": [5, -5, 0]},
        }

        # From locked_door, east should find dark_hallway
        result = find_room_in_direction(
            rooms, (0, -5, 0), "east", exclude_room="locked_door"
        )
        assert result == "dark_hallway"

        # From locked_door, north should find spawn
        result = find_room_in_direction(
            rooms, (0, -5, 0), "north", exclude_room="locked_door"
        )
        assert result == "spawn"

        # From locked_door, south should find nothing
        result = find_room_in_direction(
            rooms, (0, -5, 0), "south", exclude_room="locked_door"
        )
        assert result is None
