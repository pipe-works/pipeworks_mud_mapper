"""Comprehensive tests for PipeWorks MUD Mapper layout module.

This module tests the UI layout components that define the application structure.
Layout functions create Dash components that are then wired up with callbacks.

Test Organization
-----------------
Tests are grouped by layout module:

- **TestActionBar**: Action bar with save/export buttons and status
- **TestFileBrowser**: File browser with file list and new map button
- **TestMapPanel**: Map visualization and z-level selector
- **TestPropertiesPanel**: Room editing form with coordinates and exits
- **TestMainLayout**: Complete application layout assembly
- **TestLayoutIntegration**: Cross-component verification

Design Notes
------------
Layout tests verify:

1. Functions return correct component types
2. Critical component IDs exist (required for callbacks)
3. Component structure matches expected hierarchy
4. Default values are set correctly

These are structural tests - they verify the UI is built correctly,
not that it behaves correctly (that's what callback tests do).

See Also
--------
- ``layout/``: The layout modules being tested
- ``test_callbacks.py``: Tests for callback behavior
"""

import dash_bootstrap_components as dbc
from dash import dcc, html

from pipeworks_mud_mapper.layout import (
    create_action_bar,
    create_app_layout,
    create_file_browser,
    create_map_panel,
    create_properties_panel,
)

# =============================================================================
# Helper Functions
# =============================================================================


def find_component_by_id(component, target_id: str):
    """Recursively search for a component with the given ID.

    Parameters
    ----------
    component : dash component
        Root component to search from.
    target_id : str
        Component ID to find.

    Returns
    -------
    component or None
        The component with matching ID, or None if not found.
    """
    # Check if this component has the target ID
    if hasattr(component, "id") and component.id == target_id:
        return component

    # Check children
    if hasattr(component, "children"):
        children = component.children
        if children is None:
            return None
        if not isinstance(children, list):
            children = [children]
        for child in children:
            if child is not None:
                result = find_component_by_id(child, target_id)
                if result is not None:
                    return result

    return None


def component_has_id(component, target_id: str) -> bool:
    """Check if a component or its children contain the target ID.

    Parameters
    ----------
    component : dash component
        Root component to search from.
    target_id : str
        Component ID to find.

    Returns
    -------
    bool
        True if component with target ID exists.
    """
    return find_component_by_id(component, target_id) is not None


def get_all_component_ids(component) -> set[str]:
    """Recursively collect all component IDs.

    Parameters
    ----------
    component : dash component
        Root component to search from.

    Returns
    -------
    set[str]
        Set of all component IDs found.
    """
    ids = set()

    if hasattr(component, "id") and component.id is not None:
        # Handle pattern-matching IDs (dicts)
        if isinstance(component.id, str):
            ids.add(component.id)

    if hasattr(component, "children"):
        children = component.children
        if children is not None:
            if not isinstance(children, list):
                children = [children]
            for child in children:
                if child is not None:
                    ids.update(get_all_component_ids(child))

    return ids


# =============================================================================
# Action Bar Tests
# =============================================================================


class TestActionBar:
    """Tests for action_bar module."""

    def test_create_action_bar_returns_div(self):
        """create_action_bar should return an html.Div."""
        result = create_action_bar()
        assert isinstance(result, html.Div)

    def test_create_action_bar_has_save_button(self):
        """create_action_bar should include save-map-btn."""
        result = create_action_bar()
        assert component_has_id(result, "save-map-btn")

    def test_create_action_bar_has_export_button(self):
        """create_action_bar should include export-zone-btn."""
        result = create_action_bar()
        assert component_has_id(result, "export-zone-btn")

    def test_create_action_bar_has_status_indicator(self):
        """create_action_bar should include status-indicator."""
        result = create_action_bar()
        assert component_has_id(result, "status-indicator")

    def test_create_action_bar_buttons_initially_disabled(self):
        """create_action_bar buttons should start disabled."""
        result = create_action_bar()
        save_btn = find_component_by_id(result, "save-map-btn")
        export_btn = find_component_by_id(result, "export-zone-btn")

        assert save_btn.disabled is True
        assert export_btn.disabled is True

    def test_create_action_bar_has_validate_button(self):
        """create_action_bar should include validate button (placeholder)."""
        result = create_action_bar()
        # Validate button doesn't have an ID (placeholder), but should exist
        # Check that we have at least 3 buttons (Validate, Export, Save)
        buttons = [child for child in result.children if isinstance(child, dbc.Button)]
        assert len(buttons) >= 3

    def test_create_action_bar_status_default_text(self):
        """create_action_bar status should show 'No file loaded' initially."""
        result = create_action_bar()
        status = find_component_by_id(result, "status-indicator")
        # Status children should include "No file loaded" text
        assert "No file loaded" in str(status.children)


# =============================================================================
# File Browser Tests
# =============================================================================


class TestFileBrowser:
    """Tests for file_browser module."""

    def test_create_file_browser_returns_card(self):
        """create_file_browser should return a dbc.Card."""
        result = create_file_browser()
        assert isinstance(result, dbc.Card)

    def test_create_file_browser_has_file_list_container(self):
        """create_file_browser should include file-list-container."""
        result = create_file_browser()
        assert component_has_id(result, "file-list-container")

    def test_create_file_browser_has_new_map_button(self):
        """create_file_browser should include new-map-btn."""
        result = create_file_browser()
        assert component_has_id(result, "new-map-btn")

    def test_create_file_browser_has_header(self):
        """create_file_browser should have 'File Browser' header."""
        result = create_file_browser()
        # Card should have CardHeader as first child
        assert isinstance(result.children[0], dbc.CardHeader)
        assert "File Browser" in str(result.children[0].children)

    def test_create_file_browser_has_folder_icon(self):
        """create_file_browser should show folder with 'maps/' label."""
        result = create_file_browser()
        card_body = result.children[1]  # CardBody
        # Should contain "maps/" text
        assert "maps/" in str(card_body.children)

    def test_create_file_browser_new_map_button_style(self):
        """create_file_browser new-map-btn should be secondary outline."""
        result = create_file_browser()
        new_map_btn = find_component_by_id(result, "new-map-btn")
        assert new_map_btn.color == "secondary"
        assert new_map_btn.outline is True


# =============================================================================
# Map Panel Tests
# =============================================================================


class TestMapPanel:
    """Tests for map_panel module."""

    def test_create_map_panel_returns_card(self):
        """create_map_panel should return a dbc.Card."""
        result = create_map_panel()
        assert isinstance(result, dbc.Card)

    def test_create_map_panel_has_map_graph(self):
        """create_map_panel should include map-graph."""
        result = create_map_panel()
        assert component_has_id(result, "map-graph")

    def test_create_map_panel_has_z_level_selector(self):
        """create_map_panel should include z-level-selector."""
        result = create_map_panel()
        assert component_has_id(result, "z-level-selector")

    def test_create_map_panel_graph_is_dcc_graph(self):
        """create_map_panel map-graph should be a dcc.Graph."""
        result = create_map_panel()
        graph = find_component_by_id(result, "map-graph")
        assert isinstance(graph, dcc.Graph)

    def test_create_map_panel_graph_has_figure(self):
        """create_map_panel map-graph should have initial figure."""
        result = create_map_panel()
        graph = find_component_by_id(result, "map-graph")
        assert graph.figure is not None

    def test_create_map_panel_z_selector_has_three_options(self):
        """create_map_panel z-level-selector should have -1, 0, +1 options."""
        result = create_map_panel()
        z_selector = find_component_by_id(result, "z-level-selector")
        assert isinstance(z_selector, dbc.RadioItems)
        assert len(z_selector.options) == 3
        values = [opt["value"] for opt in z_selector.options]
        assert -1 in values
        assert 0 in values
        assert 1 in values

    def test_create_map_panel_z_selector_default_is_zero(self):
        """create_map_panel z-level-selector should default to 0."""
        result = create_map_panel()
        z_selector = find_component_by_id(result, "z-level-selector")
        assert z_selector.value == 0

    def test_create_map_panel_graph_config_scroll_zoom(self):
        """create_map_panel map-graph should have scrollZoom enabled."""
        result = create_map_panel()
        graph = find_component_by_id(result, "map-graph")
        assert graph.config.get("scrollZoom") is True

    def test_create_map_panel_graph_config_mode_bar(self):
        """create_map_panel map-graph should have mode bar enabled."""
        result = create_map_panel()
        graph = find_component_by_id(result, "map-graph")
        assert graph.config.get("displayModeBar") is True


# =============================================================================
# Properties Panel Tests
# =============================================================================


class TestPropertiesPanel:
    """Tests for properties_panel module."""

    def test_create_properties_panel_returns_card(self):
        """create_properties_panel should return a dbc.Card."""
        result = create_properties_panel()
        assert isinstance(result, dbc.Card)

    def test_create_properties_panel_has_room_id_input(self):
        """create_properties_panel should include room-id input."""
        result = create_properties_panel()
        assert component_has_id(result, "room-id")

    def test_create_properties_panel_has_room_name_input(self):
        """create_properties_panel should include room-name input."""
        result = create_properties_panel()
        assert component_has_id(result, "room-name")

    def test_create_properties_panel_has_room_description_input(self):
        """create_properties_panel should include room-description textarea."""
        result = create_properties_panel()
        assert component_has_id(result, "room-description")

    def test_create_properties_panel_has_coordinate_inputs(self):
        """create_properties_panel should include X, Y, Z coordinate inputs."""
        result = create_properties_panel()
        assert component_has_id(result, "room-coord-x")
        assert component_has_id(result, "room-coord-y")
        assert component_has_id(result, "room-coord-z")

    def test_create_properties_panel_has_add_room_button(self):
        """create_properties_panel should include add-room-btn."""
        result = create_properties_panel()
        assert component_has_id(result, "add-room-btn")

    def test_create_properties_panel_has_update_room_button(self):
        """create_properties_panel should include update-room-btn."""
        result = create_properties_panel()
        assert component_has_id(result, "update-room-btn")

    def test_create_properties_panel_has_new_room_button(self):
        """create_properties_panel should include new-room-btn."""
        result = create_properties_panel()
        assert component_has_id(result, "new-room-btn")

    def test_create_properties_panel_has_exit_checkboxes(self):
        """create_properties_panel should include exit-checkboxes."""
        result = create_properties_panel()
        assert component_has_id(result, "exit-checkboxes")

    def test_create_properties_panel_has_exit_feedback(self):
        """create_properties_panel should include exit-feedback."""
        result = create_properties_panel()
        assert component_has_id(result, "exit-feedback")

    def test_create_properties_panel_has_form_feedback(self):
        """create_properties_panel should include room-form-feedback."""
        result = create_properties_panel()
        assert component_has_id(result, "room-form-feedback")

    def test_create_properties_panel_exit_checkboxes_has_six_options(self):
        """create_properties_panel exit-checkboxes should have N,E,S,W,U,D."""
        result = create_properties_panel()
        checkboxes = find_component_by_id(result, "exit-checkboxes")
        assert isinstance(checkboxes, dbc.Checklist)
        assert len(checkboxes.options) == 6
        values = [opt["value"] for opt in checkboxes.options]
        assert set(values) == {"N", "E", "S", "W", "U", "D"}

    def test_create_properties_panel_exit_checkboxes_empty_default(self):
        """create_properties_panel exit-checkboxes should default to empty."""
        result = create_properties_panel()
        checkboxes = find_component_by_id(result, "exit-checkboxes")
        assert checkboxes.value == []

    def test_create_properties_panel_update_button_disabled(self):
        """create_properties_panel update-room-btn should start disabled."""
        result = create_properties_panel()
        update_btn = find_component_by_id(result, "update-room-btn")
        assert update_btn.disabled is True

    def test_create_properties_panel_coords_default_zero(self):
        """create_properties_panel coordinate inputs should default to 0."""
        result = create_properties_panel()
        coord_x = find_component_by_id(result, "room-coord-x")
        coord_y = find_component_by_id(result, "room-coord-y")
        coord_z = find_component_by_id(result, "room-coord-z")
        assert coord_x.value == 0
        assert coord_y.value == 0
        assert coord_z.value == 0

    def test_create_properties_panel_has_header(self):
        """create_properties_panel should have 'Room Properties' header."""
        result = create_properties_panel()
        assert isinstance(result.children[0], dbc.CardHeader)
        assert "Room Properties" in str(result.children[0].children)


# =============================================================================
# Main Layout Tests
# =============================================================================


class TestMainLayout:
    """Tests for main_layout module."""

    def test_create_app_layout_returns_container(self):
        """create_app_layout should return a dbc.Container."""
        result = create_app_layout()
        assert isinstance(result, dbc.Container)

    def test_create_app_layout_is_fluid(self):
        """create_app_layout container should be fluid."""
        result = create_app_layout()
        assert result.fluid is True

    def test_create_app_layout_has_zone_files_store(self):
        """create_app_layout should include zone-files-store."""
        result = create_app_layout()
        assert component_has_id(result, "zone-files-store")

    def test_create_app_layout_has_current_zone_data_store(self):
        """create_app_layout should include current-zone-data store."""
        result = create_app_layout()
        assert component_has_id(result, "current-zone-data")

    def test_create_app_layout_has_selected_file_store(self):
        """create_app_layout should include selected-file store."""
        result = create_app_layout()
        assert component_has_id(result, "selected-file")

    def test_create_app_layout_has_selected_room_store(self):
        """create_app_layout should include selected-room store."""
        result = create_app_layout()
        assert component_has_id(result, "selected-room")

    def test_create_app_layout_has_unsaved_changes_store(self):
        """create_app_layout should include has-unsaved-changes store."""
        result = create_app_layout()
        assert component_has_id(result, "has-unsaved-changes")

    def test_create_app_layout_has_initial_load_interval(self):
        """create_app_layout should include initial-load interval."""
        result = create_app_layout()
        assert component_has_id(result, "initial-load")

    def test_create_app_layout_has_current_zone_display(self):
        """create_app_layout should include current-zone display."""
        result = create_app_layout()
        assert component_has_id(result, "current-zone")

    def test_create_app_layout_has_new_map_modal(self):
        """create_app_layout should include new-map-modal."""
        result = create_app_layout()
        assert component_has_id(result, "new-map-modal")

    def test_create_app_layout_stores_have_defaults(self):
        """create_app_layout stores should have appropriate defaults."""
        result = create_app_layout()

        zone_files = find_component_by_id(result, "zone-files-store")
        assert zone_files.data == []

        current_zone = find_component_by_id(result, "current-zone-data")
        assert current_zone.data is None

        selected_file = find_component_by_id(result, "selected-file")
        assert selected_file.data is None

        selected_room = find_component_by_id(result, "selected-room")
        assert selected_room.data is None

        unsaved = find_component_by_id(result, "has-unsaved-changes")
        assert unsaved.data is False

    def test_create_app_layout_interval_triggers_once(self):
        """create_app_layout initial-load should trigger once."""
        result = create_app_layout()
        interval = find_component_by_id(result, "initial-load")
        assert isinstance(interval, dcc.Interval)
        assert interval.max_intervals == 1

    def test_create_app_layout_contains_all_panels(self):
        """create_app_layout should contain file browser, map, and properties."""
        result = create_app_layout()
        ids = get_all_component_ids(result)

        # File browser IDs
        assert "file-list-container" in ids
        assert "new-map-btn" in ids

        # Map panel IDs
        assert "map-graph" in ids
        assert "z-level-selector" in ids

        # Properties panel IDs
        assert "room-id" in ids
        assert "room-name" in ids
        assert "exit-checkboxes" in ids

        # Action bar IDs
        assert "save-map-btn" in ids
        assert "export-zone-btn" in ids
        assert "status-indicator" in ids


# =============================================================================
# Integration Tests
# =============================================================================


class TestLayoutIntegration:
    """Integration tests verifying layout component relationships."""

    def test_all_callback_ids_exist(self):
        """All IDs required by callbacks should exist in the layout."""
        result = create_app_layout()
        ids = get_all_component_ids(result)

        # IDs used in file_callbacks.py
        file_callback_ids = [
            "zone-files-store",
            "initial-load",
            "file-list-container",
            "selected-file",
            "current-zone-data",
            "current-zone",
            "new-map-btn",
            "new-map-modal",
            "new-map-cancel-btn",
            "new-map-create-btn",
            "new-zone-id",
            "new-zone-name",
            "new-zone-description",
            "new-map-feedback",
            "save-map-btn",
            "export-zone-btn",
            "has-unsaved-changes",
            "status-indicator",
        ]
        for id_ in file_callback_ids:
            assert id_ in ids, f"Missing ID for file callbacks: {id_}"

        # IDs used in map_callbacks.py
        map_callback_ids = [
            "map-graph",
            "z-level-selector",
            "selected-room",
        ]
        for id_ in map_callback_ids:
            assert id_ in ids, f"Missing ID for map callbacks: {id_}"

        # IDs used in room_callbacks.py
        room_callback_ids = [
            "add-room-btn",
            "new-room-btn",
            "update-room-btn",
            "room-id",
            "room-name",
            "room-description",
            "room-coord-x",
            "room-coord-y",
            "room-coord-z",
            "room-form-feedback",
        ]
        for id_ in room_callback_ids:
            assert id_ in ids, f"Missing ID for room callbacks: {id_}"

        # IDs used in exit_callbacks.py
        exit_callback_ids = [
            "exit-checkboxes",
            "exit-feedback",
        ]
        for id_ in exit_callback_ids:
            assert id_ in ids, f"Missing ID for exit callbacks: {id_}"

    def test_no_duplicate_ids(self):
        """Layout should not have duplicate component IDs."""
        result = create_app_layout()

        # Collect all IDs with their counts
        id_counts: dict[str, int] = {}

        def count_ids(component):
            if hasattr(component, "id") and component.id is not None:
                if isinstance(component.id, str):
                    id_counts[component.id] = id_counts.get(component.id, 0) + 1

            if hasattr(component, "children"):
                children = component.children
                if children is not None:
                    if not isinstance(children, list):
                        children = [children]
                    for child in children:
                        if child is not None:
                            count_ids(child)

        count_ids(result)

        # Check for duplicates
        duplicates = {k: v for k, v in id_counts.items() if v > 1}
        assert not duplicates, f"Duplicate IDs found: {duplicates}"

    def test_layout_id_count(self):
        """Layout should have expected number of component IDs."""
        result = create_app_layout()
        ids = get_all_component_ids(result)

        # Should have at least 30 IDs (all the stores, inputs, buttons, etc.)
        assert len(ids) >= 30, f"Only found {len(ids)} IDs, expected at least 30"

    def test_store_components_are_dcc_store(self):
        """All store components should be dcc.Store instances."""
        result = create_app_layout()

        store_ids = [
            "zone-files-store",
            "current-zone-data",
            "selected-file",
            "selected-room",
            "has-unsaved-changes",
        ]

        for store_id in store_ids:
            store = find_component_by_id(result, store_id)
            assert isinstance(store, dcc.Store), f"{store_id} is not a dcc.Store"

    def test_input_components_are_dbc_input(self):
        """Form input components should be dbc.Input or dbc.Textarea."""
        result = create_app_layout()

        input_ids = ["room-id", "room-name", "room-coord-x", "room-coord-y", "room-coord-z"]

        for input_id in input_ids:
            input_comp = find_component_by_id(result, input_id)
            assert isinstance(input_comp, dbc.Input), f"{input_id} is not a dbc.Input"

        # Description is textarea
        desc = find_component_by_id(result, "room-description")
        assert isinstance(desc, dbc.Textarea)

    def test_button_components_are_dbc_button(self):
        """Button components should be dbc.Button instances."""
        result = create_app_layout()

        button_ids = [
            "new-map-btn",
            "new-room-btn",
            "add-room-btn",
            "update-room-btn",
            "save-map-btn",
            "export-zone-btn",
        ]

        for button_id in button_ids:
            button = find_component_by_id(result, button_id)
            assert isinstance(button, dbc.Button), f"{button_id} is not a dbc.Button"
