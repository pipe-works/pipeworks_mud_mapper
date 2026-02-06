"""Theme toggle callbacks."""

from typing import cast

import dash_bootstrap_components as dbc
from dash import Input, Output, callback

# Bootstrap theme URLs are provided by dash-bootstrap-components.
# We keep them here so tests can validate the behavior without
# hard-coding CDN strings.
THEME_LIGHT = cast(str, dbc.themes.BOOTSTRAP)
THEME_DARK = cast(str, dbc.themes.DARKLY)


@callback(
    Output("theme-link", "href"),
    Input("theme-toggle", "value"),
)
def update_theme(is_dark: bool) -> str:
    """Swap the Bootstrap theme stylesheet based on the toggle state."""
    # The layout injects a <link> tag; swapping href is the most lightweight
    # way to flip themes without rebuilding the app or reloading the page.
    return THEME_DARK if is_dark else THEME_LIGHT
