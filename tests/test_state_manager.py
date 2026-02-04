"""Tests for the zone state manager and action handlers."""

from unittest.mock import patch

from pipeworks_mud_mapper.services.state import ZoneAction, apply_zone_action


def simple_zone() -> dict:
    """Build a minimal zone dict for action testing."""
    return {
        "id": "test_zone",
        "name": "Test Zone",
        "spawn_room": "spawn",
        "rooms": {
            "spawn": {
                "id": "spawn",
                "name": "Spawn",
                "description": "Start",
                "coords": [0, 0, 0],
                "exits": {},
                "items": [],
            }
        },
        "items": {},
    }


def test_apply_zone_action_add_room_success():
    """ADD_ROOM should update zone data and mark unsaved."""
    action = ZoneAction(
        type="ADD_ROOM",
        payload={
            "room_id": "hall",
            "room_name": "Hall",
            "room_description": "A long hall.",
            "coord_x": 1,
            "coord_y": 0,
            "coord_z": 0,
        },
    )
    transition = apply_zone_action(simple_zone(), action)

    assert transition.changed is True
    assert transition.unsaved is True
    assert transition.zone_data is not None
    assert "hall" in transition.zone_data.get("rooms", {})


def test_apply_zone_action_add_room_invalid_id():
    """ADD_ROOM should reject invalid IDs without changing zone data."""
    action = ZoneAction(
        type="ADD_ROOM",
        payload={
            "room_id": "123",
            "room_name": "Bad",
            "room_description": "",
            "coord_x": 0,
            "coord_y": 0,
            "coord_z": 0,
        },
    )
    transition = apply_zone_action(simple_zone(), action)

    assert transition.changed is False
    assert transition.zone_data is None
    assert transition.feedback is not None


def test_apply_zone_action_add_room_invalid_coords():
    """ADD_ROOM should reject invalid coordinates."""
    action = ZoneAction(
        type="ADD_ROOM",
        payload={
            "room_id": "hall",
            "room_name": "Hall",
            "room_description": "",
            "coord_x": "bad",
            "coord_y": 0,
            "coord_z": 0,
        },
    )
    transition = apply_zone_action(simple_zone(), action)
    assert transition.changed is False
    assert transition.feedback is not None


def test_apply_zone_action_update_room_success():
    """UPDATE_ROOM should update room fields."""
    action = ZoneAction(
        type="UPDATE_ROOM",
        payload={
            "selected_room": "spawn",
            "room_name": "Updated",
            "room_description": "Updated desc",
            "coord_x": 2,
            "coord_y": 3,
            "coord_z": 0,
        },
    )
    transition = apply_zone_action(simple_zone(), action)

    assert transition.changed is True
    assert transition.zone_data is not None
    updated = transition.zone_data["rooms"]["spawn"]
    assert updated["name"] == "Updated"
    assert updated["description"] == "Updated desc"
    assert updated["coords"] == [2, 3, 0]


def test_apply_zone_action_delete_and_undo():
    """DELETE_ROOM and UNDO_DELETE should round-trip room removal."""
    zone = simple_zone()
    zone["rooms"]["hall"] = {
        "id": "hall",
        "name": "Hall",
        "description": "",
        "coords": [1, 0, 0],
        "exits": {},
        "items": [],
    }

    delete_action = ZoneAction(
        type="DELETE_ROOM",
        payload={"selected_room": "hall"},
    )
    delete_transition = apply_zone_action(zone, delete_action)

    assert delete_transition.changed is True
    assert delete_transition.zone_data is not None
    assert "hall" not in delete_transition.zone_data["rooms"]

    undo_action = ZoneAction(
        type="UNDO_DELETE",
        payload={"undo_data": delete_transition.effects.get("undo_data")},
    )
    undo_transition = apply_zone_action(delete_transition.zone_data, undo_action)

    assert undo_transition.changed is True
    assert undo_transition.zone_data is not None
    assert "hall" in undo_transition.zone_data["rooms"]


def test_apply_zone_action_unknown_type():
    """apply_zone_action should raise on unknown action type."""
    action = ZoneAction(type="UNKNOWN", payload={})  # type: ignore[arg-type]
    try:
        apply_zone_action(simple_zone(), action)
    except ValueError as exc:
        assert "Unknown zone action" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unknown action")


def test_apply_zone_action_exit_rejects_when_missing_room():
    """EXIT_CHANGE should reject directions without target rooms."""
    zone = simple_zone()
    action = ZoneAction(
        type="EXIT_CHANGE",
        payload={
            "selected_room": "spawn",
            "checked_values": ["N"],
        },
    )
    transition = apply_zone_action(zone, action)

    assert transition.changed is True
    assert transition.zone_data is not None
    assert transition.effects.get("exit_values") == []


def test_apply_zone_action_exit_adds_bidirectional():
    """EXIT_CHANGE should create exits when a room exists in direction."""
    zone = simple_zone()
    zone["rooms"]["north"] = {
        "id": "north",
        "name": "North",
        "description": "",
        "coords": [0, 1, 0],
        "exits": {},
        "items": [],
    }
    action = ZoneAction(
        type="EXIT_CHANGE",
        payload={
            "selected_room": "spawn",
            "checked_values": ["N"],
        },
    )
    transition = apply_zone_action(zone, action)

    assert transition.changed is True
    updated = transition.zone_data
    assert updated is not None
    assert updated["rooms"]["spawn"]["exits"].get("north") == "north"
    assert updated["rooms"]["north"]["exits"].get("south") == "spawn"


def test_apply_zone_action_load_map_success(tmp_path):
    """LOAD_MAP should return zone data and zone name."""
    fake_file = tmp_path / "zone.map.json"
    fake_file.write_text("{}", encoding="utf-8")

    class DummyMap:
        def to_dict_with_list_coords(self):
            return {"name": "Loaded Zone", "rooms": {}}

    action = ZoneAction(type="LOAD_MAP", payload={"file_path": fake_file})
    with patch(
        "pipeworks_mud_mapper.services.state.actions_load.zone_service.load_map_file",
        return_value=DummyMap(),
    ):
        transition = apply_zone_action(None, action)

    assert transition.changed is True
    assert transition.zone_data is not None
    assert transition.effects.get("zone_name") == "Loaded Zone"


def test_apply_zone_action_apply_generation():
    """APPLY_GENERATION should update room descriptions."""
    zone = simple_zone()
    action = ZoneAction(
        type="APPLY_GENERATION",
        payload={
            "selected_room": "spawn",
            "response_text": "New desc",
            "generation_info": {"model": "x"},
            "validation_info": None,
        },
    )
    transition = apply_zone_action(zone, action)
    assert transition.changed is True
    assert transition.zone_data is not None
    assert transition.zone_data["rooms"]["spawn"]["description"] == "New desc"
