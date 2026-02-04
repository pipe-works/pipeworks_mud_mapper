"""Tests for Ollama state helpers.

These tests validate metadata building and room update logic that sits
outside the callbacks, keeping domain behavior predictable.
"""

from __future__ import annotations

import pytest

from pipeworks_mud_mapper.services.ollama_state import (
    apply_generation_to_room,
    build_generation_metadata,
)


class TestBuildGenerationMetadata:
    """Tests for generation metadata assembly."""

    def test_builds_expected_fields(self):
        """Should populate all fields with expected defaults and conversions."""
        metadata = build_generation_metadata(
            model="llama3.2:latest",
            actual_seed=123,
            template_id="ledgerfall_goblin",
            temperature=0.7,
            top_k=40,
            top_p=0.9,
            num_ctx=4096,
            num_predict=512,
            target_words=200,
            system_prompt="System",
            user_prompt="User",
        )

        assert metadata["model"] == "llama3.2:latest"
        assert metadata["actual_seed"] == 123
        assert metadata["template_id"] == "ledgerfall_goblin"
        assert metadata["temperature"] == 0.7
        assert metadata["top_k"] == 40
        assert metadata["top_p"] == 0.9
        assert metadata["num_ctx"] == 4096
        assert metadata["num_predict"] == 512
        assert metadata["target_words"] == 200
        assert metadata["system_prompt"] == "System"
        assert metadata["user_prompt"] == "User"
        assert "generated_at" in metadata

    def test_respects_explicit_template_id(self):
        """Should use provided template ID when supplied."""
        metadata = build_generation_metadata(
            model="llama3.2:latest",
            actual_seed=5,
            template_id="ledgerfall",
            temperature=0.5,
            top_k=20,
            top_p=0.8,
            num_ctx=2048,
            num_predict=256,
            target_words=120,
            system_prompt=None,
            user_prompt="Describe a room",
        )

        assert metadata["template_id"] == "ledgerfall"
        assert metadata["system_prompt"] == ""


class TestApplyGenerationToRoom:
    """Tests for applying generated text to room data."""

    @pytest.fixture
    def base_zone(self):
        """Provide a simple zone fixture for updates."""
        return {
            "id": "test",
            "name": "Test Zone",
            "rooms": {
                "room": {
                    "id": "room",
                    "name": "Room",
                    "description": "Original",
                    "coords": [0, 0, 0],
                    "exits": {},
                    "items": [],
                }
            },
            "items": {},
        }

    def test_updates_description_and_metadata(self, base_zone):
        """Should apply description and attach metadata fields."""
        generation_info = {"model": "llama3.2:latest"}
        validation_info = {"valid": True}

        updated = apply_generation_to_room(
            zone_data=base_zone,
            room_id="room",
            description="New description",
            generation_info=generation_info,
            validation_info=validation_info,
        )

        room = updated["rooms"]["room"]
        assert room["description"] == "New description"
        assert room["llm_generation"] == generation_info
        assert room["description_validation"] == validation_info

    def test_clears_metadata_when_none(self, base_zone):
        """Should remove metadata keys when no metadata is provided."""
        base_zone["rooms"]["room"]["llm_generation"] = {"model": "old"}
        base_zone["rooms"]["room"]["description_validation"] = {"valid": False}

        updated = apply_generation_to_room(
            zone_data=base_zone,
            room_id="room",
            description="Updated",
            generation_info=None,
            validation_info=None,
        )

        room = updated["rooms"]["room"]
        assert room["description"] == "Updated"
        assert "llm_generation" not in room
        assert "description_validation" not in room

    def test_raises_key_error_for_missing_room(self, base_zone):
        """Should raise if room is missing from zone data."""
        with pytest.raises(KeyError):
            apply_generation_to_room(
                zone_data=base_zone,
                room_id="missing",
                description="New description",
                generation_info=None,
                validation_info=None,
            )
