"""Action bar component for the bottom of the application.

The action bar provides status information and debug output. Primary
action buttons (Save, Export, Validate) are located in the file browser
for better accessibility.

Component Structure
-------------------
::

    ┌───────────────────────────────────────────────────────────────────┐
    │                                              [debug-btn-state]    │
    └───────────────────────────────────────────────────────────────────┘

Component IDs
-------------
- ``debug-btn-state``: Debug output for button state (hidden in production)

Notes
-----
The action bar was simplified in v0.0.8 after discovering that flexbox
layout caused visibility issues with dynamically-enabled dbc.Button
components. Primary action buttons were moved to the file browser
panel which uses a simple stacked layout.

See Also
--------
- ``file_browser.py``: Contains Save, Export, and Validate buttons
- ``callbacks/file_callbacks.py``: Callbacks for save operations
- ``callbacks/validation_callbacks.py``: Callbacks for validation
"""

from dash import html


def create_action_bar() -> html.Div:
    """Create the bottom action bar.

    The action bar provides a consistent footer area. Primary action
    buttons are located in the file browser panel for better UX.

    Returns
    -------
    html.Div
        Container with action bar content.

    Component IDs
    -------------
    - ``debug-btn-state``: Debug output span (development use)

    Notes
    -----
    This component was simplified after flexbox issues in v0.0.8.
    The Save, Export, and Validate buttons now live in file_browser.py.
    """
    return html.Div(
        [
            # Spacer to push debug output to the right
            html.Span(className="flex-grow-1"),
            # Debug output for development - shows button state
            # Can be hidden in production via CSS if needed
            html.Span(
                id="debug-btn-state",
                children="",
                className="small text-muted",
            ),
        ],
        className="d-flex align-items-center p-2 bg-light border-top",
    )
