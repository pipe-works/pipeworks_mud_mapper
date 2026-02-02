"""Callback modules for PipeWorks MUD Mapper.

This module provides Dash callbacks organized by functionality.
Callbacks are thin orchestrators that:

1. Extract data from component state
2. Call service functions for business logic
3. Return updated state to components

Architecture
------------
Callbacks are organized into functional modules:

**file_callbacks**
    File management: load, save, new map, export.
    Modal dialogs for zone creation.

**map_callbacks**
    Map visualization and interaction.
    Room selection via click events.

**room_callbacks**
    Room CRUD operations.
    Form population and validation.

**exit_callbacks**
    Exit checkbox handling.
    Bidirectional exit management.

Registration
------------
Callbacks are registered when their modules are imported.
The app.py module imports all callback modules after
initializing the Dash app::

    from pipeworks_mud_mapper.callbacks import register_callbacks

    app = dash.Dash(...)
    register_callbacks(app)

See Also
--------
- ``layout/``: UI components that callbacks interact with
- ``services/``: Business logic called by callbacks
- ``refactor_01.md``: Architecture decisions
"""

from pipeworks_mud_mapper.callbacks import (
    exit_callbacks,  # noqa: F401
    file_callbacks,  # noqa: F401
    map_callbacks,  # noqa: F401
    room_callbacks,  # noqa: F401
)


def register_callbacks(app) -> None:
    """Register all callbacks with the Dash app.

    This function is called after app initialization to ensure
    all callbacks are properly registered.

    Parameters
    ----------
    app : dash.Dash
        The Dash application instance.

    Notes
    -----
    In Dash, callbacks are registered via the @callback decorator
    which uses the global app context. Importing the callback modules
    is sufficient to register them, but this function provides an
    explicit registration point for clarity.
    """
    # Callbacks are registered on import via @callback decorators
    # This function exists to make registration explicit in app.py
    pass
