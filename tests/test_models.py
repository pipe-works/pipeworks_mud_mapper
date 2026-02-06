"""Comprehensive tests for PipeWorks MUD Mapper domain models.

This module tests the Pydantic models that form the core data structures
of the mapper application. Tests cover:

- **Coords**: Coordinate creation, conversion, and directional offset
- **Room**: Game truth room model (no coordinates)
- **MapRoom**: Authoring room model (with coordinates)
- **Zone**: Game truth zone container
- **MapFile**: Authoring zone container with two-file workflow support

The tests verify both happy paths and edge cases, including validation
errors for malformed data.

Test Organization
-----------------
Tests are grouped by model class, with each class having tests for:
- Basic creation and attribute access
- Validation (both passing and failing cases)
- Conversion methods (e.g., MapRoom.to_room(), MapFile.to_zone())
- Utility methods (e.g., find_room_in_direction)

See Also
--------
- ``models/room.py``: Room and coordinate models
- ``models/zone.py``: Zone model
- ``models/map_file.py``: MapFile model
"""

import pytest
from pydantic import ValidationError

from pipeworks_mud_mapper.models import (
    Coords,
    DescriptionValidationInfo,
    Direction,
    MapFile,
    MapRoom,
    Room,
    Zone,
)
from pipeworks_mud_mapper.models.room import (
    DIRECTION_OFFSETS,
    DIRECTIONS,
    OPPOSITE_DIRECTION,
)

# =============================================================================
# Coords Tests
# =============================================================================


class TestCoords:
    """Tests for the Coords model."""

    def test_default_coords_are_origin(self):
        """Default coordinates should be (0, 0, 0)."""
        coords = Coords()
        assert coords.x == 0
        assert coords.y == 0
        assert coords.z == 0

    def test_coords_with_values(self):
        """Coordinates should accept x, y, z values."""
        coords = Coords(x=5, y=-3, z=1)
        assert coords.x == 5
        assert coords.y == -3
        assert coords.z == 1

    def test_to_tuple(self):
        """to_tuple should return (x, y, z)."""
        coords = Coords(x=1, y=2, z=3)
        assert coords.to_tuple() == (1, 2, 3)

    def test_to_list(self):
        """to_list should return [x, y, z]."""
        coords = Coords(x=1, y=2, z=3)
        assert coords.to_list() == [1, 2, 3]

    def test_from_list(self):
        """from_list should create Coords from [x, y, z]."""
        coords = Coords.from_list([5, -3, 1])
        assert coords.x == 5
        assert coords.y == -3
        assert coords.z == 1

    def test_from_list_wrong_length_raises(self):
        """from_list with wrong number of elements should raise ValueError."""
        with pytest.raises(ValueError, match="must have 3 elements"):
            Coords.from_list([1, 2])
        with pytest.raises(ValueError, match="must have 3 elements"):
            Coords.from_list([1, 2, 3, 4])

    @pytest.mark.parametrize(
        "direction,expected",
        [
            ("north", (0, 1, 0)),
            ("south", (0, -1, 0)),
            ("east", (1, 0, 0)),
            ("west", (-1, 0, 0)),
            ("up", (0, 0, 1)),
            ("down", (0, 0, -1)),
        ],
    )
    def test_offset_from_origin(self, direction: Direction, expected: tuple[int, int, int]):
        """offset should move one unit in the given direction."""
        origin = Coords()
        result = origin.offset(direction)
        assert result.to_tuple() == expected

    def test_offset_preserves_other_axes(self):
        """offset should not affect axes not involved in the direction."""
        coords = Coords(x=10, y=20, z=30)
        result = coords.offset("north")
        assert result.x == 10  # Unchanged
        assert result.y == 21  # +1
        assert result.z == 30  # Unchanged


# =============================================================================
# Direction Constants Tests
# =============================================================================


class TestDirectionConstants:
    """Tests for direction-related constants."""

    def test_all_directions_present(self):
        """DIRECTIONS should contain all six directions."""
        assert len(DIRECTIONS) == 6
        assert set(DIRECTIONS) == {"north", "south", "east", "west", "up", "down"}

    def test_opposite_directions_symmetric(self):
        """OPPOSITE_DIRECTION should be symmetric."""
        for direction, opposite in OPPOSITE_DIRECTION.items():
            assert OPPOSITE_DIRECTION[opposite] == direction

    def test_direction_offsets_cover_all_directions(self):
        """DIRECTION_OFFSETS should have entries for all directions."""
        assert set(DIRECTION_OFFSETS.keys()) == set(DIRECTIONS)

    def test_direction_offsets_are_unit_vectors(self):
        """Each offset should have magnitude 1."""
        for direction, (dx, dy, dz) in DIRECTION_OFFSETS.items():
            magnitude = abs(dx) + abs(dy) + abs(dz)
            assert magnitude == 1, f"{direction} offset should be unit vector"


# =============================================================================
# Room Tests
# =============================================================================


class TestRoom:
    """Tests for the Room model (game truth, no coordinates)."""

    def test_minimal_room(self):
        """Room with only required fields should be valid."""
        room = Room(id="spawn", name="Spawn Room")
        assert room.id == "spawn"
        assert room.name == "Spawn Room"
        assert room.description == ""
        assert room.exits == {}
        assert room.items == []

    def test_room_with_all_fields(self):
        """Room with all fields populated."""
        room = Room(
            id="tavern",
            name="The Crooked Pipe",
            description="A cozy goblin pub.",
            exits={"north": "kitchen", "down": "cellar"},
            items=["ale_mug", "torch"],
        )
        assert room.id == "tavern"
        assert room.exits["north"] == "kitchen"
        assert "ale_mug" in room.items

    def test_room_id_must_start_with_letter(self):
        """Room ID starting with number should fail validation."""
        with pytest.raises(ValidationError, match="must start with a letter"):
            Room(id="123room", name="Bad Room")

    def test_room_id_must_be_lowercase(self):
        """Room ID with uppercase should fail validation."""
        with pytest.raises(ValidationError, match="must be lowercase"):
            Room(id="MyRoom", name="Bad Room")

    def test_room_id_allows_underscores(self):
        """Room ID with underscores should be valid."""
        room = Room(id="front_parlour", name="Front Parlour")
        assert room.id == "front_parlour"

    def test_room_id_rejects_special_chars(self):
        """Room ID with special characters should fail."""
        with pytest.raises(ValidationError, match="letters, numbers, and underscores"):
            Room(id="room-one", name="Bad Room")

    def test_room_id_cannot_be_empty(self):
        """Empty room ID should fail."""
        with pytest.raises(ValidationError):
            Room(id="", name="Bad Room")

    def test_room_name_cannot_be_empty(self):
        """Empty room name should fail."""
        with pytest.raises(ValidationError):
            Room(id="room", name="")


# =============================================================================
# MapRoom Tests
# =============================================================================


class TestMapRoom:
    """Tests for the MapRoom model (authoring, with coordinates)."""

    def test_minimal_map_room(self):
        """MapRoom with only required fields."""
        room = MapRoom(id="spawn", name="Spawn")
        assert room.id == "spawn"


# =============================================================================
# DescriptionValidationInfo Tests
# =============================================================================


class TestDescriptionValidationInfo:
    """Tests for DescriptionValidationInfo model."""

    def test_defaults_and_fields(self):
        """Model should accept required fields and populate defaults."""
        info = DescriptionValidationInfo(
            valid=True,
            hard_failures=[],
            soft_failures=[],
            metrics={"word_count": 50},
            rule_hits={"cardinal_directions": []},
        )

        assert info.valid is True
        assert info.hard_failures == []
        assert info.soft_failures == []
        assert info.metrics["word_count"] == 50
        assert info.rule_hits["cardinal_directions"] == []
        assert info.validated_at is not None

    def test_map_room_with_coords(self):
        """MapRoom with explicit coordinates."""
        room = MapRoom(
            id="spawn",
            name="Spawn",
            coords=Coords(x=5, y=-3, z=1),
        )
        assert room.coords.x == 5
        assert room.coords.y == -3
        assert room.coords.z == 1

    def test_to_room_strips_coords(self):
        """to_room should create Room without coordinates."""
        map_room = MapRoom(
            id="tavern",
            name="Tavern",
            description="A pub.",
            coords=Coords(x=10, y=20, z=0),
            exits={"north": "kitchen"},
            items=["mug"],
        )
        room = map_room.to_room()

        assert isinstance(room, Room)
        assert room.id == "tavern"
        assert room.name == "Tavern"
        assert room.description == "A pub."
        assert room.exits == {"north": "kitchen"}
        assert room.items == ["mug"]
        assert not hasattr(room, "coords") or "coords" not in room.model_fields

    def test_to_room_creates_copies(self):
        """to_room should create independent copies of exits and items."""
        map_room = MapRoom(
            id="room",
            name="Room",
            exits={"north": "other"},
            items=["item"],
        )
        room = map_room.to_room()

        # Modify original
        map_room.exits["south"] = "another"
        map_room.items.append("new_item")

        # Room should be unchanged
        assert "south" not in room.exits
        assert "new_item" not in room.items

    def test_from_dict_with_list_coords(self):
        """from_dict should handle coords as [x, y, z] list."""
        data = {
            "id": "spawn",
            "name": "Spawn",
            "description": "",
            "coords": [5, -3, 1],
            "exits": {},
            "items": [],
        }
        room = MapRoom.from_dict(data)
        assert room.coords.x == 5
        assert room.coords.y == -3
        assert room.coords.z == 1

    def test_from_dict_with_coords_object(self):
        """from_dict should handle coords as Coords object."""
        data = {
            "id": "spawn",
            "name": "Spawn",
            "coords": Coords(x=1, y=2, z=3),
            "exits": {},
            "items": [],
        }
        room = MapRoom.from_dict(data)
        assert room.coords.x == 1


# =============================================================================
# Zone Tests
# =============================================================================


class TestZone:
    """Tests for the Zone model (game truth container)."""

    def test_minimal_zone(self):
        """Zone with minimal valid data."""
        zone = Zone(
            id="tutorial",
            name="Tutorial",
            spawn_room="spawn",
            rooms={"spawn": Room(id="spawn", name="Spawn")},
        )
        assert zone.id == "tutorial"
        assert zone.spawn_room == "spawn"
        assert zone.metadata.schema_version == "0.1.0"
        assert zone.metadata.exported_from is None

    def test_spawn_room_must_exist(self):
        """spawn_room must reference an existing room."""
        with pytest.raises(ValidationError, match="does not exist in rooms"):
            Zone(
                id="bad",
                name="Bad Zone",
                spawn_room="nonexistent",
                rooms={"spawn": Room(id="spawn", name="Spawn")},
            )

    def test_room_id_must_match_key(self):
        """Room ID must match its dictionary key."""
        with pytest.raises(ValidationError, match="Room ID mismatch"):
            Zone(
                id="bad",
                name="Bad Zone",
                spawn_room="key",
                rooms={"key": Room(id="different", name="Room")},
            )

    def test_get_room_found(self):
        """get_room should return room when it exists."""
        zone = Zone(
            id="test",
            name="Test",
            spawn_room="spawn",
            rooms={"spawn": Room(id="spawn", name="Spawn")},
        )
        room = zone.get_room("spawn")
        assert room is not None
        assert room.name == "Spawn"

    def test_get_room_not_found(self):
        """get_room should return None for missing room."""
        zone = Zone(
            id="test",
            name="Test",
            spawn_room="spawn",
            rooms={"spawn": Room(id="spawn", name="Spawn")},
        )
        assert zone.get_room("nonexistent") is None

    def test_validate_exits_finds_broken_exits(self):
        """validate_exits should report exits to nonexistent rooms."""
        zone = Zone(
            id="test",
            name="Test",
            spawn_room="spawn",
            rooms={
                "spawn": Room(id="spawn", name="Spawn", exits={"north": "missing"}),
            },
        )
        warnings = zone.validate_exits()
        assert len(warnings) == 1
        assert "missing" in warnings[0]

    def test_validate_exits_ignores_cross_zone(self):
        """validate_exits should skip cross-zone exits (containing :)."""
        zone = Zone(
            id="test",
            name="Test",
            spawn_room="spawn",
            rooms={
                "spawn": Room(id="spawn", name="Spawn", exits={"west": "other_zone:room"}),
            },
        )
        warnings = zone.validate_exits()
        assert len(warnings) == 0

    def test_find_unreachable_rooms(self):
        """find_unreachable_rooms should identify orphaned rooms."""
        zone = Zone(
            id="test",
            name="Test",
            spawn_room="spawn",
            rooms={
                "spawn": Room(id="spawn", name="Spawn", exits={"north": "connected"}),
                "connected": Room(id="connected", name="Connected", exits={"south": "spawn"}),
                "orphan": Room(id="orphan", name="Orphan"),  # No connections
            },
        )
        unreachable = zone.find_unreachable_rooms()
        assert unreachable == ["orphan"]

    def test_find_unreachable_rooms_all_connected(self):
        """find_unreachable_rooms should return empty list when all reachable."""
        zone = Zone(
            id="test",
            name="Test",
            spawn_room="spawn",
            rooms={
                "spawn": Room(id="spawn", name="Spawn", exits={"north": "hall"}),
                "hall": Room(id="hall", name="Hall", exits={"south": "spawn"}),
            },
        )
        assert zone.find_unreachable_rooms() == []

    def test_find_dead_ends(self):
        """find_dead_ends should identify rooms with no exits."""
        zone = Zone(
            id="test",
            name="Test",
            spawn_room="spawn",
            rooms={
                "spawn": Room(id="spawn", name="Spawn", exits={"north": "dead_end"}),
                "dead_end": Room(id="dead_end", name="Dead End"),  # No exits
            },
        )
        dead_ends = zone.find_dead_ends()
        assert dead_ends == ["dead_end"]


# =============================================================================
# MapFile Tests
# =============================================================================


class TestMapFile:
    """Tests for the MapFile model (authoring container)."""

    def test_minimal_map_file(self):
        """MapFile with minimal valid data."""
        map_file = MapFile(
            id="tutorial",
            name="Tutorial",
            spawn_room="spawn",
            rooms={"spawn": MapRoom(id="spawn", name="Spawn")},
        )
        assert map_file.id == "tutorial"
        assert map_file.metadata.schema_version == "0.1.0"
        assert map_file.metadata.map_version == "0"
        assert map_file.metadata.map_revision == 0

    def test_to_zone_strips_all_coords(self):
        """to_zone should convert all MapRooms to Rooms."""
        map_file = MapFile(
            id="test",
            name="Test",
            spawn_room="spawn",
            rooms={
                "spawn": MapRoom(id="spawn", name="Spawn", coords=Coords(x=0, y=0, z=0)),
                "hall": MapRoom(id="hall", name="Hall", coords=Coords(x=0, y=5, z=0)),
            },
            items={"key": {"id": "key", "name": "Key"}},
        )
        zone = map_file.to_zone()

        assert isinstance(zone, Zone)
        assert zone.id == "test"
        assert zone.metadata.schema_version == map_file.metadata.schema_version
        assert len(zone.rooms) == 2
        assert all(isinstance(r, Room) for r in zone.rooms.values())
        assert zone.items == {"key": {"id": "key", "name": "Key"}}

    def test_bump_revision(self):
        """bump_revision should increment the authoring revision counter."""
        map_file = MapFile(
            id="test",
            name="Test",
            spawn_room="spawn",
            rooms={"spawn": MapRoom(id="spawn", name="Spawn")},
        )
        assert map_file.bump_revision() == 1
        assert map_file.bump_revision() == 2

    def test_bump_version(self):
        """bump_version should increment the authoring milestone version."""
        map_file = MapFile(
            id="test",
            name="Test",
            spawn_room="spawn",
            rooms={"spawn": MapRoom(id="spawn", name="Spawn")},
        )
        assert map_file.metadata.map_version == "0"
        assert map_file.bump_version() == "1"
        assert map_file.bump_version() == "2"

    def test_get_room_at_coords_found(self):
        """get_room_at_coords should find room at exact coordinates."""
        map_file = MapFile(
            id="test",
            name="Test",
            spawn_room="spawn",
            rooms={
                "spawn": MapRoom(id="spawn", name="Spawn", coords=Coords(x=0, y=0, z=0)),
                "hall": MapRoom(id="hall", name="Hall", coords=Coords(x=0, y=5, z=0)),
            },
        )
        room = map_file.get_room_at_coords(Coords(x=0, y=5, z=0))
        assert room is not None
        assert room.id == "hall"

    def test_get_room_at_coords_not_found(self):
        """get_room_at_coords should return None if no room at coords."""
        map_file = MapFile(
            id="test",
            name="Test",
            spawn_room="spawn",
            rooms={"spawn": MapRoom(id="spawn", name="Spawn", coords=Coords(x=0, y=0, z=0))},
        )
        assert map_file.get_room_at_coords(Coords(x=99, y=99, z=99)) is None

    def test_find_room_in_direction_north(self):
        """find_room_in_direction should find room to the north."""
        map_file = MapFile(
            id="test",
            name="Test",
            spawn_room="spawn",
            rooms={
                "spawn": MapRoom(id="spawn", name="Spawn", coords=Coords(x=0, y=0, z=0)),
                "north_room": MapRoom(id="north_room", name="North", coords=Coords(x=0, y=5, z=0)),
            },
        )
        room = map_file.find_room_in_direction(Coords(x=0, y=0, z=0), "north", exclude_room="spawn")
        assert room is not None
        assert room.id == "north_room"

    def test_find_room_in_direction_finds_nearest(self):
        """find_room_in_direction should return the nearest room."""
        map_file = MapFile(
            id="test",
            name="Test",
            spawn_room="spawn",
            rooms={
                "spawn": MapRoom(id="spawn", name="Spawn", coords=Coords(x=0, y=0, z=0)),
                "near": MapRoom(id="near", name="Near", coords=Coords(x=0, y=3, z=0)),
                "far": MapRoom(id="far", name="Far", coords=Coords(x=0, y=10, z=0)),
            },
        )
        room = map_file.find_room_in_direction(Coords(x=0, y=0, z=0), "north", exclude_room="spawn")
        assert room is not None
        assert room.id == "near"

    def test_find_room_in_direction_not_found(self):
        """find_room_in_direction should return None if no room in that direction."""
        map_file = MapFile(
            id="test",
            name="Test",
            spawn_room="spawn",
            rooms={
                "spawn": MapRoom(id="spawn", name="Spawn", coords=Coords(x=0, y=0, z=0)),
                "east_room": MapRoom(id="east_room", name="East", coords=Coords(x=5, y=0, z=0)),
            },
        )
        # Looking north, but only room is east
        room = map_file.find_room_in_direction(Coords(x=0, y=0, z=0), "north", exclude_room="spawn")
        assert room is None

    def test_find_room_in_direction_vertical(self):
        """find_room_in_direction should work for up/down."""
        map_file = MapFile(
            id="test",
            name="Test",
            spawn_room="spawn",
            rooms={
                "spawn": MapRoom(id="spawn", name="Spawn", coords=Coords(x=0, y=0, z=0)),
                "basement": MapRoom(id="basement", name="Basement", coords=Coords(x=0, y=0, z=-1)),
            },
        )
        room = map_file.find_room_in_direction(Coords(x=0, y=0, z=0), "down", exclude_room="spawn")
        assert room is not None
        assert room.id == "basement"

    def test_add_room(self):
        """add_room should create and add a new room."""
        map_file = MapFile(
            id="test",
            name="Test",
            spawn_room="spawn",
            rooms={"spawn": MapRoom(id="spawn", name="Spawn")},
        )
        room = map_file.add_room(
            room_id="new_room",
            name="New Room",
            coords=Coords(x=5, y=0, z=0),
            description="A new room.",
        )
        assert room.id == "new_room"
        assert "new_room" in map_file.rooms
        assert map_file.rooms["new_room"].coords.x == 5

    def test_add_room_duplicate_raises(self):
        """add_room should raise if room ID already exists."""
        map_file = MapFile(
            id="test",
            name="Test",
            spawn_room="spawn",
            rooms={"spawn": MapRoom(id="spawn", name="Spawn")},
        )
        with pytest.raises(ValueError, match="already exists"):
            map_file.add_room("spawn", "Duplicate", Coords())

    def test_create_exit_bidirectional(self):
        """create_exit with bidirectional=True should create both exits."""
        map_file = MapFile(
            id="test",
            name="Test",
            spawn_room="spawn",
            rooms={
                "spawn": MapRoom(id="spawn", name="Spawn"),
                "hall": MapRoom(id="hall", name="Hall"),
            },
        )
        map_file.create_exit("spawn", "north", "hall", bidirectional=True)

        assert map_file.rooms["spawn"].exits["north"] == "hall"
        assert map_file.rooms["hall"].exits["south"] == "spawn"

    def test_create_exit_unidirectional(self):
        """create_exit with bidirectional=False should create only one exit."""
        map_file = MapFile(
            id="test",
            name="Test",
            spawn_room="spawn",
            rooms={
                "spawn": MapRoom(id="spawn", name="Spawn"),
                "hall": MapRoom(id="hall", name="Hall"),
            },
        )
        map_file.create_exit("spawn", "north", "hall", bidirectional=False)

        assert map_file.rooms["spawn"].exits["north"] == "hall"
        assert "south" not in map_file.rooms["hall"].exits

    def test_create_exit_invalid_source(self):
        """create_exit should raise if source room doesn't exist."""
        map_file = MapFile(
            id="test",
            name="Test",
            spawn_room="spawn",
            rooms={"spawn": MapRoom(id="spawn", name="Spawn")},
        )
        with pytest.raises(ValueError, match="Source room"):
            map_file.create_exit("nonexistent", "north", "spawn")

    def test_create_exit_invalid_target(self):
        """create_exit should raise if target room doesn't exist."""
        map_file = MapFile(
            id="test",
            name="Test",
            spawn_room="spawn",
            rooms={"spawn": MapRoom(id="spawn", name="Spawn")},
        )
        with pytest.raises(ValueError, match="Target room"):
            map_file.create_exit("spawn", "north", "nonexistent")

    def test_remove_exit_bidirectional(self):
        """remove_exit with bidirectional=True should remove both exits."""
        map_file = MapFile(
            id="test",
            name="Test",
            spawn_room="spawn",
            rooms={
                "spawn": MapRoom(id="spawn", name="Spawn", exits={"north": "hall"}),
                "hall": MapRoom(id="hall", name="Hall", exits={"south": "spawn"}),
            },
        )
        map_file.remove_exit("spawn", "north", bidirectional=True)

        assert "north" not in map_file.rooms["spawn"].exits
        assert "south" not in map_file.rooms["hall"].exits

    def test_remove_exit_unidirectional(self):
        """remove_exit with bidirectional=False should only remove one exit."""
        map_file = MapFile(
            id="test",
            name="Test",
            spawn_room="spawn",
            rooms={
                "spawn": MapRoom(id="spawn", name="Spawn", exits={"north": "hall"}),
                "hall": MapRoom(id="hall", name="Hall", exits={"south": "spawn"}),
            },
        )
        map_file.remove_exit("spawn", "north", bidirectional=False)

        assert "north" not in map_file.rooms["spawn"].exits
        assert map_file.rooms["hall"].exits["south"] == "spawn"  # Still exists

    def test_from_dict_legacy_format(self):
        """from_dict should handle legacy format with list coords."""
        data = {
            "id": "test",
            "name": "Test Zone",
            "description": "",
            "spawn_room": "spawn",
            "rooms": {
                "spawn": {
                    "id": "spawn",
                    "name": "Spawn",
                    "description": "",
                    "coords": [0, 0, 0],
                    "exits": {"north": "hall"},
                    "items": [],
                },
                "hall": {
                    "id": "hall",
                    "name": "Hall",
                    "description": "",
                    "coords": [0, 5, 0],
                    "exits": {"south": "spawn"},
                    "items": [],
                },
            },
            "items": {},
        }
        map_file = MapFile.from_dict(data)

        assert map_file.id == "test"
        assert map_file.rooms["spawn"].coords.x == 0
        assert map_file.rooms["hall"].coords.y == 5

    def test_to_dict_with_list_coords(self):
        """to_dict_with_list_coords should export coords as lists."""
        map_file = MapFile(
            id="test",
            name="Test",
            spawn_room="spawn",
            rooms={
                "spawn": MapRoom(id="spawn", name="Spawn", coords=Coords(x=1, y=2, z=3)),
            },
        )
        data = map_file.to_dict_with_list_coords()

        assert data["rooms"]["spawn"]["coords"] == [1, 2, 3]


# =============================================================================
# Integration Tests
# =============================================================================


class TestTwoFileWorkflow:
    """Integration tests for the two-file workflow."""

    def test_full_workflow(self):
        """Test complete workflow: create map, edit, export zone."""
        # 1. Create new map file
        map_file = MapFile(
            id="tutorial",
            name="Tutorial Area",
            description="A small tutorial zone.",
            spawn_room="spawn",
            rooms={
                "spawn": MapRoom(
                    id="spawn",
                    name="Arrival Chamber",
                    description="You find yourself in a dimly lit chamber.",
                    coords=Coords(x=0, y=0, z=0),
                ),
            },
        )

        # 2. Add more rooms
        map_file.add_room(
            room_id="hallway",
            name="Long Hallway",
            coords=Coords(x=0, y=5, z=0),
            description="A narrow hallway stretches before you.",
        )

        # 3. Create bidirectional exit
        map_file.create_exit("spawn", "north", "hallway")

        # 4. Verify map state
        assert len(map_file.rooms) == 2
        assert map_file.rooms["spawn"].exits["north"] == "hallway"
        assert map_file.rooms["hallway"].exits["south"] == "spawn"

        # 5. Export to zone (strips coordinates)
        zone = map_file.to_zone()

        # 6. Verify zone
        assert isinstance(zone, Zone)
        assert len(zone.rooms) == 2
        assert zone.rooms["spawn"].exits["north"] == "hallway"

        # Verify coords are stripped
        spawn_room = zone.rooms["spawn"]
        assert "coords" not in spawn_room.model_fields_set

        # 7. Validate zone
        assert zone.validate_exits() == []
        assert zone.find_unreachable_rooms() == []

    def test_round_trip_serialization(self):
        """Test that map files survive JSON serialization."""
        original = MapFile(
            id="test",
            name="Test",
            spawn_room="spawn",
            rooms={
                "spawn": MapRoom(
                    id="spawn",
                    name="Spawn",
                    coords=Coords(x=0, y=0, z=0),
                    exits={"north": "hall"},
                ),
                "hall": MapRoom(
                    id="hall",
                    name="Hall",
                    coords=Coords(x=0, y=5, z=0),
                    exits={"south": "spawn"},
                ),
            },
        )

        # Serialize to dict with list coords (legacy format)
        data = original.to_dict_with_list_coords()

        # Deserialize back
        restored = MapFile.from_dict(data)

        # Verify equality
        assert restored.id == original.id
        assert restored.rooms["spawn"].coords.to_tuple() == (0, 0, 0)
        assert restored.rooms["hall"].coords.to_tuple() == (0, 5, 0)
        assert restored.rooms["spawn"].exits == original.rooms["spawn"].exits
