"""Tests for the map view component."""

import plotly.graph_objects as go

from pipeworks_mud_mapper.components.map_view import create_map_figure


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
