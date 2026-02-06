"""Tests for exit utility helpers."""

from pipeworks_mud_mapper.models.room import Direction
from pipeworks_mud_mapper.services.exit_utils import (
    EXIT_SHORT_ORDER,
    format_zone_exit,
    parse_zone_exit,
    split_exits_by_scope,
)


def test_split_exits_by_scope():
    exits: dict[Direction, str] = {
        "north": "hall",
        "south": "other:spawn",
        "east": "kitchen",
    }
    local, zone = split_exits_by_scope(exits)
    assert local == {"north": "hall", "east": "kitchen"}
    assert zone == {"south": "other:spawn"}


def test_parse_zone_exit_valid():
    zone_id, room_id = parse_zone_exit("cobbled:spawn")
    assert zone_id == "cobbled"
    assert room_id == "spawn"


def test_parse_zone_exit_invalid():
    assert parse_zone_exit(None) == (None, None)
    assert parse_zone_exit("invalid") == (None, None)
    assert parse_zone_exit("zone:") == (None, None)
    assert parse_zone_exit(":room") == (None, None)


def test_format_zone_exit():
    assert format_zone_exit("cobbled", "spawn") == "cobbled:spawn"
    assert format_zone_exit("cobbled", None) is None
    assert format_zone_exit(None, "spawn") is None


def test_exit_short_order():
    assert EXIT_SHORT_ORDER == ("N", "E", "S", "W", "U", "D")
