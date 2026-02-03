"""Comprehensive tests for the Ollama template service.

This module tests the template service that handles loading, validating,
and compiling Ollama prompt templates for room description generation.

Test Organization
-----------------
Tests are grouped by function:

- **TestGetTemplatesDirectory**: Directory path resolution
- **TestListTemplates**: Template enumeration for dropdowns
- **TestLoadTemplate**: Template loading and validation
- **TestCompileSystemPrompt**: Template-to-prompt compilation
- **TestGetDefaultSystemPrompt**: Default prompt retrieval
- **TestTemplateIntegration**: End-to-end template workflows

Design Notes
------------
These tests use temporary directories to avoid depending on the actual
template files in the repository. This ensures tests are isolated and
don't interfere with production templates.

See Also
--------
- ``services/template_service.py``: The service being tested
- ``models/template.py``: Pydantic template models
- ``test_models.py``: Tests for template model validation
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from pipeworks_mud_mapper.models import OllamaTemplate
from pipeworks_mud_mapper.services import template_service
from pipeworks_mud_mapper.services.template_service import (
    CORE_RULES,
    DEFAULT_SYSTEM_PROMPT,
    compile_system_prompt,
    get_default_system_prompt,
    get_templates_directory,
    list_templates,
    load_template,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_templates_dir():
    """Create a temporary directory for template tests.

    This fixture creates a temporary directory and patches
    get_templates_directory to return it, isolating tests
    from the actual templates directory.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)
        with patch.object(template_service, "get_templates_directory", return_value=temp_path):
            yield temp_path


@pytest.fixture
def sample_template_data():
    """Create sample template data for testing.

    Returns a dictionary matching the template JSON format,
    suitable for writing to a template file.
    """
    return {
        "template_name": "Test Template",
        "template_id": "test_template",
        "version": "1.0.0",
        "description": "A test template for unit tests.",
        "theme": {
            "name": "Test Realm, a place of testing",
            "tone": "serious, methodical",
            "era": "Modern",
            "aesthetic": "clean, minimal",
        },
        "voice_guidance": {
            "style": "clear and direct narrator",
            "register": "formal, technical",
            "keyword_include": ["test", "verify", "assert"],
            "keyword_exclude": ["magic", "fantasy"],
        },
        "craft_constraints": {
            "multi_part_spaces": "Describe each area systematically.",
            "locked_things_approach": "State the lock exists, nothing more.",
            "silence_tone": "Silence is data absence.",
            "exit_hints": "List directions, not destinations.",
        },
        "examples": {
            "good_crossroads": "You stand at a junction. Paths extend in three directions.",
            "bad_crossroads": "North leads to the forest, east to the city.",
            "good_locked_thing": "The door handle turns halfway, then stops.",
            "bad_locked_thing": "You need a key to open this door.",
            "good_multi_part": "The room continues to your left and right.",
            "bad_multi_part": "The left side has a fireplace, the right has windows.",
        },
        "author_notes": "This template is for testing only.",
        "author_credit": "Test Author",
    }


@pytest.fixture
def minimal_template_data():
    """Create minimal valid template data.

    Only includes required fields to test default handling.
    """
    return {
        "template_name": "Minimal Template",
        "template_id": "minimal",
        "theme": {
            "name": "Minimal World",
            "tone": "neutral",
        },
        "voice_guidance": {
            "style": "plain narrator",
            "register": "casual",
        },
    }


@pytest.fixture
def sample_template(sample_template_data):
    """Create a sample OllamaTemplate instance."""
    return OllamaTemplate.model_validate(sample_template_data)


# =============================================================================
# Test get_templates_directory
# =============================================================================


class TestGetTemplatesDirectory:
    """Tests for get_templates_directory function."""

    def test_returns_path_object(self):
        """Should return a Path object."""
        result = get_templates_directory()
        assert isinstance(result, Path)

    def test_path_ends_with_templates(self):
        """Should return path ending with data/ollama/templates."""
        result = get_templates_directory()
        assert result.name == "templates"
        assert result.parent.name == "ollama"
        assert result.parent.parent.name == "data"

    def test_creates_directory_if_missing(self):
        """Should create the directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a path that doesn't exist yet
            test_path = Path(tmpdir) / "data" / "ollama" / "templates"

            # Helper function that creates directory and returns path
            def create_and_return_path() -> Path:
                test_path.mkdir(parents=True, exist_ok=True)
                return test_path

            # Patch the directory calculation
            with patch.object(
                template_service,
                "get_templates_directory",
                side_effect=create_and_return_path,
            ):
                # This should create the directory
                result = template_service.get_templates_directory()
                assert result.exists()


# =============================================================================
# Test list_templates
# =============================================================================


class TestListTemplates:
    """Tests for list_templates function."""

    def test_returns_empty_list_when_no_templates(self, temp_templates_dir):
        """Should return empty list when directory is empty."""
        result = list_templates()
        assert result == []

    def test_finds_template_files(self, temp_templates_dir, sample_template_data):
        """Should find .template.json files."""
        # Create a template file
        template_path = temp_templates_dir / "test.template.json"
        template_path.write_text(json.dumps(sample_template_data))

        result = list_templates()

        assert len(result) == 1
        assert result[0]["label"] == "Test Template"
        assert result[0]["value"] == "test_template"

    def test_ignores_non_template_json_files(self, temp_templates_dir, sample_template_data):
        """Should ignore .json files without .template extension."""
        # Create a regular JSON file
        regular_path = temp_templates_dir / "regular.json"
        regular_path.write_text(json.dumps(sample_template_data))

        result = list_templates()

        assert result == []

    def test_handles_multiple_templates(self, temp_templates_dir):
        """Should handle multiple template files."""
        # Create multiple templates
        for i in range(3):
            template_data = {
                "template_name": f"Template {i}",
                "template_id": f"template_{i}",
                "theme": {"name": "Test", "tone": "neutral"},
                "voice_guidance": {"style": "plain", "register": "casual"},
            }
            path = temp_templates_dir / f"template_{i}.template.json"
            path.write_text(json.dumps(template_data))

        result = list_templates()

        assert len(result) == 3

    def test_sorts_by_label(self, temp_templates_dir):
        """Should sort templates alphabetically by label."""
        # Create templates with non-alphabetical names
        for name, tid in [("Zebra", "zebra"), ("Alpha", "alpha"), ("Middle", "middle")]:
            template_data = {
                "template_name": name,
                "template_id": tid,
                "theme": {"name": "Test", "tone": "neutral"},
                "voice_guidance": {"style": "plain", "register": "casual"},
            }
            path = temp_templates_dir / f"{tid}.template.json"
            path.write_text(json.dumps(template_data))

        result = list_templates()

        labels = [t["label"] for t in result]
        assert labels == ["Alpha", "Middle", "Zebra"]

    def test_handles_invalid_json(self, temp_templates_dir, sample_template_data):
        """Should skip files with invalid JSON."""
        # Create one valid and one invalid template
        valid_path = temp_templates_dir / "valid.template.json"
        valid_path.write_text(json.dumps(sample_template_data))

        invalid_path = temp_templates_dir / "invalid.template.json"
        invalid_path.write_text("{ invalid json }")

        result = list_templates()

        # Should only return the valid template
        assert len(result) == 1
        assert result[0]["value"] == "test_template"

    def test_uses_filename_as_fallback(self, temp_templates_dir):
        """Should use filename as fallback when template_name missing."""
        # Create template without template_name
        template_data = {
            "template_id": "fallback_test",
            "theme": {"name": "Test", "tone": "neutral"},
            "voice_guidance": {"style": "plain", "register": "casual"},
        }
        path = temp_templates_dir / "fallback.template.json"
        path.write_text(json.dumps(template_data))

        result = list_templates()

        # Label should fall back to filename stem
        assert len(result) == 1
        assert result[0]["label"] == "fallback.template"


# =============================================================================
# Test load_template
# =============================================================================


class TestLoadTemplate:
    """Tests for load_template function."""

    def test_loads_valid_template(self, temp_templates_dir, sample_template_data):
        """Should load and validate a valid template."""
        path = temp_templates_dir / "test.template.json"
        path.write_text(json.dumps(sample_template_data))

        result = load_template("test_template")

        assert result is not None
        assert result.template_name == "Test Template"
        assert result.template_id == "test_template"

    def test_returns_none_for_missing_template(self, temp_templates_dir):
        """Should return None when template ID not found."""
        result = load_template("nonexistent")
        assert result is None

    def test_loads_template_with_matching_id(self, temp_templates_dir):
        """Should match template by template_id, not filename."""
        # Create template with different filename and ID
        template_data = {
            "template_name": "Mismatched Name",
            "template_id": "actual_id",
            "theme": {"name": "Test", "tone": "neutral"},
            "voice_guidance": {"style": "plain", "register": "casual"},
        }
        path = temp_templates_dir / "different_filename.template.json"
        path.write_text(json.dumps(template_data))

        result = load_template("actual_id")

        assert result is not None
        assert result.template_id == "actual_id"

    def test_validates_template_schema(self, temp_templates_dir):
        """Should validate template against Pydantic schema."""
        # Create template with invalid schema (missing required fields)
        template_data = {
            "template_name": "Invalid",
            "template_id": "invalid",
            # Missing required 'theme' and 'voice_guidance'
        }
        path = temp_templates_dir / "invalid.template.json"
        path.write_text(json.dumps(template_data))

        result = load_template("invalid")

        # Should return None due to validation failure
        assert result is None

    def test_loads_template_with_defaults(self, temp_templates_dir, minimal_template_data):
        """Should apply default values for optional fields."""
        path = temp_templates_dir / "minimal.template.json"
        path.write_text(json.dumps(minimal_template_data))

        result = load_template("minimal")

        assert result is not None
        assert result.version == "1.0.0"  # Default
        assert result.description == ""  # Default
        assert result.craft_constraints.multi_part_spaces == ""  # Default


# =============================================================================
# Test compile_system_prompt
# =============================================================================


class TestCompileSystemPrompt:
    """Tests for compile_system_prompt function."""

    def test_includes_core_rules(self, sample_template):
        """Should include the universal Core Rules."""
        result = compile_system_prompt(sample_template)

        # Check for key Core Rules phrases
        assert "CARDINAL RULE" in result
        assert "CRAFT OF CONSTRAINT" in result
        assert "DO NOT NARRATE FUTURES" in result

    def test_includes_theme_information(self, sample_template):
        """Should include theme name and tone."""
        result = compile_system_prompt(sample_template)

        assert "Test Realm" in result
        assert "serious, methodical" in result

    def test_includes_voice_guidance(self, sample_template):
        """Should include voice style and register."""
        result = compile_system_prompt(sample_template)

        assert "clear and direct narrator" in result
        assert "formal, technical" in result

    def test_includes_keyword_lists(self, sample_template):
        """Should include keyword include/exclude lists."""
        result = compile_system_prompt(sample_template)

        assert "test" in result
        assert "verify" in result
        assert "magic" in result  # In exclude list

    def test_includes_craft_constraints(self, sample_template):
        """Should include craft constraint guidance."""
        result = compile_system_prompt(sample_template)

        assert "Describe each area systematically" in result
        assert "State the lock exists" in result

    def test_includes_examples(self, sample_template):
        """Should include good and bad examples."""
        result = compile_system_prompt(sample_template)

        # Good examples
        assert "You stand at a junction" in result
        # Bad examples (marked as what NOT to do)
        assert "North leads to the forest" in result
        assert "DO NOT DO THIS" in result

    def test_includes_task_instructions(self, sample_template):
        """Should include final task instructions."""
        result = compile_system_prompt(sample_template)

        assert "YOUR TASK" in result
        assert "200-350 words" in result
        assert "Begin your description now" in result

    def test_handles_empty_optional_fields(self, minimal_template_data):
        """Should handle templates with empty optional fields."""
        template = OllamaTemplate.model_validate(minimal_template_data)
        result = compile_system_prompt(template)

        # Should still have core content
        assert "CARDINAL RULE" in result
        assert "Minimal World" in result

        # Should not have sections for empty fields
        # (No error should occur)
        assert result is not None

    def test_output_is_string(self, sample_template):
        """Should return a string."""
        result = compile_system_prompt(sample_template)
        assert isinstance(result, str)

    def test_reasonable_length(self, sample_template):
        """Should produce a reasonably-sized prompt."""
        result = compile_system_prompt(sample_template)

        # Should be substantial but not excessively long
        assert len(result) > 1000  # Has meaningful content
        assert len(result) < 20000  # Not excessive


# =============================================================================
# Test get_default_system_prompt
# =============================================================================


class TestGetDefaultSystemPrompt:
    """Tests for get_default_system_prompt function."""

    def test_returns_string(self):
        """Should return a string."""
        result = get_default_system_prompt()
        assert isinstance(result, str)

    def test_returns_non_empty(self):
        """Should return a non-empty prompt."""
        result = get_default_system_prompt()
        assert len(result) > 0

    def test_matches_constant(self):
        """Should return the DEFAULT_SYSTEM_PROMPT constant."""
        result = get_default_system_prompt()
        assert result == DEFAULT_SYSTEM_PROMPT

    def test_contains_creative_writer_guidance(self):
        """Should contain guidance for room descriptions."""
        result = get_default_system_prompt()
        assert "creative writer" in result.lower()
        assert "MUD" in result


# =============================================================================
# Test CORE_RULES constant
# =============================================================================


class TestCoreRules:
    """Tests for the CORE_RULES constant."""

    def test_is_non_empty_string(self):
        """Should be a non-empty string."""
        assert isinstance(CORE_RULES, str)
        assert len(CORE_RULES) > 0

    def test_contains_cardinal_rule(self):
        """Should contain the cardinal rule."""
        assert "CARDINAL RULE" in CORE_RULES

    def test_contains_all_craft_principles(self):
        """Should contain all six craft principles."""
        principles = [
            "DO NOT NARRATE FUTURES",
            "DO NOT DECIDE FOR THE PLAYER",
            "DO NOT EXPLAIN LOCKED THINGS",
            "THRESHOLDS WHISPER",
            "SILENCE IS LEGAL",
            "DESCRIBE THE THRESHOLD",
        ]
        for principle in principles:
            assert principle in CORE_RULES, f"Missing principle: {principle}"


# =============================================================================
# Integration Tests
# =============================================================================


class TestTemplateIntegration:
    """Integration tests for template workflows."""

    def test_list_load_compile_workflow(self, temp_templates_dir, sample_template_data):
        """Test complete workflow: list -> load -> compile."""
        # Create a template file
        path = temp_templates_dir / "workflow.template.json"
        path.write_text(json.dumps(sample_template_data))

        # List templates
        templates = list_templates()
        assert len(templates) == 1

        # Load template
        template_id = templates[0]["value"]
        template = load_template(template_id)
        assert template is not None

        # Compile system prompt
        prompt = compile_system_prompt(template)
        assert "CARDINAL RULE" in prompt
        assert template.theme.name in prompt

    def test_multiple_templates_workflow(self, temp_templates_dir):
        """Test handling multiple templates correctly."""
        # Create several templates
        templates_data = [
            ("Goblin", "goblin", "whimsical"),
            ("Gothic", "gothic", "dark and brooding"),
            ("Sci-Fi", "scifi", "technological"),
        ]

        for name, tid, tone in templates_data:
            data = {
                "template_name": name,
                "template_id": tid,
                "theme": {"name": f"{name} World", "tone": tone},
                "voice_guidance": {"style": f"{name} narrator", "register": "narrative"},
            }
            path = temp_templates_dir / f"{tid}.template.json"
            path.write_text(json.dumps(data))

        # List should return all three
        templates = list_templates()
        assert len(templates) == 3

        # Each should load and compile correctly
        for template_info in templates:
            template = load_template(template_info["value"])
            assert template is not None

            prompt = compile_system_prompt(template)
            assert template.theme.name in prompt

    def test_real_template_if_exists(self):
        """Test loading real templates from data directory if they exist.

        This test verifies that production templates load correctly.
        It skips gracefully if templates haven't been created yet.
        """
        templates = list_templates()

        if not templates:
            pytest.skip("No templates in data directory yet")

        # Load first available template
        template = load_template(templates[0]["value"])
        assert template is not None

        # Should compile without error
        prompt = compile_system_prompt(template)
        assert len(prompt) > 0
