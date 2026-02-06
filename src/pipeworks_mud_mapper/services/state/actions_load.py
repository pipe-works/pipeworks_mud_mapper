"""Load-related zone state transitions."""

from __future__ import annotations

from pipeworks_mud_mapper.services import map_db_service
from pipeworks_mud_mapper.services.state.types import ZoneTransition


def load_map(*, map_id: str) -> ZoneTransition:
    """Load a map from SQLite into zone data.

    Parameters
    ----------
    map_id : str
        Map identifier in the SQLite database.
    """
    try:
        map_file = map_db_service.load_map(map_id)
        zone_data = map_file.to_dict_with_list_coords()
        zone_name = zone_data.get("name", map_id)
    except Exception:
        return ZoneTransition(zone_data=None, changed=False)

    return ZoneTransition(
        zone_data=zone_data,
        effects={"zone_name": zone_name},
        changed=True,
    )
