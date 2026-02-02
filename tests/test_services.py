"""Comprehensive tests for PipeWorks MUD Mapper service layer.

This module tests the service layer that provides business logic for the
mapper application. Services are framework-agnostic and can be tested
without Dash.

Test Organization
-----------------
Tests are grouped by service module:

- **TestZoneService**: File I/O operations (load, save, export)
- **TestRoomService**: Room CRUD and exit management
- **TestValidationService**: Map validation checks

Each test class covers:
- Happy path scenarios
- Edge cases
- Error conditions
- Integration with models

See Also
--------
- ``services/zone_service.py``: File I/O service
- ``services/room_service.py``: Room CRUD service
- ``services/validation_service.py``: Validation service
"""

import json
import tempfile
from pathlib import Path

import pytest

from pipeworks_mud_mapper.models import Coords, MapFile, MapRoom
from pipeworks_mud_mapper.services import (
    ValidationWarning,
    create_exit,
    create_new_map_file,
    create_room,
    delete_room,
    export_zone,
    find_room_in_direction,
    load_map_file,
    remove_exit,
    save_map_file,
    update_room,
    validate_all,
    validate_connectivity,
    validate_exit_consistency,
    validate_language_direction,
)
from pipeworks_mud_mapper.services.validation_service import (
    Severity,
    filter_by_category,
    filter_by_severity,
    has_errors,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def simple_map_file() -> MapFile:
    """Create a simple map file for testing."""
    return MapFile(
        id="test_zone",
        name="Test Zone",
        spawn_room="spawn",
        rooms={
            "spawn": MapRoom(
                id="spawn",
                name="Spawn Room",
                coords=Coords(x=0, y=0, z=0),
            ),
        },
    )


@pytest.fixture
def connected_map_file() -> MapFile:
    """Create a map file with connected rooms."""
    return MapFile(
        id="test_zone",
        name="Test Zone",
        spawn_room="spawn",
        rooms={
            "spawn": MapRoom(
                id="spawn",
                name="Spawn Room",
                coords=Coords(x=0, y=0, z=0),
                exits={"north": "hallway"},
            ),
            "hallway": MapRoom(
                id="hallway",
                name="Hallway",
                coords=Coords(x=0, y=5, z=0),
                exits={"south": "spawn", "east": "treasury"},
            ),
            "treasury": MapRoom(
                id="treasury",
                name="Treasury",
                coords=Coords(x=5, y=5, z=0),
                exits={"west": "hallway"},
            ),
        },
    )


@pytest.fixture
def temp_dir():
    """Create a temporary directory for file tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# =============================================================================
# Zone Service Tests
# =============================================================================


class TestZoneService:
    """Tests for zone_service module."""

    def test_create_new_map_file(self):
        """create_new_map_file should create a map with spawn room at origin."""
        map_file = create_new_map_file(
            zone_id="tutorial",
            name="Tutorial Area",
            spawn_room_name="Starting Chamber",
        )

        assert map_file.id == "tutorial"
        assert map_file.name == "Tutorial Area"
        assert map_file.spawn_room == "spawn"
        assert "spawn" in map_file.rooms
        assert map_file.rooms["spawn"].name == "Starting Chamber"
        assert map_file.rooms["spawn"].coords == Coords(x=0, y=0, z=0)

    def test_create_new_map_file_with_description(self):
        """create_new_map_file should accept description."""
        map_file = create_new_map_file(
            zone_id="dungeon",
            name="Dark Dungeon",
            description="A spooky dungeon.",
        )

        assert map_file.description == "A spooky dungeon."

    def test_save_and_load_map_file(self, simple_map_file, temp_dir):
        """save_map_file and load_map_file should round-trip correctly."""
        path = temp_dir / "test.map.json"

        # Save
        save_map_file(simple_map_file, path)
        assert path.exists()

        # Load
        loaded = load_map_file(path)
        assert loaded.id == simple_map_file.id
        assert loaded.name == simple_map_file.name
        assert "spawn" in loaded.rooms
        assert loaded.rooms["spawn"].coords == Coords(x=0, y=0, z=0)

    def test_save_creates_parent_directories(self, simple_map_file, temp_dir):
        """save_map_file should create parent directories if needed."""
        path = temp_dir / "deep" / "nested" / "path" / "test.map.json"

        save_map_file(simple_map_file, path)
        assert path.exists()

    def test_load_map_file_preserves_exits(self, connected_map_file, temp_dir):
        """load_map_file should preserve room exits."""
        path = temp_dir / "connected.map.json"
        save_map_file(connected_map_file, path)

        loaded = load_map_file(path)
        assert loaded.rooms["spawn"].exits["north"] == "hallway"
        assert loaded.rooms["hallway"].exits["south"] == "spawn"

    def test_export_zone_strips_coords(self, connected_map_file, temp_dir):
        """export_zone should create a zone file without coordinates."""
        zone_path = temp_dir / "zones" / "test.json"

        export_zone(connected_map_file, zone_path)
        assert zone_path.exists()

        # Read raw JSON to verify no coords
        content = json.loads(zone_path.read_text())
        for room_data in content["rooms"].values():
            assert "coords" not in room_data

    def test_export_zone_preserves_exits(self, connected_map_file, temp_dir):
        """export_zone should preserve room exits."""
        zone_path = temp_dir / "test.json"
        export_zone(connected_map_file, zone_path)

        content = json.loads(zone_path.read_text())
        assert content["rooms"]["spawn"]["exits"]["north"] == "hallway"

    def test_load_zone_file_adds_default_coords(self, temp_dir):
        """load_map_file on a zone file should add default coords."""
        # Create a zone file (no coords)
        zone_data = {
            "id": "test",
            "name": "Test",
            "spawn_room": "spawn",
            "rooms": {
                "spawn": {
                    "id": "spawn",
                    "name": "Spawn",
                    "exits": {},
                    "items": [],
                }
            },
            "items": {},
        }
        zone_path = temp_dir / "zone.json"
        zone_path.write_text(json.dumps(zone_data))

        # Load as map file
        map_file = load_map_file(zone_path)
        assert map_file.rooms["spawn"].coords == Coords(x=0, y=0, z=0)


# =============================================================================
# Room Service Tests
# =============================================================================


class TestRoomService:
    """Tests for room_service module."""

    def test_create_room(self, simple_map_file):
        """create_room should add a new room."""
        room = create_room(
            simple_map_file,
            room_id="hallway",
            name="Hallway",
            coords=Coords(x=0, y=5, z=0),
            description="A long hallway.",
        )

        assert room.id == "hallway"
        assert "hallway" in simple_map_file.rooms
        assert simple_map_file.rooms["hallway"].coords.y == 5

    def test_create_room_duplicate_raises(self, simple_map_file):
        """create_room with existing ID should raise."""
        with pytest.raises(ValueError, match="already exists"):
            create_room(simple_map_file, "spawn", "Duplicate", Coords())

    def test_update_room_name(self, simple_map_file):
        """update_room should update room name."""
        update_room(simple_map_file, "spawn", name="Grand Entrance")
        assert simple_map_file.rooms["spawn"].name == "Grand Entrance"

    def test_update_room_description(self, simple_map_file):
        """update_room should update room description."""
        update_room(simple_map_file, "spawn", description="A dark room.")
        assert simple_map_file.rooms["spawn"].description == "A dark room."

    def test_update_room_coords(self, simple_map_file):
        """update_room should update room coordinates."""
        update_room(simple_map_file, "spawn", coords=Coords(x=10, y=20, z=30))
        assert simple_map_file.rooms["spawn"].coords == Coords(x=10, y=20, z=30)

    def test_update_room_nonexistent_raises(self, simple_map_file):
        """update_room on nonexistent room should raise."""
        with pytest.raises(ValueError, match="does not exist"):
            update_room(simple_map_file, "nonexistent", name="New Name")

    def test_delete_room(self, connected_map_file):
        """delete_room should remove a room."""
        delete_room(connected_map_file, "treasury")
        assert "treasury" not in connected_map_file.rooms

    def test_delete_room_removes_exits(self, connected_map_file):
        """delete_room should remove exits pointing to the deleted room."""
        delete_room(connected_map_file, "treasury")
        assert "east" not in connected_map_file.rooms["hallway"].exits

    def test_delete_room_keeps_exits_if_requested(self, connected_map_file):
        """delete_room with remove_exits=False should keep dangling exits."""
        delete_room(connected_map_file, "treasury", remove_exits=False)
        # Exit still exists but points to deleted room
        assert connected_map_file.rooms["hallway"].exits.get("east") == "treasury"

    def test_delete_spawn_room_raises(self, simple_map_file):
        """delete_room on spawn room should raise."""
        with pytest.raises(ValueError, match="Cannot delete spawn room"):
            delete_room(simple_map_file, "spawn")

    def test_delete_nonexistent_room_raises(self, simple_map_file):
        """delete_room on nonexistent room should raise."""
        with pytest.raises(ValueError, match="does not exist"):
            delete_room(simple_map_file, "nonexistent")

    def test_create_exit_bidirectional(self, simple_map_file):
        """create_exit should create bidirectional exits by default."""
        create_room(simple_map_file, "hallway", "Hallway", Coords(x=0, y=5, z=0))
        create_exit(simple_map_file, "spawn", "north", "hallway")

        assert simple_map_file.rooms["spawn"].exits["north"] == "hallway"
        assert simple_map_file.rooms["hallway"].exits["south"] == "spawn"

    def test_create_exit_unidirectional(self, simple_map_file):
        """create_exit with bidirectional=False should create one-way exit."""
        create_room(simple_map_file, "pit", "Pit", Coords(x=0, y=0, z=-1))
        create_exit(simple_map_file, "spawn", "down", "pit", bidirectional=False)

        assert simple_map_file.rooms["spawn"].exits["down"] == "pit"
        assert "up" not in simple_map_file.rooms["pit"].exits

    def test_remove_exit_bidirectional(self, connected_map_file):
        """remove_exit should remove both directions by default."""
        remove_exit(connected_map_file, "spawn", "north")

        assert "north" not in connected_map_file.rooms["spawn"].exits
        assert "south" not in connected_map_file.rooms["hallway"].exits

    def test_remove_exit_unidirectional(self, connected_map_file):
        """remove_exit with bidirectional=False should remove one direction."""
        remove_exit(connected_map_file, "spawn", "north", bidirectional=False)

        assert "north" not in connected_map_file.rooms["spawn"].exits
        assert connected_map_file.rooms["hallway"].exits["south"] == "spawn"

    def test_find_room_in_direction(self, connected_map_file):
        """find_room_in_direction should find the nearest room."""
        room = find_room_in_direction(
            connected_map_file,
            Coords(x=0, y=0, z=0),
            "north",
            exclude_room="spawn",
        )
        assert room is not None
        assert room.id == "hallway"

    def test_find_room_in_direction_not_found(self, simple_map_file):
        """find_room_in_direction should return None if no room found."""
        room = find_room_in_direction(
            simple_map_file,
            Coords(x=0, y=0, z=0),
            "north",
            exclude_room="spawn",
        )
        assert room is None


# =============================================================================
# Validation Service Tests
# =============================================================================


class TestValidationService:
    """Tests for validation_service module."""

    def test_validate_all_clean_map(self, connected_map_file):
        """validate_all on a well-formed map should return minimal warnings."""
        warnings = validate_all(connected_map_file)
        # Treasury is a dead end, so we expect an INFO warning
        assert all(w.severity != Severity.ERROR for w in warnings)

    def test_validate_connectivity_broken_exit(self, simple_map_file):
        """validate_connectivity should detect broken exit references."""
        simple_map_file.rooms["spawn"].exits["north"] = "nonexistent"

        warnings = validate_connectivity(simple_map_file)
        errors = [w for w in warnings if w.severity == Severity.ERROR]

        assert len(errors) == 1
        assert "nonexistent" in errors[0].message

    def test_validate_connectivity_unreachable_room(self, simple_map_file):
        """validate_connectivity should detect unreachable rooms."""
        # Add an orphan room with no connections
        simple_map_file.rooms["orphan"] = MapRoom(
            id="orphan",
            name="Orphan Room",
            coords=Coords(x=100, y=100, z=0),
        )

        warnings = validate_connectivity(simple_map_file)
        unreachable = [w for w in warnings if "unreachable" in w.message.lower()]

        assert len(unreachable) == 1
        assert unreachable[0].room_id == "orphan"

    def test_validate_connectivity_dead_end(self, simple_map_file):
        """validate_connectivity should detect dead-end rooms."""
        warnings = validate_connectivity(simple_map_file)
        dead_ends = [w for w in warnings if "dead end" in w.message.lower()]

        assert len(dead_ends) == 1
        assert dead_ends[0].room_id == "spawn"
        assert dead_ends[0].severity == Severity.INFO

    def test_validate_exit_consistency_asymmetric(self):
        """validate_exit_consistency should detect asymmetric exits."""
        map_file = MapFile(
            id="test",
            name="Test",
            spawn_room="a",
            rooms={
                "a": MapRoom(
                    id="a",
                    name="Room A",
                    coords=Coords(x=0, y=0, z=0),
                    exits={"north": "b"},
                ),
                "b": MapRoom(
                    id="b",
                    name="Room B",
                    coords=Coords(x=0, y=5, z=0),
                    # No south exit back to a
                ),
            },
        )

        warnings = validate_exit_consistency(map_file)
        asymmetric = [w for w in warnings if "asymmetric" in w.message.lower()]

        assert len(asymmetric) == 1

    def test_validate_exit_consistency_direction_mismatch(self):
        """validate_exit_consistency should detect direction/coord mismatches."""
        map_file = MapFile(
            id="test",
            name="Test",
            spawn_room="a",
            rooms={
                "a": MapRoom(
                    id="a",
                    name="Room A",
                    coords=Coords(x=0, y=0, z=0),
                    exits={"north": "b"},  # Says north
                ),
                "b": MapRoom(
                    id="b",
                    name="Room B",
                    coords=Coords(x=0, y=-5, z=0),  # But B is south!
                    exits={"south": "a"},
                ),
            },
        )

        warnings = validate_exit_consistency(map_file)
        mismatches = [w for w in warnings if "direction mismatch" in w.message.lower()]

        assert len(mismatches) == 1
        assert mismatches[0].severity == Severity.WARNING

    def test_validate_language_direction_upper(self):
        """validate_language_direction should flag 'upper' not reached via up."""
        map_file = MapFile(
            id="test",
            name="Test",
            spawn_room="main",
            rooms={
                "main": MapRoom(
                    id="main",
                    name="Main Hall",
                    coords=Coords(x=0, y=0, z=0),
                    exits={"north": "upper"},  # North, not up!
                ),
                "upper": MapRoom(
                    id="upper",
                    name="Upper Landing",  # Has "upper" in name
                    coords=Coords(x=0, y=5, z=0),
                    exits={"south": "main"},
                ),
            },
        )

        warnings = validate_language_direction(map_file)

        assert len(warnings) == 1
        assert "upper" in warnings[0].message.lower()
        assert warnings[0].room_id == "upper"

    def test_validate_language_direction_basement(self):
        """validate_language_direction should flag 'basement' not reached via down."""
        map_file = MapFile(
            id="test",
            name="Test",
            spawn_room="main",
            rooms={
                "main": MapRoom(
                    id="main",
                    name="Main Hall",
                    coords=Coords(x=0, y=0, z=0),
                    exits={"east": "cellar"},  # East, not down!
                ),
                "cellar": MapRoom(
                    id="cellar",
                    name="The Basement",  # Has "basement" in name
                    coords=Coords(x=5, y=0, z=0),
                    exits={"west": "main"},
                ),
            },
        )

        warnings = validate_language_direction(map_file)

        assert len(warnings) == 1
        assert "basement" in warnings[0].message.lower()

    def test_validate_language_direction_correct_usage(self):
        """validate_language_direction should not flag correct vertical naming."""
        map_file = MapFile(
            id="test",
            name="Test",
            spawn_room="main",
            rooms={
                "main": MapRoom(
                    id="main",
                    name="Main Hall",
                    coords=Coords(x=0, y=0, z=0),
                    exits={"up": "attic"},
                ),
                "attic": MapRoom(
                    id="attic",
                    name="Dusty Attic",  # Has "attic" - vertical word
                    coords=Coords(x=0, y=0, z=1),
                    exits={"down": "main"},
                ),
            },
        )

        warnings = validate_language_direction(map_file)

        # Should be empty - attic IS reached via up
        assert len(warnings) == 0

    def test_has_errors(self):
        """has_errors should return True if any warning is an error."""
        warnings = [
            ValidationWarning(Severity.INFO, "test", "room", "Info message"),
            ValidationWarning(Severity.ERROR, "test", "room", "Error message"),
        ]
        assert has_errors(warnings) is True

    def test_has_errors_no_errors(self):
        """has_errors should return False if no errors."""
        warnings = [
            ValidationWarning(Severity.INFO, "test", "room", "Info message"),
            ValidationWarning(Severity.WARNING, "test", "room", "Warning message"),
        ]
        assert has_errors(warnings) is False

    def test_filter_by_severity(self):
        """filter_by_severity should return only matching warnings."""
        warnings = [
            ValidationWarning(Severity.INFO, "test", "room", "Info"),
            ValidationWarning(Severity.ERROR, "test", "room", "Error"),
            ValidationWarning(Severity.INFO, "test", "room", "Info 2"),
        ]
        filtered = filter_by_severity(warnings, Severity.INFO)
        assert len(filtered) == 2

    def test_filter_by_category(self):
        """filter_by_category should return only matching warnings."""
        warnings = [
            ValidationWarning(Severity.INFO, "connectivity", "room", "Conn"),
            ValidationWarning(Severity.INFO, "language", "room", "Lang"),
            ValidationWarning(Severity.INFO, "connectivity", "room", "Conn 2"),
        ]
        filtered = filter_by_category(warnings, "connectivity")
        assert len(filtered) == 2


# =============================================================================
# Integration Tests
# =============================================================================


class TestServiceIntegration:
    """Integration tests across multiple services."""

    def test_full_workflow(self, temp_dir):
        """Test complete workflow: create, edit, validate, export."""
        # 1. Create new map
        map_file = create_new_map_file(
            zone_id="tutorial",
            name="Tutorial Dungeon",
            spawn_room_name="Entrance",
        )

        # 2. Add rooms
        create_room(map_file, "hallway", "Dark Hallway", Coords(x=0, y=5, z=0))
        create_room(map_file, "treasury", "Treasury", Coords(x=5, y=5, z=0))
        create_room(map_file, "cellar", "Cellar", Coords(x=0, y=0, z=-1))

        # 3. Create exits
        create_exit(map_file, "spawn", "north", "hallway")
        create_exit(map_file, "hallway", "east", "treasury")
        create_exit(map_file, "spawn", "down", "cellar")

        # 4. Validate
        warnings = validate_all(map_file)
        assert not has_errors(warnings)

        # 5. Save map file
        map_path = temp_dir / "maps" / "tutorial.map.json"
        save_map_file(map_file, map_path)
        assert map_path.exists()

        # 6. Export zone
        zone_path = temp_dir / "zones" / "tutorial.json"
        export_zone(map_file, zone_path)
        assert zone_path.exists()

        # 7. Reload and verify
        reloaded = load_map_file(map_path)
        assert len(reloaded.rooms) == 4
        assert reloaded.rooms["spawn"].exits["north"] == "hallway"

    def test_validation_blocks_bad_export(self, simple_map_file, temp_dir):
        """Validation should catch errors before export."""
        # Create a broken map
        simple_map_file.rooms["spawn"].exits["north"] = "nonexistent"

        # Validate
        warnings = validate_all(simple_map_file)
        assert has_errors(warnings)

        # In real usage, we would block export here
        # (The service doesn't enforce this, but the UI would)
