"""Shared metadata models for map and zone files.

These models capture versioning and export provenance while keeping the
runtime schema clean. Authoring files (MapFile) include version counters,
while exported zone files include an exported_from stamp.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ExportedFrom(BaseModel):
    """Provenance for a zone export.

    Stored under ``metadata.exported_from`` on exported zone files.
    """

    map_id: str = Field(..., min_length=1, description="Source map identifier")
    map_version: str = Field(..., min_length=1, description="Map version at export time")
    map_revision: int = Field(..., ge=0, description="Map revision at export time")
    exported_at: datetime = Field(..., description="Export timestamp (ISO in JSON)")
    exporter: str = Field(..., min_length=1, description="Exporter name and version")


class MapMetadata(BaseModel):
    """Metadata stored on authoring ``*.map.json`` files."""

    schema_version: str = Field(default="0.1.0", description="Runtime JSON schema version")
    map_version: str = Field(default="0", description="Authoring milestone (export counter)")
    map_revision: int = Field(default=0, ge=0, description="Authoring save counter")


class ZoneMetadata(BaseModel):
    """Metadata stored on exported zone files."""

    schema_version: str = Field(default="0.1.0", description="Runtime JSON schema version")
    exported_from: ExportedFrom | None = Field(
        default=None,
        description="Export provenance from the source map file",
    )
