"""Main Dash application for the PipeWorks MUD Mapper.

This module provides the web-based zone editor application entry point.
The application is built using Dash and Plotly for interactive visualization
and editing of MUD zone files.

Architecture
------------
The application follows a modular architecture:

- **layout/**: UI structure (Dash components)
- **callbacks/**: Interactivity (Dash callbacks)
- **services/**: Business logic (pure Python)
- **models/**: Domain models (Pydantic)
- **components/**: Reusable Plotly/Dash components
- **utils/**: File I/O and utilities

Application Flow
----------------
1. App initializes with Bootstrap theme
2. Layout is created from layout/ modules
3. Callbacks are registered from callbacks/ modules
4. run_app() starts the development server

Usage
-----
Run the application from command line::

    python -m pipeworks_mud_mapper

Or import and run programmatically::

    from pipeworks_mud_mapper.app import run_app
    run_app(debug=True, port=8050)

Access the application at http://127.0.0.1:8050 in your browser.

See Also
--------
- ``layout/``: UI component definitions
- ``callbacks/``: Callback definitions
- ``services/``: Business logic
- ``models/``: Domain models
"""

import dash
import dash_bootstrap_components as dbc

from pipeworks_mud_mapper.layout import create_app_layout
from pipeworks_mud_mapper.services.app_config import get_server_settings

# =============================================================================
# Application Initialization
# =============================================================================

app = dash.Dash(
    __name__,
    # Load only the Bootstrap icon set here.
    # Theme CSS is injected via a layout <link> so it can be toggled at runtime.
    external_stylesheets=[dbc.icons.BOOTSTRAP],
    title="PipeWorks MUD Mapper",
)
"""
The main Dash application instance.

Configured with:
- Bootstrap theme for consistent styling
- Custom title shown in browser tab
- Serves the Flask app on run()
"""

# =============================================================================
# Application Layout
# =============================================================================

app.layout = create_app_layout()

# =============================================================================
# Callback Registration
# =============================================================================

# Import callback modules to register them with the app.
# Callbacks use the @callback decorator which registers automatically.
from pipeworks_mud_mapper.callbacks import register_callbacks  # noqa: E402

register_callbacks(app)


# =============================================================================
# Application Entry Point
# =============================================================================


def run_app(debug: bool = True, port: int | None = None) -> None:
    """Run the Dash application.

    Starts the Flask development server and opens the mapper
    application in the browser.

    Parameters
    ----------
    debug : bool, optional
        Enable debug mode with auto-reload (default: True).
        Set to False for production deployments.
    port : int | None, optional
        Port to run the server on. When omitted, uses config/server.ini
        (or the default 8050 when not configured).

    Examples
    --------
    Run with defaults::

        >>> from pipeworks_mud_mapper.app import run_app
        >>> run_app()

    Run on different port::

        >>> run_app(debug=False, port=8080)

    Notes
    -----
    - In debug mode, the server auto-reloads on code changes
    - Access the application at http://127.0.0.1:{port}
    - Ctrl+C to stop the server
    """
    if port is None:
        port = get_server_settings()["port"]
    app.run(debug=debug, port=port)
