"""Tests for workspace zone exit callbacks."""

from dash import no_update

from pipeworks_mud_mapper.callbacks import exit_callbacks


class DummyCtx:
    """Simple stand-in for dash.ctx in unit tests."""

    def __init__(self, triggered_id):
        self.triggered_id = triggered_id


def _simple_zone():
    return {
        "rooms": {
            "spawn": {
                "id": "spawn",
                "name": "Spawn",
                "description": "",
                "coords": [0, 0, 0],
                "exits": {},
                "items": [],
            }
        }
    }


def test_update_workspace_zone_exit_table_no_room():
    """update_workspace_zone_exit_table should prompt when no room selected."""
    result = exit_callbacks.update_workspace_zone_exit_table(None, None)
    assert "Select a room" in str(result)


def test_update_workspace_zone_exit_table_missing_zone_data():
    """update_workspace_zone_exit_table should handle missing zone data."""
    result = exit_callbacks.update_workspace_zone_exit_table("spawn", None)
    assert "Zone data is unavailable" in str(result)


def test_update_workspace_zone_exit_table_missing_room():
    """update_workspace_zone_exit_table should handle unknown rooms."""
    zone_data = _simple_zone()
    result = exit_callbacks.update_workspace_zone_exit_table("missing", zone_data)
    assert "not found" in str(result)


def test_update_workspace_zone_exit_table_no_exits():
    """update_workspace_zone_exit_table should handle rooms with no exits."""
    zone_data = _simple_zone()
    result = exit_callbacks.update_workspace_zone_exit_table("spawn", zone_data)
    assert "No zone exits defined" in str(result)


def test_update_workspace_zone_exit_table_with_exit():
    """update_workspace_zone_exit_table should render zone exits in a table."""
    zone_data = _simple_zone()
    zone_data["rooms"]["spawn"]["exits"]["north"] = "alpha:spawn"
    zone_data["rooms"]["spawn"]["exits"]["portal"] = "beta:gate"

    result = exit_callbacks.update_workspace_zone_exit_table("spawn", zone_data)

    assert "alpha:spawn" in str(result)
    assert "beta:gate" in str(result)
    assert "Dir" in str(result)
    assert "Zone" in str(result)


def test_load_workspace_zone_exit_zone_options(monkeypatch):
    """Zone dropdown options should be loaded from the world metadata."""
    monkeypatch.setattr(exit_callbacks, "load_world_zone_ids", lambda: ["alpha", "beta"])
    options = exit_callbacks.load_workspace_zone_exit_zone_options(1)

    assert options[0]["value"] == "alpha"
    assert options[1]["value"] == "beta"


def test_update_workspace_zone_exit_room_options(monkeypatch):
    """Room options should follow the selected zone and preserve unlisted values."""
    monkeypatch.setattr(
        exit_callbacks,
        "load_zone_room_ids",
        lambda zone_id: ["room_a", "room_b"] if zone_id == "alpha" else [],
    )

    options, disabled = exit_callbacks.update_workspace_zone_exit_room_options("alpha", "room_z")

    assert disabled is False
    assert {"label": "room_a", "value": "room_a"} in options
    assert {"label": "room_b", "value": "room_b"} in options
    assert {"label": "room_z (unlisted)", "value": "room_z"} in options


def test_update_workspace_zone_exit_room_options_no_zone():
    """Room options should be disabled when no zone is selected."""
    options, disabled = exit_callbacks.update_workspace_zone_exit_room_options(None, None)
    assert options == []
    assert disabled is True


def test_populate_workspace_zone_exit_editor_from_row_click(monkeypatch):
    """Row clicks should populate the editor with the zone exit target."""
    zone_data = _simple_zone()
    zone_data["rooms"]["spawn"]["exits"]["north"] = "alpha:spawn"

    monkeypatch.setattr(
        exit_callbacks,
        "ctx",
        DummyCtx({"type": "workspace-zone-exit-row", "direction": "N"}),
    )

    direction, zone_id, room_id = exit_callbacks.populate_workspace_zone_exit_editor(
        "spawn",
        [1],
        zone_data,
    )

    assert direction == "N"
    assert zone_id == "alpha"
    assert room_id == "spawn"


def test_populate_workspace_zone_exit_editor_clears_on_room_change(monkeypatch):
    """Selecting a new room should clear the editor."""
    monkeypatch.setattr(exit_callbacks, "ctx", DummyCtx("selected-room"))

    direction, zone_id, room_id = exit_callbacks.populate_workspace_zone_exit_editor(
        "spawn",
        [0],
        _simple_zone(),
    )

    assert direction is None
    assert zone_id is None
    assert room_id is None


def test_populate_workspace_zone_exit_editor_invalid_trigger(monkeypatch):
    """Invalid triggers should no-op."""
    monkeypatch.setattr(exit_callbacks, "ctx", DummyCtx("workspace-zone-exit-row"))

    direction, zone_id, room_id = exit_callbacks.populate_workspace_zone_exit_editor(
        "spawn",
        [1],
        _simple_zone(),
    )

    assert direction is no_update
    assert zone_id is no_update
    assert room_id is no_update


def test_handle_workspace_zone_exit_save_add(monkeypatch):
    """Saving a zone exit should update current-zone-data."""
    zone_data = _simple_zone()

    monkeypatch.setattr(exit_callbacks, "ctx", DummyCtx("workspace-zone-exit-save"))

    updated_zone, feedback, unsaved = exit_callbacks.handle_workspace_zone_exit_action(
        1,
        None,
        "N",
        "alpha",
        "spawn",
        "spawn",
        zone_data,
    )

    assert updated_zone["rooms"]["spawn"]["exits"]["north"] == "alpha:spawn"
    assert "Saved" in str(feedback)
    assert unsaved is True


def test_handle_workspace_zone_exit_save_missing_inputs(monkeypatch):
    """Saving without a zone or room should return a warning."""
    zone_data = _simple_zone()
    monkeypatch.setattr(exit_callbacks, "ctx", DummyCtx("workspace-zone-exit-save"))

    updated_zone, feedback, unsaved = exit_callbacks.handle_workspace_zone_exit_action(
        1,
        None,
        "N",
        None,
        None,
        "spawn",
        zone_data,
    )

    assert updated_zone is no_update
    assert "Select both a zone and a room" in str(feedback)
    assert unsaved is no_update


def test_handle_workspace_zone_exit_save_conflict(monkeypatch):
    """Zone exits should not overwrite local exits in the same direction."""
    zone_data = _simple_zone()
    zone_data["rooms"]["spawn"]["exits"]["north"] = "hall"

    monkeypatch.setattr(exit_callbacks, "ctx", DummyCtx("workspace-zone-exit-save"))

    updated_zone, feedback, unsaved = exit_callbacks.handle_workspace_zone_exit_action(
        1,
        None,
        "N",
        "alpha",
        "spawn",
        "spawn",
        zone_data,
    )

    assert updated_zone is no_update
    assert "remove the local exit" in str(feedback).lower()
    assert unsaved is no_update


def test_handle_workspace_zone_exit_save_existing(monkeypatch):
    """Saving an unchanged zone exit should no-op."""
    zone_data = _simple_zone()
    zone_data["rooms"]["spawn"]["exits"]["north"] = "alpha:spawn"
    monkeypatch.setattr(exit_callbacks, "ctx", DummyCtx("workspace-zone-exit-save"))

    updated_zone, feedback, unsaved = exit_callbacks.handle_workspace_zone_exit_action(
        1,
        None,
        "N",
        "alpha",
        "spawn",
        "spawn",
        zone_data,
    )

    assert updated_zone is no_update
    assert "already set" in str(feedback)
    assert unsaved is no_update


def test_handle_workspace_zone_exit_clear(monkeypatch):
    """Clearing a zone exit should remove only the cross-zone exit."""
    zone_data = _simple_zone()
    zone_data["rooms"]["spawn"]["exits"]["north"] = "alpha:spawn"

    monkeypatch.setattr(exit_callbacks, "ctx", DummyCtx("workspace-zone-exit-clear"))

    updated_zone, feedback, unsaved = exit_callbacks.handle_workspace_zone_exit_action(
        None,
        1,
        "N",
        None,
        None,
        "spawn",
        zone_data,
    )

    assert "north" not in updated_zone["rooms"]["spawn"]["exits"]
    assert "Cleared" in str(feedback)
    assert unsaved is True


def test_handle_workspace_zone_exit_clear_missing(monkeypatch):
    """Clearing a missing zone exit should no-op."""
    zone_data = _simple_zone()

    monkeypatch.setattr(exit_callbacks, "ctx", DummyCtx("workspace-zone-exit-clear"))

    updated_zone, feedback, unsaved = exit_callbacks.handle_workspace_zone_exit_action(
        None,
        1,
        "N",
        None,
        None,
        "spawn",
        zone_data,
    )

    assert updated_zone is no_update
    assert "No zone exit" in str(feedback)
    assert unsaved is no_update


def test_handle_workspace_zone_exit_invalid_trigger(monkeypatch):
    """Non-action triggers should no-op."""
    zone_data = _simple_zone()
    monkeypatch.setattr(exit_callbacks, "ctx", DummyCtx("workspace-zone-exit-zone"))

    updated_zone, feedback, unsaved = exit_callbacks.handle_workspace_zone_exit_action(
        None,
        None,
        "N",
        None,
        None,
        "spawn",
        zone_data,
    )

    assert updated_zone is no_update
    assert feedback is no_update
    assert unsaved is no_update


def test_handle_workspace_zone_exit_invalid_direction(monkeypatch):
    """Invalid direction selections should return a warning."""
    zone_data = _simple_zone()
    monkeypatch.setattr(exit_callbacks, "ctx", DummyCtx("workspace-zone-exit-save"))

    updated_zone, feedback, unsaved = exit_callbacks.handle_workspace_zone_exit_action(
        1,
        None,
        "INVALID",
        "alpha",
        "spawn",
        "spawn",
        zone_data,
    )

    assert updated_zone is no_update
    assert "Choose a direction" in str(feedback)
    assert unsaved is no_update


def test_handle_workspace_zone_exit_missing_room(monkeypatch):
    """Missing selected room should return a warning."""
    zone_data = _simple_zone()
    monkeypatch.setattr(exit_callbacks, "ctx", DummyCtx("workspace-zone-exit-save"))

    updated_zone, feedback, unsaved = exit_callbacks.handle_workspace_zone_exit_action(
        1,
        None,
        "N",
        "alpha",
        "spawn",
        None,
        zone_data,
    )

    assert updated_zone is no_update
    assert "Select a room" in str(feedback)
    assert unsaved is no_update
