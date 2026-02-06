"""Comprehensive tests for PipeWorks MUD Mapper service layer.

This module tests the service layer that provides business logic for the
mapper application. Services are framework-agnostic and can be tested
without Dash.

Test Organization
-----------------
Tests are grouped by service module:

- **TestZoneService**: File I/O operations (load, save, export)
- **TestValidationService**: Map validation checks

Each test class covers:
- Happy path scenarios
- Edge cases
- Error conditions
- Integration with models

See Also
--------
- ``services/zone_service.py``: File I/O service
- ``services/validation_service.py``: Validation service
"""

import json
import tempfile
from datetime import UTC
from pathlib import Path

import pytest

from pipeworks_mud_mapper.models import Coords, MapFile, MapRoom
from pipeworks_mud_mapper.services import (
    ValidationWarning,
    create_new_map_file,
    export_zone,
    list_map_files,
    list_zone_files,
    load_map_file,
    save_map_file,
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
        assert loaded.metadata.map_revision == 1

    def test_save_map_file_bumps_revision(self, simple_map_file, temp_dir):
        """save_map_file should increment map_revision by default."""
        path = temp_dir / "test.map.json"
        assert simple_map_file.metadata.map_revision == 0

        save_map_file(simple_map_file, path)
        assert simple_map_file.metadata.map_revision == 1

    def test_save_creates_parent_directories(self, simple_map_file, temp_dir):
        """save_map_file should create parent directories if needed."""
        path = temp_dir / "deep" / "nested" / "path" / "test.map.json"

        save_map_file(simple_map_file, path)
        assert path.exists()

    def test_list_map_files_filters_extension(self, temp_dir):
        """list_map_files should return only *.map.json files."""
        maps_dir = temp_dir / "maps"
        maps_dir.mkdir(parents=True, exist_ok=True)
        (maps_dir / "alpha.map.json").write_text("{}")
        (maps_dir / "beta.map.json").write_text("{}")
        (maps_dir / "ignore.json").write_text("{}")

        results = list_map_files(maps_dir)
        names = [p.name for p in results]

        assert "alpha.map.json" in names
        assert "beta.map.json" in names
        assert "ignore.json" not in names

    def test_list_zone_files_filters_extension(self, temp_dir):
        """list_zone_files should return only *.json files."""
        zones_dir = temp_dir / "zones"
        zones_dir.mkdir(parents=True, exist_ok=True)
        (zones_dir / "alpha.json").write_text("{}")
        (zones_dir / "beta.json").write_text("{}")
        (zones_dir / "ignore.map.json").write_text("{}")

        results = list_zone_files(zones_dir)
        names = [p.name for p in results]

        assert "alpha.json" in names
        assert "beta.json" in names
        assert "ignore.map.json" not in names

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

    def test_export_zone_adds_metadata(self, simple_map_file, temp_dir):
        """export_zone should include schema_version and exported_from metadata."""
        simple_map_file.metadata.map_version = "3"
        simple_map_file.metadata.map_revision = 7

        zone_path = temp_dir / "test.json"
        export_zone(simple_map_file, zone_path)

        content = json.loads(zone_path.read_text())
        assert content["metadata"]["schema_version"] == "0.1.0"
        exported_from = content["metadata"]["exported_from"]
        assert exported_from["map_id"] == simple_map_file.id
        assert exported_from["map_version"] == "3"
        assert exported_from["map_revision"] == 7
        assert exported_from["exporter"].startswith("pipeworks_mud_mapper")

    def test_export_zone_strips_llm_generation(self, simple_map_file, temp_dir):
        """export_zone should strip llm_generation metadata.

        LLM generation metadata (model, seed, prompts, etc.) is authoring
        scaffolding that supports map creation but shouldn't be included
        in the game truth file consumed by the MUD server.

        This follows the same pattern as coordinates - useful for authoring,
        but not part of the final game state.
        """
        from datetime import datetime

        from pipeworks_mud_mapper.models import OllamaGenerationInfo

        # Add llm_generation metadata to the spawn room
        gen_info = OllamaGenerationInfo(
            model="gemma2:2b",
            actual_seed=12345,
            template_id="ledgerfall_goblin",
            temperature=0.7,
            top_k=40,
            top_p=0.9,
            num_ctx=4096,
            num_predict=512,
            system_prompt="You are a creative writer...",
            user_prompt="Describe a quiet alley",
            generated_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        )
        simple_map_file.rooms["spawn"].llm_generation = gen_info

        # Verify llm_generation is set before export
        assert simple_map_file.rooms["spawn"].llm_generation is not None

        # Export to zone file
        zone_path = temp_dir / "zones" / "test.json"
        export_zone(simple_map_file, zone_path)
        assert zone_path.exists()

        # Read raw JSON to verify no llm_generation
        content = json.loads(zone_path.read_text())
        for room_data in content["rooms"].values():
            assert (
                "llm_generation" not in room_data
            ), "llm_generation should be stripped from zone export"

    def test_export_zone_strips_description_validation(self, simple_map_file, temp_dir):
        """export_zone should strip description_validation metadata."""
        from pipeworks_mud_mapper.models import DescriptionValidationInfo

        simple_map_file.rooms["spawn"].description_validation = DescriptionValidationInfo(
            valid=True,
            hard_failures=[],
            soft_failures=[],
            metrics={"word_count": 42, "target_words": 50},
            rule_hits={},
        )

        zone_path = temp_dir / "zones" / "test.json"
        export_zone(simple_map_file, zone_path)
        content = json.loads(zone_path.read_text())

        for room_data in content["rooms"].values():
            assert (
                "description_validation" not in room_data
            ), "description_validation should be stripped from zone export"

    def test_export_zone_strips_both_coords_and_llm_generation(self, simple_map_file, temp_dir):
        """export_zone should strip both coords and llm_generation.

        Both fields are authoring scaffolding that should be removed
        when exporting to the game truth format.
        """
        from datetime import datetime

        from pipeworks_mud_mapper.models import OllamaGenerationInfo

        # Add llm_generation to the room
        gen_info = OllamaGenerationInfo(
            model="llama3:8b",
            actual_seed=99999,
            template_id="ledgerfall_goblin",
            temperature=0.5,
            top_k=30,
            top_p=0.8,
            num_ctx=2048,
            num_predict=256,
            system_prompt="Custom prompt",
            user_prompt="Describe this room",
            generated_at=datetime.now(UTC),
        )
        simple_map_file.rooms["spawn"].llm_generation = gen_info

        # Verify both are set before export
        assert simple_map_file.rooms["spawn"].coords is not None
        assert simple_map_file.rooms["spawn"].llm_generation is not None

        # Export to zone file
        zone_path = temp_dir / "test.json"
        export_zone(simple_map_file, zone_path)

        # Read raw JSON
        content = json.loads(zone_path.read_text())
        spawn_data = content["rooms"]["spawn"]

        # Both should be stripped
        assert "coords" not in spawn_data
        assert "llm_generation" not in spawn_data

        # But other fields should be preserved
        assert spawn_data["id"] == "spawn"
        assert spawn_data["name"] == "Spawn Room"

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

    def test_create_validation_report_structure(self, simple_map_file):
        """create_validation_report should return correct structure."""
        from pipeworks_mud_mapper.services.validation_service import (
            create_validation_report,
        )

        warnings = validate_all(simple_map_file)
        report = create_validation_report("test.map.json", warnings)

        # Check structure
        assert "timestamp" in report
        assert "map_file" in report
        assert "summary" in report
        assert "warnings" in report

        # Check summary structure
        assert "errors" in report["summary"]
        assert "warnings" in report["summary"]
        assert "info" in report["summary"]
        assert "total" in report["summary"]
        assert "passed" in report["summary"]

        # Check map file name
        assert report["map_file"] == "test.map.json"

    def test_create_validation_report_counts(self):
        """create_validation_report should count warnings correctly."""
        from pipeworks_mud_mapper.services.validation_service import (
            create_validation_report,
        )

        warnings = [
            ValidationWarning(Severity.ERROR, "test", "room", "Error 1"),
            ValidationWarning(Severity.ERROR, "test", "room", "Error 2"),
            ValidationWarning(Severity.WARNING, "test", "room", "Warning"),
            ValidationWarning(Severity.INFO, "test", "room", "Info"),
        ]
        report = create_validation_report("test.map.json", warnings)

        assert report["summary"]["errors"] == 2
        assert report["summary"]["warnings"] == 1
        assert report["summary"]["info"] == 1
        assert report["summary"]["total"] == 4
        assert report["summary"]["passed"] is False  # Has errors

    def test_create_validation_report_passed(self):
        """create_validation_report should mark passed when no errors."""
        from pipeworks_mud_mapper.services.validation_service import (
            create_validation_report,
        )

        warnings = [
            ValidationWarning(Severity.WARNING, "test", "room", "Warning"),
            ValidationWarning(Severity.INFO, "test", "room", "Info"),
        ]
        report = create_validation_report("test.map.json", warnings)

        assert report["summary"]["passed"] is True  # No errors

    def test_write_validation_report(self, simple_map_file, temp_dir):
        """write_validation_report should write report to file."""
        from pipeworks_mud_mapper.services.validation_service import (
            write_validation_report,
        )

        warnings = validate_all(simple_map_file)
        output_path = write_validation_report(
            "test.map.json",
            warnings,
            output_dir=str(temp_dir / "validation"),
        )

        # Check file was written
        import json
        from pathlib import Path

        path = Path(output_path)
        assert path.exists()
        assert path.name == "test.validation.json"

        # Check contents
        with open(path) as f:
            report = json.load(f)

        assert report["map_file"] == "test.map.json"
        assert "summary" in report

    def test_write_validation_report_creates_directory(self, simple_map_file, temp_dir):
        """write_validation_report should create output directory if needed."""
        from pipeworks_mud_mapper.services.validation_service import (
            write_validation_report,
        )

        output_dir = temp_dir / "new_validation_dir"
        assert not output_dir.exists()

        write_validation_report(
            "test.map.json",
            [],
            output_dir=str(output_dir),
        )

        assert output_dir.exists()

    def test_write_validation_report_filename_extraction(self, temp_dir):
        """write_validation_report should extract base name correctly."""
        from pathlib import Path

        from pipeworks_mud_mapper.services.validation_service import (
            write_validation_report,
        )

        # Test with .map.json extension
        path1 = write_validation_report(
            "my_zone.map.json",
            [],
            output_dir=str(temp_dir),
        )
        assert Path(path1).name == "my_zone.validation.json"

        # Test with .json extension
        path2 = write_validation_report(
            "other_zone.json",
            [],
            output_dir=str(temp_dir),
        )
        assert Path(path2).name == "other_zone.validation.json"


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
        map_file.rooms["hallway"] = MapRoom(
            id="hallway",
            name="Dark Hallway",
            coords=Coords(x=0, y=5, z=0),
            exits={},
        )
        map_file.rooms["treasury"] = MapRoom(
            id="treasury",
            name="Treasury",
            coords=Coords(x=5, y=5, z=0),
            exits={},
        )
        map_file.rooms["cellar"] = MapRoom(
            id="cellar",
            name="Cellar",
            coords=Coords(x=0, y=0, z=-1),
            exits={},
        )

        # 3. Create exits
        map_file.rooms["spawn"].exits["north"] = "hallway"
        map_file.rooms["hallway"].exits["south"] = "spawn"
        map_file.rooms["hallway"].exits["east"] = "treasury"
        map_file.rooms["treasury"].exits["west"] = "hallway"
        map_file.rooms["spawn"].exits["down"] = "cellar"
        map_file.rooms["cellar"].exits["up"] = "spawn"

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
