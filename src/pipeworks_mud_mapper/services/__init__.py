"""Service layer for PipeWorks MUD Mapper.

This module provides the business logic layer that sits between the UI
(Dash callbacks) and the data models. Services are designed to be:

1. **Framework-agnostic**: No Dash imports - can be tested independently
2. **Stateless**: Operate on models passed as arguments
3. **Focused**: Each service has a single responsibility

Architecture
------------
The service layer implements the "thin callback" pattern where Dash callbacks
become simple orchestrators that:

1. Extract data from component state
2. Call service functions
3. Return updated state to components

This separation enables:

- Unit testing without Dash test harnesses
- Reuse in CLI tools or other interfaces
- Clear boundaries between UI and business logic

Service Modules
---------------
**zone_service**
    File I/O operations: load, save, export, create new zones.
    Handles the two-file workflow (map files vs zone files).

**validation_service**
    Map validation: connectivity, exit consistency, language-direction
    conflicts. Returns structured warnings for UI display.

Usage
-----
In a Dash callback::

    from pipeworks_mud_mapper.services import zone_service

    @app.callback(...)
    def handle_save(map_data, filename):
        map_file = MapFile.from_dict(map_data)
        zone_service.save_map_file(map_file, Path(filename))
        return "Saved successfully"

See Also
--------
- ``models/``: Domain models operated on by services
- ``callbacks/``: Dash callbacks that use services (Phase 4)
- ``refactor_01.md``: Architecture decisions and rationale
"""

from pipeworks_mud_mapper.services.description_validator import (
    load_validator_config,
    validate_description,
)
from pipeworks_mud_mapper.services.template_service import (
    compile_system_prompt,
    get_templates_directory,
    list_templates,
    load_template,
)
from pipeworks_mud_mapper.services.validation_service import (
    ValidationWarning,
    validate_all,
    validate_connectivity,
    validate_exit_consistency,
    validate_language_direction,
)
from pipeworks_mud_mapper.services.zone_service import (
    create_new_map_file,
    export_zone,
    list_map_files,
    load_map_file,
    save_map_file,
)

__all__ = [
    # Zone service
    "load_map_file",
    "save_map_file",
    "export_zone",
    "create_new_map_file",
    # Validation service
    "ValidationWarning",
    "validate_all",
    "validate_connectivity",
    "validate_exit_consistency",
    "validate_language_direction",
    # Template service
    "get_templates_directory",
    "list_templates",
    "load_template",
    "compile_system_prompt",
    # Zone helpers
    "list_map_files",
    # Description validator
    "load_validator_config",
    "validate_description",
]
