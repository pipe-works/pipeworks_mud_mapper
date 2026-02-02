"""Room service for CRUD operations and exit management.

This module provides functions for manipulating rooms and exits within
a MapFile. All operations are performed in-place on the provided MapFile
instance.

Design Principles
-----------------
1. **In-place mutation**: Functions modify the MapFile directly rather than
   returning new instances. This matches the expected behavior for UI updates.

2. **Bidirectional exits by default**: When creating an exit A→B, the reverse
   exit B→A is created automatically unless explicitly disabled. This matches
   the design decision in ``goblin_cartography.md``.

3. **Validation on demand**: Functions perform minimal validation. Use the
   validation service for comprehensive checks before saving.

Exit Management
---------------
Exits connect rooms via cardinal directions (north, south, east, west, up, down).
The mapper supports:

- **Same-zone exits**: Target is a room ID (e.g., "hallway")
- **Cross-zone exits**: Target includes zone (e.g., "docks:pier")

Bidirectional exits are the default because MUD players expect symmetric
navigation. One-way exits (trapdoors, slides) can be created by setting
``bidirectional=False``.

Examples
--------
Creating a room::

    from pipeworks_mud_mapper.services import room_service
    from pipeworks_mud_mapper.models import Coords

    room_service.create_room(
        map_file,
        room_id="treasury",
        name="Treasury",
        coords=Coords(x=5, y=0, z=-1),
        description="Gold glitters in the torchlight.",
    )

Connecting rooms::

    room_service.create_exit(
        map_file,
        from_room="hallway",
        direction="east",
        to_room="treasury",
    )
    # Creates: hallway→east→treasury AND treasury→west→hallway

One-way exit (trapdoor)::

    room_service.create_exit(
        map_file,
        from_room="tower",
        direction="down",
        to_room="pit",
        bidirectional=False,
    )
    # Creates only: tower→down→pit (no return exit)

See Also
--------
- ``models/map_file.py``: MapFile model with underlying methods
- ``models/room.py``: Room and coordinate models
- ``goblin_cartography.md`` Section 1.7: Cardinal Points and Movement
"""

from pipeworks_mud_mapper.models import Coords, Direction, MapFile, MapRoom


def create_room(
    map_file: MapFile,
    room_id: str,
    name: str,
    coords: Coords,
    description: str = "",
) -> MapRoom:
    """Create a new room in the map file.

    Parameters
    ----------
    map_file : MapFile
        The map file to add the room to.
    room_id : str
        Unique identifier for the room.
    name : str
        Display name for the room.
    coords : Coords
        Position in 3D space.
    description : str, optional
        Room description text.

    Returns
    -------
    MapRoom
        The newly created room.

    Raises
    ------
    ValueError
        If a room with that ID already exists.
        If the room ID is invalid (must start with letter, lowercase).

    Examples
    --------
    >>> room = create_room(
    ...     map_file,
    ...     room_id="armory",
    ...     name="The Armory",
    ...     coords=Coords(x=10, y=0, z=0),
    ... )
    """
    return map_file.add_room(
        room_id=room_id,
        name=name,
        coords=coords,
        description=description,
    )


def update_room(
    map_file: MapFile,
    room_id: str,
    name: str | None = None,
    description: str | None = None,
    coords: Coords | None = None,
) -> MapRoom:
    """Update an existing room's properties.

    Only provided fields are updated; None values are ignored.

    Parameters
    ----------
    map_file : MapFile
        The map file containing the room.
    room_id : str
        ID of the room to update.
    name : str, optional
        New display name.
    description : str, optional
        New description text.
    coords : Coords, optional
        New position in 3D space.

    Returns
    -------
    MapRoom
        The updated room.

    Raises
    ------
    ValueError
        If the room does not exist.

    Examples
    --------
    >>> update_room(map_file, "spawn", name="Grand Entrance")
    >>> update_room(map_file, "spawn", coords=Coords(x=0, y=0, z=1))
    """
    room = map_file.get_room(room_id)
    if room is None:
        raise ValueError(f"Room '{room_id}' does not exist")

    if name is not None:
        room.name = name
    if description is not None:
        room.description = description
    if coords is not None:
        room.coords = coords

    return room


def delete_room(
    map_file: MapFile,
    room_id: str,
    remove_exits: bool = True,
) -> None:
    """Delete a room from the map file.

    Parameters
    ----------
    map_file : MapFile
        The map file containing the room.
    room_id : str
        ID of the room to delete.
    remove_exits : bool, default True
        If True, also remove all exits pointing to this room from other rooms.

    Raises
    ------
    ValueError
        If the room does not exist.
        If trying to delete the spawn room.

    Examples
    --------
    >>> delete_room(map_file, "old_room")

    Notes
    -----
    The spawn room cannot be deleted. Change spawn_room first if you need
    to remove the current spawn room.
    """
    if room_id not in map_file.rooms:
        raise ValueError(f"Room '{room_id}' does not exist")

    if room_id == map_file.spawn_room:
        raise ValueError(
            f"Cannot delete spawn room '{room_id}'. " "Change spawn_room to another room first."
        )

    # Remove exits pointing to this room from other rooms
    if remove_exits:
        for other_room in map_file.rooms.values():
            if other_room.id == room_id:
                continue
            # Find and remove exits to the deleted room
            exits_to_remove = [
                direction for direction, target in other_room.exits.items() if target == room_id
            ]
            for direction in exits_to_remove:
                del other_room.exits[direction]

    # Remove the room itself
    del map_file.rooms[room_id]


def create_exit(
    map_file: MapFile,
    from_room: str,
    direction: Direction,
    to_room: str,
    bidirectional: bool = True,
) -> None:
    """Create an exit between two rooms.

    By default, creates a bidirectional exit (both A→B and B→A).

    Parameters
    ----------
    map_file : MapFile
        The map file containing the rooms.
    from_room : str
        Source room ID.
    direction : Direction
        Direction of the exit (north, south, east, west, up, down).
    to_room : str
        Target room ID.
    bidirectional : bool, default True
        If True, also create the reverse exit.

    Raises
    ------
    ValueError
        If either room does not exist.

    Examples
    --------
    Bidirectional exit::

        >>> create_exit(map_file, "spawn", "north", "hallway")
        # Creates: spawn→north→hallway AND hallway→south→spawn

    One-way exit::

        >>> create_exit(map_file, "tower", "down", "pit", bidirectional=False)
        # Creates only: tower→down→pit
    """
    map_file.create_exit(from_room, direction, to_room, bidirectional)


def remove_exit(
    map_file: MapFile,
    from_room: str,
    direction: Direction,
    bidirectional: bool = True,
) -> None:
    """Remove an exit from a room.

    By default, removes both the exit and its reverse (if it exists and
    points back).

    Parameters
    ----------
    map_file : MapFile
        The map file containing the room.
    from_room : str
        Source room ID.
    direction : Direction
        Direction of the exit to remove.
    bidirectional : bool, default True
        If True, also remove the reverse exit from the target room.

    Examples
    --------
    >>> remove_exit(map_file, "spawn", "north")
    # Removes: spawn→north AND (if exists) target→south→spawn
    """
    map_file.remove_exit(from_room, direction, bidirectional)


def find_room_in_direction(
    map_file: MapFile,
    from_coords: Coords,
    direction: Direction,
    exclude_room: str | None = None,
) -> MapRoom | None:
    """Find the nearest room in a given direction.

    Searches for rooms that lie in the specified direction from the given
    coordinates, regardless of distance. Used for auto-connecting exits
    when the target room may not be at an adjacent coordinate.

    Parameters
    ----------
    map_file : MapFile
        The map file to search.
    from_coords : Coords
        Starting position to search from.
    direction : Direction
        Direction to search in.
    exclude_room : str, optional
        Room ID to exclude (typically the source room).

    Returns
    -------
    MapRoom or None
        The nearest room in that direction, or None if no room found.

    Examples
    --------
    >>> room = find_room_in_direction(
    ...     map_file,
    ...     Coords(x=0, y=0, z=0),
    ...     "north",
    ...     exclude_room="spawn",
    ... )
    >>> if room:
    ...     print(f"Found {room.name} to the north")
    """
    return map_file.find_room_in_direction(from_coords, direction, exclude_room)


def get_exit_target(map_file: MapFile, room_id: str, direction: Direction) -> str | None:
    """Get the target room ID for an exit.

    Parameters
    ----------
    map_file : MapFile
        The map file containing the room.
    room_id : str
        Source room ID.
    direction : Direction
        Direction of the exit.

    Returns
    -------
    str or None
        Target room ID, or None if no exit in that direction.

    Examples
    --------
    >>> target = get_exit_target(map_file, "spawn", "north")
    >>> if target:
    ...     print(f"North leads to {target}")
    """
    room = map_file.get_room(room_id)
    if room is None:
        return None
    return room.exits.get(direction)


def has_exit(map_file: MapFile, room_id: str, direction: Direction) -> bool:
    """Check if a room has an exit in a given direction.

    Parameters
    ----------
    map_file : MapFile
        The map file containing the room.
    room_id : str
        Room ID to check.
    direction : Direction
        Direction to check.

    Returns
    -------
    bool
        True if the room has an exit in that direction.

    Examples
    --------
    >>> if has_exit(map_file, "spawn", "north"):
    ...     print("There's a way north!")
    """
    return get_exit_target(map_file, room_id, direction) is not None


def get_connected_rooms(map_file: MapFile, room_id: str) -> list[tuple[Direction, str]]:
    """Get all rooms connected to a given room via exits.

    Parameters
    ----------
    map_file : MapFile
        The map file containing the room.
    room_id : str
        Room ID to check.

    Returns
    -------
    list[tuple[Direction, str]]
        List of (direction, target_room_id) tuples.

    Examples
    --------
    >>> connections = get_connected_rooms(map_file, "spawn")
    >>> for direction, target in connections:
    ...     print(f"{direction} -> {target}")
    """
    room = map_file.get_room(room_id)
    if room is None:
        return []
    return [(direction, target) for direction, target in room.exits.items()]
