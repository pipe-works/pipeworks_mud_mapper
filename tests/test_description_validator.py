"""Tests for the description validator service."""

import json

import pytest

from pipeworks_mud_mapper.services.description_validator import (
    ValidationResult,
    load_validator_config,
    validate_description,
)


@pytest.fixture
def temp_config(tmp_path, monkeypatch):
    config = {
        "word_count": {"enabled": True, "min_ratio": 0.5, "max_ratio": 1.5},
        "banned_phrases": ["opens onto"],
        "cardinal_directions": ["north", "east"],
        "traversal_verbs": ["leads", "spill"],
    }
    config_path = tmp_path / "description_validator.json"
    config_path.write_text(json.dumps(config))

    from pipeworks_mud_mapper.services import description_validator

    monkeypatch.setattr(description_validator, "_get_config_path", lambda: config_path)
    return config


def test_load_validator_config_missing(tmp_path, monkeypatch):
    from pipeworks_mud_mapper.services import description_validator

    missing_path = tmp_path / "missing.json"
    monkeypatch.setattr(description_validator, "_get_config_path", lambda: missing_path)

    config = load_validator_config()
    assert config == {}


def test_load_validator_config_invalid_json(tmp_path, monkeypatch):
    from pipeworks_mud_mapper.services import description_validator

    bad_path = tmp_path / "bad.json"
    bad_path.write_text("{not valid json")
    monkeypatch.setattr(description_validator, "_get_config_path", lambda: bad_path)

    config = load_validator_config()
    assert config == {}


def test_validate_description_passes_within_bounds(temp_config):
    text = "Dust hangs in the still air, softening the stonework. A faint drip echoes."
    result = validate_description(text, target_words=20)

    assert isinstance(result, ValidationResult)
    assert result.valid is True
    assert result.hard_failures == []
    assert result.metrics["word_count"] >= result.metrics["min_words"]
    assert result.metrics["word_count"] <= result.metrics["max_words"]


def test_validate_description_word_count_failure(temp_config):
    text = "Too short."
    result = validate_description(text, target_words=20)

    assert result.valid is False
    assert "word_count_out_of_bounds" in result.hard_failures
    assert result.metrics["word_count"] < result.metrics["min_words"]


def test_validate_description_banned_phrase_hit(temp_config):
    text = "A narrow doorway opens onto a quiet hall."
    result = validate_description(text, target_words=10)

    assert result.valid is False
    assert any("banned_phrase:opens onto" in failure for failure in result.hard_failures)
    assert "opens onto" in result.rule_hits.get("banned_phrases", [])


def test_validate_description_cardinal_direction_hit(temp_config):
    text = "The air is colder to the north, carrying a damp chill."
    result = validate_description(text, target_words=20)

    assert result.valid is False
    assert any("cardinal_direction:north" in failure for failure in result.hard_failures)
    assert "north" in result.rule_hits.get("cardinal_directions", [])


def test_validate_description_traversal_verb_hit(temp_config):
    text = "A low arch leads into a darker passage."
    result = validate_description(text, target_words=20)

    assert result.valid is False
    assert any("traversal_verb:leads" in failure for failure in result.hard_failures)
    assert "leads" in result.rule_hits.get("traversal_verbs", [])


def test_validate_description_word_boundary_avoids_false_positive(temp_config):
    text = "A northward draft brushes your cheek."
    result = validate_description(text, target_words=10)

    # Should not hit cardinal direction for "north" inside "northward".
    assert "cardinal_directions" not in result.rule_hits
