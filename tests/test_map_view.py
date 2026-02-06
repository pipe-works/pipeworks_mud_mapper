"""Tests for the map view component.

This module tests the Plotly-based map visualization functions that render
MUD zone maps. Tests cover:

- Base figure creation (grid, crosshair, dimensions)
- Room rendering with Z-level styling
- Exit line drawing
- Selection highlighting
- Flattened multi-level display
"""

import plotly.graph_objects as go

from pipeworks_mud_mapper.components.map_view import (
    SELECTED_ROOM_COLOR,
    Z_LEVEL_STYLES,
    Z_LEVEL_VISUAL_OFFSET,
    Z_RENDER_ORDER,
    create_map_figure,
    create_map_figure_with_rooms,
)


class TestCreateMapFigure:
    """Tests for create_map_figure function."""

    def test_returns_figure(self):
        """Function returns a Plotly Figure."""
        fig = create_map_figure()
        assert isinstance(fig, go.Figure)

    def test_no_title_by_default(self):
        """Default figure has no title."""
        fig = create_map_figure()
        # Title text should be None for flattened view
        # (Plotly returns an empty Title object, not None)
        assert fig.layout.title.text is None

    def test_custom_title(self):
        """Custom title is set when provided."""
        fig = create_map_figure(title="Test Zone")
        assert fig.layout.title.text == "Test Zone"

    def test_axis_range(self):
        """Axes have correct range (-21 to 21)."""
        fig = create_map_figure()
        # Plotly returns range as tuple
        assert fig.layout.xaxis.range == (-21, 21)
        assert fig.layout.yaxis.range == (-21, 21)

    def test_has_crosshair_shapes(self):
        """Figure has crosshair lines at origin."""
        fig = create_map_figure()
        # Should have 2 shapes (vertical and horizontal lines)
        assert len(fig.layout.shapes) == 2

        # Check one is vertical (x0 == x1 == 0) and one is horizontal (y0 == y1 == 0)
        shapes = fig.layout.shapes
        x_coords = [(s.x0, s.x1) for s in shapes]
        y_coords = [(s.y0, s.y1) for s in shapes]

        # Vertical line: x0 == x1 == 0
        assert (0, 0) in x_coords
        # Horizontal line: y0 == y1 == 0
        assert (0, 0) in y_coords

    def test_square_aspect_ratio(self):
        """Y axis is anchored to X for square aspect."""
        fig = create_map_figure()
        assert fig.layout.yaxis.scaleanchor == "x"
        assert fig.layout.yaxis.scaleratio == 1

    def test_fixed_dimensions(self):
        """Figure has fixed width and height."""
        fig = create_map_figure()
        assert fig.layout.width == 700
        assert fig.layout.height == 650
        assert fig.layout.autosize is False


class TestCreateMapFigureWithRooms:
    """Tests for create_map_figure_with_rooms function."""

    def test_returns_figure(self):
        """Function returns a Plotly Figure."""
        fig = create_map_figure_with_rooms()
        assert isinstance(fig, go.Figure)

    def test_empty_rooms_returns_base_figure(self):
        """Empty rooms dict returns base figure with only background trace."""
        fig = create_map_figure_with_rooms(rooms={})
        # Should only have the clickable background trace, no room traces
        room_traces = [t for t in fig.data if t.text is not None and len(t.text) > 0]
        assert len(room_traces) == 0

    def test_none_rooms_returns_base_figure(self):
        """None rooms returns base figure with only background trace."""
        fig = create_map_figure_with_rooms(rooms=None)
        # Should only have the clickable background trace, no room traces
        room_traces = [t for t in fig.data if t.text is not None and len(t.text) > 0]
        assert len(room_traces) == 0

    def test_single_room_at_origin(self):
        """Single room renders at correct position."""
        rooms = {
            "spawn": {
                "id": "spawn",
                "name": "Spawn Room",
                "coords": [0, 0, 0],
                "exits": {},
            }
        }
        fig = create_map_figure_with_rooms(rooms=rooms)
        # Should have at least one room trace
        assert len(fig.data) >= 1
        # Find the room trace (has text labels)
        room_traces = [t for t in fig.data if t.text is not None and len(t.text) > 0]
        assert len(room_traces) >= 1
        assert "spawn" in room_traces[0].text

    def test_default_shows_all_z_levels(self):
        """Default (no filter) shows all Z-levels."""
        rooms = {
            "ground": {"id": "ground", "name": "Ground", "coords": [0, 0, 0], "exits": {}},
            "basement": {"id": "basement", "name": "Basement", "coords": [0, 0, -1], "exits": {}},
            "attic": {"id": "attic", "name": "Attic", "coords": [0, 0, 1], "exits": {}},
        }
        fig = create_map_figure_with_rooms(rooms=rooms)
        room_traces = [t for t in fig.data if t.text is not None and len(t.text) > 0]
        all_labels = []
        for t in room_traces:
            all_labels.extend(t.text)
        assert "ground" in all_labels
        assert "basement" in all_labels
        assert "attic" in all_labels

    def test_room_filtering_by_visible_z_levels(self):
        """Only rooms on visible Z-levels are shown."""
        rooms = {
            "ground": {"id": "ground", "name": "Ground", "coords": [0, 0, 0], "exits": {}},
            "basement": {"id": "basement", "name": "Basement", "coords": [0, 0, -1], "exits": {}},
            "attic": {"id": "attic", "name": "Attic", "coords": [0, 0, 1], "exits": {}},
        }
        # Only show ground level
        fig = create_map_figure_with_rooms(rooms=rooms, visible_z_levels=[0])
        room_traces = [t for t in fig.data if t.text is not None and len(t.text) > 0]
        all_labels = []
        for t in room_traces:
            all_labels.extend(t.text)
        assert "ground" in all_labels
        assert "basement" not in all_labels
        assert "attic" not in all_labels

    def test_empty_filter_shows_no_rooms(self):
        """Empty filter list shows no rooms."""
        rooms = {
            "ground": {"id": "ground", "name": "Ground", "coords": [0, 0, 0], "exits": {}},
        }
        fig = create_map_figure_with_rooms(rooms=rooms, visible_z_levels=[])
        # Filter out the background trace when counting room traces
        room_traces = [t for t in fig.data if t.text is not None and len(t.text) > 0]
        assert len(room_traces) == 0

    def test_selected_room_highlighted(self):
        """Selected room has red color."""
        rooms = {
            "room1": {"id": "room1", "name": "Room 1", "coords": [0, 0, 0], "exits": {}},
            "room2": {"id": "room2", "name": "Room 2", "coords": [1, 0, 0], "exits": {}},
        }
        fig = create_map_figure_with_rooms(rooms=rooms, selected_room="room1")
        # Find the scatter trace with room markers (not background)
        room_traces = [t for t in fig.data if t.text is not None and len(t.text) > 0]
        room_trace = room_traces[0]
        # Selected room (room1) should have red color
        colors = room_trace.marker.color
        assert SELECTED_ROOM_COLOR in colors

    def test_exit_lines_drawn_between_rooms(self):
        """Exit connections are drawn as lines."""
        rooms = {
            "room1": {
                "id": "room1",
                "name": "Room 1",
                "coords": [0, 0, 0],
                "exits": {"east": "room2"},
            },
            "room2": {
                "id": "room2",
                "name": "Room 2",
                "coords": [1, 0, 0],
                "exits": {"west": "room1"},
            },
        }
        fig = create_map_figure_with_rooms(rooms=rooms)
        # Should have line traces for exits
        line_traces = [t for t in fig.data if t.mode == "lines"]
        assert len(line_traces) > 0

    def test_cross_zone_exits_skipped(self):
        """Exits with ':' (cross-zone) are not drawn."""
        rooms = {
            "room1": {
                "id": "room1",
                "name": "Room 1",
                "coords": [0, 0, 0],
                "exits": {"north": "other_zone:room"},  # Cross-zone exit
            },
        }
        fig = create_map_figure_with_rooms(rooms=rooms)
        # Should not have any line traces for cross-zone exit
        line_traces = [t for t in fig.data if t.mode == "lines"]
        assert len(line_traces) == 0

    def test_zone_exit_markers_rendered(self):
        """Cross-zone exits should render triangle markers."""
        rooms = {
            "room1": {
                "id": "room1",
                "name": "Room 1",
                "coords": [0, 0, 0],
                "exits": {"north": "other_zone:spawn"},
            },
        }
        fig = create_map_figure_with_rooms(rooms=rooms)
        marker_traces = [t for t in fig.data if t.mode == "markers" and t.hovertext is not None]
        assert any("Zone exit" in str(t.hovertext) for t in marker_traces)

    def test_hover_text_includes_z_level(self):
        """Hover text includes Z-level information."""
        rooms = {
            "spawn": {
                "id": "spawn",
                "name": "The Spawn Room",
                "coords": [0, 0, 0],
                "exits": {"north": "hall"},
            },
            "hall": {
                "id": "hall",
                "name": "Hall",
                "coords": [0, 1, 0],
                "exits": {"south": "spawn"},
            },
        }
        fig = create_map_figure_with_rooms(rooms=rooms)
        # Find room trace (not background)
        room_traces = [t for t in fig.data if t.text is not None and len(t.text) > 0]
        room_trace = room_traces[0]
        hover_texts = room_trace.hovertext
        # Check hover text contains room name and Z-level
        assert any("The Spawn Room" in str(h) for h in hover_texts)
        assert any("Z-level: 0" in str(h) for h in hover_texts)

    def test_z_level_styling(self):
        """Rooms have different sizes based on Z-level."""
        rooms = {
            "down": {"id": "down", "name": "Down", "coords": [0, 0, -1], "exits": {}},
            "ground": {"id": "ground", "name": "Ground", "coords": [5, 0, 0], "exits": {}},
            "up": {"id": "up", "name": "Up", "coords": [10, 0, 1], "exits": {}},
        }
        fig = create_map_figure_with_rooms(rooms=rooms)

        # Find traces for each Z-level based on marker size
        room_traces = [t for t in fig.data if t.text is not None and len(t.text) > 0]

        # Check sizes match Z_LEVEL_STYLES
        for trace in room_traces:
            size = trace.marker.size
            if "down" in trace.text:
                assert size == Z_LEVEL_STYLES[-1]["size"]
            elif "ground" in trace.text:
                assert size == Z_LEVEL_STYLES[0]["size"]
            elif "up" in trace.text:
                assert size == Z_LEVEL_STYLES[1]["size"]

    def test_vertical_exit_labels(self):
        """Stacked rooms with vertical exits show U/D labels."""
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
                "exits": {"up": "ground"},
            },
        }
        fig = create_map_figure_with_rooms(rooms=rooms)

        # Should have annotation for U/D label
        assert len(fig.layout.annotations) > 0
        labels = [a.text for a in fig.layout.annotations]
        # Should have U, D, or U/D label
        assert any(label in ["U", "D", "U/D"] for label in labels)

    def test_vertical_exit_lines(self):
        """Vertical exits should render dashed connector lines."""
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
                "exits": {"up": "ground"},
            },
        }
        fig = create_map_figure_with_rooms(rooms=rooms)

        dashed_lines = [
            trace
            for trace in fig.data
            if getattr(trace, "mode", None) == "lines"
            and getattr(trace, "line", None)
            and getattr(trace.line, "dash", None) == "dot"
        ]

        assert dashed_lines, "Expected dashed vertical exit line trace"


class TestZLevelConstants:
    """Tests for Z-level configuration constants."""

    def test_all_z_levels_have_styles(self):
        """All Z-levels (-1, 0, 1) should have style definitions."""
        assert -1 in Z_LEVEL_STYLES
        assert 0 in Z_LEVEL_STYLES
        assert 1 in Z_LEVEL_STYLES

    def test_z_minus_one_is_smallest(self):
        """z=-1 should have smallest marker size."""
        assert Z_LEVEL_STYLES[-1]["size"] < Z_LEVEL_STYLES[0]["size"]
        assert Z_LEVEL_STYLES[-1]["size"] < Z_LEVEL_STYLES[1]["size"]

    def test_z_zero_is_largest(self):
        """z=0 should have largest marker size."""
        assert Z_LEVEL_STYLES[0]["size"] > Z_LEVEL_STYLES[-1]["size"]
        assert Z_LEVEL_STYLES[0]["size"] > Z_LEVEL_STYLES[1]["size"]

    def test_render_order_ground_last(self):
        """Ground level (z=0) should be rendered last."""
        assert Z_RENDER_ORDER[-1] == 0

    def test_render_order_down_first(self):
        """Down level (z=-1) should be rendered first."""
        assert Z_RENDER_ORDER[0] == -1

    def test_selected_color_is_red(self):
        """Selected room color should be red."""
        assert "255" in SELECTED_ROOM_COLOR  # Red component
        assert "100" in SELECTED_ROOM_COLOR  # Specific shade

    def test_visual_offset_ground_is_zero(self):
        """Ground level (z=0) should have no visual offset."""
        assert Z_LEVEL_VISUAL_OFFSET[0] == (0.0, 0.0)

    def test_visual_offset_down_is_negative(self):
        """Down level (z=-1) should have negative offset."""
        offset = Z_LEVEL_VISUAL_OFFSET[-1]
        assert offset[0] < 0  # X offset negative
        assert offset[1] < 0  # Y offset negative

    def test_visual_offset_up_is_positive(self):
        """Up level (z=+1) should have positive offset."""
        offset = Z_LEVEL_VISUAL_OFFSET[1]
        assert offset[0] > 0  # X offset positive
        assert offset[1] > 0  # Y offset positive

    def test_visual_offset_symmetry(self):
        """Up and down offsets should be symmetric around ground."""
        down_offset = Z_LEVEL_VISUAL_OFFSET[-1]
        up_offset = Z_LEVEL_VISUAL_OFFSET[1]
        # X offsets should be opposite
        assert down_offset[0] == -up_offset[0]
        # Y offsets should be opposite
        assert down_offset[1] == -up_offset[1]
