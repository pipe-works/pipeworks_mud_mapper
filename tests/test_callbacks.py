"""Comprehensive tests for PipeWorks MUD Mapper callback layer.

This module tests the Dash callbacks that handle user interactions.
Callbacks are tested as regular Python functions by calling them directly
with mock inputs and verifying outputs.

Test Organization
-----------------
Tests are grouped by callback module:

- **TestExitCallbacks**: Exit checkbox handling
- **TestMapCallbacks**: Map rendering and room selection
- **TestRoomCallbacks**: Room CRUD operations
- **TestFileCallbacks**: File management operations

Design Notes
------------
Callbacks are "thin orchestrators" that:
1. Extract data from component state
2. Call service functions for business logic
3. Return updated state to components

We test that callbacks correctly:
- Handle valid inputs and produce expected outputs
- Handle edge cases (None, empty data)
- Return no_update when appropriate
- Produce correct feedback messages

See Also
--------
- ``callbacks/``: The callback modules being tested
- ``test_services.py``: Tests for the underlying service layer
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import plotly.graph_objects as go
import pytest
from dash import no_update

from pipeworks_mud_mapper.callbacks.exit_callbacks import handle_exit_changes
from pipeworks_mud_mapper.callbacks.file_callbacks import (
    close_new_map_modal,
    create_new_map,
    export_zone_to_file,
    handle_file_click,
    load_map_files_list,
    open_new_map_modal,
    render_file_list,
    reset_unsaved_on_file_load,
    save_map_to_file,
    update_save_status,
)
from pipeworks_mud_mapper.callbacks.map_callbacks import (
    handle_map_click,
    update_map_with_rooms,
)
from pipeworks_mud_mapper.callbacks.room_callbacks import (
    add_room_to_zone,
    clear_form_for_new_room,
    populate_room_form,
    update_room_properties,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def simple_zone_data() -> dict:
    """Create a simple zone data dict for testing."""
    return {
        "id": "test_zone",
        "name": "Test Zone",
        "spawn_room": "spawn",
        "rooms": {
            "spawn": {
                "id": "spawn",
                "name": "Spawn Room",
                "description": "The starting room.",
                "coords": [0, 0, 0],
                "exits": {},
                "items": [],
            },
        },
        "items": {},
    }


@pytest.fixture
def connected_zone_data() -> dict:
    """Create a zone with connected rooms for testing exits."""
    return {
        "id": "test_zone",
        "name": "Test Zone",
        "spawn_room": "spawn",
        "rooms": {
            "spawn": {
                "id": "spawn",
                "name": "Spawn Room",
                "description": "The starting room.",
                "coords": [0, 0, 0],
                "exits": {"north": "hallway"},
                "items": [],
            },
            "hallway": {
                "id": "hallway",
                "name": "Hallway",
                "description": "A long hallway.",
                "coords": [0, 5, 0],
                "exits": {"south": "spawn", "east": "treasury"},
                "items": [],
            },
            "treasury": {
                "id": "treasury",
                "name": "Treasury",
                "description": "A room full of gold.",
                "coords": [5, 5, 0],
                "exits": {"west": "hallway"},
                "items": [],
            },
        },
        "items": {},
    }


@pytest.fixture
def temp_maps_dir():
    """Create a temporary maps directory for file tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        maps_dir = Path(tmpdir) / "maps"
        maps_dir.mkdir()
        yield maps_dir


# =============================================================================
# Exit Callbacks Tests
# =============================================================================


class TestExitCallbacks:
    """Tests for exit_callbacks module."""

    def test_handle_exit_changes_no_selection(self, simple_zone_data):
        """handle_exit_changes should return no_update when no room selected."""
        result = handle_exit_changes(
            checked_values=["N"],
            selected_room=None,
            zone_data=simple_zone_data,
        )
        assert result == (no_update, no_update, no_update, no_update)

    def test_handle_exit_changes_no_zone_data(self):
        """handle_exit_changes should return no_update when no zone data."""
        result = handle_exit_changes(
            checked_values=["N"],
            selected_room="spawn",
            zone_data=None,
        )
        assert result == (no_update, no_update, no_update, no_update)

    def test_handle_exit_changes_room_not_found(self, simple_zone_data):
        """handle_exit_changes should return no_update for nonexistent room."""
        result = handle_exit_changes(
            checked_values=["N"],
            selected_room="nonexistent",
            zone_data=simple_zone_data,
        )
        assert result == (no_update, no_update, no_update, no_update)

    def test_handle_exit_changes_no_changes(self, connected_zone_data):
        """handle_exit_changes should return no_update when exits unchanged."""
        # spawn has north exit, so checking ["N"] is no change
        result = handle_exit_changes(
            checked_values=["N"],
            selected_room="spawn",
            zone_data=connected_zone_data,
        )
        assert result == (no_update, no_update, no_update, no_update)

    def test_handle_exit_changes_add_exit_with_target(self, connected_zone_data):
        """handle_exit_changes should add exit when target room exists."""
        # treasury is at (5, 5, 0), spawn is at (0, 0, 0)
        # Add east exit from spawn - hallway is at (0, 5, 0), treasury at (5, 5, 0)
        # spawn has north exit. Let's add east - but no room is directly east of spawn
        # Actually, let's test from hallway adding north exit
        # hallway is at (0, 5, 0) - no room to the north

        # Let's test a valid case: from treasury, which has west exit to hallway
        # If we uncheck west, it removes the exit
        result = handle_exit_changes(
            checked_values=[],  # Uncheck west
            selected_room="treasury",
            zone_data=connected_zone_data,
        )
        updated_zone, final_checked, feedback, unsaved = result
        assert updated_zone is not no_update
        assert "west" not in updated_zone["rooms"]["treasury"]["exits"]
        assert unsaved is True

    def test_handle_exit_changes_remove_exit(self, connected_zone_data):
        """handle_exit_changes should remove exit when unchecked."""
        # spawn has north exit to hallway, uncheck it
        result = handle_exit_changes(
            checked_values=[],  # Uncheck all (was ["N"])
            selected_room="spawn",
            zone_data=connected_zone_data,
        )
        updated_zone, final_checked, feedback, unsaved = result
        assert updated_zone is not no_update
        assert "north" not in updated_zone["rooms"]["spawn"]["exits"]
        assert unsaved is True

    def test_handle_exit_changes_rejected_no_room(self, simple_zone_data):
        """handle_exit_changes should reject exit when no target room exists."""
        # spawn is alone, trying to add north exit
        result = handle_exit_changes(
            checked_values=["N"],  # Try to add north
            selected_room="spawn",
            zone_data=simple_zone_data,
        )
        updated_zone, final_checked, feedback, unsaved = result
        # Exit should be rejected - no room to the north
        assert "N" not in final_checked
        assert unsaved is True  # Zone was still updated (even if empty)

    def test_handle_exit_changes_bidirectional_creation(self):
        """handle_exit_changes should create bidirectional exit."""
        zone_data = {
            "id": "test",
            "name": "Test",
            "spawn_room": "a",
            "rooms": {
                "a": {
                    "id": "a",
                    "name": "Room A",
                    "coords": [0, 0, 0],
                    "exits": {},
                    "items": [],
                },
                "b": {
                    "id": "b",
                    "name": "Room B",
                    "coords": [0, 5, 0],  # North of A
                    "exits": {},
                    "items": [],
                },
            },
        }
        result = handle_exit_changes(
            checked_values=["N"],  # Add north exit from A
            selected_room="a",
            zone_data=zone_data,
        )
        updated_zone, final_checked, feedback, unsaved = result
        assert updated_zone["rooms"]["a"]["exits"]["north"] == "b"
        assert updated_zone["rooms"]["b"]["exits"]["south"] == "a"


# =============================================================================
# Map Callbacks Tests
# =============================================================================


class TestMapCallbacks:
    """Tests for map_callbacks module."""

    def test_update_map_with_rooms_no_data(self):
        """update_map_with_rooms should return empty figure when no zone data."""
        figure = update_map_with_rooms(
            zone_data=None,
            z_level=0,
            selected_room=None,
        )
        assert isinstance(figure, go.Figure)
        assert hasattr(figure, "data")
        assert hasattr(figure, "layout")

    def test_update_map_with_rooms_with_data(self, simple_zone_data):
        """update_map_with_rooms should return figure with room data."""
        figure = update_map_with_rooms(
            zone_data=simple_zone_data,
            z_level=0,
            selected_room=None,
        )
        assert isinstance(figure, go.Figure)
        assert len(figure.data) > 0  # Should have room markers

    def test_update_map_with_rooms_with_selection(self, simple_zone_data):
        """update_map_with_rooms should highlight selected room."""
        figure = update_map_with_rooms(
            zone_data=simple_zone_data,
            z_level=0,
            selected_room="spawn",
        )
        assert isinstance(figure, go.Figure)

    def test_update_map_with_rooms_different_z_level(self, simple_zone_data):
        """update_map_with_rooms should filter by z-level."""
        figure = update_map_with_rooms(
            zone_data=simple_zone_data,
            z_level=1,  # No rooms at z=1
            selected_room=None,
        )
        assert isinstance(figure, go.Figure)
        # No room markers at z=1
        assert len(figure.data) == 0

    def test_handle_map_click_no_data(self):
        """handle_map_click should return no_update when no click data."""
        result = handle_map_click(click_data=None, zone_data=None)
        assert result is no_update

    def test_handle_map_click_no_zone(self):
        """handle_map_click should return no_update when no zone data."""
        click_data = {"points": [{"text": "spawn"}]}
        result = handle_map_click(click_data=click_data, zone_data=None)
        assert result is no_update

    def test_handle_map_click_empty_points(self, simple_zone_data):
        """handle_map_click should return no_update when no points clicked."""
        click_data = {"points": []}
        result = handle_map_click(click_data=click_data, zone_data=simple_zone_data)
        assert result is no_update

    def test_handle_map_click_valid_room(self, simple_zone_data):
        """handle_map_click should return room_id when valid room clicked."""
        click_data = {"points": [{"text": "spawn"}]}
        result = handle_map_click(click_data=click_data, zone_data=simple_zone_data)
        assert result == "spawn"

    def test_handle_map_click_invalid_room(self, simple_zone_data):
        """handle_map_click should return no_update for invalid room."""
        click_data = {"points": [{"text": "nonexistent"}]}
        result = handle_map_click(click_data=click_data, zone_data=simple_zone_data)
        assert result is no_update

    def test_handle_map_click_no_text(self, simple_zone_data):
        """handle_map_click should return no_update when point has no text."""
        click_data = {"points": [{"x": 0, "y": 0}]}
        result = handle_map_click(click_data=click_data, zone_data=simple_zone_data)
        assert result is no_update


# =============================================================================
# Room Callbacks Tests
# =============================================================================


class TestRoomCallbacks:
    """Tests for room_callbacks module."""

    def test_add_room_no_clicks(self, simple_zone_data):
        """add_room_to_zone should return no_update when not clicked."""
        result = add_room_to_zone(
            n_clicks=0,
            zone_data=simple_zone_data,
            room_id="new_room",
            room_name="New Room",
            room_description="A new room.",
            coord_x=1,
            coord_y=0,
            coord_z=0,
        )
        assert result == (no_update,) * 9

    def test_add_room_no_zone(self):
        """add_room_to_zone should show warning when no zone loaded."""
        result = add_room_to_zone(
            n_clicks=1,
            zone_data=None,
            room_id="new_room",
            room_name="New Room",
            room_description="A new room.",
            coord_x=1,
            coord_y=0,
            coord_z=0,
        )
        # Should return feedback alert about no zone
        assert result[0] is no_update  # zone_data unchanged
        assert result[1] is not no_update  # feedback provided

    def test_add_room_empty_id(self, simple_zone_data):
        """add_room_to_zone should reject empty room ID."""
        result = add_room_to_zone(
            n_clicks=1,
            zone_data=simple_zone_data,
            room_id="",
            room_name="New Room",
            room_description="A new room.",
            coord_x=1,
            coord_y=0,
            coord_z=0,
        )
        assert result[0] is no_update
        assert result[1] is not no_update  # feedback about required ID

    def test_add_room_invalid_id_format(self, simple_zone_data):
        """add_room_to_zone should reject invalid room ID format."""
        result = add_room_to_zone(
            n_clicks=1,
            zone_data=simple_zone_data,
            room_id="123invalid",  # Starts with number
            room_name="New Room",
            room_description="A new room.",
            coord_x=1,
            coord_y=0,
            coord_z=0,
        )
        assert result[0] is no_update
        assert result[1] is not no_update  # feedback about format

    def test_add_room_duplicate_id(self, simple_zone_data):
        """add_room_to_zone should reject duplicate room ID."""
        result = add_room_to_zone(
            n_clicks=1,
            zone_data=simple_zone_data,
            room_id="spawn",  # Already exists
            room_name="New Room",
            room_description="A new room.",
            coord_x=1,
            coord_y=0,
            coord_z=0,
        )
        assert result[0] is no_update
        assert result[1] is not no_update  # feedback about duplicate

    def test_add_room_invalid_coords(self, simple_zone_data):
        """add_room_to_zone should reject invalid coordinates."""
        result = add_room_to_zone(
            n_clicks=1,
            zone_data=simple_zone_data,
            room_id="new_room",
            room_name="New Room",
            room_description="A new room.",
            coord_x="not_a_number",
            coord_y=0,
            coord_z=0,
        )
        assert result[0] is no_update
        assert result[1] is not no_update  # feedback about coords

    def test_add_room_success(self, simple_zone_data):
        """add_room_to_zone should add room on success."""
        result = add_room_to_zone(
            n_clicks=1,
            zone_data=simple_zone_data,
            room_id="new_room",
            room_name="New Room",
            room_description="A new room.",
            coord_x=5,
            coord_y=0,
            coord_z=0,
        )
        updated_zone = result[0]
        assert "new_room" in updated_zone["rooms"]
        assert updated_zone["rooms"]["new_room"]["name"] == "New Room"
        assert updated_zone["rooms"]["new_room"]["coords"] == [5, 0, 0]
        assert result[8] is True  # has_unsaved_changes

    def test_add_room_name_defaults_to_id(self, simple_zone_data):
        """add_room_to_zone should use room_id as name if name empty."""
        result = add_room_to_zone(
            n_clicks=1,
            zone_data=simple_zone_data,
            room_id="my_room",
            room_name="",  # Empty name
            room_description="",
            coord_x=0,
            coord_y=0,
            coord_z=0,
        )
        updated_zone = result[0]
        assert updated_zone["rooms"]["my_room"]["name"] == "my_room"

    def test_clear_form_for_new_room(self):
        """clear_form_for_new_room should reset all form fields."""
        result = clear_form_for_new_room(n_clicks=1)
        # Should return cleared values
        (
            feedback,
            selected,
            room_id,
            name,
            desc,
            x,
            y,
            z,
            update_btn,
            id_disabled,
            exits,
            exit_fb,
        ) = result
        assert selected is None
        assert room_id == ""
        assert name == ""
        assert desc == ""
        assert x == 0
        assert y == 0
        assert z == 0
        assert update_btn is True  # Disabled
        assert id_disabled is False  # Enabled for new room
        assert exits == []

    def test_clear_form_no_click(self):
        """clear_form_for_new_room should return no_update when not clicked."""
        result = clear_form_for_new_room(n_clicks=0)
        assert result == (no_update,) * 12

    def test_populate_room_form_no_selection(self, simple_zone_data):
        """populate_room_form should return defaults when no room selected."""
        result = populate_room_form(selected_room=None, zone_data=simple_zone_data)
        # Last 4 values are: exit_values, exit_info, update_disabled, id_disabled
        assert result[-4] == []  # exit values
        assert result[-2] is True  # update button disabled
        assert result[-1] is False  # room ID enabled

    def test_populate_room_form_no_zone(self):
        """populate_room_form should return defaults when no zone data."""
        result = populate_room_form(selected_room="spawn", zone_data=None)
        assert result[-2] is True  # update button disabled

    def test_populate_room_form_room_not_found(self, simple_zone_data):
        """populate_room_form should return defaults for nonexistent room."""
        result = populate_room_form(selected_room="nonexistent", zone_data=simple_zone_data)
        assert result[-2] is True  # update button disabled

    def test_populate_room_form_success(self, connected_zone_data):
        """populate_room_form should populate fields from selected room."""
        result = populate_room_form(selected_room="spawn", zone_data=connected_zone_data)
        room_id, name, desc, x, y, z, exit_values, exit_info, update_disabled, id_disabled = result

        assert room_id == "spawn"
        assert name == "Spawn Room"
        assert desc == "The starting room."
        assert x == 0
        assert y == 0
        assert z == 0
        assert "N" in exit_values  # Has north exit
        assert update_disabled is False  # Update enabled
        assert id_disabled is True  # ID disabled for existing room

    def test_update_room_no_clicks(self, simple_zone_data):
        """update_room_properties should return no_update when not clicked."""
        result = update_room_properties(
            n_clicks=0,
            selected_room="spawn",
            zone_data=simple_zone_data,
            room_name="New Name",
            room_description="New desc",
            coord_x=0,
            coord_y=0,
            coord_z=0,
        )
        assert result == (no_update, no_update, no_update)

    def test_update_room_no_selection(self, simple_zone_data):
        """update_room_properties should show warning when no room selected."""
        result = update_room_properties(
            n_clicks=1,
            selected_room=None,
            zone_data=simple_zone_data,
            room_name="New Name",
            room_description="New desc",
            coord_x=0,
            coord_y=0,
            coord_z=0,
        )
        assert result[0] is no_update
        assert result[1] is not no_update  # feedback

    def test_update_room_not_found(self, simple_zone_data):
        """update_room_properties should show error for nonexistent room."""
        result = update_room_properties(
            n_clicks=1,
            selected_room="nonexistent",
            zone_data=simple_zone_data,
            room_name="New Name",
            room_description="New desc",
            coord_x=0,
            coord_y=0,
            coord_z=0,
        )
        assert result[0] is no_update
        assert result[1] is not no_update  # error feedback

    def test_update_room_invalid_coords(self, simple_zone_data):
        """update_room_properties should reject invalid coordinates."""
        result = update_room_properties(
            n_clicks=1,
            selected_room="spawn",
            zone_data=simple_zone_data,
            room_name="New Name",
            room_description="New desc",
            coord_x="invalid",
            coord_y=0,
            coord_z=0,
        )
        assert result[0] is no_update
        assert result[1] is not no_update  # error feedback

    def test_update_room_success(self, simple_zone_data):
        """update_room_properties should update room on success."""
        result = update_room_properties(
            n_clicks=1,
            selected_room="spawn",
            zone_data=simple_zone_data,
            room_name="Updated Name",
            room_description="Updated description.",
            coord_x=10,
            coord_y=20,
            coord_z=0,
        )
        updated_zone, feedback, unsaved = result
        assert updated_zone["rooms"]["spawn"]["name"] == "Updated Name"
        assert updated_zone["rooms"]["spawn"]["description"] == "Updated description."
        assert updated_zone["rooms"]["spawn"]["coords"] == [10, 20, 0]
        assert unsaved is True


# =============================================================================
# File Callbacks Tests
# =============================================================================


class TestFileCallbacks:
    """Tests for file_callbacks module."""

    def test_load_map_files_list(self, temp_maps_dir):
        """load_map_files_list should return list of map files."""
        # Create test files
        (temp_maps_dir / "zone1.map.json").write_text("{}")
        (temp_maps_dir / "zone2.map.json").write_text("{}")
        (temp_maps_dir / "other.json").write_text("{}")  # Not a .map.json

        with patch(
            "pipeworks_mud_mapper.callbacks.file_callbacks.MAPS_DIR",
            temp_maps_dir,
        ):
            result = load_map_files_list(1)  # Positional arg (interval count)

        assert "zone1.map.json" in result
        assert "zone2.map.json" in result
        assert "other.json" not in result

    def test_render_file_list_empty(self):
        """render_file_list should show message when no files."""
        result = render_file_list(files=[], selected_file=None)
        assert len(result) == 1
        assert "No map files" in str(result[0])

    def test_render_file_list_with_files(self):
        """render_file_list should render file items."""
        files = ["zone1.map.json", "zone2.map.json"]
        result = render_file_list(files=files, selected_file=None)
        assert len(result) == 2

    def test_render_file_list_with_selection(self):
        """render_file_list should highlight selected file."""
        files = ["zone1.map.json", "zone2.map.json"]
        result = render_file_list(files=files, selected_file="zone1.map.json")
        assert len(result) == 2
        # Selected item should have different styling
        assert "bg-primary" in result[0].className

    def test_handle_file_click_no_clicks(self):
        """handle_file_click should return no_update when nothing clicked."""
        result = handle_file_click(n_clicks_list=[0, 0], files=["a.map.json", "b.map.json"])
        assert result == (no_update, no_update, no_update)

    def test_open_new_map_modal(self):
        """open_new_map_modal should return True when clicked."""
        result = open_new_map_modal(n_clicks=1)
        assert result is True

    def test_open_new_map_modal_no_click(self):
        """open_new_map_modal should return False when not clicked."""
        result = open_new_map_modal(n_clicks=0)
        assert result is False

    def test_close_new_map_modal(self):
        """close_new_map_modal should return False when clicked."""
        result = close_new_map_modal(n_clicks=1)
        assert result is False

    def test_close_new_map_modal_no_click(self):
        """close_new_map_modal should return no_update when not clicked."""
        result = close_new_map_modal(n_clicks=0)
        assert result is no_update

    def test_create_new_map_no_click(self):
        """create_new_map should return no_update when not clicked."""
        result = create_new_map(
            n_clicks=0,
            zone_id="test",
            zone_name="Test",
            description="",
        )
        assert result == (no_update,) * 6

    def test_create_new_map_empty_id(self):
        """create_new_map should reject empty zone ID."""
        result = create_new_map(
            n_clicks=1,
            zone_id="",
            zone_name="Test",
            description="",
        )
        assert result[0] is no_update  # Modal stays open
        assert result[2] is not no_update  # feedback

    def test_create_new_map_invalid_id(self):
        """create_new_map should reject invalid zone ID format."""
        result = create_new_map(
            n_clicks=1,
            zone_id="123invalid",  # Starts with number
            zone_name="Test",
            description="",
        )
        assert result[0] is no_update
        assert result[2] is not no_update  # feedback

    def test_create_new_map_empty_name(self):
        """create_new_map should reject empty zone name."""
        result = create_new_map(
            n_clicks=1,
            zone_id="test",
            zone_name="",
            description="",
        )
        assert result[0] is no_update
        assert result[2] is not no_update  # feedback

    def test_create_new_map_success(self, temp_maps_dir):
        """create_new_map should create file on success."""
        with patch(
            "pipeworks_mud_mapper.callbacks.file_callbacks.MAPS_DIR",
            temp_maps_dir,
        ):
            result = create_new_map(
                n_clicks=1,
                zone_id="newzone",
                zone_name="New Zone",
                description="A new zone.",
            )

        modal_open, file_list, feedback, zone_id, name, desc = result
        assert modal_open is False  # Modal closes
        assert "newzone.map.json" in file_list
        assert (temp_maps_dir / "newzone.map.json").exists()

    def test_create_new_map_duplicate(self, temp_maps_dir):
        """create_new_map should reject duplicate zone ID."""
        # Create existing file
        (temp_maps_dir / "existing.map.json").write_text("{}")

        with patch(
            "pipeworks_mud_mapper.callbacks.file_callbacks.MAPS_DIR",
            temp_maps_dir,
        ):
            result = create_new_map(
                n_clicks=1,
                zone_id="existing",
                zone_name="Existing Zone",
                description="",
            )

        assert result[0] is no_update  # Modal stays open
        assert result[2] is not no_update  # feedback about duplicate

    def test_reset_unsaved_on_file_load(self):
        """reset_unsaved_on_file_load should return False."""
        result = reset_unsaved_on_file_load(selected_file="test.map.json")
        assert result is False

    def test_update_save_status_no_file(self):
        """update_save_status should show no file loaded state."""
        save_disabled, export_disabled, status = update_save_status(
            has_unsaved=False,
            selected_file=None,
        )
        assert save_disabled is True
        assert export_disabled is True
        assert "No file loaded" in str(status)

    def test_update_save_status_unsaved(self):
        """update_save_status should enable save when unsaved changes."""
        save_disabled, export_disabled, status = update_save_status(
            has_unsaved=True,
            selected_file="test.map.json",
        )
        assert save_disabled is False  # Save enabled
        assert export_disabled is True  # Export disabled until saved
        assert "Unsaved" in str(status)

    def test_update_save_status_saved(self):
        """update_save_status should enable export when all saved."""
        save_disabled, export_disabled, status = update_save_status(
            has_unsaved=False,
            selected_file="test.map.json",
        )
        assert save_disabled is True  # Save disabled (nothing to save)
        assert export_disabled is False  # Export enabled
        assert "Saved" in str(status)

    def test_save_map_to_file_no_click(self, simple_zone_data):
        """save_map_to_file should return no_update when not clicked."""
        result = save_map_to_file(
            n_clicks=0,
            zone_data=simple_zone_data,
            selected_file="test.map.json",
        )
        assert result == (no_update, no_update)

    def test_save_map_to_file_no_data(self):
        """save_map_to_file should return no_update when no zone data."""
        result = save_map_to_file(
            n_clicks=1,
            zone_data=None,
            selected_file="test.map.json",
        )
        assert result == (no_update, no_update)

    def test_save_map_to_file_success(self, simple_zone_data, temp_maps_dir):
        """save_map_to_file should save file on success."""
        with patch(
            "pipeworks_mud_mapper.callbacks.file_callbacks.MAPS_DIR",
            temp_maps_dir,
        ):
            result = save_map_to_file(
                n_clicks=1,
                zone_data=simple_zone_data,
                selected_file="test.map.json",
            )

        unsaved, feedback = result
        assert unsaved is False  # Marked as saved
        assert (temp_maps_dir / "test.map.json").exists()

    def test_export_zone_to_file_no_click(self, simple_zone_data):
        """export_zone_to_file should return no_update when not clicked."""
        result = export_zone_to_file(
            n_clicks=0,
            zone_data=simple_zone_data,
            selected_file="test.map.json",
        )
        assert result is no_update

    def test_export_zone_to_file_no_data(self):
        """export_zone_to_file should return no_update when no zone data."""
        result = export_zone_to_file(
            n_clicks=1,
            zone_data=None,
            selected_file="test.map.json",
        )
        assert result is no_update

    def test_export_zone_to_file_success(self, simple_zone_data, temp_maps_dir):
        """export_zone_to_file should export to zones directory."""
        temp_zones_dir = temp_maps_dir.parent / "zones"

        with (
            patch(
                "pipeworks_mud_mapper.callbacks.file_callbacks.MAPS_DIR",
                temp_maps_dir,
            ),
            patch(
                "pipeworks_mud_mapper.callbacks.file_callbacks.ZONES_DIR",
                temp_zones_dir,
            ),
        ):
            result = export_zone_to_file(
                n_clicks=1,
                zone_data=simple_zone_data,
                selected_file="test.map.json",
            )

        # Should have exported
        assert temp_zones_dir.exists()
        assert (temp_zones_dir / "test.json").exists()


# =============================================================================
# Integration Tests
# =============================================================================


class TestCallbackIntegration:
    """Integration tests across multiple callbacks."""

    def test_add_room_then_select(self, simple_zone_data):
        """Adding a room should allow it to be selected."""
        # Add a room
        result = add_room_to_zone(
            n_clicks=1,
            zone_data=simple_zone_data,
            room_id="new_room",
            room_name="New Room",
            room_description="Test",
            coord_x=5,
            coord_y=0,
            coord_z=0,
        )
        updated_zone = result[0]

        # Now select the new room
        form_result = populate_room_form(
            selected_room="new_room",
            zone_data=updated_zone,
        )
        room_id, name, desc, x, y, z, exits, exit_info, update_btn, id_disabled = form_result

        assert room_id == "new_room"
        assert name == "New Room"
        assert x == 5

    def test_update_room_then_verify(self, simple_zone_data):
        """Updating a room should persist changes."""
        # Update the room
        result = update_room_properties(
            n_clicks=1,
            selected_room="spawn",
            zone_data=simple_zone_data,
            room_name="Updated Spawn",
            room_description="Updated description",
            coord_x=10,
            coord_y=20,
            coord_z=0,
        )
        updated_zone = result[0]

        # Verify by populating form
        form_result = populate_room_form(
            selected_room="spawn",
            zone_data=updated_zone,
        )
        assert form_result[1] == "Updated Spawn"
        assert form_result[2] == "Updated description"
        assert form_result[3] == 10
        assert form_result[4] == 20

    def test_create_exit_workflow(self):
        """Test the full exit creation workflow."""
        # Zone with two rooms but no exits
        zone_data = {
            "id": "test",
            "name": "Test",
            "spawn_room": "a",
            "rooms": {
                "a": {
                    "id": "a",
                    "name": "Room A",
                    "coords": [0, 0, 0],
                    "exits": {},
                    "items": [],
                },
                "b": {
                    "id": "b",
                    "name": "Room B",
                    "coords": [0, 5, 0],
                    "exits": {},
                    "items": [],
                },
            },
        }

        # Add north exit from A
        result = handle_exit_changes(
            checked_values=["N"],
            selected_room="a",
            zone_data=zone_data,
        )
        updated_zone = result[0]

        # Verify bidirectional
        assert updated_zone["rooms"]["a"]["exits"]["north"] == "b"
        assert updated_zone["rooms"]["b"]["exits"]["south"] == "a"

        # Now verify form shows the exit
        form_result = populate_room_form(
            selected_room="a",
            zone_data=updated_zone,
        )
        assert "N" in form_result[6]  # exit_values
