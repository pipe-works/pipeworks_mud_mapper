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
    _get_cached_map_files,
    _should_throttle_snapshot,
    export_zone_to_file,
    handle_dev_snapshotting,
    handle_file_click,
    handle_new_map_modal,
    load_dev_snapshot_files_list,
    load_map_files_list,
    poll_io_jobs,
    render_dev_snapshot_list,
    render_file_list,
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
    confirm_delete_room,
    populate_room_form,
    render_room_form_feedback,
    undo_delete_room,
    update_delete_button_state,
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
    """Tests for map_callbacks module.

    The map callback now uses visible_z_levels (list) instead of z_level (int)
    to support the flattened multi-level display with filtering.
    """

    def test_update_map_with_rooms_no_data(self):
        """update_map_with_rooms should return empty figure when no zone data."""
        figure = update_map_with_rooms(
            zone_data=None,
            visible_z_levels=[-1, 0, 1],
            selected_room=None,
            visual_offset=1.0,
        )
        assert isinstance(figure, go.Figure)
        assert hasattr(figure, "data")
        assert hasattr(figure, "layout")

    def test_update_map_with_rooms_with_data(self, simple_zone_data):
        """update_map_with_rooms should return figure with room data."""
        figure = update_map_with_rooms(
            zone_data=simple_zone_data,
            visible_z_levels=[-1, 0, 1],
            selected_room=None,
            visual_offset=1.0,
        )
        assert isinstance(figure, go.Figure)
        assert len(figure.data) > 0  # Should have room markers

    def test_update_map_with_rooms_with_selection(self, simple_zone_data):
        """update_map_with_rooms should highlight selected room."""
        figure = update_map_with_rooms(
            zone_data=simple_zone_data,
            visible_z_levels=[-1, 0, 1],
            selected_room="spawn",
            visual_offset=1.0,
        )
        assert isinstance(figure, go.Figure)

    def test_update_map_with_rooms_filtered_z_levels(self, simple_zone_data):
        """update_map_with_rooms should filter by visible_z_levels."""
        figure = update_map_with_rooms(
            zone_data=simple_zone_data,
            visible_z_levels=[1],  # Only show z=1, spawn is at z=0
            selected_room=None,
            visual_offset=1.0,
        )
        assert isinstance(figure, go.Figure)
        # No room markers at z=1 (spawn is at z=0), filter out background
        room_traces = [t for t in figure.data if t.text is not None and len(t.text) > 0]
        assert len(room_traces) == 0

    def test_update_map_with_rooms_empty_filter(self, simple_zone_data):
        """update_map_with_rooms should show no rooms with empty filter."""
        figure = update_map_with_rooms(
            zone_data=simple_zone_data,
            visible_z_levels=[],  # No levels visible
            selected_room=None,
            visual_offset=1.0,
        )
        assert isinstance(figure, go.Figure)
        # No room traces, filter out background
        room_traces = [t for t in figure.data if t.text is not None and len(t.text) > 0]
        assert len(room_traces) == 0

    def test_handle_map_click_no_data(self):
        """handle_map_click should return no_update when no click data."""
        result = handle_map_click(click_data=None, zone_data=None, current_selection=None)
        assert result is no_update

    def test_handle_map_click_no_zone(self):
        """handle_map_click should return no_update when no zone data."""
        click_data = {"points": [{"text": "spawn"}]}
        result = handle_map_click(click_data=click_data, zone_data=None, current_selection=None)
        assert result is no_update

    def test_handle_map_click_empty_points(self, simple_zone_data):
        """handle_map_click should return no_update when no points clicked."""
        click_data: dict = {"points": []}
        result = handle_map_click(
            click_data=click_data, zone_data=simple_zone_data, current_selection=None
        )
        assert result is no_update

    def test_handle_map_click_valid_room(self, simple_zone_data):
        """handle_map_click should return room_id when valid room clicked."""
        click_data = {"points": [{"text": "spawn"}]}
        result = handle_map_click(
            click_data=click_data, zone_data=simple_zone_data, current_selection=None
        )
        assert result == "spawn"

    def test_handle_map_click_toggle_unselect(self, simple_zone_data):
        """handle_map_click should return None when clicking same room (toggle)."""
        click_data = {"points": [{"text": "spawn"}]}
        result = handle_map_click(
            click_data=click_data, zone_data=simple_zone_data, current_selection="spawn"
        )
        assert result is None

    def test_handle_map_click_invalid_room(self, simple_zone_data):
        """handle_map_click should return no_update for invalid room."""
        click_data = {"points": [{"text": "nonexistent"}]}
        result = handle_map_click(
            click_data=click_data, zone_data=simple_zone_data, current_selection=None
        )
        assert result is no_update

    def test_handle_map_click_no_text(self, simple_zone_data):
        """handle_map_click should return no_update when point has no text."""
        click_data = {"points": [{"x": 0, "y": 0}]}
        result = handle_map_click(
            click_data=click_data, zone_data=simple_zone_data, current_selection=None
        )
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

    def test_render_room_form_feedback_no_payloads(self):
        """render_room_form_feedback should return no_update when empty."""
        result = render_room_form_feedback(None, None, None, None, None, None, None)
        assert result is no_update

    def test_render_room_form_feedback_latest_payload(self):
        """render_room_form_feedback should return latest feedback content."""
        older = {"content": "Old", "ts": 1.0}
        newer = {"content": "New", "ts": 2.0}
        result = render_room_form_feedback(older, None, newer, None, None, None, None)
        assert "New" in str(result)


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

    def test_get_cached_map_files_uses_cache(self):
        """_get_cached_map_files should return cached results within TTL."""
        fake_dir = Path("/tmp/fake")
        with (
            patch("pipeworks_mud_mapper.callbacks.file_callbacks._FILE_LIST_CACHE", {}),
            patch("pipeworks_mud_mapper.callbacks.file_callbacks.list_map_files") as mock_list,
            patch("pipeworks_mud_mapper.callbacks.file_callbacks.time.monotonic") as mock_clock,
        ):
            mock_list.side_effect = [
                [Path("first.map.json")],
                [Path("second.map.json")],
            ]
            mock_clock.side_effect = [0.0, 0.1]

            first = _get_cached_map_files(fake_dir)
            second = _get_cached_map_files(fake_dir)

        assert first == [Path("first.map.json")]
        assert second == [Path("first.map.json")]
        assert mock_list.call_count == 1

    def test_get_cached_map_files_force_refresh(self):
        """_get_cached_map_files should bypass cache when forced."""
        fake_dir = Path("/tmp/fake")
        with (
            patch("pipeworks_mud_mapper.callbacks.file_callbacks._FILE_LIST_CACHE", {}),
            patch("pipeworks_mud_mapper.callbacks.file_callbacks.list_map_files") as mock_list,
            patch("pipeworks_mud_mapper.callbacks.file_callbacks.time.monotonic") as mock_clock,
        ):
            mock_list.side_effect = [
                [Path("first.map.json")],
                [Path("second.map.json")],
            ]
            mock_clock.side_effect = [0.0, 0.1]

            first = _get_cached_map_files(fake_dir)
            second = _get_cached_map_files(fake_dir, force_refresh=True)

        assert first == [Path("first.map.json")]
        assert second == [Path("second.map.json")]
        assert mock_list.call_count == 2

    def test_should_throttle_snapshot(self):
        """_should_throttle_snapshot should return True within cooldown window."""
        with (
            patch("pipeworks_mud_mapper.callbacks.file_callbacks._LAST_SNAPSHOT_TS", {}),
            patch("pipeworks_mud_mapper.callbacks.file_callbacks.time.monotonic") as mock_clock,
        ):
            mock_clock.side_effect = [0.0, 0.1]

            first = _should_throttle_snapshot("zone:test")
            second = _should_throttle_snapshot("zone:test")

        assert first is False
        assert second is True

    def test_load_dev_snapshot_files_list(self, temp_maps_dir):
        """load_dev_snapshot_files_list should return dev snapshot map files."""
        # Create dev snapshot files in a temp directory.
        (temp_maps_dir / "snapshot1.map.json").write_text("{}")
        (temp_maps_dir / "snapshot2.map.json").write_text("{}")
        (temp_maps_dir / "ignore.txt").write_text("nope")

        with (
            patch(
                "pipeworks_mud_mapper.callbacks.file_callbacks.DEV_MAPS_DIR",
                temp_maps_dir,
            ),
            patch("pipeworks_mud_mapper.callbacks.file_callbacks.ctx") as mock_ctx,
        ):
            mock_ctx.triggered_id = "initial-load"
            result = load_dev_snapshot_files_list(1, None, None)

        assert "snapshot1.map.json" in result
        assert "snapshot2.map.json" in result
        assert "ignore.txt" not in result

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

    def test_render_dev_snapshot_list_empty(self):
        """render_dev_snapshot_list should show message when no snapshots."""
        result = render_dev_snapshot_list(files=[], selected_file=None)
        assert len(result) == 1
        assert "No dev snapshots" in str(result[0])

    def test_render_dev_snapshot_list_with_files(self):
        """render_dev_snapshot_list should render snapshot items."""
        files = ["snap1.map.json", "snap2.map.json"]
        result = render_dev_snapshot_list(files=files, selected_file=None)
        assert len(result) == 2

    def test_render_dev_snapshot_list_with_selection(self):
        """render_dev_snapshot_list should highlight selected snapshot."""
        files = ["snap1.map.json", "snap2.map.json"]
        result = render_dev_snapshot_list(files=files, selected_file="snap1.map.json")
        assert len(result) == 2
        assert "bg-primary" in result[0].className

    def test_handle_file_click_no_clicks(self):
        """handle_file_click should return no_update when nothing clicked."""
        result = handle_file_click(
            map_clicks=[0, 0],
            snapshot_clicks=[0, 0],
            current_file=None,
        )
        assert result == (no_update, no_update, no_update, no_update)

    def test_handle_new_map_modal_open(self):
        """handle_new_map_modal should open when the button is clicked."""
        with patch("pipeworks_mud_mapper.callbacks.file_callbacks.ctx") as mock_ctx:
            mock_ctx.triggered_id = "new-map-btn"
            result = handle_new_map_modal(
                open_clicks=1,
                cancel_clicks=0,
                create_clicks=0,
                zone_id="",
                zone_name="",
                description="",
            )

        assert result == (True, no_update, no_update, no_update, no_update, no_update)

    def test_handle_new_map_modal_cancel(self):
        """handle_new_map_modal should close when cancel is clicked."""
        with patch("pipeworks_mud_mapper.callbacks.file_callbacks.ctx") as mock_ctx:
            mock_ctx.triggered_id = "new-map-cancel-btn"
            result = handle_new_map_modal(
                open_clicks=0,
                cancel_clicks=1,
                create_clicks=0,
                zone_id="",
                zone_name="",
                description="",
            )

        assert result == (False, no_update, no_update, no_update, no_update, no_update)

    def test_handle_new_map_modal_create_no_click(self):
        """handle_new_map_modal should no-op when create is not clicked."""
        with patch("pipeworks_mud_mapper.callbacks.file_callbacks.ctx") as mock_ctx:
            mock_ctx.triggered_id = "new-map-create-btn"
            result = handle_new_map_modal(
                open_clicks=0,
                cancel_clicks=0,
                create_clicks=0,
                zone_id="test",
                zone_name="Test",
                description="",
            )

        assert result == (no_update,) * 6

    def test_handle_new_map_modal_empty_id(self):
        """handle_new_map_modal should reject empty zone ID."""
        with patch("pipeworks_mud_mapper.callbacks.file_callbacks.ctx") as mock_ctx:
            mock_ctx.triggered_id = "new-map-create-btn"
            result = handle_new_map_modal(
                open_clicks=0,
                cancel_clicks=0,
                create_clicks=1,
                zone_id="",
                zone_name="Test",
                description="",
            )

        assert result[0] is True  # Modal stays open
        assert result[2] is not no_update  # feedback

    def test_handle_new_map_modal_invalid_id(self):
        """handle_new_map_modal should reject invalid zone ID format."""
        with patch("pipeworks_mud_mapper.callbacks.file_callbacks.ctx") as mock_ctx:
            mock_ctx.triggered_id = "new-map-create-btn"
            result = handle_new_map_modal(
                open_clicks=0,
                cancel_clicks=0,
                create_clicks=1,
                zone_id="123invalid",  # Starts with number
                zone_name="Test",
                description="",
            )

        assert result[0] is True
        assert result[2] is not no_update  # feedback

    def test_handle_new_map_modal_empty_name(self):
        """handle_new_map_modal should reject empty zone name."""
        with patch("pipeworks_mud_mapper.callbacks.file_callbacks.ctx") as mock_ctx:
            mock_ctx.triggered_id = "new-map-create-btn"
            result = handle_new_map_modal(
                open_clicks=0,
                cancel_clicks=0,
                create_clicks=1,
                zone_id="test",
                zone_name="",
                description="",
            )

        assert result[0] is True
        assert result[2] is not no_update  # feedback

    def test_handle_new_map_modal_success(self, temp_maps_dir):
        """handle_new_map_modal should create file on success."""
        with (
            patch(
                "pipeworks_mud_mapper.callbacks.file_callbacks.MAPS_DIR",
                temp_maps_dir,
            ),
            patch("pipeworks_mud_mapper.callbacks.file_callbacks.ctx") as mock_ctx,
        ):
            mock_ctx.triggered_id = "new-map-create-btn"
            result = handle_new_map_modal(
                open_clicks=0,
                cancel_clicks=0,
                create_clicks=1,
                zone_id="newzone",
                zone_name="New Zone",
                description="A new zone.",
            )

        modal_open, file_list, feedback, zone_id, name, desc = result
        assert modal_open is False  # Modal closes
        assert "newzone.map.json" in file_list
        assert (temp_maps_dir / "newzone.map.json").exists()

    def test_handle_new_map_modal_duplicate(self, temp_maps_dir):
        """handle_new_map_modal should reject duplicate zone ID."""
        # Create existing file
        (temp_maps_dir / "existing.map.json").write_text("{}")

        with (
            patch(
                "pipeworks_mud_mapper.callbacks.file_callbacks.MAPS_DIR",
                temp_maps_dir,
            ),
            patch("pipeworks_mud_mapper.callbacks.file_callbacks.ctx") as mock_ctx,
        ):
            mock_ctx.triggered_id = "new-map-create-btn"
            result = handle_new_map_modal(
                open_clicks=0,
                cancel_clicks=0,
                create_clicks=1,
                zone_id="existing",
                zone_name="Existing Zone",
                description="",
            )

        assert result[0] is True  # Modal stays open
        assert result[2] is not no_update  # feedback about duplicate

    def test_update_save_status_no_file(self):
        """update_save_status should show no file loaded state."""
        save_disabled, export_disabled, status, debug = update_save_status(
            has_unsaved=False,
            selected_file=None,
        )
        assert save_disabled is True
        assert export_disabled is True
        assert "No file loaded" in status

    def test_update_save_status_unsaved(self):
        """update_save_status should enable save when unsaved changes."""
        save_disabled, export_disabled, status, debug = update_save_status(
            has_unsaved=True,
            selected_file="test.map.json",
        )
        assert save_disabled is False  # Save enabled
        assert export_disabled is True  # Export disabled until saved
        assert "Unsaved" in status

    def test_update_save_status_saved(self):
        """update_save_status should enable export when all saved."""
        save_disabled, export_disabled, status, debug = update_save_status(
            has_unsaved=False,
            selected_file="test.map.json",
        )
        assert save_disabled is True  # Save disabled (nothing to save)
        assert export_disabled is False  # Export enabled
        assert "Saved" in status.children

    def test_save_map_to_file_no_click(self, simple_zone_data):
        """save_map_to_file should return no_update when not clicked."""
        result = save_map_to_file(
            n_clicks=0,
            zone_data=simple_zone_data,
            selected_file="test.map.json",
            dev_save_enabled=False,
            io_jobs=None,
        )
        assert result == (no_update, no_update, no_update)

    def test_save_map_to_file_no_data(self):
        """save_map_to_file should return no_update when no zone data."""
        result = save_map_to_file(
            n_clicks=1,
            zone_data=None,
            selected_file="test.map.json",
            dev_save_enabled=False,
            io_jobs=None,
        )
        assert result == (no_update, no_update, no_update)

    def test_save_map_to_file_success(self, simple_zone_data, temp_maps_dir):
        """save_map_to_file should queue a save job on success."""
        with patch(
            "pipeworks_mud_mapper.callbacks.file_callbacks.MAPS_DIR",
            temp_maps_dir,
        ):
            result = save_map_to_file(
                n_clicks=1,
                zone_data=simple_zone_data,
                selected_file="test.map.json",
                dev_save_enabled=False,
                io_jobs=None,
            )

        unsaved, feedback, job_store = result
        assert unsaved is True  # Save queued, still unsaved until job completes
        assert job_store and job_store["jobs"]

    def test_save_map_to_file_dev_snapshot(self, simple_zone_data, temp_maps_dir, tmp_path):
        """save_map_to_file should queue a dev snapshot when enabled."""
        with (
            patch(
                "pipeworks_mud_mapper.callbacks.file_callbacks.MAPS_DIR",
                temp_maps_dir,
            ),
            patch(
                "pipeworks_mud_mapper.callbacks.file_callbacks.DEV_MAPS_DIR",
                tmp_path,
            ),
        ):
            result = save_map_to_file(
                n_clicks=1,
                zone_data=simple_zone_data,
                selected_file="test.map.json",
                dev_save_enabled=True,
                io_jobs=None,
            )

        unsaved, feedback, job_store = result
        assert unsaved is True
        assert job_store and job_store["jobs"]

    def test_dev_snapshot_map_disabled(self, simple_zone_data, tmp_path):
        """handle_dev_snapshotting should no-op when toggle is off."""
        with (
            patch("pipeworks_mud_mapper.callbacks.file_callbacks.DEV_MAPS_DIR", tmp_path),
            patch(
                "pipeworks_mud_mapper.callbacks.file_callbacks._should_throttle_snapshot",
                lambda _k: False,
            ),
            patch("pipeworks_mud_mapper.callbacks.file_callbacks.ctx") as mock_ctx,
        ):
            mock_ctx.triggered_id = "current-zone-data"
            result = handle_dev_snapshotting(
                zone_data=simple_zone_data,
                generation_info=None,
                dev_save_enabled=False,
                response_text=None,
                validation_info=None,
                selected_room=None,
                selected_file="test.map.json",
                io_jobs=None,
            )

        assert result == (no_update, no_update)

    def test_dev_snapshot_map_disabled_list(self, simple_zone_data, tmp_path):
        """handle_dev_snapshotting should no-op when checkbox list is empty."""
        with (
            patch("pipeworks_mud_mapper.callbacks.file_callbacks.DEV_MAPS_DIR", tmp_path),
            patch(
                "pipeworks_mud_mapper.callbacks.file_callbacks._should_throttle_snapshot",
                lambda _k: False,
            ),
            patch("pipeworks_mud_mapper.callbacks.file_callbacks.ctx") as mock_ctx,
        ):
            mock_ctx.triggered_id = "current-zone-data"
            result = handle_dev_snapshotting(
                zone_data=simple_zone_data,
                generation_info=None,
                dev_save_enabled=[],
                response_text=None,
                validation_info=None,
                selected_room=None,
                selected_file="test.map.json",
                io_jobs=None,
            )

        assert result == (no_update, no_update)

    def test_dev_snapshot_map_success(self, simple_zone_data, tmp_path):
        """handle_dev_snapshotting should write a snapshot on map change."""
        with (
            patch("pipeworks_mud_mapper.callbacks.file_callbacks.DEV_MAPS_DIR", tmp_path),
            patch(
                "pipeworks_mud_mapper.callbacks.file_callbacks._should_throttle_snapshot",
                lambda _k: False,
            ),
            patch("pipeworks_mud_mapper.callbacks.file_callbacks.ctx") as mock_ctx,
        ):
            mock_ctx.triggered_id = "current-zone-data"
            result = handle_dev_snapshotting(
                zone_data=simple_zone_data,
                generation_info=None,
                dev_save_enabled=True,
                response_text=None,
                validation_info=None,
                selected_room=None,
                selected_file="test.map.json",
                io_jobs=None,
            )

        payload, job_store = result
        assert isinstance(payload, dict)
        assert "snapshot" in payload
        assert job_store and job_store["jobs"]

    def test_dev_snapshot_map_fallback_name(self, simple_zone_data, tmp_path):
        """handle_dev_snapshotting should use zone id if no selected_file."""
        with (
            patch("pipeworks_mud_mapper.callbacks.file_callbacks.DEV_MAPS_DIR", tmp_path),
            patch(
                "pipeworks_mud_mapper.callbacks.file_callbacks._should_throttle_snapshot",
                lambda _k: False,
            ),
            patch("pipeworks_mud_mapper.callbacks.file_callbacks.ctx") as mock_ctx,
        ):
            mock_ctx.triggered_id = "current-zone-data"
            result = handle_dev_snapshotting(
                zone_data=simple_zone_data,
                generation_info=None,
                dev_save_enabled=True,
                response_text=None,
                validation_info=None,
                selected_room=None,
                selected_file=None,
                io_jobs=None,
            )

        payload, job_store = result
        assert isinstance(payload, dict)
        assert job_store and job_store["jobs"]

    def test_dev_snapshot_generation_disabled(self, simple_zone_data, tmp_path):
        """handle_dev_snapshotting should no-op for generation when toggle is off."""
        generation_info = {
            "model": "gemma2:2b",
            "actual_seed": 12345,
            "template_id": "__custom__",
            "temperature": 0.7,
            "top_k": 40,
            "top_p": 0.9,
            "num_ctx": 4096,
            "num_predict": 128,
            "system_prompt": "System",
            "user_prompt": "User",
            "generated_at": "2026-02-04T10:30:00+00:00",
        }
        with (
            patch("pipeworks_mud_mapper.callbacks.file_callbacks.DEV_MAPS_DIR", tmp_path),
            patch(
                "pipeworks_mud_mapper.callbacks.file_callbacks._should_throttle_snapshot",
                lambda _k: False,
            ),
            patch("pipeworks_mud_mapper.callbacks.file_callbacks.ctx") as mock_ctx,
        ):
            mock_ctx.triggered_id = "ollama-last-generation-info"
            result = handle_dev_snapshotting(
                zone_data=simple_zone_data,
                generation_info=generation_info,
                dev_save_enabled=False,
                response_text="Generated text.",
                validation_info=None,
                selected_room="spawn",
                selected_file="test.map.json",
                io_jobs=None,
            )

        assert result == (no_update, no_update)

    def test_dev_snapshot_generation_disabled_list(self, simple_zone_data, tmp_path):
        """handle_dev_snapshotting should no-op for generation with empty list toggle."""
        generation_info = {
            "model": "gemma2:2b",
            "actual_seed": 12345,
            "template_id": "__custom__",
            "temperature": 0.7,
            "top_k": 40,
            "top_p": 0.9,
            "num_ctx": 4096,
            "num_predict": 128,
            "system_prompt": "System",
            "user_prompt": "User",
            "generated_at": "2026-02-04T10:30:00+00:00",
        }
        with (
            patch("pipeworks_mud_mapper.callbacks.file_callbacks.DEV_MAPS_DIR", tmp_path),
            patch(
                "pipeworks_mud_mapper.callbacks.file_callbacks._should_throttle_snapshot",
                lambda _k: False,
            ),
            patch("pipeworks_mud_mapper.callbacks.file_callbacks.ctx") as mock_ctx,
        ):
            mock_ctx.triggered_id = "ollama-last-generation-info"
            result = handle_dev_snapshotting(
                zone_data=simple_zone_data,
                generation_info=generation_info,
                dev_save_enabled=[],
                response_text="Generated text.",
                validation_info=None,
                selected_room="spawn",
                selected_file="test.map.json",
                io_jobs=None,
            )

        assert result == (no_update, no_update)

    def test_dev_snapshot_generation_success(self, simple_zone_data, tmp_path):
        """handle_dev_snapshotting should write a snapshot on generation."""
        generation_info = {
            "model": "gemma2:2b",
            "actual_seed": 12345,
            "template_id": "__custom__",
            "temperature": 0.7,
            "top_k": 40,
            "top_p": 0.9,
            "num_ctx": 4096,
            "num_predict": 128,
            "system_prompt": "System",
            "user_prompt": "User",
            "generated_at": "2026-02-04T10:30:00+00:00",
        }
        with (
            patch("pipeworks_mud_mapper.callbacks.file_callbacks.DEV_MAPS_DIR", tmp_path),
            patch(
                "pipeworks_mud_mapper.callbacks.file_callbacks._should_throttle_snapshot",
                lambda _k: False,
            ),
            patch("pipeworks_mud_mapper.callbacks.file_callbacks.ctx") as mock_ctx,
        ):
            mock_ctx.triggered_id = "ollama-last-generation-info"
            result = handle_dev_snapshotting(
                zone_data=simple_zone_data,
                generation_info=generation_info,
                dev_save_enabled=True,
                response_text="Generated text.",
                validation_info={"valid": True},
                selected_room="spawn",
                selected_file="test.map.json",
                io_jobs=None,
            )

        payload, job_store = result
        assert isinstance(payload, dict)
        assert payload.get("trigger") == "generation"
        assert job_store and job_store["jobs"]

    def test_dev_snapshot_generation_no_selected_room(self, simple_zone_data, tmp_path):
        """handle_dev_snapshotting should snapshot without injecting when no room selected."""
        generation_info = {
            "model": "gemma2:2b",
            "actual_seed": 12345,
            "template_id": "__custom__",
            "temperature": 0.7,
            "top_k": 40,
            "top_p": 0.9,
            "num_ctx": 4096,
            "num_predict": 128,
            "system_prompt": "System",
            "user_prompt": "User",
            "generated_at": "2026-02-04T10:30:00+00:00",
        }
        with (
            patch("pipeworks_mud_mapper.callbacks.file_callbacks.DEV_MAPS_DIR", tmp_path),
            patch(
                "pipeworks_mud_mapper.callbacks.file_callbacks._should_throttle_snapshot",
                lambda _k: False,
            ),
            patch("pipeworks_mud_mapper.callbacks.file_callbacks.ctx") as mock_ctx,
        ):
            mock_ctx.triggered_id = "ollama-last-generation-info"
            result = handle_dev_snapshotting(
                zone_data=simple_zone_data,
                generation_info=generation_info,
                dev_save_enabled=True,
                response_text="Generated text.",
                validation_info={"valid": True},
                selected_room=None,
                selected_file="test.map.json",
                io_jobs=None,
            )

        payload, job_store = result
        assert isinstance(payload, dict)
        assert job_store and job_store["jobs"]

    def test_export_zone_to_file_no_click(self, simple_zone_data):
        """export_zone_to_file should return no_update when not clicked."""
        result = export_zone_to_file(
            n_clicks=0,
            zone_data=simple_zone_data,
            selected_file="test.map.json",
            io_jobs=None,
        )
        assert result == (no_update, no_update)

    def test_export_zone_to_file_no_data(self):
        """export_zone_to_file should return no_update when no zone data."""
        result = export_zone_to_file(
            n_clicks=1,
            zone_data=None,
            selected_file="test.map.json",
            io_jobs=None,
        )
        assert result == (no_update, no_update)

    def test_export_zone_to_file_success(self, simple_zone_data, temp_maps_dir):
        """export_zone_to_file should queue an export job."""
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
                io_jobs=None,
            )

        feedback, job_store = result
        assert job_store and job_store["jobs"]

    def test_poll_io_jobs_no_jobs(self):
        """poll_io_jobs should no-op when no jobs are queued."""
        result = poll_io_jobs(n_intervals=1, io_jobs={"jobs": []})
        assert result == (no_update, no_update, no_update, no_update, no_update)

    def test_poll_io_jobs_save_complete(self):
        """poll_io_jobs should emit save feedback on completion."""
        io_jobs = {"jobs": [{"id": "job-1", "type": "save", "display_name": "test"}]}
        with (
            patch(
                "pipeworks_mud_mapper.callbacks.file_callbacks.get_io_job_status",
                return_value={"status": "done"},
            ),
            patch("pipeworks_mud_mapper.callbacks.file_callbacks.forget_io_job"),
        ):
            job_store, save_feedback, export_feedback, snapshot_status, unsaved = poll_io_jobs(
                n_intervals=1,
                io_jobs=io_jobs,
            )

        assert job_store == {"jobs": []}
        assert save_feedback is not no_update
        assert export_feedback is no_update
        assert snapshot_status is no_update
        assert unsaved is False


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


# =============================================================================
# Delete Room Tests
# =============================================================================


class TestDeleteRoomCallbacks:
    """Tests for room deletion callbacks."""

    @pytest.fixture
    def zone_with_exits(self) -> dict:
        """Create a zone with connected rooms for delete testing."""
        return {
            "id": "test_zone",
            "name": "Test Zone",
            "spawn_room": "spawn",
            "rooms": {
                "spawn": {
                    "id": "spawn",
                    "name": "Spawn Room",
                    "description": "Starting room.",
                    "coords": [0, 0, 0],
                    "exits": {"north": "hallway"},
                    "items": [],
                },
                "hallway": {
                    "id": "hallway",
                    "name": "Hallway",
                    "description": "A long hallway.",
                    "coords": [0, 5, 0],
                    "exits": {"south": "spawn", "north": "exit_room"},
                    "items": [],
                },
                "exit_room": {
                    "id": "exit_room",
                    "name": "Exit Room",
                    "description": "The exit.",
                    "coords": [0, 10, 0],
                    "exits": {"south": "hallway"},
                    "items": [],
                },
            },
        }

    def test_delete_button_disabled_no_selection(self):
        """Delete button should be disabled when no room is selected."""
        result = update_delete_button_state(
            selected_room=None,
            zone_data={"spawn_room": "spawn", "rooms": {}},
        )
        assert result is True  # Disabled

    def test_delete_button_disabled_for_spawn(self, zone_with_exits):
        """Delete button should be disabled for spawn room."""
        result = update_delete_button_state(
            selected_room="spawn",
            zone_data=zone_with_exits,
        )
        assert result is True  # Disabled - can't delete spawn

    def test_delete_button_enabled_for_non_spawn(self, zone_with_exits):
        """Delete button should be enabled for non-spawn rooms."""
        result = update_delete_button_state(
            selected_room="hallway",
            zone_data=zone_with_exits,
        )
        assert result is False  # Enabled

    def test_confirm_delete_removes_room(self, zone_with_exits):
        """Confirming delete should remove the room from zone data."""
        result = confirm_delete_room(
            n_clicks=1,
            selected_room="exit_room",
            zone_data=zone_with_exits,
        )
        updated_zone = result[0]
        selected_room = result[1]
        undo_data = result[3]

        # Room should be deleted
        assert "exit_room" not in updated_zone["rooms"]

        # Selection should be cleared
        assert selected_room is None

        # Undo data should be stored
        assert undo_data is not None
        assert undo_data["room_id"] == "exit_room"

    def test_confirm_delete_removes_incoming_exits(self, zone_with_exits):
        """Deleting a room should remove exits from other rooms pointing to it."""
        result = confirm_delete_room(
            n_clicks=1,
            selected_room="hallway",
            zone_data=zone_with_exits,
        )
        updated_zone = result[0]
        undo_data = result[3]

        # Hallway should be deleted
        assert "hallway" not in updated_zone["rooms"]

        # Exit from spawn to hallway should be removed
        assert "north" not in updated_zone["rooms"]["spawn"]["exits"]

        # Exit from exit_room to hallway should be removed
        assert "south" not in updated_zone["rooms"]["exit_room"]["exits"]

        # Undo data should contain the removed exits
        assert len(undo_data["removed_exits"]) == 2

    def test_confirm_delete_no_click(self, zone_with_exits):
        """No deletion should happen without a click."""
        result = confirm_delete_room(
            n_clicks=0,
            selected_room="hallway",
            zone_data=zone_with_exits,
        )
        # All outputs should be no_update
        assert result == (no_update,) * 7

    def test_undo_delete_restores_room(self, zone_with_exits):
        """Undo should restore the deleted room."""
        # First delete a room
        delete_result = confirm_delete_room(
            n_clicks=1,
            selected_room="exit_room",
            zone_data=zone_with_exits,
        )
        updated_zone = delete_result[0]
        undo_data = delete_result[3]

        # Verify it's deleted
        assert "exit_room" not in updated_zone["rooms"]

        # Now undo
        undo_result = undo_delete_room(
            n_clicks=1,
            undo_data=undo_data,
            zone_data=updated_zone,
        )
        restored_zone = undo_result[0]

        # Room should be restored
        assert "exit_room" in restored_zone["rooms"]
        assert restored_zone["rooms"]["exit_room"]["name"] == "Exit Room"

    def test_undo_delete_restores_exits(self, zone_with_exits):
        """Undo should restore exits from other rooms."""
        # Delete hallway (which has incoming exits from spawn and exit_room)
        delete_result = confirm_delete_room(
            n_clicks=1,
            selected_room="hallway",
            zone_data=zone_with_exits,
        )
        updated_zone = delete_result[0]
        undo_data = delete_result[3]

        # Verify exits are removed
        assert "north" not in updated_zone["rooms"]["spawn"]["exits"]
        assert "south" not in updated_zone["rooms"]["exit_room"]["exits"]

        # Now undo
        undo_result = undo_delete_room(
            n_clicks=1,
            undo_data=undo_data,
            zone_data=updated_zone,
        )
        restored_zone = undo_result[0]

        # Exits should be restored
        assert restored_zone["rooms"]["spawn"]["exits"]["north"] == "hallway"
        assert restored_zone["rooms"]["exit_room"]["exits"]["south"] == "hallway"

    def test_undo_delete_no_undo_data(self, zone_with_exits):
        """Undo should do nothing without undo data."""
        result = undo_delete_room(
            n_clicks=1,
            undo_data=None,
            zone_data=zone_with_exits,
        )
        assert result == (no_update,) * 4


# =============================================================================
# Validation Callback Tests
# =============================================================================


class TestValidationCallbacks:
    """Tests for validation callbacks.

    These tests verify the validation UI callbacks that run validation
    checks and display results to the user.
    """

    @pytest.fixture
    def zone_with_issues(self) -> dict:
        """Create a zone with validation issues for testing."""
        return {
            "id": "test_zone",
            "name": "Test Zone",
            "spawn_room": "spawn",
            "rooms": {
                "spawn": {
                    "id": "spawn",
                    "name": "Spawn Room",
                    "description": "Starting room.",
                    "coords": [0, 0, 0],
                    "exits": {"north": "room_a"},
                    "items": [],
                },
                "room_a": {
                    "id": "room_a",
                    "name": "Room A",
                    "description": "A room.",
                    "coords": [0, 5, 0],
                    "exits": {},  # No return exit (asymmetric)
                    "items": [],
                },
                "orphan": {
                    "id": "orphan",
                    "name": "Orphan Room",
                    "description": "Unreachable room.",
                    "coords": [10, 10, 0],
                    "exits": {},  # No exits and unreachable
                    "items": [],
                },
            },
        }

    def test_update_validate_button_no_file(self):
        """Validate button should be disabled when no file is selected."""
        from pipeworks_mud_mapper.callbacks.validation_callbacks import (
            update_validate_button_state,
        )

        result = update_validate_button_state(selected_file=None)
        assert result is True  # Disabled

    def test_update_validate_button_with_file(self):
        """Validate button should be enabled when file is selected."""
        from pipeworks_mud_mapper.callbacks.validation_callbacks import (
            update_validate_button_state,
        )

        result = update_validate_button_state(selected_file="test.map.json")
        assert result is False  # Enabled

    def test_run_validation_no_click(self, simple_zone_data):
        """run_validation should return no_update when not clicked."""
        from pipeworks_mud_mapper.callbacks.validation_callbacks import run_validation

        result = run_validation(
            n_clicks=0,
            zone_data=simple_zone_data,
            selected_file="test.map.json",
        )
        assert result == (no_update, no_update, no_update)

    def test_run_validation_no_data(self):
        """run_validation should return no_update when no zone data."""
        from pipeworks_mud_mapper.callbacks.validation_callbacks import run_validation

        result = run_validation(
            n_clicks=1,
            zone_data=None,
            selected_file="test.map.json",
        )
        assert result == (no_update, no_update, no_update)

    def test_run_validation_success(self, simple_zone_data, tmp_path):
        """run_validation should open modal and return report."""
        from pipeworks_mud_mapper.callbacks.validation_callbacks import run_validation

        # Patch write_validation_report to use temp path
        with patch(
            "pipeworks_mud_mapper.callbacks.validation_callbacks.validation_service.write_validation_report"
        ) as mock_write:
            mock_write.return_value = str(tmp_path / "test.validation.json")

            result = run_validation(
                n_clicks=1,
                zone_data=simple_zone_data,
                selected_file="test.map.json",
            )

        modal_open, modal_body, report = result

        # Modal should be open
        assert modal_open is True

        # Modal body should have content (list of components)
        assert modal_body is not None
        assert isinstance(modal_body, list)

        # Report should be a dict with expected structure
        assert isinstance(report, dict)
        assert "timestamp" in report
        assert "map_file" in report
        assert "summary" in report
        assert "warnings" in report

    def test_run_validation_with_issues(self, zone_with_issues, tmp_path):
        """run_validation should detect validation issues."""
        from pipeworks_mud_mapper.callbacks.validation_callbacks import run_validation

        with patch(
            "pipeworks_mud_mapper.callbacks.validation_callbacks.validation_service.write_validation_report"
        ) as mock_write:
            mock_write.return_value = str(tmp_path / "test.validation.json")

            result = run_validation(
                n_clicks=1,
                zone_data=zone_with_issues,
                selected_file="test.map.json",
            )

        modal_open, modal_body, report = result

        # Should have warnings
        assert report["summary"]["total"] > 0

        # Should have unreachable room warning
        assert any(w["room_id"] == "orphan" for w in report["warnings"])

    def test_close_validation_modal(self):
        """close_validation_modal should close the modal."""
        from pipeworks_mud_mapper.callbacks.validation_callbacks import (
            close_validation_modal,
        )

        result = close_validation_modal(n_clicks=1)
        assert result is False  # Modal closed

    def test_close_validation_modal_no_click(self):
        """close_validation_modal should return no_update without click."""
        from pipeworks_mud_mapper.callbacks.validation_callbacks import (
            close_validation_modal,
        )

        result = close_validation_modal(n_clicks=None)
        assert result is no_update
