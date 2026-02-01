"""Tests for the map view component."""

import plotly.graph_objects as go

from pipeworks_mud_mapper.components.map_view import (
    create_map_figure,
    create_map_figure_with_rooms,
)


class TestCreateMapFigure:
    """Tests for create_map_figure function."""

    def test_returns_figure(self):
        """Function returns a Plotly Figure."""
        fig = create_map_figure()
        assert isinstance(fig, go.Figure)

    def test_default_z_level(self):
        """Default z_level is 0."""
        fig = create_map_figure()
        assert "z = 0" in fig.layout.title.text

    def test_custom_z_level(self):
        """Z level is reflected in title."""
        fig = create_map_figure(z_level=-1)
        assert "z = -1" in fig.layout.title.text

        fig = create_map_figure(z_level=1)
        assert "z = 1" in fig.layout.title.text

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
        """Empty rooms dict returns base figure without room traces."""
        fig = create_map_figure_with_rooms(rooms={})
        # Should only have crosshair shapes, no data traces
        assert len(fig.data) == 0

    def test_none_rooms_returns_base_figure(self):
        """None rooms returns base figure."""
        fig = create_map_figure_with_rooms(rooms=None)
        assert len(fig.data) == 0

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
        fig = create_map_figure_with_rooms(rooms=rooms, z_level=0)
        # Should have one scatter trace for the room
        assert len(fig.data) >= 1
        # Find the room trace (has text labels)
        room_trace = [t for t in fig.data if t.text is not None and len(t.text) > 0][0]
        assert "spawn" in room_trace.text

    def test_room_filtering_by_z_level(self):
        """Only rooms on the specified z-level are shown."""
        rooms = {
            "ground": {"id": "ground", "name": "Ground", "coords": [0, 0, 0], "exits": {}},
            "basement": {"id": "basement", "name": "Basement", "coords": [0, 0, -1], "exits": {}},
            "attic": {"id": "attic", "name": "Attic", "coords": [0, 0, 1], "exits": {}},
        }
        # z=0 should only show "ground"
        fig = create_map_figure_with_rooms(rooms=rooms, z_level=0)
        room_traces = [t for t in fig.data if t.text is not None and len(t.text) > 0]
        all_labels = []
        for t in room_traces:
            all_labels.extend(t.text)
        assert "ground" in all_labels
        assert "basement" not in all_labels
        assert "attic" not in all_labels

    def test_selected_room_highlighted(self):
        """Selected room has different color."""
        rooms = {
            "room1": {"id": "room1", "name": "Room 1", "coords": [0, 0, 0], "exits": {}},
            "room2": {"id": "room2", "name": "Room 2", "coords": [1, 0, 0], "exits": {}},
        }
        fig = create_map_figure_with_rooms(rooms=rooms, z_level=0, selected_room="room1")
        # Find the scatter trace with room markers
        room_trace = [t for t in fig.data if t.text is not None and len(t.text) > 0][0]
        # Selected room (room1) should have red color
        colors = room_trace.marker.color
        assert "rgba(255, 100, 100, 1)" in colors  # Selected color

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
        fig = create_map_figure_with_rooms(rooms=rooms, z_level=0)
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
        fig = create_map_figure_with_rooms(rooms=rooms, z_level=0)
        # Should not have any line traces for cross-zone exit
        line_traces = [t for t in fig.data if t.mode == "lines"]
        assert len(line_traces) == 0

    def test_up_exit_shows_indicator(self):
        """Up exits show triangle-up indicator."""
        rooms = {
            "ground": {
                "id": "ground",
                "name": "Ground",
                "coords": [0, 0, 0],
                "exits": {"up": "attic"},
            },
            "attic": {
                "id": "attic",
                "name": "Attic",
                "coords": [0, 0, 1],
                "exits": {"down": "ground"},
            },
        }
        fig = create_map_figure_with_rooms(rooms=rooms, z_level=0)
        # Should have triangle-up marker
        triangle_traces = [
            t for t in fig.data if hasattr(t, "marker") and t.marker.symbol == "triangle-up"
        ]
        assert len(triangle_traces) > 0

    def test_down_exit_shows_indicator(self):
        """Down exits show triangle-down indicator."""
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
        fig = create_map_figure_with_rooms(rooms=rooms, z_level=0)
        # Should have triangle-down marker
        triangle_traces = [
            t for t in fig.data if hasattr(t, "marker") and t.marker.symbol == "triangle-down"
        ]
        assert len(triangle_traces) > 0

    def test_hover_text_includes_room_info(self):
        """Hover text includes room name and exits."""
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
        fig = create_map_figure_with_rooms(rooms=rooms, z_level=0)
        room_trace = [t for t in fig.data if t.text is not None and len(t.text) > 0][0]
        hover_texts = room_trace.hovertext
        # Check hover text contains room name
        assert any("The Spawn Room" in str(h) for h in hover_texts)
