"""Comprehensive tests for OllamaGenerationInfo model.

This module tests the Pydantic model that stores LLM generation metadata
for room descriptions. The metadata enables:

1. **Reproducibility**: Same seed + parameters = same output
2. **Provenance**: Track how descriptions were generated

Test Organization
-----------------
- **TestOllamaGenerationInfoBasics**: Model creation and defaults
- **TestOllamaGenerationInfoValidation**: Field validation and constraints
- **TestOllamaGenerationInfoSerialization**: JSON serialization round-trips

See Also
--------
- ``models/ollama_generation.py``: The model being tested
- ``models/room.py``: MapRoom model that contains this metadata
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from pipeworks_mud_mapper.models import OllamaGenerationInfo

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def valid_generation_info() -> dict:
    """Create a valid generation info dict for testing.

    Returns a dictionary with all required fields populated with valid values.
    This can be used directly to create OllamaGenerationInfo instances.
    """
    return {
        "model": "gemma2:2b",
        "actual_seed": 12345,
        "template_id": "ledgerfall_goblin",
        "temperature": 0.7,
        "top_k": 40,
        "top_p": 0.9,
        "num_ctx": 4096,
        "num_predict": 512,
        "system_prompt": "You are a creative writer for a MUD...",
        "user_prompt": "Describe a quiet alley in Ledgerfall",
    }


# =============================================================================
# Basic Creation Tests
# =============================================================================


class TestOllamaGenerationInfoBasics:
    """Tests for basic OllamaGenerationInfo creation and defaults."""

    def test_create_with_all_fields(self, valid_generation_info):
        """OllamaGenerationInfo should accept all required fields."""
        info = OllamaGenerationInfo(**valid_generation_info)

        assert info.model == "gemma2:2b"
        assert info.actual_seed == 12345
        assert info.template_id == "ledgerfall_goblin"
        assert info.temperature == 0.7
        assert info.top_k == 40
        assert info.top_p == 0.9
        assert info.num_ctx == 4096
        assert info.num_predict == 512
        assert info.system_prompt == "You are a creative writer for a MUD..."
        assert info.user_prompt == "Describe a quiet alley in Ledgerfall"

    def test_generated_at_defaults_to_now(self, valid_generation_info):
        """generated_at should default to current UTC time if not provided.

        This test verifies that when generated_at is not provided, a default
        timestamp is created. We allow some tolerance for test execution time.
        """
        before = datetime.now(UTC)
        info = OllamaGenerationInfo(**valid_generation_info)
        after = datetime.now(UTC)

        # generated_at should be between before and after
        assert before <= info.generated_at <= after

    def test_generated_at_explicit_value(self, valid_generation_info):
        """generated_at should accept explicit timestamp."""
        explicit_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
        valid_generation_info["generated_at"] = explicit_time

        info = OllamaGenerationInfo(**valid_generation_info)

        assert info.generated_at == explicit_time

    def test_custom_template_id(self, valid_generation_info):
        """template_id should accept '__custom__' for manual prompts."""
        valid_generation_info["template_id"] = "__custom__"

        info = OllamaGenerationInfo(**valid_generation_info)

        assert info.template_id == "__custom__"

    def test_empty_system_prompt_allowed(self, valid_generation_info):
        """system_prompt can be empty string (for custom mode without system prompt)."""
        valid_generation_info["system_prompt"] = ""

        info = OllamaGenerationInfo(**valid_generation_info)

        assert info.system_prompt == ""


# =============================================================================
# Validation Tests
# =============================================================================


class TestOllamaGenerationInfoValidation:
    """Tests for field validation and constraints."""

    def test_model_must_not_be_empty(self, valid_generation_info):
        """model field must have at least 1 character."""
        valid_generation_info["model"] = ""

        with pytest.raises(ValidationError, match="at least 1"):
            OllamaGenerationInfo(**valid_generation_info)

    def test_actual_seed_must_be_non_negative(self, valid_generation_info):
        """actual_seed must be >= 0 (no random mode indicator stored).

        The actual_seed field stores the seed that was *actually* used,
        not the user's request. Even if user requested -1 (random),
        actual_seed will contain the generated positive seed.
        """
        valid_generation_info["actual_seed"] = -1

        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            OllamaGenerationInfo(**valid_generation_info)

    def test_actual_seed_zero_is_valid(self, valid_generation_info):
        """actual_seed of 0 should be valid."""
        valid_generation_info["actual_seed"] = 0

        info = OllamaGenerationInfo(**valid_generation_info)

        assert info.actual_seed == 0

    def test_actual_seed_large_value(self, valid_generation_info):
        """actual_seed should accept large values (up to 2^31-1)."""
        valid_generation_info["actual_seed"] = 2**31 - 1

        info = OllamaGenerationInfo(**valid_generation_info)

        assert info.actual_seed == 2**31 - 1

    # Temperature validation tests
    def test_temperature_minimum(self, valid_generation_info):
        """temperature must be >= 0.0."""
        valid_generation_info["temperature"] = -0.1

        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            OllamaGenerationInfo(**valid_generation_info)

    def test_temperature_maximum(self, valid_generation_info):
        """temperature must be <= 2.0."""
        valid_generation_info["temperature"] = 2.1

        with pytest.raises(ValidationError, match="less than or equal to 2"):
            OllamaGenerationInfo(**valid_generation_info)

    def test_temperature_boundary_values(self, valid_generation_info):
        """temperature boundary values (0.0 and 2.0) should be valid."""
        valid_generation_info["temperature"] = 0.0
        info1 = OllamaGenerationInfo(**valid_generation_info)
        assert info1.temperature == 0.0

        valid_generation_info["temperature"] = 2.0
        info2 = OllamaGenerationInfo(**valid_generation_info)
        assert info2.temperature == 2.0

    # Top-K validation tests
    def test_top_k_minimum(self, valid_generation_info):
        """top_k must be >= 1."""
        valid_generation_info["top_k"] = 0

        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            OllamaGenerationInfo(**valid_generation_info)

    def test_top_k_maximum(self, valid_generation_info):
        """top_k must be <= 100."""
        valid_generation_info["top_k"] = 101

        with pytest.raises(ValidationError, match="less than or equal to 100"):
            OllamaGenerationInfo(**valid_generation_info)

    def test_top_k_boundary_values(self, valid_generation_info):
        """top_k boundary values (1 and 100) should be valid."""
        valid_generation_info["top_k"] = 1
        info1 = OllamaGenerationInfo(**valid_generation_info)
        assert info1.top_k == 1

        valid_generation_info["top_k"] = 100
        info2 = OllamaGenerationInfo(**valid_generation_info)
        assert info2.top_k == 100

    # Top-P validation tests
    def test_top_p_minimum(self, valid_generation_info):
        """top_p must be >= 0.0."""
        valid_generation_info["top_p"] = -0.1

        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            OllamaGenerationInfo(**valid_generation_info)

    def test_top_p_maximum(self, valid_generation_info):
        """top_p must be <= 1.0."""
        valid_generation_info["top_p"] = 1.1

        with pytest.raises(ValidationError, match="less than or equal to 1"):
            OllamaGenerationInfo(**valid_generation_info)

    def test_top_p_boundary_values(self, valid_generation_info):
        """top_p boundary values (0.0 and 1.0) should be valid."""
        valid_generation_info["top_p"] = 0.0
        info1 = OllamaGenerationInfo(**valid_generation_info)
        assert info1.top_p == 0.0

        valid_generation_info["top_p"] = 1.0
        info2 = OllamaGenerationInfo(**valid_generation_info)
        assert info2.top_p == 1.0

    # num_ctx validation tests
    def test_num_ctx_minimum(self, valid_generation_info):
        """num_ctx must be >= 512."""
        valid_generation_info["num_ctx"] = 511

        with pytest.raises(ValidationError, match="greater than or equal to 512"):
            OllamaGenerationInfo(**valid_generation_info)

    def test_num_ctx_maximum(self, valid_generation_info):
        """num_ctx must be <= 8192."""
        valid_generation_info["num_ctx"] = 8193

        with pytest.raises(ValidationError, match="less than or equal to 8192"):
            OllamaGenerationInfo(**valid_generation_info)

    def test_num_ctx_boundary_values(self, valid_generation_info):
        """num_ctx boundary values (512 and 8192) should be valid."""
        valid_generation_info["num_ctx"] = 512
        info1 = OllamaGenerationInfo(**valid_generation_info)
        assert info1.num_ctx == 512

        valid_generation_info["num_ctx"] = 8192
        info2 = OllamaGenerationInfo(**valid_generation_info)
        assert info2.num_ctx == 8192

    # num_predict validation tests
    def test_num_predict_minimum(self, valid_generation_info):
        """num_predict must be >= 30."""
        valid_generation_info["num_predict"] = 29

        with pytest.raises(ValidationError, match="greater than or equal to 30"):
            OllamaGenerationInfo(**valid_generation_info)

    def test_num_predict_maximum(self, valid_generation_info):
        """num_predict must be <= 2048."""
        valid_generation_info["num_predict"] = 2049

        with pytest.raises(ValidationError, match="less than or equal to 2048"):
            OllamaGenerationInfo(**valid_generation_info)

    def test_num_predict_boundary_values(self, valid_generation_info):
        """num_predict boundary values (64 and 2048) should be valid."""
        valid_generation_info["num_predict"] = 64
        info1 = OllamaGenerationInfo(**valid_generation_info)
        assert info1.num_predict == 64

        valid_generation_info["num_predict"] = 2048
        info2 = OllamaGenerationInfo(**valid_generation_info)
        assert info2.num_predict == 2048


# =============================================================================
# Serialization Tests
# =============================================================================


class TestOllamaGenerationInfoSerialization:
    """Tests for JSON serialization and deserialization."""

    def test_model_dump_preserves_all_fields(self, valid_generation_info):
        """model_dump should preserve all field values."""
        info = OllamaGenerationInfo(**valid_generation_info)
        data = info.model_dump()

        assert data["model"] == valid_generation_info["model"]
        assert data["actual_seed"] == valid_generation_info["actual_seed"]
        assert data["template_id"] == valid_generation_info["template_id"]
        assert data["temperature"] == valid_generation_info["temperature"]
        assert data["top_k"] == valid_generation_info["top_k"]
        assert data["top_p"] == valid_generation_info["top_p"]
        assert data["num_ctx"] == valid_generation_info["num_ctx"]
        assert data["num_predict"] == valid_generation_info["num_predict"]
        assert data["system_prompt"] == valid_generation_info["system_prompt"]
        assert data["user_prompt"] == valid_generation_info["user_prompt"]
        # generated_at will be present (default or explicit)
        assert "generated_at" in data

    def test_model_dump_json_mode(self, valid_generation_info):
        """model_dump(mode='json') should serialize datetime as ISO string.

        This is critical for JSON serialization - datetime objects need to
        be converted to strings for storage in .map.json files.
        """
        explicit_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
        valid_generation_info["generated_at"] = explicit_time

        info = OllamaGenerationInfo(**valid_generation_info)
        data = info.model_dump(mode="json")

        # In JSON mode, datetime becomes ISO string
        assert isinstance(data["generated_at"], str)
        assert "2024-01-15" in data["generated_at"]

    def test_round_trip_serialization(self, valid_generation_info):
        """OllamaGenerationInfo should survive dict round-trip.

        Create -> model_dump -> model_validate should preserve all values.
        """
        original = OllamaGenerationInfo(**valid_generation_info)
        data = original.model_dump()
        restored = OllamaGenerationInfo.model_validate(data)

        assert restored.model == original.model
        assert restored.actual_seed == original.actual_seed
        assert restored.template_id == original.template_id
        assert restored.temperature == original.temperature
        assert restored.top_k == original.top_k
        assert restored.top_p == original.top_p
        assert restored.num_ctx == original.num_ctx
        assert restored.num_predict == original.num_predict
        assert restored.system_prompt == original.system_prompt
        assert restored.user_prompt == original.user_prompt
        assert restored.generated_at == original.generated_at

    def test_json_serialization_round_trip(self, valid_generation_info):
        """OllamaGenerationInfo should survive JSON round-trip.

        This tests the actual JSON serialization/deserialization path
        that occurs when saving/loading .map.json files.
        """
        import json

        explicit_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
        valid_generation_info["generated_at"] = explicit_time

        original = OllamaGenerationInfo(**valid_generation_info)

        # Serialize to JSON string (as would happen in file save)
        json_str = json.dumps(original.model_dump(mode="json"))

        # Deserialize from JSON string (as would happen in file load)
        data = json.loads(json_str)
        restored = OllamaGenerationInfo.model_validate(data)

        assert restored.model == original.model
        assert restored.actual_seed == original.actual_seed
        # Note: datetime comparison - Pydantic handles ISO string -> datetime
        assert restored.generated_at == original.generated_at


# =============================================================================
# Integration with MapRoom Tests
# =============================================================================


class TestOllamaGenerationInfoWithMapRoom:
    """Tests for OllamaGenerationInfo integration with MapRoom model.

    These tests verify that llm_generation metadata is correctly stored
    in MapRoom and stripped during zone export.
    """

    def test_maproom_with_llm_generation(self, valid_generation_info):
        """MapRoom should accept llm_generation metadata."""
        from pipeworks_mud_mapper.models import Coords, MapRoom

        # Create generation info
        gen_info = OllamaGenerationInfo(**valid_generation_info)

        # Create room with generation info
        room = MapRoom(
            id="spawn",
            name="Spawn Room",
            description="A generated description.",
            coords=Coords(x=0, y=0, z=0),
            llm_generation=gen_info,
        )

        assert room.llm_generation is not None
        assert room.llm_generation.model == "gemma2:2b"
        assert room.llm_generation.actual_seed == 12345

    def test_maproom_without_llm_generation(self):
        """MapRoom should work without llm_generation (default None)."""
        from pipeworks_mud_mapper.models import Coords, MapRoom

        room = MapRoom(
            id="spawn",
            name="Spawn Room",
            coords=Coords(x=0, y=0, z=0),
        )

        assert room.llm_generation is None

    def test_to_room_strips_llm_generation(self, valid_generation_info):
        """MapRoom.to_room() should strip llm_generation metadata.

        When converting to Room (game truth), authoring metadata like
        llm_generation should be removed since the game server doesn't
        need it.
        """
        from pipeworks_mud_mapper.models import Coords, MapRoom

        gen_info = OllamaGenerationInfo(**valid_generation_info)

        map_room = MapRoom(
            id="spawn",
            name="Spawn Room",
            description="A generated description.",
            coords=Coords(x=0, y=0, z=0),
            llm_generation=gen_info,
        )

        # Convert to Room (game truth)
        room = map_room.to_room()

        # Room model shouldn't have llm_generation field at all
        assert not hasattr(room, "llm_generation")
        # Verify description is preserved
        assert room.description == "A generated description."

    def test_from_dict_with_llm_generation(self, valid_generation_info):
        """MapRoom.from_dict should parse llm_generation from dict."""
        from pipeworks_mud_mapper.models import MapRoom

        # Add generated_at as ISO string (as it would appear in JSON)
        valid_generation_info["generated_at"] = "2024-01-15T10:30:00+00:00"

        room_data = {
            "id": "spawn",
            "name": "Spawn Room",
            "description": "A generated description.",
            "coords": [0, 0, 0],
            "exits": {},
            "items": [],
            "llm_generation": valid_generation_info,
        }

        room = MapRoom.from_dict(room_data)

        assert room.llm_generation is not None
        assert room.llm_generation.model == "gemma2:2b"
        assert room.llm_generation.actual_seed == 12345

    def test_from_dict_without_llm_generation_legacy(self):
        """MapRoom.from_dict should handle legacy files without llm_generation.

        Older map files won't have llm_generation field. The model should
        handle this gracefully by defaulting to None.
        """
        from pipeworks_mud_mapper.models import MapRoom

        # Legacy room data without llm_generation
        room_data = {
            "id": "spawn",
            "name": "Spawn Room",
            "description": "Manual description.",
            "coords": [0, 0, 0],
            "exits": {},
            "items": [],
            # No llm_generation field
        }

        room = MapRoom.from_dict(room_data)

        assert room.llm_generation is None
        assert room.description == "Manual description."
