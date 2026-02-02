"""Validation callbacks for PipeWorks MUD Mapper.

This module provides callbacks for running validation checks on map files
and displaying results in a modal dialog. It also writes validation reports
to the data/validation/ directory for CI/CD and record-keeping purposes.

Callbacks
---------
``update_validate_button_state``
    Enables/disables the Validate button based on whether a map is loaded.

``run_validation``
    Runs all validation checks, opens the results modal, writes report file.

``close_validation_modal``
    Closes the validation results modal.

``select_room_from_validation``
    Handles clicking on a room ID in validation results to select it on map.

Validation Categories
---------------------
The validation service checks for three categories of issues:

**Connectivity**
    - Broken exit references (ERROR - blocks export)
    - Unreachable rooms from spawn (WARNING)
    - Dead-end rooms with no exits (INFO)

**Consistency**
    - Asymmetric exits (INFO - may be intentional one-way doors)
    - Direction/coordinate mismatches (WARNING)

**Language**
    - "Upper Landing" problem - vertical words in names that don't match
      the navigational direction (INFO)

Severity Levels
---------------
- **ERROR**: Must be fixed before export (broken references)
- **WARNING**: Should be reviewed but may be intentional
- **INFO**: Informational - worth noting but likely intentional

See Also
--------
- ``services/validation_service.py``: Validation logic and report generation
- ``layout/main_layout.py``: Validation modal definition
- ``layout/file_browser.py``: Validate button location
"""

import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, ctx, html, no_update

from pipeworks_mud_mapper.models import MapFile
from pipeworks_mud_mapper.services import validation_service


@callback(
    Output("validate-zone-btn", "disabled"),
    Input("selected-file", "data"),
)
def update_validate_button_state(selected_file: str | None) -> bool:
    """Enable/disable the Validate button based on whether a map is loaded.

    The Validate button is enabled when a map file is loaded (selected-file
    is not None). This prevents users from attempting to validate when
    there's no data to check.

    Parameters
    ----------
    selected_file : str or None
        Currently selected map file name, or None if no file is loaded.

    Returns
    -------
    bool
        True to disable the button (no file), False to enable (file loaded).
    """
    # Button is disabled when no file is selected
    return selected_file is None


@callback(
    Output("validation-results-modal", "is_open", allow_duplicate=True),
    Output("validation-results-body", "children"),
    Output("validation-report", "data"),
    Input("validate-zone-btn", "n_clicks"),
    State("current-zone-data", "data"),
    State("selected-file", "data"),
    prevent_initial_call=True,
)
def run_validation(
    n_clicks: int | None,
    zone_data: dict | None,
    selected_file: str | None,
) -> tuple:
    """Run validation checks and display results in modal.

    This callback:
    1. Converts the zone data to a MapFile model
    2. Runs all validation checks via validation_service
    3. Writes a validation report to data/validation/
    4. Opens the modal with formatted results

    Parameters
    ----------
    n_clicks : int or None
        Number of times the Validate button has been clicked.
    zone_data : dict or None
        Current zone data from the store.
    selected_file : str or None
        Name of the currently selected map file.

    Returns
    -------
    tuple
        (modal_is_open, modal_body_children, validation_report_data)
        - modal_is_open: True to show the modal
        - modal_body_children: Formatted validation results
        - validation_report_data: Report dict for storage
    """
    # Early return if no click or no data
    if not n_clicks or not zone_data or not selected_file:
        return no_update, no_update, no_update

    # Convert zone data to MapFile model for validation
    map_file = MapFile.from_dict(zone_data)

    # Run all validation checks
    warnings = validation_service.validate_all(map_file)

    # Write validation report to file
    try:
        report_path = validation_service.write_validation_report(selected_file, warnings)
        report_written = True
    except OSError:
        report_path = None
        report_written = False

    # Create the validation report for storage
    report = validation_service.create_validation_report(selected_file, warnings)

    # Build the modal content
    modal_content = _build_validation_modal_content(warnings, report, report_path, report_written)

    return True, modal_content, report


def _build_validation_modal_content(
    warnings: list,
    report: dict,
    report_path: str | None,
    report_written: bool,
) -> list:
    """Build the modal body content from validation results.

    Creates a structured display with:
    - Summary banner showing pass/fail and counts
    - Report file path (if written successfully)
    - Categorized list of warnings with severity icons

    Parameters
    ----------
    warnings : list
        List of ValidationWarning objects from validation_service.
    report : dict
        Validation report dictionary with summary counts.
    report_path : str or None
        Path where report was written, or None if write failed.
    report_written : bool
        Whether the report was successfully written to disk.

    Returns
    -------
    list
        List of Dash components for the modal body.
    """
    content = []
    summary = report["summary"]

    # -------------------------------------------------------------------------
    # Summary Banner
    # -------------------------------------------------------------------------
    if summary["passed"]:
        # Success banner - no errors found
        banner_color = "success"
        banner_icon = "bi-check-circle-fill"
        banner_text = "Validation Passed"
        banner_subtext = "No errors found. Map is ready for export."
    else:
        # Error banner - errors must be fixed
        banner_color = "danger"
        banner_icon = "bi-x-circle-fill"
        banner_text = "Validation Failed"
        banner_subtext = f"{summary['errors']} error(s) must be fixed before export."

    content.append(
        dbc.Alert(
            [
                html.I(className=f"bi {banner_icon} me-2"),
                html.Strong(banner_text),
                html.Div(banner_subtext, className="small mt-1"),
            ],
            color=banner_color,
            className="mb-3",
        )
    )

    # -------------------------------------------------------------------------
    # Summary Counts
    # -------------------------------------------------------------------------
    content.append(
        html.Div(
            [
                # Error count badge
                dbc.Badge(
                    f"{summary['errors']} Errors",
                    color="danger" if summary["errors"] > 0 else "secondary",
                    className="me-2",
                ),
                # Warning count badge
                dbc.Badge(
                    f"{summary['warnings']} Warnings",
                    color="warning" if summary["warnings"] > 0 else "secondary",
                    className="me-2",
                ),
                # Info count badge
                dbc.Badge(
                    f"{summary['info']} Info",
                    color="info" if summary["info"] > 0 else "secondary",
                    className="me-2",
                ),
            ],
            className="mb-3",
        )
    )

    # -------------------------------------------------------------------------
    # Report File Path
    # -------------------------------------------------------------------------
    if report_written and report_path:
        content.append(
            html.Div(
                [
                    html.I(className="bi bi-file-earmark-text me-2 text-muted"),
                    html.Small(
                        f"Report saved: {report_path}",
                        className="text-muted font-monospace",
                    ),
                ],
                className="mb-3",
            )
        )

    # -------------------------------------------------------------------------
    # Warnings List (grouped by category)
    # -------------------------------------------------------------------------
    if warnings:
        # Group warnings by category
        categories: dict[str, list] = {"connectivity": [], "consistency": [], "language": []}
        for w in warnings:
            if w.category in categories:
                categories[w.category].append(w)

        # Add each category section
        for category, cat_warnings in categories.items():
            if not cat_warnings:
                continue

            # Category header with icon
            cat_icons = {
                "connectivity": "bi-diagram-3",
                "consistency": "bi-arrow-left-right",
                "language": "bi-chat-quote",
            }
            cat_titles = {
                "connectivity": "Connectivity Issues",
                "consistency": "Exit Consistency",
                "language": "Language-Direction Conflicts",
            }

            content.append(
                html.H6(
                    [
                        html.I(className=f"bi {cat_icons[category]} me-2"),
                        cat_titles[category],
                    ],
                    className="mt-3 mb-2",
                )
            )

            # Warning items
            for warning in cat_warnings:
                # Severity icon and color
                if warning.severity.value == "error":
                    icon = "bi-x-circle-fill text-danger"
                elif warning.severity.value == "warning":
                    icon = "bi-exclamation-triangle-fill text-warning"
                else:
                    icon = "bi-info-circle-fill text-info"

                # Build warning item with clickable room ID
                warning_content = [
                    html.I(className=f"bi {icon} me-2"),
                ]

                # Add clickable room ID if present
                if warning.room_id:
                    warning_content.append(
                        html.Span(
                            f"[{warning.room_id}]",
                            id={"type": "validation-room-link", "room": warning.room_id},
                            className="font-monospace text-primary me-2",
                            style={"cursor": "pointer", "textDecoration": "underline"},
                            title="Click to select room on map",
                        )
                    )

                warning_content.append(html.Span(warning.message))

                content.append(
                    html.Div(
                        warning_content,
                        className="mb-2 small",
                    )
                )
    else:
        # No warnings at all - show success message
        content.append(
            html.Div(
                [
                    html.I(className="bi bi-emoji-smile me-2 text-success"),
                    "No issues found. Your map is looking good!",
                ],
                className="text-center text-muted mt-4",
            )
        )

    return content


@callback(
    Output("validation-results-modal", "is_open", allow_duplicate=True),
    Input("validation-close-btn", "n_clicks"),
    prevent_initial_call=True,
)
def close_validation_modal(n_clicks: int | None):
    """Close the validation results modal.

    Parameters
    ----------
    n_clicks : int or None
        Number of times the Close button has been clicked.

    Returns
    -------
    bool or dash.no_update
        False to close the modal, or no_update if not clicked.
    """
    if n_clicks:
        return False
    return no_update


@callback(
    Output("selected-room", "data", allow_duplicate=True),
    Output("validation-results-modal", "is_open", allow_duplicate=True),
    Input({"type": "validation-room-link", "room": "__all__"}, "n_clicks"),
    State({"type": "validation-room-link", "room": "__all__"}, "id"),
    prevent_initial_call=True,
)
def select_room_from_validation(n_clicks_list: list, id_list: list) -> tuple:
    """Handle clicking on a room ID in validation results.

    When a user clicks on a room ID in the validation results, this callback:
    1. Selects that room on the map
    2. Closes the validation modal so the user can see the room

    Parameters
    ----------
    n_clicks_list : list
        List of n_clicks values for all room links.
    id_list : list
        List of ID dictionaries for all room links.

    Returns
    -------
    tuple
        (selected_room_id, modal_is_open)
        - selected_room_id: The room ID that was clicked
        - modal_is_open: False to close the modal
    """
    # Find which room was clicked by checking ctx.triggered_id
    if not ctx.triggered_id:
        return no_update, no_update

    # ctx.triggered_id will be the dict with the room ID
    triggered_id = ctx.triggered_id
    if isinstance(triggered_id, dict) and "room" in triggered_id:
        room_id = triggered_id["room"]
        # Select the room and close the modal
        return room_id, False

    return no_update, no_update
