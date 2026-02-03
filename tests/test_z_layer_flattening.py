"""Tests for Z-layer flattening in map visualization.

This module provides comprehensive tests for the flattened Z-layer display
feature, which shows all rooms on a single 2D plane with visual differentiation
by Z-level.

The flattening feature enables:

- Viewing all Z-levels simultaneously
- Visual differentiation by size and color
- U/D labels for stacked rooms with vertical exits
- Click selection with Z-level filtering

Test Categories
---------------
- **TestZLevelStyles**: Visual styling constants
- **TestGroupRoomsByZLevel**: Room grouping helper
- **TestFindStackedPositions**: Stacked position detection
- **TestDrawAllExitLines**: Exit line rendering
- **TestDrawRoomsAtZLevel**: Single-level room rendering
- **TestAddVerticalExitLabels**: U/D label placement
- **TestCreateMapFigureWithRooms**: Full integration tests
- **TestZLevelFiltering**: Layer visibility filtering
"""

import plotly.graph_objects as go
import pytest

from pipeworks_mud_mapper.components.map_view import (
    SELECTED_ROOM_COLOR,
    Z_LEVEL_STYLES,
    Z_RENDER_ORDER,
    _add_vertical_exit_labels,
    _draw_all_exit_lines,
    _draw_rooms_at_z_level,
    _find_stacked_positions,
    _get_visual_coords,
    _group_rooms_by_z_level,
    create_map_figure_with_rooms,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def multi_z_rooms() -> dict:
    """Create rooms at multiple Z-levels for testing.

    Layout::

        z=1:  attic at (0, 0, 1)
        z=0:  ground at (0, 0, 0), east_room at (5, 0, 0)
        z=-1: basement at (0, 0, -1)

    Ground has both up and down exits to attic and basement.
    """
    return {
        "ground": {
            "id": "ground",
            "name": "Ground Room",
            "coords": [0, 0, 0],
            "exits": {"down": "basement", "up": "attic", "east": "east_room"},
        },
        "basement": {
            "id": "basement",
            "name": "Basement",
            "coords": [0, 0, -1],
            "exits": {"up": "ground"},
        },
        "attic": {
            "id": "attic",
            "name": "Attic",
            "coords": [0, 0, 1],
            "exits": {"down": "ground"},
        },
        "east_room": {
            "id": "east_room",
            "name": "East Room",
            "coords": [5, 0, 0],
            "exits": {"west": "ground"},
        },
    }


@pytest.fixture
def stacked_tower() -> dict:
    """Create rooms stacked at same X,Y with different Z.

    Layout::

        z=1:  tower_top at (10, 10, 1)
        z=0:  tower_mid at (10, 10, 0)
        z=-1: tower_base at (10, 10, -1)

    All rooms have vertical exits to adjacent levels.
    """
    return {
        "tower_base": {
            "id": "tower_base",
            "name": "Tower Base",
            "coords": [10, 10, -1],
            "exits": {"up": "tower_mid"},
        },
        "tower_mid": {
            "id": "tower_mid",
            "name": "Tower Middle",
            "coords": [10, 10, 0],
            "exits": {"down": "tower_base", "up": "tower_top"},
        },
        "tower_top": {
            "id": "tower_top",
            "name": "Tower Top",
            "coords": [10, 10, 1],
            "exits": {"down": "tower_mid"},
        },
    }


@pytest.fixture
def horizontal_rooms() -> dict:
    """Create rooms on same Z-level for exit line testing.

    Layout::

        west_room -- center -- east_room
           (0,0,0)   (5,0,0)   (10,0,0)
    """
    return {
        "west_room": {
            "id": "west_room",
            "name": "West Room",
            "coords": [0, 0, 0],
            "exits": {"east": "center"},
        },
        "center": {
            "id": "center",
            "name": "Center",
            "coords": [5, 0, 0],
            "exits": {"west": "west_room", "east": "east_room"},
        },
        "east_room": {
            "id": "east_room",
            "name": "East Room",
            "coords": [10, 0, 0],
            "exits": {"west": "center"},
        },
    }


# =============================================================================
# Z-Level Style Tests
# =============================================================================


class TestZLevelStyles:
    """Tests for Z-level visual configuration constants."""

    def test_all_z_levels_have_styles(self):
        """All Z-levels (-1, 0, 1) should have style definitions."""
        assert -1 in Z_LEVEL_STYLES
        assert 0 in Z_LEVEL_STYLES
        assert 1 in Z_LEVEL_STYLES

    def test_style_has_required_keys(self):
        """Each style should have all required configuration keys."""
        required_keys = ["size", "color", "border_color", "border_width", "label"]
        for z_level, style in Z_LEVEL_STYLES.items():
            for key in required_keys:
                assert key in style, f"Z-level {z_level} missing key: {key}"

    def test_z_minus_one_is_smallest(self):
        """z=-1 (Down) should have smallest marker size."""
        assert Z_LEVEL_STYLES[-1]["size"] < Z_LEVEL_STYLES[0]["size"]
        assert Z_LEVEL_STYLES[-1]["size"] < Z_LEVEL_STYLES[1]["size"]

    def test_z_zero_is_largest(self):
        """z=0 (Ground) should have largest marker size."""
        assert Z_LEVEL_STYLES[0]["size"] > Z_LEVEL_STYLES[-1]["size"]
        assert Z_LEVEL_STYLES[0]["size"] > Z_LEVEL_STYLES[1]["size"]

    def test_render_order_ground_last(self):
        """Ground level (z=0) should be rendered last (on top)."""
        assert Z_RENDER_ORDER[-1] == 0

    def test_render_order_down_first(self):
        """Down level (z=-1) should be rendered first (at back)."""
        assert Z_RENDER_ORDER[0] == -1

    def test_render_order_contains_all_levels(self):
        """Render order should contain all three Z-levels."""
        assert set(Z_RENDER_ORDER) == {-1, 0, 1}


# =============================================================================
# Group Rooms By Z-Level Tests
# =============================================================================


class TestGroupRoomsByZLevel:
    """Tests for _group_rooms_by_z_level helper function."""

    def test_groups_correctly(self, multi_z_rooms):
        """Rooms should be grouped by their Z coordinate."""
        result = _group_rooms_by_z_level(multi_z_rooms, [-1, 0, 1])

        assert -1 in result
        assert 0 in result
        assert 1 in result
        assert "basement" in result[-1]
        assert "ground" in result[0]
        assert "east_room" in result[0]
        assert "attic" in result[1]

    def test_respects_visible_filter(self, multi_z_rooms):
        """Only visible Z-levels should be included in result."""
        result = _group_rooms_by_z_level(multi_z_rooms, [0])

        assert -1 not in result
        assert 1 not in result
        assert 0 in result
        assert len(result[0]) == 2  # ground and east_room

    def test_empty_rooms(self):
        """Empty rooms dict should return empty result."""
        result = _group_rooms_by_z_level({}, [-1, 0, 1])
        assert result == {}

    def test_empty_filter(self, multi_z_rooms):
        """Empty filter should return empty result."""
        result = _group_rooms_by_z_level(multi_z_rooms, [])
        assert result == {}

    def test_partial_filter(self, multi_z_rooms):
        """Partial filter should only include specified levels."""
        result = _group_rooms_by_z_level(multi_z_rooms, [-1, 0])

        assert -1 in result
        assert 0 in result
        assert 1 not in result

    def test_handles_missing_coords(self):
        """Rooms without coords should default to z=0."""
        rooms = {
            "no_coords": {"id": "no_coords", "name": "No Coords", "exits": {}},
        }
        result = _group_rooms_by_z_level(rooms, [0])

        assert 0 in result
        assert "no_coords" in result[0]


# =============================================================================
# Find Stacked Positions Tests
# =============================================================================


class TestFindStackedPositions:
    """Tests for _find_stacked_positions helper function."""

    def test_finds_stacked(self, stacked_tower):
        """Should find positions with 2+ rooms."""
        result = _find_stacked_positions(stacked_tower, [-1, 0, 1])

        assert (10, 10) in result
        assert len(result[(10, 10)]) == 3

    def test_ignores_single_rooms(self, multi_z_rooms):
        """Positions with only 1 room should not be included."""
        result = _find_stacked_positions(multi_z_rooms, [-1, 0, 1])

        # (0, 0) has 3 rooms (basement, ground, attic) - stacked
        assert (0, 0) in result
        # (5, 0) has only 1 room (east_room) - not stacked
        assert (5, 0) not in result

    def test_respects_visibility(self, stacked_tower):
        """Should only count rooms on visible Z-levels."""
        # Only show ground level
        result = _find_stacked_positions(stacked_tower, [0])

        # With only z=0 visible, (10, 10) only has 1 room
        assert (10, 10) not in result

    def test_empty_rooms(self):
        """Empty rooms dict should return empty result."""
        result = _find_stacked_positions({}, [-1, 0, 1])
        assert result == {}

    def test_two_levels_stacked(self, multi_z_rooms):
        """Two rooms at same X,Y should be detected as stacked."""
        # Filter to only ground and basement
        result = _find_stacked_positions(multi_z_rooms, [-1, 0])

        # (0, 0) should still be stacked (ground and basement)
        assert (0, 0) in result
        assert len(result[(0, 0)]) == 2


# =============================================================================
# Draw Exit Lines Tests
# =============================================================================


class TestDrawAllExitLines:
    """Tests for _draw_all_exit_lines helper function."""

    def test_draws_cardinal_exits(self, horizontal_rooms):
        """Cardinal exits (N/E/S/W) should draw lines."""
        fig = go.Figure()
        _draw_all_exit_lines(fig, horizontal_rooms, [-1, 0, 1])

        # Should have lines for west<->center and center<->east
        line_traces = [t for t in fig.data if t.mode == "lines"]
        assert len(line_traces) == 2

    def test_skips_vertical_exits(self, multi_z_rooms):
        """Up/down exits should not draw lines."""
        fig = go.Figure()
        _draw_all_exit_lines(fig, multi_z_rooms, [-1, 0, 1])

        # ground has up/down exits but they should not create lines
        # Only the east<->west exit between ground and east_room should draw
        line_traces = [t for t in fig.data if t.mode == "lines"]
        assert len(line_traces) == 1

    def test_avoids_duplicate_lines(self, horizontal_rooms):
        """Bidirectional exits should only draw one line."""
        fig = go.Figure()
        _draw_all_exit_lines(fig, horizontal_rooms, [-1, 0, 1])

        # west_room->center and center->west_room should be one line
        # center->east_room and east_room->center should be one line
        line_traces = [t for t in fig.data if t.mode == "lines"]
        assert len(line_traces) == 2  # Not 4

    def test_skips_cross_zone_exits(self):
        """Cross-zone exits (with ':') should not draw lines."""
        rooms = {
            "room1": {
                "id": "room1",
                "name": "Room 1",
                "coords": [0, 0, 0],
                "exits": {"north": "other_zone:room"},
            },
        }
        fig = go.Figure()
        _draw_all_exit_lines(fig, rooms, [-1, 0, 1])

        line_traces = [t for t in fig.data if t.mode == "lines"]
        assert len(line_traces) == 0

    def test_skips_nonexistent_targets(self):
        """Exits to non-existent rooms should not draw lines."""
        rooms = {
            "room1": {
                "id": "room1",
                "name": "Room 1",
                "coords": [0, 0, 0],
                "exits": {"north": "does_not_exist"},
            },
        }
        fig = go.Figure()
        _draw_all_exit_lines(fig, rooms, [-1, 0, 1])

        line_traces = [t for t in fig.data if t.mode == "lines"]
        assert len(line_traces) == 0

    def test_respects_visibility_filter(self, horizontal_rooms):
        """Should not draw lines for rooms outside visible Z-levels."""
        fig = go.Figure()
        # All rooms are at z=0, filter to z=1 only
        _draw_all_exit_lines(fig, horizontal_rooms, [1])

        line_traces = [t for t in fig.data if t.mode == "lines"]
        assert len(line_traces) == 0


# =============================================================================
# Draw Rooms At Z-Level Tests
# =============================================================================


class TestDrawRoomsAtZLevel:
    """Tests for _draw_rooms_at_z_level helper function."""

    def test_draws_correct_size(self, multi_z_rooms):
        """Rooms should use Z-level specific marker size."""
        grouped = _group_rooms_by_z_level(multi_z_rooms, [-1, 0, 1])

        fig = go.Figure()
        _draw_rooms_at_z_level(fig, grouped[-1], -1, None)

        # Basement should have size from Z_LEVEL_STYLES[-1]
        trace = fig.data[0]
        assert trace.marker.size == Z_LEVEL_STYLES[-1]["size"]

    def test_selected_room_is_red(self, multi_z_rooms):
        """Selected room should be red regardless of Z-level."""
        grouped = _group_rooms_by_z_level(multi_z_rooms, [-1, 0, 1])

        fig = go.Figure()
        _draw_rooms_at_z_level(fig, grouped[0], 0, "ground")

        trace = fig.data[0]
        # Find index of ground room
        ground_idx = list(trace.text).index("ground")
        assert trace.marker.color[ground_idx] == SELECTED_ROOM_COLOR

    def test_hover_includes_z_level(self, multi_z_rooms):
        """Hover text should include Z-level info."""
        grouped = _group_rooms_by_z_level(multi_z_rooms, [-1, 0, 1])

        fig = go.Figure()
        _draw_rooms_at_z_level(fig, grouped[-1], -1, None)

        trace = fig.data[0]
        assert "Z-level: -1" in trace.hovertext[0]

    def test_room_labels_set(self, multi_z_rooms):
        """Room IDs should be set as text labels."""
        grouped = _group_rooms_by_z_level(multi_z_rooms, [-1, 0, 1])

        fig = go.Figure()
        _draw_rooms_at_z_level(fig, grouped[0], 0, None)

        trace = fig.data[0]
        assert "ground" in trace.text
        assert "east_room" in trace.text

    def test_empty_rooms_at_level(self):
        """Empty rooms dict should not add any traces."""
        fig = go.Figure()
        _draw_rooms_at_z_level(fig, {}, 0, None)

        assert len(fig.data) == 0

    def test_uses_z_level_colors(self, multi_z_rooms):
        """Non-selected rooms should use Z-level color."""
        grouped = _group_rooms_by_z_level(multi_z_rooms, [-1, 0, 1])

        fig = go.Figure()
        _draw_rooms_at_z_level(fig, grouped[-1], -1, None)

        trace = fig.data[0]
        # All colors should be the z=-1 style color (no selection)
        assert Z_LEVEL_STYLES[-1]["color"] in trace.marker.color


# =============================================================================
# Add Vertical Exit Labels Tests
# =============================================================================


class TestAddVerticalExitLabels:
    """Tests for _add_vertical_exit_labels helper function."""

    def test_adds_ud_label_for_both_exits(self, stacked_tower):
        """Position with both up and down exits should show "U/D"."""
        stacked = _find_stacked_positions(stacked_tower, [-1, 0, 1])

        fig = go.Figure()
        _add_vertical_exit_labels(fig, stacked, stacked_tower)

        # Should have annotation
        assert len(fig.layout.annotations) > 0
        # tower_mid has both up and down
        texts = [a.text for a in fig.layout.annotations]
        assert "U/D" in texts

    def test_u_only_for_up_exit(self):
        """Position with only up exit should show "U"."""
        rooms = {
            "basement": {
                "id": "basement",
                "name": "Basement",
                "coords": [0, 0, -1],
                "exits": {"up": "ground"},
            },
            "ground": {
                "id": "ground",
                "name": "Ground",
                "coords": [0, 0, 0],
                "exits": {},  # No down exit
            },
        }
        stacked = _find_stacked_positions(rooms, [-1, 0])

        fig = go.Figure()
        _add_vertical_exit_labels(fig, stacked, rooms)

        # Should show U only (basement has up, ground has neither)
        assert len(fig.layout.annotations) == 1
        assert fig.layout.annotations[0].text == "U"

    def test_d_only_for_down_exit(self):
        """Position with only down exit should show "D"."""
        rooms = {
            "ground": {
                "id": "ground",
                "name": "Ground",
                "coords": [0, 0, 0],
                "exits": {"down": "basement"},
            },
            "basement": {
                "id": "basement",
                "name": "Basement",
                "coords": [0, 0, -1],
                "exits": {},  # No up exit
            },
        }
        stacked = _find_stacked_positions(rooms, [-1, 0])

        fig = go.Figure()
        _add_vertical_exit_labels(fig, stacked, rooms)

        # Should show D only
        assert len(fig.layout.annotations) == 1
        assert fig.layout.annotations[0].text == "D"

    def test_no_label_without_vertical_exits(self):
        """Stacked rooms without vertical exits should not get labels."""
        rooms = {
            "upper": {"id": "upper", "coords": [5, 5, 1], "exits": {}},
            "lower": {"id": "lower", "coords": [5, 5, 0], "exits": {}},
        }
        stacked = _find_stacked_positions(rooms, [0, 1])

        fig = go.Figure()
        _add_vertical_exit_labels(fig, stacked, rooms)

        assert len(fig.layout.annotations) == 0

    def test_empty_stacked_positions(self):
        """Empty stacked positions should not add any annotations."""
        fig = go.Figure()
        _add_vertical_exit_labels(fig, {}, {})

        assert len(fig.layout.annotations) == 0


# =============================================================================
# Full Integration Tests
# =============================================================================


class TestCreateMapFigureWithRoomsIntegration:
    """Integration tests for create_map_figure_with_rooms."""

    def test_returns_figure(self, multi_z_rooms):
        """Function returns a Plotly Figure."""
        fig = create_map_figure_with_rooms(multi_z_rooms)
        assert isinstance(fig, go.Figure)

    def test_default_shows_all_levels(self, multi_z_rooms):
        """Default (no filter) should show all Z-levels."""
        fig = create_map_figure_with_rooms(multi_z_rooms)

        # Should have traces for all 4 rooms
        room_traces = [t for t in fig.data if t.text is not None and len(t.text) > 0]
        all_labels = []
        for t in room_traces:
            all_labels.extend(t.text)

        assert "ground" in all_labels
        assert "basement" in all_labels
        assert "attic" in all_labels
        assert "east_room" in all_labels

    def test_filter_hides_levels(self, multi_z_rooms):
        """Filtering should hide rooms at non-visible Z-levels."""
        fig = create_map_figure_with_rooms(multi_z_rooms, visible_z_levels=[0])

        room_traces = [t for t in fig.data if t.text is not None and len(t.text) > 0]
        all_labels = []
        for t in room_traces:
            all_labels.extend(t.text)

        assert "ground" in all_labels
        assert "east_room" in all_labels
        assert "basement" not in all_labels
        assert "attic" not in all_labels

    def test_no_title_in_flattened_view(self, multi_z_rooms):
        """Flattened view should not have a title."""
        fig = create_map_figure_with_rooms(multi_z_rooms)

        # Title text should be None (Plotly returns an empty Title object, not None)
        assert fig.layout.title.text is None

    def test_render_order(self, stacked_tower):
        """Ground level should be rendered last (on top)."""
        fig = create_map_figure_with_rooms(stacked_tower)

        # Find room traces (have text labels)
        room_traces = [t for t in fig.data if t.text is not None and len(t.text) > 0]

        # Last room trace should be z=0 (tower_mid)
        last_trace = room_traces[-1]
        assert "tower_mid" in last_trace.text

    def test_selected_room_always_red(self, multi_z_rooms):
        """Selected room should be red regardless of Z-level."""
        # Select basement (z=-1)
        fig = create_map_figure_with_rooms(multi_z_rooms, selected_room="basement")

        # Find trace containing basement
        for trace in fig.data:
            if hasattr(trace, "text") and trace.text is not None:
                if "basement" in list(trace.text):
                    idx = list(trace.text).index("basement")
                    assert trace.marker.color[idx] == SELECTED_ROOM_COLOR
                    return

        pytest.fail("Basement not found in traces")

    def test_has_exit_lines(self, horizontal_rooms):
        """Should draw exit lines for cardinal directions."""
        fig = create_map_figure_with_rooms(horizontal_rooms)

        line_traces = [t for t in fig.data if t.mode == "lines"]
        assert len(line_traces) >= 1

    def test_has_vertical_labels(self, stacked_tower):
        """Should have U/D labels for stacked rooms."""
        fig = create_map_figure_with_rooms(stacked_tower)

        # Should have at least one annotation for U/D
        assert len(fig.layout.annotations) > 0


# =============================================================================
# Z-Level Filter Tests
# =============================================================================


class TestZLevelFiltering:
    """Tests for Z-level filtering behavior."""

    def test_empty_filter_shows_nothing(self, multi_z_rooms):
        """Empty filter list should show base map only."""
        fig = create_map_figure_with_rooms(multi_z_rooms, visible_z_levels=[])

        # Should have no room traces (filter out background)
        room_traces = [t for t in fig.data if t.text is not None and len(t.text) > 0]
        assert len(room_traces) == 0

    def test_partial_filter(self, multi_z_rooms):
        """Partial filter should show only selected levels."""
        fig = create_map_figure_with_rooms(multi_z_rooms, visible_z_levels=[-1, 0])

        room_traces = [t for t in fig.data if t.text is not None and len(t.text) > 0]
        all_labels = []
        for t in room_traces:
            all_labels.extend(t.text)

        assert "basement" in all_labels  # z=-1
        assert "ground" in all_labels  # z=0
        assert "attic" not in all_labels  # z=+1 filtered out

    def test_single_level_filter(self, multi_z_rooms):
        """Single level filter should show only that level."""
        fig = create_map_figure_with_rooms(multi_z_rooms, visible_z_levels=[-1])

        room_traces = [t for t in fig.data if t.text is not None and len(t.text) > 0]
        all_labels = []
        for t in room_traces:
            all_labels.extend(t.text)

        assert "basement" in all_labels
        assert len(all_labels) == 1

    def test_none_filter_shows_all(self, multi_z_rooms):
        """None filter (default) should show all levels."""
        fig = create_map_figure_with_rooms(multi_z_rooms, visible_z_levels=None)

        room_traces = [t for t in fig.data if t.text is not None and len(t.text) > 0]
        all_labels = []
        for t in room_traces:
            all_labels.extend(t.text)

        assert len(all_labels) == 4  # All rooms visible

    def test_filter_affects_stacked_labels(self, stacked_tower):
        """Filtering should affect whether U/D labels appear."""
        # With all visible, should have U/D label
        fig_all = create_map_figure_with_rooms(stacked_tower, visible_z_levels=[-1, 0, 1])
        assert len(fig_all.layout.annotations) > 0

        # With only one level, no stacking, no labels
        fig_one = create_map_figure_with_rooms(stacked_tower, visible_z_levels=[0])
        assert len(fig_one.layout.annotations) == 0

    def test_filter_affects_exit_lines(self, horizontal_rooms):
        """Filtering should hide exit lines for hidden rooms."""
        # All at z=0, with z=0 visible
        fig_visible = create_map_figure_with_rooms(horizontal_rooms, visible_z_levels=[0])
        visible_lines = [t for t in fig_visible.data if t.mode == "lines"]

        # With z=1 only (no rooms there)
        fig_hidden = create_map_figure_with_rooms(horizontal_rooms, visible_z_levels=[1])
        hidden_lines = [t for t in fig_hidden.data if t.mode == "lines"]

        assert len(visible_lines) > 0
        assert len(hidden_lines) == 0


class TestVisualOffset:
    """Tests for Z-level visual offset (stacked room separation)."""

    def test_get_visual_coords_ground_no_offset(self):
        """Ground level (z=0) should have no offset."""
        x, y = _get_visual_coords(5, 10, 0)
        assert x == 5.0
        assert y == 10.0

    def test_get_visual_coords_down_offset(self):
        """Down level (z=-1) should offset left and down."""
        x, y = _get_visual_coords(5, 10, -1)
        assert x < 5.0  # Offset left
        assert y < 10.0  # Offset down

    def test_get_visual_coords_up_offset(self):
        """Up level (z=+1) should offset right and up."""
        x, y = _get_visual_coords(5, 10, 1)
        assert x > 5.0  # Offset right
        assert y > 10.0  # Offset up

    def test_get_visual_coords_unknown_z(self):
        """Unknown Z-levels should have no offset."""
        x, y = _get_visual_coords(5, 10, 99)
        assert x == 5.0
        assert y == 10.0

    def test_stacked_rooms_different_visual_positions(self, stacked_tower):
        """Stacked rooms should render at different visual positions."""
        fig = create_map_figure_with_rooms(stacked_tower)

        # Find room traces (have text labels, not background)
        room_traces = [t for t in fig.data if t.text is not None and len(t.text) > 0]

        # Collect all visual x,y positions
        positions = set()
        for trace in room_traces:
            for i in range(len(trace.x)):
                positions.add((trace.x[i], trace.y[i]))

        # Should have 3 distinct positions (basement, ground, attic)
        assert len(positions) == 3

    def test_visual_offset_separates_overlapping_rooms(self, stacked_tower):
        """Stacked rooms should not overlap visually."""
        fig = create_map_figure_with_rooms(stacked_tower)

        # Find room traces (not background)
        room_traces = [t for t in fig.data if t.text is not None and len(t.text) > 0]

        # Collect positions as list
        positions = []
        for trace in room_traces:
            for i in range(len(trace.x)):
                positions.append((trace.x[i], trace.y[i]))

        # No two positions should be identical
        assert len(positions) == len(set(positions))
