"""Validation service for map integrity checks.

This module provides validation functions that check map files for common
issues. Validations are non-destructive - they return warnings but don't
modify the map.

Validation Categories
---------------------
**Connectivity**
    - Unreachable rooms (no path from spawn)
    - Dead-end rooms (no exits)
    - Broken exit references

**Exit Consistency**
    - Asymmetric exits (A→B exists but B→A doesn't)
    - Direction conflicts (exit says "north" but coords say "south")

**Language-Direction**
    - Room names with vertical words ("Upper", "Basement") that don't
      match their navigational reality
    - This catches the "Upper Landing" problem from goblin_cartography.md

Warning Severity
----------------
Warnings have severity levels:

- **ERROR**: Must be fixed before export (broken references)
- **WARNING**: Should be reviewed but may be intentional (dead ends)
- **INFO**: Informational only (asymmetric exits may be intended)

Usage
-----
Run all validations::

    from pipeworks_mud_mapper.services import validation_service

    warnings = validation_service.validate_all(map_file)
    for warning in warnings:
        print(f"[{warning.severity}] {warning.room_id}: {warning.message}")

Run specific validations::

    conn_warnings = validation_service.validate_connectivity(map_file)
    exit_warnings = validation_service.validate_exit_consistency(map_file)

See Also
--------
- ``goblin_cartography.md`` Section 1.9: Developer Mapping Tools
- ``goblin_cartography.md`` Section 1.7: The "Upper Landing" Problem
"""

from dataclasses import dataclass
from enum import Enum

from pipeworks_mud_mapper.models import Direction, MapFile
from pipeworks_mud_mapper.models.room import OPPOSITE_DIRECTION


class Severity(str, Enum):
    """Severity level for validation warnings."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationWarning:
    """A validation warning or error.

    Attributes
    ----------
    severity : Severity
        How serious this issue is.
    category : str
        Category of the warning (connectivity, consistency, language).
    room_id : str or None
        Room ID related to the warning, if applicable.
    message : str
        Human-readable description of the issue.
    details : dict
        Additional structured data about the issue.
    """

    severity: Severity
    category: str
    room_id: str | None
    message: str
    details: dict | None = None

    def __str__(self) -> str:
        """Format warning as a string."""
        room_part = f" [{self.room_id}]" if self.room_id else ""
        return f"[{self.severity.value.upper()}]{room_part} {self.message}"


def validate_all(map_file: MapFile) -> list[ValidationWarning]:
    """Run all validation checks on a map file.

    Parameters
    ----------
    map_file : MapFile
        The map file to validate.

    Returns
    -------
    list[ValidationWarning]
        All warnings from all validation checks, sorted by severity.

    Examples
    --------
    >>> warnings = validate_all(map_file)
    >>> errors = [w for w in warnings if w.severity == Severity.ERROR]
    >>> if errors:
    ...     print("Cannot export: fix errors first")
    """
    warnings: list[ValidationWarning] = []

    warnings.extend(validate_connectivity(map_file))
    warnings.extend(validate_exit_consistency(map_file))
    warnings.extend(validate_language_direction(map_file))

    # Sort by severity (errors first)
    severity_order = {Severity.ERROR: 0, Severity.WARNING: 1, Severity.INFO: 2}
    warnings.sort(key=lambda w: severity_order[w.severity])

    return warnings


def validate_connectivity(map_file: MapFile) -> list[ValidationWarning]:
    """Check for connectivity issues.

    Checks for:
    - Unreachable rooms (no path from spawn)
    - Dead-end rooms (no exits)
    - Broken exit references (exit to nonexistent room)

    Parameters
    ----------
    map_file : MapFile
        The map file to validate.

    Returns
    -------
    list[ValidationWarning]
        Connectivity warnings.

    Examples
    --------
    >>> warnings = validate_connectivity(map_file)
    >>> for w in warnings:
    ...     if "unreachable" in w.message:
    ...         print(f"Orphan room: {w.room_id}")
    """
    warnings: list[ValidationWarning] = []

    # Check for broken exit references
    for room_id, room in map_file.rooms.items():
        for direction, target in room.exits.items():
            # Skip cross-zone exits
            if ":" in target:
                continue
            if target not in map_file.rooms:
                warnings.append(
                    ValidationWarning(
                        severity=Severity.ERROR,
                        category="connectivity",
                        room_id=room_id,
                        message=f"Exit '{direction}' leads to nonexistent room '{target}'",
                        details={"direction": direction, "target": target},
                    )
                )

    # Check for unreachable rooms
    unreachable = _find_unreachable_rooms(map_file)
    for room_id in unreachable:
        warnings.append(
            ValidationWarning(
                severity=Severity.WARNING,
                category="connectivity",
                room_id=room_id,
                message=f"Room is unreachable from spawn '{map_file.spawn_room}'",
            )
        )

    # Check for dead-end rooms
    for room_id, room in map_file.rooms.items():
        if not room.exits:
            warnings.append(
                ValidationWarning(
                    severity=Severity.INFO,
                    category="connectivity",
                    room_id=room_id,
                    message="Room has no exits (dead end)",
                )
            )

    return warnings


def _find_unreachable_rooms(map_file: MapFile) -> list[str]:
    """Find rooms that cannot be reached from spawn.

    Uses breadth-first search from spawn_room.
    """
    if not map_file.rooms:
        return []

    reachable: set[str] = set()
    queue = [map_file.spawn_room]

    while queue:
        current = queue.pop(0)
        if current in reachable:
            continue
        reachable.add(current)

        room = map_file.rooms.get(current)
        if room:
            for target in room.exits.values():
                # Handle cross-zone exits - only follow same-zone
                if ":" not in target and target not in reachable:
                    queue.append(target)

    all_rooms = set(map_file.rooms.keys())
    return sorted(all_rooms - reachable)


def validate_exit_consistency(map_file: MapFile) -> list[ValidationWarning]:
    """Check for exit consistency issues.

    Checks for:
    - Asymmetric exits (A→north→B but B has no south→A)
    - Direction/coordinate mismatches (exit says "north" but room is south)

    Parameters
    ----------
    map_file : MapFile
        The map file to validate.

    Returns
    -------
    list[ValidationWarning]
        Exit consistency warnings.

    Notes
    -----
    Asymmetric exits are flagged as INFO, not errors, because some asymmetry
    is intentional (one-way doors, hidden passages, trapdoors).
    """
    warnings: list[ValidationWarning] = []

    checked_pairs: set[tuple[str, str]] = set()

    for room_id, room in map_file.rooms.items():
        for direction, target in room.exits.items():
            # Skip cross-zone exits
            if ":" in target:
                continue

            # Skip if already checked this pair
            pair: tuple[str, str] = (min(room_id, target), max(room_id, target))
            if pair in checked_pairs:
                continue
            checked_pairs.add(pair)

            target_room = map_file.rooms.get(target)
            if not target_room:
                continue  # Already caught by connectivity check

            # Check for asymmetric exits
            opposite = OPPOSITE_DIRECTION.get(direction)
            if opposite:
                return_exit = target_room.exits.get(opposite)
                if return_exit != room_id:
                    if return_exit is None:
                        warnings.append(
                            ValidationWarning(
                                severity=Severity.INFO,
                                category="consistency",
                                room_id=room_id,
                                message=(
                                    f"Asymmetric exit: {room_id}→{direction}→{target}, "
                                    f"but {target} has no {opposite} exit back"
                                ),
                                details={
                                    "from_room": room_id,
                                    "direction": direction,
                                    "to_room": target,
                                    "expected_return": opposite,
                                },
                            )
                        )
                    else:
                        warnings.append(
                            ValidationWarning(
                                severity=Severity.INFO,
                                category="consistency",
                                room_id=room_id,
                                message=(
                                    f"Exit mismatch: {room_id}→{direction}→{target}, "
                                    f"but {target}→{opposite}→{return_exit} (not back to {room_id})"
                                ),
                                details={
                                    "from_room": room_id,
                                    "direction": direction,
                                    "to_room": target,
                                    "return_direction": opposite,
                                    "actual_return": return_exit,
                                },
                            )
                        )

            # Check for direction/coordinate mismatches
            warning = _check_direction_coords_match(room, target_room, direction)
            if warning:
                warnings.append(warning)

    return warnings


def _check_direction_coords_match(
    from_room,
    to_room,
    direction: Direction,
) -> ValidationWarning | None:
    """Check if an exit direction matches the coordinate relationship.

    For example, if room A has an exit "north" to room B, but B is actually
    south of A according to coordinates, this is a mismatch.
    """
    from_coords = from_room.coords.to_tuple()
    to_coords = to_room.coords.to_tuple()

    dx = to_coords[0] - from_coords[0]
    dy = to_coords[1] - from_coords[1]
    dz = to_coords[2] - from_coords[2]

    # Determine actual direction based on coordinates
    actual_direction = None
    if dx > 0 and dy == 0 and dz == 0:
        actual_direction = "east"
    elif dx < 0 and dy == 0 and dz == 0:
        actual_direction = "west"
    elif dy > 0 and dx == 0 and dz == 0:
        actual_direction = "north"
    elif dy < 0 and dx == 0 and dz == 0:
        actual_direction = "south"
    elif dz > 0 and dx == 0 and dy == 0:
        actual_direction = "up"
    elif dz < 0 and dx == 0 and dy == 0:
        actual_direction = "down"
    # If movement is diagonal or zero, we can't determine direction

    if actual_direction and actual_direction != direction:
        return ValidationWarning(
            severity=Severity.WARNING,
            category="consistency",
            room_id=from_room.id,
            message=(
                f"Direction mismatch: exit says '{direction}' to '{to_room.id}', "
                f"but coordinates suggest '{actual_direction}'"
            ),
            details={
                "from_room": from_room.id,
                "to_room": to_room.id,
                "exit_direction": direction,
                "coordinate_direction": actual_direction,
                "from_coords": list(from_coords),
                "to_coords": list(to_coords),
            },
        )

    return None


# Words that imply vertical position
VERTICAL_WORDS_UP = {"upper", "upstairs", "attic", "top", "tower", "rooftop", "above"}
VERTICAL_WORDS_DOWN = {
    "lower",
    "downstairs",
    "basement",
    "cellar",
    "underground",
    "below",
    "pit",
    "dungeon",
}


def validate_language_direction(map_file: MapFile) -> list[ValidationWarning]:
    """Check for language-direction conflicts in room names.

    Flags rooms whose names contain vertical words (like "Upper", "Basement")
    but are not reached via the corresponding vertical direction (up/down).

    This catches the "Upper Landing" problem from goblin_cartography.md:
    a room named "Upper Landing" reached via "north" creates cognitive
    dissonance for players trying to build a mental map.

    Parameters
    ----------
    map_file : MapFile
        The map file to validate.

    Returns
    -------
    list[ValidationWarning]
        Language-direction conflict warnings.

    Notes
    -----
    These are flagged as INFO because the author may have intentional reasons
    for the naming, or may be using the word in a non-directional sense.
    """
    warnings: list[ValidationWarning] = []

    for room_id, room in map_file.rooms.items():
        name_lower = room.name.lower()
        name_words = set(name_lower.split())

        # Check for "upper" type words
        upper_matches = name_words & VERTICAL_WORDS_UP
        if upper_matches:
            # Check if any incoming exit is "up"
            reached_via_up = _is_room_reached_via(map_file, room_id, "up")
            if not reached_via_up:
                warnings.append(
                    ValidationWarning(
                        severity=Severity.INFO,
                        category="language",
                        room_id=room_id,
                        message=(
                            f"Room name contains '{list(upper_matches)[0]}' but "
                            "is not reached via 'up' from any connected room"
                        ),
                        details={
                            "vertical_word": list(upper_matches)[0],
                            "expected_direction": "up",
                        },
                    )
                )

        # Check for "lower" type words
        lower_matches = name_words & VERTICAL_WORDS_DOWN
        if lower_matches:
            # Check if any incoming exit is "down"
            reached_via_down = _is_room_reached_via(map_file, room_id, "down")
            if not reached_via_down:
                warnings.append(
                    ValidationWarning(
                        severity=Severity.INFO,
                        category="language",
                        room_id=room_id,
                        message=(
                            f"Room name contains '{list(lower_matches)[0]}' but "
                            "is not reached via 'down' from any connected room"
                        ),
                        details={
                            "vertical_word": list(lower_matches)[0],
                            "expected_direction": "down",
                        },
                    )
                )

    return warnings


def _is_room_reached_via(map_file: MapFile, room_id: str, direction: Direction) -> bool:
    """Check if any room has an exit in the given direction to this room."""
    for other_room in map_file.rooms.values():
        if other_room.exits.get(direction) == room_id:
            return True
    return False


def has_errors(warnings: list[ValidationWarning]) -> bool:
    """Check if any warnings are errors.

    Parameters
    ----------
    warnings : list[ValidationWarning]
        List of validation warnings.

    Returns
    -------
    bool
        True if any warning has ERROR severity.

    Examples
    --------
    >>> warnings = validate_all(map_file)
    >>> if has_errors(warnings):
    ...     print("Fix errors before exporting")
    """
    return any(w.severity == Severity.ERROR for w in warnings)


def filter_by_severity(
    warnings: list[ValidationWarning],
    severity: Severity,
) -> list[ValidationWarning]:
    """Filter warnings by severity level.

    Parameters
    ----------
    warnings : list[ValidationWarning]
        List of validation warnings.
    severity : Severity
        Severity level to filter for.

    Returns
    -------
    list[ValidationWarning]
        Warnings matching the specified severity.

    Examples
    --------
    >>> errors = filter_by_severity(warnings, Severity.ERROR)
    """
    return [w for w in warnings if w.severity == severity]


def filter_by_category(
    warnings: list[ValidationWarning],
    category: str,
) -> list[ValidationWarning]:
    """Filter warnings by category.

    Parameters
    ----------
    warnings : list[ValidationWarning]
        List of validation warnings.
    category : str
        Category to filter for (connectivity, consistency, language).

    Returns
    -------
    list[ValidationWarning]
        Warnings matching the specified category.

    Examples
    --------
    >>> conn_issues = filter_by_category(warnings, "connectivity")
    """
    return [w for w in warnings if w.category == category]


def create_validation_report(
    map_file_name: str,
    warnings: list[ValidationWarning],
) -> dict:
    """Create a validation report dictionary.

    Creates a structured report suitable for JSON serialization and
    display in the UI. The report includes a summary with counts by
    severity and a pass/fail status based on whether any errors exist.

    Parameters
    ----------
    map_file_name : str
        Name of the map file that was validated.
    warnings : list[ValidationWarning]
        List of validation warnings from validate_all().

    Returns
    -------
    dict
        Validation report with the following structure::

            {
                "timestamp": "2026-02-02T17:00:00Z",
                "map_file": "ledgerfall_alley.map.json",
                "summary": {
                    "errors": 0,
                    "warnings": 2,
                    "info": 3,
                    "total": 5,
                    "passed": true
                },
                "warnings": [
                    {
                        "severity": "warning",
                        "category": "connectivity",
                        "room_id": "room_1",
                        "message": "Room is unreachable from spawn"
                    }
                ]
            }

    Examples
    --------
    >>> warnings = validate_all(map_file)
    >>> report = create_validation_report("my_zone.map.json", warnings)
    >>> if report["summary"]["passed"]:
    ...     print("Validation passed!")
    """
    from datetime import UTC, datetime

    # Count warnings by severity
    error_count = len([w for w in warnings if w.severity == Severity.ERROR])
    warning_count = len([w for w in warnings if w.severity == Severity.WARNING])
    info_count = len([w for w in warnings if w.severity == Severity.INFO])

    # Build the report structure
    report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "map_file": map_file_name,
        "summary": {
            "errors": error_count,
            "warnings": warning_count,
            "info": info_count,
            "total": len(warnings),
            "passed": error_count == 0,  # Pass if no errors (warnings OK)
        },
        "warnings": [
            {
                "severity": w.severity.value,
                "category": w.category,
                "room_id": w.room_id,
                "message": w.message,
                "details": w.details,
            }
            for w in warnings
        ],
    }

    return report


def write_validation_report(
    map_file_name: str,
    warnings: list[ValidationWarning],
    output_dir: str | None = None,
) -> str:
    """Write a validation report to a JSON file.

    Creates a validation report and writes it to the data/validation/
    directory. The file is named after the map file with a .validation.json
    extension.

    Parameters
    ----------
    map_file_name : str
        Name of the map file that was validated (e.g., "my_zone.map.json").
    warnings : list[ValidationWarning]
        List of validation warnings from validate_all().
    output_dir : str, optional
        Directory to write the report to. Defaults to "data/validation/".

    Returns
    -------
    str
        Absolute path to the written validation report file.

    Raises
    ------
    OSError
        If the output directory cannot be created or the file cannot be written.

    Examples
    --------
    >>> warnings = validate_all(map_file)
    >>> report_path = write_validation_report("my_zone.map.json", warnings)
    >>> print(f"Report written to: {report_path}")

    Notes
    -----
    The validation directory is created if it doesn't exist. Previous
    validation reports for the same map file are overwritten.

    The report file uses the naming convention:
    ``{zone_id}.validation.json`` where zone_id is extracted from
    the map file name (e.g., "my_zone.map.json" -> "my_zone.validation.json").
    """
    import json
    from pathlib import Path

    # Default to data/validation/ directory
    output_path_dir: Path
    if output_dir is None:
        # Find the project data directory relative to the package
        package_dir = Path(__file__).parent.parent.parent.parent
        output_path_dir = package_dir / "data" / "validation"
    else:
        output_path_dir = Path(output_dir)

    # Ensure the output directory exists
    output_path_dir.mkdir(parents=True, exist_ok=True)

    # Create the report
    report = create_validation_report(map_file_name, warnings)

    # Generate output filename from map file name
    # "my_zone.map.json" -> "my_zone.validation.json"
    base_name = map_file_name
    if base_name.endswith(".map.json"):
        base_name = base_name[:-9]  # Remove ".map.json"
    elif base_name.endswith(".json"):
        base_name = base_name[:-5]  # Remove ".json"

    output_filename = f"{base_name}.validation.json"
    output_path = output_path_dir / output_filename

    # Write the report with pretty formatting
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return str(output_path.resolve())
