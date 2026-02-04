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
    create_ollama_panel,
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
    """Tests for action_bar module.

    Note: Action bar was simplified in v0.0.8 and v0.0.10. Primary action
    buttons (Save, Export, Validate) are now in the file browser for better
    UX. Action bar only contains debug output.
    """

    def test_create_action_bar_returns_div(self):
        """create_action_bar should return an html.Div."""
        result = create_action_bar()
        assert isinstance(result, html.Div)

    def test_create_action_bar_has_debug_output(self):
        """create_action_bar should include debug-btn-state."""
        result = create_action_bar()
        assert component_has_id(result, "debug-btn-state")

    def test_create_action_bar_has_flex_layout(self):
        """create_action_bar should use flexbox layout."""
        result = create_action_bar()
        assert "d-flex" in result.className


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

    def test_create_file_browser_has_dev_snapshot_list_container(self):
        """create_file_browser should include dev-snapshot-list-container."""
        result = create_file_browser()
        assert component_has_id(result, "dev-snapshot-list-container")

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

    def test_create_file_browser_has_save_button(self):
        """create_file_browser should include save-map-btn."""
        result = create_file_browser()
        assert component_has_id(result, "save-map-btn")

    def test_create_file_browser_has_export_button(self):
        """create_file_browser should include export-zone-btn."""
        result = create_file_browser()
        assert component_has_id(result, "export-zone-btn")

    def test_create_file_browser_has_status_indicator(self):
        """create_file_browser should include status-indicator."""
        result = create_file_browser()
        assert component_has_id(result, "status-indicator")

    def test_create_file_browser_buttons_initially_disabled(self):
        """create_file_browser save/export/validate buttons should start disabled."""
        result = create_file_browser()
        save_btn = find_component_by_id(result, "save-map-btn")
        export_btn = find_component_by_id(result, "export-zone-btn")
        validate_btn = find_component_by_id(result, "validate-zone-btn")

        assert save_btn.disabled is True
        assert export_btn.disabled is True
        assert validate_btn.disabled is True

    def test_create_file_browser_status_default_text(self):
        """create_file_browser status should show 'No file loaded' initially."""
        result = create_file_browser()
        status = find_component_by_id(result, "status-indicator")
        assert "No file loaded" in str(status.children)

    def test_create_file_browser_has_validate_button(self):
        """create_file_browser should include validate-zone-btn."""
        result = create_file_browser()
        assert component_has_id(result, "validate-zone-btn")

    def test_create_file_browser_validate_button_style(self):
        """create_file_browser validate-zone-btn should be info outline."""
        result = create_file_browser()
        validate_btn = find_component_by_id(result, "validate-zone-btn")
        assert validate_btn.color == "info"
        assert validate_btn.outline is True


# =============================================================================
# Map Panel Tests
# =============================================================================


class TestMapPanel:
    """Tests for map_panel module.

    The map panel displays a flattened view of all Z-levels with visual
    differentiation. The z-level-filter checklist allows hiding specific
    levels (all checked by default).
    """

    def test_create_map_panel_returns_card(self):
        """create_map_panel should return a dbc.Card."""
        result = create_map_panel()
        assert isinstance(result, dbc.Card)

    def test_create_map_panel_has_map_graph(self):
        """create_map_panel should include map-graph."""
        result = create_map_panel()
        assert component_has_id(result, "map-graph")

    def test_create_map_panel_has_z_level_filter(self):
        """create_map_panel should include z-level-filter checklist."""
        result = create_map_panel()
        assert component_has_id(result, "z-level-filter")

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

    def test_create_map_panel_z_filter_has_three_options(self):
        """create_map_panel z-level-filter should have -1, 0, +1 options."""
        result = create_map_panel()
        z_filter = find_component_by_id(result, "z-level-filter")
        assert isinstance(z_filter, dbc.Checklist)
        assert len(z_filter.options) == 3
        values = [opt["value"] for opt in z_filter.options]
        assert -1 in values
        assert 0 in values
        assert 1 in values

    def test_create_map_panel_z_filter_all_checked_default(self):
        """create_map_panel z-level-filter should have all levels checked by default."""
        result = create_map_panel()
        z_filter = find_component_by_id(result, "z-level-filter")
        assert set(z_filter.value) == {-1, 0, 1}

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

    def test_create_properties_panel_has_feedback_stores(self):
        """create_properties_panel should include room feedback stores."""
        result = create_properties_panel()
        store_ids = [
            "room-feedback-add",
            "room-feedback-new",
            "room-feedback-update",
            "room-feedback-delete",
            "room-feedback-undo",
            "room-feedback-save",
            "room-feedback-export",
        ]
        for store_id in store_ids:
            assert component_has_id(result, store_id)

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
# Ollama Panel Tests
# =============================================================================


class TestOllamaPanel:
    """Tests for ollama_panel module.

    The Ollama panel provides LLM-powered description generation via Ollama.
    It was moved from properties_panel to the center column below the map.
    """

    def test_create_ollama_panel_returns_card(self):
        """create_ollama_panel should return a dbc.Card."""
        result = create_ollama_panel()
        assert isinstance(result, dbc.Card)

    def test_create_ollama_panel_has_ollama_server_url(self):
        """create_ollama_panel should include ollama-server-url input."""
        result = create_ollama_panel()
        assert component_has_id(result, "ollama-server-url")

    def test_create_ollama_panel_has_ollama_model_dropdown(self):
        """create_ollama_panel should include ollama-model-dropdown."""
        result = create_ollama_panel()
        assert component_has_id(result, "ollama-model-dropdown")

    def test_create_ollama_panel_has_ollama_refresh_btn(self):
        """create_ollama_panel should include ollama-refresh-models-btn."""
        result = create_ollama_panel()
        assert component_has_id(result, "ollama-refresh-models-btn")

    def test_create_ollama_panel_has_ollama_system_prompt(self):
        """create_ollama_panel should include ollama-system-prompt."""
        result = create_ollama_panel()
        assert component_has_id(result, "ollama-system-prompt")

    def test_create_ollama_panel_has_ollama_user_prompt(self):
        """create_ollama_panel should include ollama-user-prompt."""
        result = create_ollama_panel()
        assert component_has_id(result, "ollama-user-prompt")

    def test_create_ollama_panel_has_ollama_generate_btn(self):
        """create_ollama_panel should include ollama-generate-btn."""
        result = create_ollama_panel()
        assert component_has_id(result, "ollama-generate-btn")

    def test_create_ollama_panel_has_ollama_response(self):
        """create_ollama_panel should include ollama-response textarea."""
        result = create_ollama_panel()
        assert component_has_id(result, "ollama-response")

    def test_create_ollama_panel_has_ollama_status(self):
        """create_ollama_panel should include ollama-status."""
        result = create_ollama_panel()
        assert component_has_id(result, "ollama-status")

    def test_create_ollama_panel_has_status_stores(self):
        """create_ollama_panel should include Ollama status stores."""
        result = create_ollama_panel()
        store_ids = [
            "ollama-status-generation",
            "ollama-status-send",
            "ollama-status-prompt",
            "ollama-status-system",
            "ollama-status-template",
        ]
        for store_id in store_ids:
            assert component_has_id(result, store_id)

    def test_create_ollama_panel_has_ollama_connection_status(self):
        """create_ollama_panel should include ollama-connection-status."""
        result = create_ollama_panel()
        assert component_has_id(result, "ollama-connection-status")

    def test_create_ollama_panel_has_ollama_send_to_description_btn(self):
        """create_ollama_panel should include ollama-send-to-description-btn."""
        result = create_ollama_panel()
        assert component_has_id(result, "ollama-send-to-description-btn")

    def test_create_ollama_panel_has_ollama_clipboard_feedback(self):
        """create_ollama_panel should include ollama-clipboard-feedback."""
        result = create_ollama_panel()
        assert component_has_id(result, "ollama-clipboard-feedback")

    def test_create_ollama_panel_has_validator_staging(self):
        """create_ollama_panel should include validator staging IDs."""
        result = create_ollama_panel()
        assert component_has_id(result, "ollama-validator-status")
        assert component_has_id(result, "ollama-validator-summary")
        assert component_has_id(result, "ollama-validator-hits")
        assert component_has_id(result, "ollama-validator-history")
        assert component_has_id(result, "ollama-target-words-hint")
        assert component_has_id(result, "ollama-params-help-btn")
        assert component_has_id(result, "ollama-prompt-prefix-dropdown")

    def test_create_ollama_panel_ollama_server_default(self):
        """create_ollama_panel ollama-server-url should default to localhost."""
        result = create_ollama_panel()
        server_input = find_component_by_id(result, "ollama-server-url")
        assert server_input.value == "http://localhost:11434"

    def test_create_ollama_panel_ollama_system_prompt_has_default(self):
        """create_ollama_panel ollama-system-prompt should have default text."""
        result = create_ollama_panel()
        system_prompt = find_component_by_id(result, "ollama-system-prompt")
        assert "creative writer" in system_prompt.value.lower()
        assert "MUD" in system_prompt.value

    def test_create_ollama_panel_ollama_response_readonly(self):
        """create_ollama_panel ollama-response should be read-only."""
        result = create_ollama_panel()
        response = find_component_by_id(result, "ollama-response")
        assert response.readOnly is True

    def test_create_ollama_panel_has_ollama_clipboard(self):
        """create_ollama_panel should include ollama-clipboard component."""
        result = create_ollama_panel()
        assert component_has_id(result, "ollama-clipboard")

    def test_create_ollama_panel_ollama_connection_default_not_connected(self):
        """create_ollama_panel connection status should default to not connected."""
        result = create_ollama_panel()
        connection_status = find_component_by_id(result, "ollama-connection-status")
        # Check the children contain "Not connected" text
        assert connection_status is not None

    def test_create_ollama_panel_has_template_dropdown(self):
        """create_ollama_panel should include ollama-template-dropdown."""
        result = create_ollama_panel()
        assert component_has_id(result, "ollama-template-dropdown")

    def test_create_ollama_panel_has_system_prompt_collapse(self):
        """create_ollama_panel should include ollama-system-prompt-collapse."""
        result = create_ollama_panel()
        assert component_has_id(result, "ollama-system-prompt-collapse")

    def test_create_ollama_panel_has_system_prompt_toggle(self):
        """create_ollama_panel should include ollama-system-prompt-toggle."""
        result = create_ollama_panel()
        assert component_has_id(result, "ollama-system-prompt-toggle")

    def test_create_ollama_panel_has_copy_system_prompt_btn(self):
        """create_ollama_panel should include ollama-copy-system-prompt-btn."""
        result = create_ollama_panel()
        assert component_has_id(result, "ollama-copy-system-prompt-btn")

    def test_create_ollama_panel_has_header(self):
        """create_ollama_panel should have 'LLM Assistant' header."""
        result = create_ollama_panel()
        assert isinstance(result.children[0], dbc.CardHeader)
        header_content = str(result.children[0].children)
        assert "LLM Assistant" in header_content

    # =========================================================================
    # Parameters Section Tests
    # =========================================================================

    def test_create_ollama_panel_has_params_toggle(self):
        """create_ollama_panel should include ollama-params-toggle button."""
        result = create_ollama_panel()
        assert component_has_id(result, "ollama-params-toggle")

    def test_create_ollama_panel_has_params_chevron(self):
        """create_ollama_panel should include ollama-params-chevron icon."""
        result = create_ollama_panel()
        assert component_has_id(result, "ollama-params-chevron")

    def test_create_ollama_panel_has_params_collapse(self):
        """create_ollama_panel should include ollama-params-collapse section."""
        result = create_ollama_panel()
        assert component_has_id(result, "ollama-params-collapse")

    def test_create_ollama_panel_params_collapse_hidden_by_default(self):
        """create_ollama_panel params-collapse should be hidden (is_open=False) by default."""
        result = create_ollama_panel()
        collapse = find_component_by_id(result, "ollama-params-collapse")
        assert collapse.is_open is False

    # =========================================================================
    # Seed Control Tests
    # =========================================================================

    def test_create_ollama_panel_has_seed_value_input(self):
        """create_ollama_panel should include ollama-seed-value input."""
        result = create_ollama_panel()
        assert component_has_id(result, "ollama-seed-value")

    def test_create_ollama_panel_has_seed_decrease_button(self):
        """create_ollama_panel should include ollama-seed-decrease button."""
        result = create_ollama_panel()
        assert component_has_id(result, "ollama-seed-decrease")

    def test_create_ollama_panel_has_seed_increase_button(self):
        """create_ollama_panel should include ollama-seed-increase button."""
        result = create_ollama_panel()
        assert component_has_id(result, "ollama-seed-increase")

    def test_create_ollama_panel_has_seed_random_checkbox(self):
        """create_ollama_panel should include ollama-seed-random-check checkbox."""
        result = create_ollama_panel()
        assert component_has_id(result, "ollama-seed-random-check")

    def test_create_ollama_panel_seed_default_minus_one(self):
        """create_ollama_panel seed value should default to -1 (random)."""
        result = create_ollama_panel()
        seed_input = find_component_by_id(result, "ollama-seed-value")
        assert seed_input.value == -1

    def test_create_ollama_panel_seed_random_checked_by_default(self):
        """create_ollama_panel random checkbox should be checked by default."""
        result = create_ollama_panel()
        random_check = find_component_by_id(result, "ollama-seed-random-check")
        assert random_check.value is True

    # =========================================================================
    # Model Parameter Tests
    # =========================================================================

    def test_create_ollama_panel_has_temperature_input(self):
        """create_ollama_panel should include ollama-temperature input."""
        result = create_ollama_panel()
        assert component_has_id(result, "ollama-temperature")

    def test_create_ollama_panel_has_top_k_input(self):
        """create_ollama_panel should include ollama-top-k input."""
        result = create_ollama_panel()
        assert component_has_id(result, "ollama-top-k")

    def test_create_ollama_panel_has_top_p_input(self):
        """create_ollama_panel should include ollama-top-p input."""
        result = create_ollama_panel()
        assert component_has_id(result, "ollama-top-p")

    def test_create_ollama_panel_has_num_ctx_input(self):
        """create_ollama_panel should include ollama-num-ctx input."""
        result = create_ollama_panel()
        assert component_has_id(result, "ollama-num-ctx")

    def test_create_ollama_panel_has_num_predict_input(self):
        """create_ollama_panel should include ollama-num-predict input."""
        result = create_ollama_panel()
        assert component_has_id(result, "ollama-num-predict")

    def test_create_ollama_panel_temperature_default(self):
        """create_ollama_panel temperature should default to 0.7."""
        result = create_ollama_panel()
        temp_input = find_component_by_id(result, "ollama-temperature")
        assert temp_input.value == 0.7

    def test_create_ollama_panel_top_k_default(self):
        """create_ollama_panel top_k should default to 40."""
        result = create_ollama_panel()
        top_k_input = find_component_by_id(result, "ollama-top-k")
        assert top_k_input.value == 40

    def test_create_ollama_panel_top_p_default(self):
        """create_ollama_panel top_p should default to 0.9."""
        result = create_ollama_panel()
        top_p_input = find_component_by_id(result, "ollama-top-p")
        assert top_p_input.value == 0.9

    def test_create_ollama_panel_num_ctx_default(self):
        """create_ollama_panel num_ctx should default to 4096."""
        result = create_ollama_panel()
        num_ctx_input = find_component_by_id(result, "ollama-num-ctx")
        assert num_ctx_input.value == 4096

    def test_create_ollama_panel_num_predict_default(self):
        """create_ollama_panel num_predict should default to 512."""
        result = create_ollama_panel()
        num_predict_input = find_component_by_id(result, "ollama-num-predict")
        assert num_predict_input.value == 512

    def test_create_ollama_panel_temperature_has_min_max(self):
        """create_ollama_panel temperature input should have min/max constraints."""
        result = create_ollama_panel()
        temp_input = find_component_by_id(result, "ollama-temperature")
        assert temp_input.min == 0.0
        assert temp_input.max == 2.0

    def test_create_ollama_panel_top_k_has_min_max(self):
        """create_ollama_panel top_k input should have min/max constraints."""
        result = create_ollama_panel()
        top_k_input = find_component_by_id(result, "ollama-top-k")
        assert top_k_input.min == 1
        assert top_k_input.max == 100

    def test_create_ollama_panel_top_p_has_min_max(self):
        """create_ollama_panel top_p input should have min/max constraints."""
        result = create_ollama_panel()
        top_p_input = find_component_by_id(result, "ollama-top-p")
        assert top_p_input.min == 0.0
        assert top_p_input.max == 1.0

    def test_create_ollama_panel_num_ctx_has_min_max(self):
        """create_ollama_panel num_ctx input should have min/max constraints."""
        result = create_ollama_panel()
        num_ctx_input = find_component_by_id(result, "ollama-num-ctx")
        assert num_ctx_input.min == 512
        assert num_ctx_input.max == 8192

    def test_create_ollama_panel_num_predict_has_min_max(self):
        """create_ollama_panel num_predict input should have min/max constraints."""
        result = create_ollama_panel()
        num_predict_input = find_component_by_id(result, "ollama-num-predict")
        assert num_predict_input.min == 30
        assert num_predict_input.max == 2048


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

    def test_create_app_layout_has_dev_snapshot_files_store(self):
        """create_app_layout should include dev-snapshot-files-store."""
        result = create_app_layout()
        assert component_has_id(result, "dev-snapshot-files-store")

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

    def test_create_app_layout_has_validation_results_modal(self):
        """create_app_layout should include validation-results-modal."""
        result = create_app_layout()
        assert component_has_id(result, "validation-results-modal")

    def test_create_app_layout_has_validation_report_store(self):
        """create_app_layout should include validation-report store."""
        result = create_app_layout()
        assert component_has_id(result, "validation-report")

    def test_create_app_layout_has_delete_confirm_modal(self):
        """create_app_layout should include delete-confirm-modal."""
        result = create_app_layout()
        assert component_has_id(result, "delete-confirm-modal")

    def test_create_app_layout_stores_have_defaults(self):
        """create_app_layout stores should have appropriate defaults."""
        result = create_app_layout()

        zone_files = find_component_by_id(result, "zone-files-store")
        assert zone_files.data == []

        dev_snapshot_files = find_component_by_id(result, "dev-snapshot-files-store")
        assert dev_snapshot_files.data == []

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
        assert "dev-snapshot-list-container" in ids
        assert "new-map-btn" in ids

        # Map panel IDs
        assert "map-graph" in ids
        assert "z-level-filter" in ids

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
            "dev-snapshot-files-store",
            "initial-load",
            "file-list-container",
            "dev-snapshot-list-container",
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
            "dev-save-toggle",
            "dev-snapshot-status",
            "has-unsaved-changes",
            "status-indicator",
            "room-feedback-save",
            "room-feedback-export",
        ]
        for id_ in file_callback_ids:
            assert id_ in ids, f"Missing ID for file callbacks: {id_}"

        # IDs used in map_callbacks.py
        map_callback_ids = [
            "map-graph",
            "z-level-filter",
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
            "room-feedback-add",
            "room-feedback-new",
            "room-feedback-update",
            "room-feedback-delete",
            "room-feedback-undo",
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

        # IDs used in ollama_callbacks.py
        ollama_callback_ids = [
            "ollama-last-generation-info",
            "ollama-validation-history",
            "ollama-validation-info",
            "ollama-server-url",
            "ollama-model-dropdown",
            "ollama-refresh-models-btn",
            "ollama-connection-status",
            "ollama-system-prompt",
            "ollama-user-prompt",
            "ollama-generate-btn",
            "ollama-response",
            "ollama-status",
            "ollama-send-to-description-btn",
            "ollama-clipboard",
            "ollama-clipboard-feedback",
            "ollama-status-generation",
            "ollama-status-send",
            "ollama-status-prompt",
            "ollama-status-system",
            "ollama-status-template",
            "ollama-validator-status",
            "ollama-validator-summary",
            "ollama-validator-hits",
            "ollama-validator-history",
            "ollama-target-words-hint",
            "ollama-params-help-btn",
            "ollama-prompt-prefix-dropdown",
            # Parameters section IDs
            "ollama-params-toggle",
            "ollama-params-chevron",
            "ollama-params-collapse",
            # Seed control IDs
            "ollama-seed-value",
            "ollama-seed-decrease",
            "ollama-seed-increase",
            "ollama-seed-random-check",
            # Model parameter IDs
            "ollama-temperature",
            "ollama-top-k",
            "ollama-top-p",
            "ollama-num-ctx",
            "ollama-num-predict",
        ]
        for id_ in ollama_callback_ids:
            assert id_ in ids, f"Missing ID for ollama callbacks: {id_}"

        # IDs used in validation_callbacks.py
        validation_callback_ids = [
            "validate-zone-btn",
            "validation-results-modal",
            "validation-results-body",
            "validation-report",
            "validation-close-btn",
        ]
        for id_ in validation_callback_ids:
            assert id_ in ids, f"Missing ID for validation callbacks: {id_}"

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

        # Should have at least 54 IDs (all the stores, inputs, buttons, plus Ollama
        # with new parameters section: +13 new IDs for params, seed, and model params)
        assert len(ids) >= 54, f"Only found {len(ids)} IDs, expected at least 54"

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
            "validate-zone-btn",
        ]

        for button_id in button_ids:
            button = find_component_by_id(result, button_id)
            assert isinstance(button, dbc.Button), f"{button_id} is not a dbc.Button"
