"""Load-related zone state transitions."""

from __future__ import annotations

from pipeworks_mud_mapper.services import zone_service
from pipeworks_mud_mapper.services.state.types import ZoneTransition


def load_map(*, file_path) -> ZoneTransition:
    """Load a map file into zone data.

    Parameters
    ----------
    file_path : Path
        Full path to the map file.
    """
    try:
        map_file = zone_service.load_map_file(file_path)
        zone_data = map_file.to_dict_with_list_coords()
        zone_name = zone_data.get("name", file_path.name)
    except Exception:
        return ZoneTransition(zone_data=None, changed=False)

    return ZoneTransition(
        zone_data=zone_data,
        effects={"zone_name": zone_name},
        changed=True,
    )
