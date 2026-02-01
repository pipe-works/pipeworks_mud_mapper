"""Zone file I/O utilities for the MUD Mapper."""

import copy
import json
from collections import deque
from pathlib import Path

# Direction offsets: (dx, dy, dz)
# X = East(+) / West(-), Y = North(+) / South(-), Z = Up(+) / Down(-)
DIRECTION_OFFSETS: dict[str, tuple[int, int, int]] = {
    "north": (0, 1, 0),
    "south": (0, -1, 0),
    "east": (1, 0, 0),
    "west": (-1, 0, 0),
    "up": (0, 0, 1),
    "down": (0, 0, -1),
}


def create_blank_zone(zone_id: str, zone_name: str, description: str = "") -> dict:
    """Create a blank zone template with a single spawn room.

    Args:
        zone_id: Unique identifier for the zone (alphanumeric + underscore).
        zone_name: Display name for the zone.
        description: Optional description of the zone.

    Returns:
        A dict containing the zone structure with one empty spawn room.
    """
    return {
        "id": zone_id,
        "name": zone_name,
        "description": description,
        "spawn_room": "spawn",
        "rooms": {
            "spawn": {
                "id": "spawn",
                "name": "Starting Room",
                "description": "An empty room waiting to be defined.",
                "exits": {},
                "items": [],
            }
        },
        "items": {},
    }


def save_zone_json(zone_data: dict, file_path: Path) -> None:
    """Save zone data to a JSON file.

    Args:
        zone_data: The zone data dictionary to save.
        file_path: Path where the JSON file will be written.
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as f:
        json.dump(zone_data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def load_zone_json(file_path: Path) -> dict:
    """Load zone data from a JSON file.

    Args:
        file_path: Path to the JSON file to load.

    Returns:
        The zone data dictionary.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    file_path = Path(file_path)
    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def list_zone_files(directory: Path) -> list[Path]:
    """List all .json zone files in a directory.

    Args:
        directory: Path to the directory to scan.

    Returns:
        List of Path objects for each .json file found, sorted by name.
    """
    directory = Path(directory)
    if not directory.exists():
        return []
    return sorted(directory.glob("*.json"))


def auto_layout_rooms(zone_data: dict) -> dict:
    """Add coords to rooms based on exit directions.

    Walks from spawn_room using BFS, computing positions based on
    cardinal directions:
    - north: y+1, south: y-1
    - east: x+1, west: x-1
    - up: z+1, down: z-1

    Rooms that already have coords are preserved. Cross-zone exits
    (containing ':') are ignored.

    Args:
        zone_data: Zone dictionary with rooms.

    Returns:
        A copy of zone_data with coords added to each reachable room.
    """
    zone = copy.deepcopy(zone_data)
    rooms = zone.get("rooms", {})

    if not rooms:
        return zone

    # Find spawn room
    spawn_id = zone.get("spawn_room", "spawn")
    if spawn_id not in rooms:
        # Fall back to first room if spawn doesn't exist
        spawn_id = next(iter(rooms))

    # Track visited rooms and their coordinates
    visited: dict[str, tuple[int, int, int]] = {}

    # BFS queue: (room_id, x, y, z)
    queue: deque[tuple[str, int, int, int]] = deque()
    queue.append((spawn_id, 0, 0, 0))
    visited[spawn_id] = (0, 0, 0)

    while queue:
        room_id, x, y, z = queue.popleft()
        room = rooms.get(room_id)
        if not room:
            continue

        exits = room.get("exits", {})
        for direction, target in exits.items():
            # Skip cross-zone exits
            if ":" in str(target):
                continue

            # Skip unknown directions
            if direction not in DIRECTION_OFFSETS:
                continue

            # Skip already visited rooms
            if target in visited:
                continue

            # Skip rooms not in this zone
            if target not in rooms:
                continue

            # Compute new position
            dx, dy, dz = DIRECTION_OFFSETS[direction]
            new_x, new_y, new_z = x + dx, y + dy, z + dz

            visited[target] = (new_x, new_y, new_z)
            queue.append((target, new_x, new_y, new_z))

    # Apply coords to rooms
    for room_id, (rx, ry, rz) in visited.items():
        if room_id in rooms:
            # Preserve existing coords if present
            if "coords" not in rooms[room_id]:
                rooms[room_id]["coords"] = [rx, ry, rz]

    # Handle any unvisited rooms (disconnected) - place at origin
    for room_id in rooms:
        if "coords" not in rooms[room_id]:
            rooms[room_id]["coords"] = [0, 0, 0]

    return zone
