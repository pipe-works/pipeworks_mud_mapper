"""Tests for Ollama helper modules.

These tests cover:
- Config defaults (shared constants)
- UI status helpers (consistent markup)
- Asset loading and cache behavior for prompt prefixes
"""

from __future__ import annotations

import json

from pipeworks_mud_mapper.services import ollama_assets, ollama_config, ollama_ui


class TestOllamaConfig:
    """Tests for shared Ollama configuration defaults."""

    def test_defaults_are_defined(self):
        """Defaults should be present and sane for UI/callback usage."""
        # Each constant is expected to exist and be in a reasonable range.
        assert isinstance(ollama_config.DEFAULT_SEED, int)
        assert ollama_config.DEFAULT_SEED == -1
        assert 0.0 <= ollama_config.DEFAULT_TEMPERATURE <= 2.0
        assert 1 <= ollama_config.DEFAULT_TOP_K <= 100
        assert 0.0 <= ollama_config.DEFAULT_TOP_P <= 1.0
        assert 512 <= ollama_config.DEFAULT_NUM_CTX <= 8192
        assert 30 <= ollama_config.DEFAULT_NUM_PREDICT <= 2048
        assert 25 <= ollama_config.DEFAULT_TARGET_WORDS <= 500

    def test_timeouts_are_positive(self):
        """Timeouts should be positive to avoid immediate failures."""
        assert ollama_config.OLLAMA_TIMEOUT_SECONDS > 0
        assert ollama_config.OLLAMA_MODEL_REFRESH_TIMEOUT_SECONDS > 0


class TestOllamaUiHelpers:
    """Tests for status message helpers used by callbacks."""

    def test_status_ok_contains_success_class(self):
        """Success helper should include a green success class."""
        status = ollama_ui.status_ok("All good")
        assert "text-success" in str(status)
        assert "All good" in str(status)

    def test_status_warning_contains_warning_class(self):
        """Warning helper should include a yellow warning class."""
        status = ollama_ui.status_warning("Check this")
        assert "text-warning" in str(status)
        assert "Check this" in str(status)

    def test_status_error_contains_error_class(self):
        """Error helper should include a red error class."""
        status = ollama_ui.status_error("Bad")
        assert "text-danger" in str(status)
        assert "Bad" in str(status)

    def test_status_info_muted(self):
        """Muted info helper should render with muted styling."""
        status = ollama_ui.status_info("FYI", muted=True)
        assert "text-muted" in str(status)
        assert "FYI" in str(status)

    def test_status_pending_spins(self):
        """Pending helper should include spinner class for animation."""
        status = ollama_ui.status_pending("Working")
        assert "spinning" in str(status)
        assert "Working" in str(status)


class TestOllamaAssets:
    """Tests for prompt prefix asset loading and caching."""

    def test_load_prompt_prefixes_missing_file(self, tmp_path, monkeypatch):
        """Missing file should return an empty list."""
        missing = tmp_path / "missing.json"

        # Force the asset loader to point at a non-existent file path.
        monkeypatch.setattr(ollama_assets, "_prompt_prefixes_path", lambda: missing)

        # Clear the cache to ensure the new path is used.
        result = ollama_assets.load_prompt_prefixes(reload=True)
        assert result == []

    def test_load_prompt_prefixes_invalid_json(self, tmp_path, monkeypatch):
        """Invalid JSON should return an empty list."""
        config_path = tmp_path / "prompt_prefixes.json"
        config_path.write_text("{bad json}")

        monkeypatch.setattr(ollama_assets, "_prompt_prefixes_path", lambda: config_path)

        result = ollama_assets.load_prompt_prefixes(reload=True)
        assert result == []

    def test_load_prompt_prefixes_success_and_cache(self, tmp_path, monkeypatch):
        """Valid JSON should load and cache prompt prefixes."""
        config_path = tmp_path / "prompt_prefixes.json"
        prefix_entry = {"label": "Exact 30", "value": "exact_30", "prefix": "Write 30 words."}
        payload = [
            prefix_entry,
            "bad",  # Non-dict entries should be ignored.
        ]
        config_path.write_text(json.dumps(payload))

        monkeypatch.setattr(ollama_assets, "_prompt_prefixes_path", lambda: config_path)

        # First load should read from disk.
        first = ollama_assets.load_prompt_prefixes(reload=True)
        assert first == [payload[0]]

        # Modify the file and ensure cached result does not change without reload.
        prefix_entry["label"] = "Changed"
        config_path.write_text(json.dumps(payload))

        cached = ollama_assets.load_prompt_prefixes(reload=False)
        assert cached[0]["label"] == "Exact 30"

        # Reload should pick up the change.
        refreshed = ollama_assets.load_prompt_prefixes(reload=True)
        assert refreshed[0]["label"] == "Changed"

    def test_load_prompt_prefixes_non_list_returns_empty(self, tmp_path, monkeypatch):
        """Non-list JSON should return empty list for safety."""
        config_path = tmp_path / "prompt_prefixes.json"
        config_path.write_text(json.dumps({"bad": "shape"}))

        monkeypatch.setattr(ollama_assets, "_prompt_prefixes_path", lambda: config_path)

        result = ollama_assets.load_prompt_prefixes(reload=True)
        assert result == []
