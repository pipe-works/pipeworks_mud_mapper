"""Description validation metadata model.

Stores the latest validator output for an LLM-generated room description.
This metadata is authoring scaffolding and is stripped on zone export,
mirroring how coordinates and LLM provenance are treated.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class DescriptionValidationInfo(BaseModel):
    """Metadata produced by the description validator.

    This is intentionally small and explicit. It preserves enough information
    to understand validator outcomes without forcing any narrative changes.
    """

    valid: bool = Field(
        ...,
        description="Whether the description passed hard rules",
    )
    hard_failures: list[str] = Field(
        default_factory=list,
        description="List of hard rule failures",
    )
    soft_failures: list[str] = Field(
        default_factory=list,
        description="List of soft rule failures (advisory)",
    )
    metrics: dict = Field(
        default_factory=dict,
        description="Validation metrics (word count, bounds, etc.)",
    )
    rule_hits: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Matched tokens grouped by rule name",
    )
    validated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp of the validation run",
    )
