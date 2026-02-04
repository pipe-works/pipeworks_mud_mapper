"""Comprehensive tests for Ollama LLM integration callbacks.

This module tests the Ollama callbacks that handle communication with
a local Ollama server for generating room descriptions, including
the template-based system prompt system and model parameters.

Test Organization
-----------------
Tests are grouped by callback function:

- **TestRefreshOllamaModels**: Model list fetching from server
- **TestGenerateDescription**: LLM text generation via /api/chat
- **TestGenerateDescriptionWithParameters**: LLM generation with model parameters
- **TestSendToDescription**: Sending response to room description
- **TestHandleClipboardCopy**: Clipboard feedback handling
- **TestPopulatePromptFromDescription**: Populating prompt from room description
- **TestLoadTemplateOptions**: Template dropdown population
- **TestHandleTemplateSelection**: Template selection and compilation
- **TestToggleSystemPromptCollapse**: System prompt collapse toggle
- **TestToggleParamsCollapse**: Parameters section collapse toggle
- **TestHandleSeedControls**: Seed control interactions
- **TestCopySystemPrompt**: System prompt clipboard feedback
- **TestSeedIsolation**: Verifies seed doesn't affect global random state

Design Notes
------------
These tests mock the httpx client to avoid requiring an actual
Ollama server. We test:

- Successful API responses (using /api/chat endpoint)
- Network errors (connection refused, timeout)
- HTTP errors (4xx, 5xx)
- Edge cases (empty responses, missing data)
- Template loading, compilation, and UI state management
- Model parameters (seed, temperature, top_k, top_p, num_ctx, num_predict)
- Seed isolation (critical for determinism in other parts of the app)

API Migration
-------------
The generate_description callback uses Ollama's ``/api/chat`` endpoint
instead of ``/api/generate`` for proper system/user message separation.
Tests verify the messages array format with distinct roles.

Parameter Testing
-----------------
The generate_description callback accepts model parameters that control
LLM behavior. Tests verify:

- Parameters are passed correctly in the options dict
- Default values are used when parameters are None
- Seed handling: -1 triggers random seed using isolated RNG
- Random seed generation doesn't poison global random state

See Also
--------
- ``callbacks/ollama_callbacks.py``: The callbacks being tested
- ``test_layout.py``: Tests for the Ollama UI components
- ``test_template_service.py``: Tests for template loading/compilation
"""

import random
from unittest.mock import MagicMock, patch

import httpx
import pytest
from dash import no_update

from pipeworks_mud_mapper.callbacks.ollama_callbacks import (
    apply_prompt_prefix,
    copy_system_prompt,
    generate_description,
    handle_clipboard_copy,
    handle_seed_controls,
    handle_template_selection,
    load_prompt_prefix_options,
    load_template_options,
    populate_prompt_from_description,
    refresh_ollama_models,
    send_to_description,
    toggle_params_collapse,
    toggle_system_prompt_collapse,
    update_target_words_hint,
    validate_ollama_response,
)
from pipeworks_mud_mapper.layout.ollama_panel import (
    DEFAULT_NUM_CTX,
    DEFAULT_NUM_PREDICT,
    DEFAULT_SEED,
    DEFAULT_TARGET_WORDS,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_K,
    DEFAULT_TOP_P,
)
from pipeworks_mud_mapper.services.description_validator import ValidationResult

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_models_response():
    """Create a mock response for /api/tags endpoint."""
    return {
        "models": [
            {"name": "llama3.2:latest", "size": 2000000000},
            {"name": "mistral:7b", "size": 4000000000},
            {"name": "codellama:13b", "size": 7000000000},
        ]
    }


@pytest.fixture
def mock_chat_response():
    """Create a mock response for /api/chat endpoint.

    The /api/chat endpoint returns a different format than /api/generate,
    with the response text nested under message.content.
    """
    return {
        "model": "llama3.2:latest",
        "message": {
            "role": "assistant",
            "content": "The ancient stone hall stretches before you, its vaulted "
            "ceiling lost in shadow. Flickering torchlight casts dancing "
            "patterns across weathered flagstones.",
        },
        "done": True,
    }


# =============================================================================
# Test refresh_ollama_models
# =============================================================================


class TestRefreshOllamaModels:
    """Tests for the refresh_ollama_models callback."""

    def test_no_clicks_returns_no_update(self):
        """Should return no_update when button not clicked."""
        result = refresh_ollama_models(n_clicks=0, server_url="http://localhost:11434")
        assert result == (no_update, no_update, no_update)

    def test_none_clicks_returns_no_update(self):
        """Should return no_update when n_clicks is None."""
        result = refresh_ollama_models(n_clicks=None, server_url="http://localhost:11434")
        assert result == (no_update, no_update, no_update)

    def test_empty_server_url(self):
        """Should return warning when server URL is empty."""
        options, status, placeholder = refresh_ollama_models(n_clicks=1, server_url="")
        assert options == []
        assert "Please enter a server URL" in str(status)
        assert "Enter server URL" in placeholder

    def test_none_server_url(self):
        """Should return warning when server URL is None."""
        options, status, placeholder = refresh_ollama_models(n_clicks=1, server_url=None)
        assert options == []
        assert "Please enter a server URL" in str(status)

    def test_successful_model_fetch(self, mock_models_response):
        """Should return model options on successful API call."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_models_response
        mock_response.raise_for_status = MagicMock()

        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            options, status, placeholder = refresh_ollama_models(
                n_clicks=1, server_url="http://localhost:11434"
            )

        assert len(options) == 3
        assert options[0]["value"] == "llama3.2:latest"
        assert options[1]["value"] == "mistral:7b"
        assert options[2]["value"] == "codellama:13b"
        assert "Connected" in str(status)
        assert "3 model" in str(status)
        assert placeholder == "Select a model"

    def test_successful_fetch_normalizes_url(self, mock_models_response):
        """Should strip trailing slash from server URL."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_models_response
        mock_response.raise_for_status = MagicMock()

        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.httpx.Client") as mock_client:
            mock_instance = mock_client.return_value.__enter__.return_value
            mock_instance.get.return_value = mock_response

            refresh_ollama_models(n_clicks=1, server_url="http://localhost:11434/")

            # Verify URL was normalized (no double slash)
            mock_instance.get.assert_called_once_with("http://localhost:11434/api/tags")

    def test_empty_models_list(self):
        """Should show connected but no models when list is empty."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"models": []}
        mock_response.raise_for_status = MagicMock()

        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            options, status, placeholder = refresh_ollama_models(
                n_clicks=1, server_url="http://localhost:11434"
            )

        assert options == []
        assert "Connected" in str(status)
        assert "no models" in str(status)
        assert "No models" in placeholder

    def test_connection_error(self):
        """Should handle connection refused error."""
        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = httpx.ConnectError(
                "Connection refused"
            )

            options, status, placeholder = refresh_ollama_models(
                n_clicks=1, server_url="http://localhost:11434"
            )

        assert options == []
        assert "Not connected" in str(status)
        assert "Connection failed" in placeholder

    def test_http_status_error(self):
        """Should handle HTTP error responses."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = httpx.HTTPStatusError(
                "Server error", request=MagicMock(), response=mock_response
            )

            options, status, placeholder = refresh_ollama_models(
                n_clicks=1, server_url="http://localhost:11434"
            )

        assert options == []
        assert "Not connected" in str(status)
        assert "HTTP 500" in str(status)

    def test_generic_exception(self):
        """Should handle unexpected exceptions gracefully."""
        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = Exception(
                "Unexpected error occurred"
            )

            options, status, placeholder = refresh_ollama_models(
                n_clicks=1, server_url="http://localhost:11434"
            )

        assert options == []
        assert "Error:" in str(status)

    def test_connection_status_shows_green_on_success(self, mock_models_response):
        """Should show green success indicator when connected."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_models_response
        mock_response.raise_for_status = MagicMock()

        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            options, status, placeholder = refresh_ollama_models(
                n_clicks=1, server_url="http://localhost:11434"
            )

        assert "text-success" in str(status)

    def test_connection_status_shows_red_on_failure(self):
        """Should show red error indicator when connection fails."""
        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = httpx.ConnectError(
                "Connection refused"
            )

            options, status, placeholder = refresh_ollama_models(
                n_clicks=1, server_url="http://localhost:11434"
            )

        assert "text-danger" in str(status)


# =============================================================================
# Test generate_description
# =============================================================================


class TestGenerateDescription:
    """Tests for the generate_description callback.

    Note: These tests use default parameter values. For tests specifically
    targeting parameter handling, see TestGenerateDescriptionWithParameters.
    """

    def test_no_clicks_returns_no_update(self):
        """Should return no_update when button not clicked."""
        result = generate_description(
            n_clicks=0,
            server_url="http://localhost:11434",
            model="llama3.2:latest",
            system_prompt="You are helpful.",
            user_prompt="Describe a room.",
            seed=DEFAULT_SEED,
            temperature=DEFAULT_TEMPERATURE,
            top_k=DEFAULT_TOP_K,
            top_p=DEFAULT_TOP_P,
            num_ctx=DEFAULT_NUM_CTX,
            num_predict=DEFAULT_NUM_PREDICT,
            template_id="__custom__",
            target_words=DEFAULT_TARGET_WORDS,
        )
        # Now returns 3 values: (response, status, generation_info)
        assert result == (no_update, no_update, no_update)

    def test_empty_server_url(self):
        """Should return warning when server URL is empty."""
        response, status, gen_info = generate_description(
            n_clicks=1,
            server_url="",
            model="llama3.2:latest",
            system_prompt="You are helpful.",
            user_prompt="Describe a room.",
            seed=DEFAULT_SEED,
            temperature=DEFAULT_TEMPERATURE,
            top_k=DEFAULT_TOP_K,
            top_p=DEFAULT_TOP_P,
            num_ctx=DEFAULT_NUM_CTX,
            num_predict=DEFAULT_NUM_PREDICT,
            template_id="__custom__",
            target_words=DEFAULT_TARGET_WORDS,
        )
        assert response == ""
        assert "Please enter a server URL" in str(status)
        assert gen_info is None  # No metadata on validation error

    def test_no_model_selected(self):
        """Should return warning when no model selected."""
        response, status, gen_info = generate_description(
            n_clicks=1,
            server_url="http://localhost:11434",
            model=None,
            system_prompt="You are helpful.",
            user_prompt="Describe a room.",
            seed=DEFAULT_SEED,
            temperature=DEFAULT_TEMPERATURE,
            top_k=DEFAULT_TOP_K,
            top_p=DEFAULT_TOP_P,
            num_ctx=DEFAULT_NUM_CTX,
            num_predict=DEFAULT_NUM_PREDICT,
            template_id="__custom__",
            target_words=DEFAULT_TARGET_WORDS,
        )
        assert response == ""
        assert "Please select a model" in str(status)
        assert gen_info is None

    def test_empty_model_selected(self):
        """Should return warning when model is empty string."""
        response, status, gen_info = generate_description(
            n_clicks=1,
            server_url="http://localhost:11434",
            model="",
            system_prompt="You are helpful.",
            user_prompt="Describe a room.",
            seed=DEFAULT_SEED,
            temperature=DEFAULT_TEMPERATURE,
            top_k=DEFAULT_TOP_K,
            top_p=DEFAULT_TOP_P,
            num_ctx=DEFAULT_NUM_CTX,
            num_predict=DEFAULT_NUM_PREDICT,
            template_id="__custom__",
            target_words=DEFAULT_TARGET_WORDS,
        )
        assert response == ""
        assert "Please select a model" in str(status)
        assert gen_info is None

    def test_empty_user_prompt(self):
        """Should return warning when user prompt is empty."""
        response, status, gen_info = generate_description(
            n_clicks=1,
            server_url="http://localhost:11434",
            model="llama3.2:latest",
            system_prompt="You are helpful.",
            user_prompt="",
            seed=DEFAULT_SEED,
            temperature=DEFAULT_TEMPERATURE,
            top_k=DEFAULT_TOP_K,
            top_p=DEFAULT_TOP_P,
            num_ctx=DEFAULT_NUM_CTX,
            num_predict=DEFAULT_NUM_PREDICT,
            template_id="__custom__",
            target_words=DEFAULT_TARGET_WORDS,
        )
        assert response == ""
        assert "Please enter a user prompt" in str(status)
        assert gen_info is None

    def test_successful_generation(self, mock_chat_response):
        """Should return generated text on successful API call."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_chat_response
        mock_response.raise_for_status = MagicMock()

        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            response, status, gen_info = generate_description(
                n_clicks=1,
                server_url="http://localhost:11434",
                model="llama3.2:latest",
                system_prompt="You are a creative writer.",
                user_prompt="Describe a medieval hall.",
                seed=42,  # Fixed seed for reproducibility
                temperature=DEFAULT_TEMPERATURE,
                top_k=DEFAULT_TOP_K,
                top_p=DEFAULT_TOP_P,
                num_ctx=DEFAULT_NUM_CTX,
                num_predict=DEFAULT_NUM_PREDICT,
                template_id="__custom__",
                target_words=DEFAULT_TARGET_WORDS,
            )

        assert "ancient stone hall" in response
        assert "Generated successfully" in str(status)
        # Verify metadata is returned on success
        assert gen_info is not None
        assert gen_info["model"] == "llama3.2:latest"
        assert gen_info["actual_seed"] == 42
        assert gen_info["template_id"] == "__custom__"

    def test_generation_without_system_prompt(self, mock_chat_response):
        """Should work without a system prompt using /api/chat."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_chat_response
        mock_response.raise_for_status = MagicMock()

        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.httpx.Client") as mock_client:
            mock_instance = mock_client.return_value.__enter__.return_value
            mock_instance.post.return_value = mock_response

            response, status, gen_info = generate_description(
                n_clicks=1,
                server_url="http://localhost:11434",
                model="llama3.2:latest",
                system_prompt="",  # No system prompt
                user_prompt="Describe a medieval hall.",
                seed=42,
                temperature=DEFAULT_TEMPERATURE,
                top_k=DEFAULT_TOP_K,
                top_p=DEFAULT_TOP_P,
                num_ctx=DEFAULT_NUM_CTX,
                num_predict=DEFAULT_NUM_PREDICT,
                template_id="__custom__",
                target_words=DEFAULT_TARGET_WORDS,
            )

        assert response != ""
        # Verify messages array has only user message (no system)
        call_args = mock_instance.post.call_args
        sent_json = call_args[1]["json"]
        assert "messages" in sent_json
        assert len(sent_json["messages"]) == 1
        assert sent_json["messages"][0]["role"] == "user"
        assert sent_json["messages"][0]["content"] == "Describe a medieval hall."
        # Verify metadata is returned
        assert gen_info is not None
        assert gen_info["system_prompt"] == ""

    def test_generation_with_system_prompt(self, mock_chat_response):
        """Should send system and user messages separately via /api/chat."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_chat_response
        mock_response.raise_for_status = MagicMock()

        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.httpx.Client") as mock_client:
            mock_instance = mock_client.return_value.__enter__.return_value
            mock_instance.post.return_value = mock_response

            response, status, gen_info = generate_description(
                n_clicks=1,
                server_url="http://localhost:11434",
                model="llama3.2:latest",
                system_prompt="Be creative.",
                user_prompt="Describe a hall.",
                seed=42,
                temperature=DEFAULT_TEMPERATURE,
                top_k=DEFAULT_TOP_K,
                top_p=DEFAULT_TOP_P,
                num_ctx=DEFAULT_NUM_CTX,
                num_predict=DEFAULT_NUM_PREDICT,
                template_id="ledgerfall_goblin",
                target_words=DEFAULT_TARGET_WORDS,
            )

        # Verify messages array has both system and user messages
        call_args = mock_instance.post.call_args
        sent_json = call_args[1]["json"]
        assert "messages" in sent_json
        assert len(sent_json["messages"]) == 2
        assert sent_json["messages"][0]["role"] == "system"
        assert sent_json["messages"][0]["content"] == "Be creative."
        assert sent_json["messages"][1]["role"] == "user"
        assert sent_json["messages"][1]["content"] == "Describe a hall."
        # Verify metadata captures template_id
        assert gen_info["template_id"] == "ledgerfall_goblin"
        assert gen_info["system_prompt"] == "Be creative."

    def test_empty_response_from_model(self):
        """Should handle empty response from model via /api/chat."""
        mock_response = MagicMock()
        # /api/chat returns empty content under message.content
        mock_response.json.return_value = {"message": {"role": "assistant", "content": ""}}
        mock_response.raise_for_status = MagicMock()

        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            response, status, gen_info = generate_description(
                n_clicks=1,
                server_url="http://localhost:11434",
                model="llama3.2:latest",
                system_prompt="",
                user_prompt="Describe a room.",
                seed=42,
                temperature=DEFAULT_TEMPERATURE,
                top_k=DEFAULT_TOP_K,
                top_p=DEFAULT_TOP_P,
                num_ctx=DEFAULT_NUM_CTX,
                num_predict=DEFAULT_NUM_PREDICT,
                template_id="__custom__",
                target_words=DEFAULT_TARGET_WORDS,
            )

        assert response == ""
        assert "Empty response" in str(status)
        assert gen_info is None  # No metadata on empty response

    def test_connection_error(self):
        """Should handle connection refused error."""
        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.side_effect = httpx.ConnectError(
                "Connection refused"
            )

            response, status, gen_info = generate_description(
                n_clicks=1,
                server_url="http://localhost:11434",
                model="llama3.2:latest",
                system_prompt="",
                user_prompt="Describe a room.",
                seed=42,
                temperature=DEFAULT_TEMPERATURE,
                top_k=DEFAULT_TOP_K,
                top_p=DEFAULT_TOP_P,
                num_ctx=DEFAULT_NUM_CTX,
                num_predict=DEFAULT_NUM_PREDICT,
                template_id="__custom__",
                target_words=DEFAULT_TARGET_WORDS,
            )

        assert response == ""
        assert "Cannot connect to server" in str(status)
        assert gen_info is None  # No metadata on error

    def test_timeout_error(self):
        """Should handle request timeout."""
        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.side_effect = (
                httpx.TimeoutException("Request timed out")
            )

            response, status, gen_info = generate_description(
                n_clicks=1,
                server_url="http://localhost:11434",
                model="llama3.2:latest",
                system_prompt="",
                user_prompt="Describe a room.",
                seed=42,
                temperature=DEFAULT_TEMPERATURE,
                top_k=DEFAULT_TOP_K,
                top_p=DEFAULT_TOP_P,
                num_ctx=DEFAULT_NUM_CTX,
                num_predict=DEFAULT_NUM_PREDICT,
                template_id="__custom__",
                target_words=DEFAULT_TARGET_WORDS,
            )

        assert response == ""
        assert "Request timed out" in str(status)
        assert gen_info is None

    def test_http_status_error(self):
        """Should handle HTTP error responses."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.side_effect = (
                httpx.HTTPStatusError("Not found", request=MagicMock(), response=mock_response)
            )

            response, status, gen_info = generate_description(
                n_clicks=1,
                server_url="http://localhost:11434",
                model="nonexistent:model",
                system_prompt="",
                user_prompt="Describe a room.",
                seed=42,
                temperature=DEFAULT_TEMPERATURE,
                top_k=DEFAULT_TOP_K,
                top_p=DEFAULT_TOP_P,
                num_ctx=DEFAULT_NUM_CTX,
                num_predict=DEFAULT_NUM_PREDICT,
                template_id="__custom__",
                target_words=DEFAULT_TARGET_WORDS,
            )

        assert response == ""
        assert "Server error: 404" in str(status)
        assert gen_info is None


# =============================================================================
# Test send_to_description
# =============================================================================


class TestSendToDescription:
    """Tests for the send_to_description callback."""

    @pytest.fixture
    def sample_zone_data(self):
        """Create sample zone data for testing."""
        return {
            "id": "test",
            "name": "Test Zone",
            "spawn_room": "spawn",
            "rooms": {
                "spawn": {
                    "id": "spawn",
                    "name": "Spawn Room",
                    "description": "Original description",
                    "coords": [0, 0, 0],
                    "exits": {},
                    "items": [],
                }
            },
            "items": {},
        }

    @pytest.fixture
    def sample_generation_info(self):
        """Create sample generation metadata for testing."""
        return {
            "model": "llama3.2:latest",
            "actual_seed": 12345,
            "template_id": "__custom__",
            "temperature": 0.7,
            "top_k": 40,
            "top_p": 0.9,
            "num_ctx": 4096,
            "num_predict": 512,
            "system_prompt": "You are a creative writer.",
            "user_prompt": "Describe a room.",
            "generated_at": "2024-01-15T10:30:00+00:00",
        }

    @pytest.fixture
    def sample_validation_info(self):
        """Create sample validation metadata for testing."""
        return {
            "valid": False,
            "hard_failures": ["word_count_out_of_bounds"],
            "soft_failures": [],
            "metrics": {"word_count": 12, "target_words": 50, "min_words": 33, "max_words": 58},
            "rule_hits": {"banned_phrases": ["opens onto"]},
            "validated_at": "2026-02-04T09:12:00+00:00",
        }

    def test_no_clicks_returns_no_update(self, sample_zone_data):
        """Should return no_update when button not clicked."""
        result = send_to_description(
            n_clicks=0,
            response_text="Some text",
            selected_room="spawn",
            zone_data=sample_zone_data,
            generation_info=None,
            validation_info=None,
        )
        assert result == (no_update, no_update, no_update, no_update)

    def test_none_clicks_returns_no_update(self, sample_zone_data):
        """Should return no_update when n_clicks is None."""
        result = send_to_description(
            n_clicks=None,
            response_text="Some text",
            selected_room="spawn",
            zone_data=sample_zone_data,
            generation_info=None,
            validation_info=None,
        )
        assert result == (no_update, no_update, no_update, no_update)

    def test_empty_response_text(self, sample_zone_data):
        """Should show 'Nothing to send' when response is empty."""
        description, zone, unsaved, status = send_to_description(
            n_clicks=1,
            response_text="",
            selected_room="spawn",
            zone_data=sample_zone_data,
            generation_info=None,
            validation_info=None,
        )
        assert description is no_update
        assert zone is no_update
        assert unsaved is no_update
        assert "Nothing to send" in str(status)

    def test_none_response_text(self, sample_zone_data):
        """Should show 'Nothing to send' when response is None."""
        description, zone, unsaved, status = send_to_description(
            n_clicks=1,
            response_text=None,
            selected_room="spawn",
            zone_data=sample_zone_data,
            generation_info=None,
            validation_info=None,
        )
        assert description is no_update
        assert "Nothing to send" in str(status)

    def test_no_room_selected_updates_form_only(self):
        """Should update form but not zone when no room selected."""
        test_text = "A dark room with stone walls."
        description, zone, unsaved, status = send_to_description(
            n_clicks=1,
            response_text=test_text,
            selected_room=None,
            zone_data=None,
            generation_info=None,
            validation_info=None,
        )
        assert description == test_text
        assert zone is no_update
        assert unsaved is no_update
        assert "select a room" in str(status).lower()

    def test_successful_send_updates_zone(self, sample_zone_data):
        """Should update zone data when room is selected."""
        test_text = "A new description for the room."
        description, zone, unsaved, status = send_to_description(
            n_clicks=1,
            response_text=test_text,
            selected_room="spawn",
            zone_data=sample_zone_data,
            generation_info=None,
            validation_info=None,
        )
        assert description == test_text
        assert zone is not no_update
        assert zone["rooms"]["spawn"]["description"] == test_text
        assert unsaved is True
        assert "Applied" in str(status)

    def test_room_not_found(self, sample_zone_data):
        """Should handle room not found in zone."""
        test_text = "A new description."
        description, zone, unsaved, status = send_to_description(
            n_clicks=1,
            response_text=test_text,
            selected_room="nonexistent",
            zone_data=sample_zone_data,
            generation_info=None,
            validation_info=None,
        )
        assert description == test_text
        assert zone is no_update
        assert "not found" in str(status).lower()

    def test_does_not_mutate_original_zone(self, sample_zone_data):
        """Should create new zone dict, not mutate original."""
        original_description = sample_zone_data["rooms"]["spawn"]["description"]
        test_text = "New description"

        description, zone, unsaved, status = send_to_description(
            n_clicks=1,
            response_text=test_text,
            selected_room="spawn",
            zone_data=sample_zone_data,
            generation_info=None,
            validation_info=None,
        )

        # Original should be unchanged
        assert sample_zone_data["rooms"]["spawn"]["description"] == original_description
        # New zone should have updated description
        assert zone["rooms"]["spawn"]["description"] == test_text

    def test_stores_generation_metadata(self, sample_zone_data, sample_generation_info):
        """Should store llm_generation metadata when provided.

        When a room description is applied, the generation metadata should
        be attached to the room for provenance tracking and reproducibility.
        """
        test_text = "A generated description."
        description, zone, unsaved, status = send_to_description(
            n_clicks=1,
            response_text=test_text,
            selected_room="spawn",
            zone_data=sample_zone_data,
            generation_info=sample_generation_info,
            validation_info=None,
        )

        # Verify metadata is stored
        assert zone["rooms"]["spawn"]["llm_generation"] is not None
        assert zone["rooms"]["spawn"]["llm_generation"]["model"] == "llama3.2:latest"
        assert zone["rooms"]["spawn"]["llm_generation"]["actual_seed"] == 12345
        assert zone["rooms"]["spawn"]["llm_generation"]["template_id"] == "__custom__"

    def test_clears_metadata_when_none(self, sample_zone_data):
        """Should clear llm_generation when no metadata provided.

        If the user edits the response manually or metadata is unavailable,
        any existing llm_generation should be cleared since it no longer
        accurately describes the description.
        """
        # First add some existing metadata to the room
        sample_zone_data["rooms"]["spawn"]["llm_generation"] = {
            "model": "old_model",
            "actual_seed": 99999,
        }

        test_text = "Manually edited description."
        description, zone, unsaved, status = send_to_description(
            n_clicks=1,
            response_text=test_text,
            selected_room="spawn",
            zone_data=sample_zone_data,
            generation_info=None,  # No metadata
            validation_info=None,
        )

        # Existing metadata should be cleared
        assert "llm_generation" not in zone["rooms"]["spawn"]

    def test_stores_validation_metadata(self, sample_zone_data, sample_validation_info):
        """Should store description_validation metadata when provided."""
        test_text = "A generated description."
        description, zone, unsaved, status = send_to_description(
            n_clicks=1,
            response_text=test_text,
            selected_room="spawn",
            zone_data=sample_zone_data,
            generation_info=None,
            validation_info=sample_validation_info,
        )

        assert zone["rooms"]["spawn"]["description_validation"] is not None
        assert zone["rooms"]["spawn"]["description_validation"]["valid"] is False
        assert (
            "word_count_out_of_bounds"
            in zone["rooms"]["spawn"]["description_validation"]["hard_failures"]
        )

    def test_clears_validation_metadata_when_none(self, sample_zone_data):
        """Should clear description_validation when no metadata provided."""
        sample_zone_data["rooms"]["spawn"]["description_validation"] = {"valid": True}
        test_text = "Manual edit."
        description, zone, unsaved, status = send_to_description(
            n_clicks=1,
            response_text=test_text,
            selected_room="spawn",
            zone_data=sample_zone_data,
            generation_info=None,
            validation_info=None,
        )

        assert "description_validation" not in zone["rooms"]["spawn"]


# =============================================================================
# Test handle_clipboard_copy
# =============================================================================


class TestHandleClipboardCopy:
    """Tests for the handle_clipboard_copy callback."""

    def test_no_clicks_returns_no_update(self):
        """Should return no_update when clipboard not clicked."""
        result = handle_clipboard_copy(n_clicks=0, response_text="Some text")
        assert result is no_update

    def test_none_clicks_returns_no_update(self):
        """Should return no_update when n_clicks is None."""
        result = handle_clipboard_copy(n_clicks=None, response_text="Some text")
        assert result is no_update

    def test_empty_response_text(self):
        """Should show 'Nothing to copy' when response is empty."""
        result = handle_clipboard_copy(n_clicks=1, response_text="")
        assert "Nothing to copy" in str(result)

    def test_none_response_text(self):
        """Should show 'Nothing to copy' when response is None."""
        result = handle_clipboard_copy(n_clicks=1, response_text=None)
        assert "Nothing to copy" in str(result)

    def test_successful_copy_feedback(self):
        """Should show success message when text exists."""
        result = handle_clipboard_copy(n_clicks=1, response_text="Generated description text")
        assert "Copied to clipboard" in str(result)


# =============================================================================
# Integration Tests
# =============================================================================


class TestOllamaIntegration:
    """Integration tests for Ollama callback workflows."""

    def test_full_workflow_fetch_and_generate(self, mock_models_response, mock_chat_response):
        """Test complete workflow: fetch models, then generate text."""
        # First, fetch models
        mock_tags_response = MagicMock()
        mock_tags_response.json.return_value = mock_models_response
        mock_tags_response.raise_for_status = MagicMock()

        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_tags_response

            options, status, placeholder = refresh_ollama_models(
                n_clicks=1, server_url="http://localhost:11434"
            )

        assert len(options) == 3
        selected_model = options[0]["value"]

        # Then generate with selected model
        mock_gen_response = MagicMock()
        mock_gen_response.json.return_value = mock_chat_response
        mock_gen_response.raise_for_status = MagicMock()

        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.return_value = mock_gen_response

            response, status, gen_info = generate_description(
                n_clicks=1,
                server_url="http://localhost:11434",
                model=selected_model,
                system_prompt="You are a creative writer.",
                user_prompt="Describe a dark dungeon.",
                seed=42,
                temperature=DEFAULT_TEMPERATURE,
                top_k=DEFAULT_TOP_K,
                top_p=DEFAULT_TOP_P,
                num_ctx=DEFAULT_NUM_CTX,
                num_predict=DEFAULT_NUM_PREDICT,
                template_id="__custom__",
                target_words=DEFAULT_TARGET_WORDS,
            )

        assert "ancient stone hall" in response
        assert gen_info is not None

    def test_generate_and_send_workflow(self, mock_chat_response):
        """Test workflow: generate text, then send to description."""
        # Generate text
        mock_response = MagicMock()
        mock_response.json.return_value = mock_chat_response
        mock_response.raise_for_status = MagicMock()

        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            response, status, gen_info = generate_description(
                n_clicks=1,
                server_url="http://localhost:11434",
                model="llama3.2:latest",
                system_prompt="",
                user_prompt="Describe a room.",
                seed=42,
                temperature=DEFAULT_TEMPERATURE,
                top_k=DEFAULT_TOP_K,
                top_p=DEFAULT_TOP_P,
                num_ctx=DEFAULT_NUM_CTX,
                num_predict=DEFAULT_NUM_PREDICT,
                template_id="__custom__",
                target_words=DEFAULT_TARGET_WORDS,
            )

        # Send to description (without room selection - just updates form field)
        description, zone, unsaved, send_status = send_to_description(
            n_clicks=1,
            response_text=response,
            selected_room=None,
            zone_data=None,
            generation_info=gen_info,
            validation_info=None,
        )

        assert description == response
        assert "Sent to form" in str(send_status)

    def test_server_down_recovery(self, mock_models_response):
        """Test that UI recovers gracefully when server comes back up."""
        # First attempt - server down
        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = httpx.ConnectError(
                "Connection refused"
            )

            options, status, placeholder = refresh_ollama_models(
                n_clicks=1, server_url="http://localhost:11434"
            )

        assert options == []
        assert "Not connected" in str(status)

        # Second attempt - server back up
        mock_response = MagicMock()
        mock_response.json.return_value = mock_models_response
        mock_response.raise_for_status = MagicMock()

        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            options, status, placeholder = refresh_ollama_models(
                n_clicks=2,  # Second click
                server_url="http://localhost:11434",
            )

        assert len(options) == 3
        assert "Connected" in str(status)


# =============================================================================
# Test populate_prompt_from_description
# =============================================================================


class TestPopulatePromptFromDescription:
    """Tests for the populate_prompt_from_description callback."""

    def test_no_clicks_returns_no_update(self):
        """Should return no_update when button not clicked."""
        result = populate_prompt_from_description(
            n_clicks=0,
            room_description="Some description",
            room_name="Test Room",
        )
        assert result == (no_update, no_update)

    def test_none_clicks_returns_no_update(self):
        """Should return no_update when n_clicks is None."""
        result = populate_prompt_from_description(
            n_clicks=None,
            room_description="Some description",
            room_name="Test Room",
        )
        assert result == (no_update, no_update)

    def test_empty_description_shows_message(self):
        """Should show message when description is empty."""
        prompt, status = populate_prompt_from_description(
            n_clicks=1,
            room_description="",
            room_name="Test Room",
        )
        assert prompt is no_update
        assert "No description to use" in str(status)

    def test_none_description_shows_message(self):
        """Should show message when description is None."""
        prompt, status = populate_prompt_from_description(
            n_clicks=1,
            room_description=None,
            room_name="Test Room",
        )
        assert prompt is no_update
        assert "No description to use" in str(status)

    def test_populates_with_room_name(self):
        """Should include room name in generated prompt."""
        test_description = "A dark and dusty cellar."
        prompt, status = populate_prompt_from_description(
            n_clicks=1,
            room_description=test_description,
            room_name="The Wine Cellar",
        )
        assert "The Wine Cellar" in prompt
        assert test_description in prompt
        assert "Rewrite" in prompt
        assert "copied to prompt" in str(status).lower()

    def test_populates_without_room_name(self):
        """Should work without room name."""
        test_description = "A bright sunny meadow."
        prompt, status = populate_prompt_from_description(
            n_clicks=1,
            room_description=test_description,
            room_name=None,
        )
        assert test_description in prompt
        assert "Rewrite this room description" in prompt
        assert "copied to prompt" in str(status).lower()

    def test_populates_with_empty_room_name(self):
        """Should work when room name is empty string."""
        test_description = "Stone walls surround you."
        prompt, status = populate_prompt_from_description(
            n_clicks=1,
            room_description=test_description,
            room_name="",
        )
        assert test_description in prompt
        # Empty room name should be treated like None
        assert "Rewrite this room description" in prompt


# =============================================================================
# Test Template Callbacks
# =============================================================================


class TestLoadTemplateOptions:
    """Tests for the load_template_options callback.

    This callback populates the template dropdown with available templates
    from the data/ollama/templates/ directory.
    """

    def test_returns_list(self):
        """Should return a list of template options."""
        result = load_template_options(n_clicks=0)
        assert isinstance(result, list)

    def test_includes_custom_option(self):
        """Should include 'Custom' option at the end."""
        result = load_template_options(n_clicks=1)

        # Last option should be Custom
        assert result[-1]["value"] == "__custom__"
        assert "Custom" in result[-1]["label"]

    def test_loads_on_startup(self):
        """Should load templates even with n_clicks=0 (initial load)."""
        result = load_template_options(n_clicks=0)

        # Should still return options (at minimum, the Custom option)
        assert len(result) >= 1


class TestHandleTemplateSelection:
    """Tests for the handle_template_selection callback.

    This callback compiles the selected template into a system prompt
    and updates the UI state accordingly.

    Note: The callback now returns 5 values (prompt, read_only, is_open, chevron, status).
    See TestHandleTemplateSelectionNewBehavior for tests of the new collapse behavior.
    """

    def test_no_selection_returns_no_update(self):
        """Should return no_update when nothing selected."""
        result = handle_template_selection(template_id=None, target_words=300)
        assert result == (no_update, no_update, no_update, no_update, no_update)

    def test_custom_mode_enables_editing(self):
        """Should enable editing when 'Custom' is selected."""
        prompt, read_only, is_open, chevron, status = handle_template_selection(
            template_id="__custom__", target_words=300
        )

        # Custom mode should be editable
        assert read_only is False
        # Collapse should be open (custom mode opens for editing)
        assert is_open is True
        # Chevron should be down (open state)
        assert "chevron-down" in chevron
        # Should have some prompt text
        assert len(prompt) > 0
        # Status should mention custom mode
        assert "Custom" in str(status) or "edit" in str(status).lower()

    def test_template_selection_makes_readonly(self):
        """Should make prompt read-only when template selected."""
        # Mock the template service (imported inside the function)
        mock_template = MagicMock()
        mock_template.template_name = "Test Template"
        mock_template.version = "1.0.0"
        mock_template.theme.name = "Test Realm"

        with (
            patch("pipeworks_mud_mapper.services.template_service.load_template") as mock_load,
            patch(
                "pipeworks_mud_mapper.services.template_service.compile_system_prompt"
            ) as mock_compile,
        ):
            mock_load.return_value = mock_template
            mock_compile.return_value = "Compiled system prompt"

            prompt, read_only, is_open, chevron, status = handle_template_selection(
                template_id="test_template", target_words=300
            )

        # Template mode should be read-only
        assert read_only is True
        # Collapse should be CLOSED by default (changed behavior)
        assert is_open is False
        # Chevron should be right (closed state)
        assert "chevron-right" in chevron
        # Should have compiled prompt
        assert prompt == "Compiled system prompt"

    def test_missing_template_shows_error(self):
        """Should show error when template not found."""
        with patch("pipeworks_mud_mapper.services.template_service.load_template") as mock_load:
            mock_load.return_value = None

            prompt, read_only, is_open, chevron, status = handle_template_selection(
                template_id="nonexistent", target_words=300
            )

        # Should not update prompt when template missing
        assert prompt is no_update
        # Chevron should not update either
        assert chevron is no_update
        # Status should indicate error
        assert "not found" in str(status).lower()


class TestToggleSystemPromptCollapse:
    """Tests for the toggle_system_prompt_collapse callback.

    This callback toggles the collapse state and updates the chevron icon.
    """

    def test_no_clicks_returns_no_update(self):
        """Should return no_update when not clicked."""
        result = toggle_system_prompt_collapse(n_clicks=0, is_open=False)
        assert result == (no_update, no_update)

    def test_toggle_from_closed_to_open(self):
        """Should open collapse when currently closed."""
        new_is_open, icon_class = toggle_system_prompt_collapse(n_clicks=1, is_open=False)
        assert new_is_open is True
        assert "chevron-down" in icon_class

    def test_toggle_from_open_to_closed(self):
        """Should close collapse when currently open."""
        new_is_open, icon_class = toggle_system_prompt_collapse(n_clicks=1, is_open=True)
        assert new_is_open is False
        assert "chevron-right" in icon_class


class TestCopySystemPrompt:
    """Tests for the copy_system_prompt callback.

    This callback provides feedback when the system prompt is copied.
    """

    def test_no_clicks_returns_no_update(self):
        """Should return no_update when not clicked."""
        result = copy_system_prompt(n_clicks=0, system_prompt="Some prompt")
        assert result is no_update

    def test_empty_prompt_shows_message(self):
        """Should show message when prompt is empty."""
        result = copy_system_prompt(n_clicks=1, system_prompt="")
        assert "No system prompt" in str(result)

    def test_none_prompt_shows_message(self):
        """Should show message when prompt is None."""
        result = copy_system_prompt(n_clicks=1, system_prompt=None)
        assert "No system prompt" in str(result)

    def test_successful_copy_feedback(self):
        """Should show success message when prompt exists."""
        result = copy_system_prompt(n_clicks=1, system_prompt="A valid system prompt")
        assert "copied" in str(result).lower()


# =============================================================================
# Test validate_ollama_response
# =============================================================================


class TestValidateOllamaResponse:
    """Tests for the validate_ollama_response callback."""

    def test_no_response_text(self):
        """Should return waiting status when no response is present."""
        result = validate_ollama_response(
            response_text=None,
            target_words=DEFAULT_TARGET_WORDS,
            history=[],
        )
        status, summary, hits, history_display, history_data, validation_info = result
        assert "Waiting for a response" in str(status)
        assert "No response" in str(summary)
        assert "No rule hits" in str(hits)
        assert history_data is no_update
        assert validation_info is no_update

    def test_validation_populates_history_and_metadata(self, monkeypatch):
        """Should render hits and return metadata for storage."""
        dummy = ValidationResult(
            valid=False,
            hard_failures=["word_count_out_of_bounds"],
            metrics={"word_count": 10, "min_words": 5, "max_words": 15},
            rule_hits={"cardinal_directions": ["north"]},
        )

        monkeypatch.setattr(
            "pipeworks_mud_mapper.callbacks.ollama_callbacks.validate_description",
            lambda text, target_words: dummy,
        )

        result = validate_ollama_response(
            response_text="A test response",
            target_words=10,
            history=[],
        )
        status, summary, hits, history_display, history_data, validation_info = result

        assert "Review needed" in str(status)
        assert "Hard failures" in str(summary)
        assert "cardinal directions" in str(hits)
        assert isinstance(history_data, list)
        assert len(history_data) == 1
        assert validation_info["valid"] is False
        assert "validated_at" in validation_info


# =============================================================================
# Test update_target_words_hint
# =============================================================================


class TestUpdateTargetWordsHint:
    """Tests for the update_target_words_hint helper."""

    def test_no_value(self):
        """Should return generic guidance when target_words is missing."""
        assert update_target_words_hint(None) == "25-500: Guides LLM output length"

    def test_exact_length_for_short(self):
        """Should describe exact length for short targets."""
        assert update_target_words_hint(30) == "Exact length: 30 words"

    def test_range_for_longer(self):
        """Should describe a range for longer targets."""
        assert update_target_words_hint(60) == "Range: 40-70 (aim ~60)"


# =============================================================================
# Test prompt prefix presets
# =============================================================================


class TestPromptPrefixPresets:
    """Tests for prompt prefix preset loading and application."""

    def test_load_prompt_prefix_options_missing_file(self, monkeypatch):
        """Should return empty list when config file is missing."""

        def fake_open(*_args, **_kwargs):
            raise FileNotFoundError

        monkeypatch.setattr("builtins.open", fake_open)

        assert load_prompt_prefix_options(1) == []

    def test_load_prompt_prefix_options_invalid_json(self, monkeypatch):
        """Should return empty list for invalid JSON."""
        import io

        fake_file = io.StringIO("{bad json")

        def fake_open(*_args, **_kwargs):
            fake_file.seek(0)
            return fake_file

        monkeypatch.setattr("builtins.open", fake_open)

        assert load_prompt_prefix_options(1) == []

    def test_load_prompt_prefix_options_success(self, monkeypatch):
        """Should return option list for valid config."""
        import io
        import json

        config = [
            {"label": "Exact 30", "value": "exact_30", "prefix": "Write 30 words exactly."},
            {"value": "short", "prefix": "Short response."},
            "bad",
        ]
        fake_file = io.StringIO(json.dumps(config))

        def fake_open(*_args, **_kwargs):
            fake_file.seek(0)
            return fake_file

        monkeypatch.setattr("builtins.open", fake_open)

        result = load_prompt_prefix_options(1)
        assert result == [
            {"label": "Exact 30", "value": "exact_30"},
            {"label": "short", "value": "short"},
        ]

    def test_apply_prompt_prefix(self, monkeypatch):
        """Should prepend prefix when selected."""
        import io
        import json

        config = [
            {
                "label": "Exact 30",
                "value": "exact_30",
                "prefix": "Write 30 words exactly.",
            }
        ]
        fake_file = io.StringIO(json.dumps(config))

        def fake_open(*_args, **_kwargs):
            fake_file.seek(0)
            return fake_file

        monkeypatch.setattr("builtins.open", fake_open)

        result = apply_prompt_prefix("exact_30", "a quiet alley")
        assert result.startswith("Write 30 words exactly.")

    def test_apply_prompt_prefix_no_prefix(self):
        """Should no-op when no prefix is selected."""
        assert apply_prompt_prefix(None, "a quiet alley") is no_update

    def test_apply_prompt_prefix_missing_entry(self, monkeypatch):
        """Should no-op when selected prefix is not in config."""
        import io
        import json

        config = [{"label": "Exact 30", "value": "exact_30", "prefix": "Write 30 words."}]
        fake_file = io.StringIO(json.dumps(config))

        def fake_open(*_args, **_kwargs):
            fake_file.seek(0)
            return fake_file

        monkeypatch.setattr("builtins.open", fake_open)

        assert apply_prompt_prefix("unknown", "a quiet alley") is no_update

    def test_apply_prompt_prefix_already_present(self, monkeypatch):
        """Should return original text when prefix already present."""
        import io
        import json

        config = [{"label": "Exact 30", "value": "exact_30", "prefix": "Write 30 words exactly."}]
        fake_file = io.StringIO(json.dumps(config))

        def fake_open(*_args, **_kwargs):
            fake_file.seek(0)
            return fake_file

        monkeypatch.setattr("builtins.open", fake_open)

        prompt = "Write 30 words exactly.\na quiet alley"
        assert apply_prompt_prefix("exact_30", prompt) == prompt


# =============================================================================
# Test generate_description with parameters
# =============================================================================


class TestGenerateDescriptionWithParameters:
    """Tests for generate_description with model parameters.

    These tests verify that model parameters (seed, temperature, top_k,
    top_p, num_ctx, num_predict) are correctly passed to the Ollama API.
    """

    @pytest.fixture
    def mock_chat_response(self):
        """Create a mock response for /api/chat endpoint."""
        return {
            "model": "llama3.2:latest",
            "message": {
                "role": "assistant",
                "content": "A dark chamber with flickering torches.",
            },
            "done": True,
        }

    def test_parameters_passed_to_api(self, mock_chat_response):
        """Should pass all parameters in the options dict."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_chat_response
        mock_response.raise_for_status = MagicMock()

        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.httpx.Client") as mock_client:
            mock_instance = mock_client.return_value.__enter__.return_value
            mock_instance.post.return_value = mock_response

            generate_description(
                n_clicks=1,
                server_url="http://localhost:11434",
                model="llama3.2:latest",
                system_prompt="Test prompt",
                user_prompt="Describe a room",
                seed=42,
                temperature=0.5,
                top_k=30,
                top_p=0.8,
                num_ctx=2048,
                num_predict=256,
                template_id="__custom__",
                target_words=200,
            )

        # Verify the API call included options
        call_args = mock_instance.post.call_args
        sent_json = call_args[1]["json"]
        assert "options" in sent_json

        options = sent_json["options"]
        assert options["seed"] == 42
        assert options["temperature"] == 0.5
        assert options["top_k"] == 30
        assert options["top_p"] == 0.8
        assert options["num_ctx"] == 2048
        assert options["num_predict"] == 256

    def test_default_parameters_used_when_none(self, mock_chat_response):
        """Should use default values when parameters are None."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_chat_response
        mock_response.raise_for_status = MagicMock()

        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.httpx.Client") as mock_client:
            mock_instance = mock_client.return_value.__enter__.return_value
            mock_instance.post.return_value = mock_response

            generate_description(
                n_clicks=1,
                server_url="http://localhost:11434",
                model="llama3.2:latest",
                system_prompt="Test prompt",
                user_prompt="Describe a room",
                seed=None,
                temperature=None,
                top_k=None,
                top_p=None,
                num_ctx=None,
                num_predict=None,
                template_id=None,
                target_words=None,
            )

        # Verify defaults were used
        call_args = mock_instance.post.call_args
        sent_json = call_args[1]["json"]
        options = sent_json["options"]

        # Seed will be random when DEFAULT_SEED (-1), so just check it's >= 0
        assert options["seed"] >= 0  # Random seed is always positive
        assert options["temperature"] == DEFAULT_TEMPERATURE
        assert options["top_k"] == DEFAULT_TOP_K
        assert options["top_p"] == DEFAULT_TOP_P
        assert options["num_ctx"] == DEFAULT_NUM_CTX
        assert options["num_predict"] == DEFAULT_NUM_PREDICT

    def test_random_seed_generates_positive_value(self, mock_chat_response):
        """Should generate positive seed when seed is -1."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_chat_response
        mock_response.raise_for_status = MagicMock()

        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.httpx.Client") as mock_client:
            mock_instance = mock_client.return_value.__enter__.return_value
            mock_instance.post.return_value = mock_response

            response, status, gen_info = generate_description(
                n_clicks=1,
                server_url="http://localhost:11434",
                model="llama3.2:latest",
                system_prompt="Test prompt",
                user_prompt="Describe a room",
                seed=-1,  # Random mode
                temperature=0.7,
                top_k=40,
                top_p=0.9,
                num_ctx=4096,
                num_predict=512,
                template_id="__custom__",
                target_words=DEFAULT_TARGET_WORDS,
            )

        call_args = mock_instance.post.call_args
        sent_json = call_args[1]["json"]
        options = sent_json["options"]

        # Random seed should be a positive integer
        assert options["seed"] >= 0
        assert options["seed"] < 2**31
        # Verify metadata captures the actual random seed
        assert gen_info["actual_seed"] == options["seed"]

    def test_fixed_seed_used_directly(self, mock_chat_response):
        """Should use fixed seed value when seed >= 0."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_chat_response
        mock_response.raise_for_status = MagicMock()

        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.httpx.Client") as mock_client:
            mock_instance = mock_client.return_value.__enter__.return_value
            mock_instance.post.return_value = mock_response

            response, status, gen_info = generate_description(
                n_clicks=1,
                server_url="http://localhost:11434",
                model="llama3.2:latest",
                system_prompt="Test prompt",
                user_prompt="Describe a room",
                seed=12345,  # Fixed seed
                temperature=0.7,
                top_k=40,
                top_p=0.9,
                num_ctx=4096,
                num_predict=512,
                template_id="__custom__",
                target_words=DEFAULT_TARGET_WORDS,
            )

        call_args = mock_instance.post.call_args
        sent_json = call_args[1]["json"]
        options = sent_json["options"]

        # Fixed seed should be used as-is
        assert options["seed"] == 12345
        # Verify metadata captures the seed
        assert gen_info["actual_seed"] == 12345

    def test_status_shows_seed_info(self, mock_chat_response):
        """Should show seed info in status message on success."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_chat_response
        mock_response.raise_for_status = MagicMock()

        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            response, status, gen_info = generate_description(
                n_clicks=1,
                server_url="http://localhost:11434",
                model="llama3.2:latest",
                system_prompt="Test prompt",
                user_prompt="Describe a room",
                seed=42,
                temperature=0.7,
                top_k=40,
                top_p=0.9,
                num_ctx=4096,
                num_predict=512,
                template_id="__custom__",
                target_words=DEFAULT_TARGET_WORDS,
            )

        # Status should mention the seed for reproducibility
        assert "seed" in str(status).lower()
        assert "42" in str(status)


# =============================================================================
# Test toggle_params_collapse
# =============================================================================


class TestToggleParamsCollapse:
    """Tests for the toggle_params_collapse callback.

    This callback toggles the parameters section collapse and updates
    the chevron icon.
    """

    def test_no_clicks_returns_no_update(self):
        """Should return no_update when not clicked."""
        result = toggle_params_collapse(n_clicks=0, is_open=False)
        assert result == (no_update, no_update)

    def test_toggle_from_closed_to_open(self):
        """Should open collapse when currently closed."""
        new_is_open, icon_class = toggle_params_collapse(n_clicks=1, is_open=False)
        assert new_is_open is True
        assert "chevron-down" in icon_class

    def test_toggle_from_open_to_closed(self):
        """Should close collapse when currently open."""
        new_is_open, icon_class = toggle_params_collapse(n_clicks=1, is_open=True)
        assert new_is_open is False
        assert "chevron-right" in icon_class


# =============================================================================
# Test handle_seed_controls
# =============================================================================


class TestHandleSeedControls:
    """Tests for the handle_seed_controls callback.

    This callback manages interaction between seed value input,
    +/- buttons, and the random checkbox.
    """

    def test_random_checkbox_checked_sets_seed_minus_one(self):
        """Should set seed to -1 when random checkbox is checked."""
        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.ctx") as mock_ctx:
            mock_ctx.triggered_id = "ollama-seed-random-check"

            seed, random_checked = handle_seed_controls(
                decrease_clicks=0,
                increase_clicks=0,
                random_checked=True,
                current_seed=42,
            )

        assert seed == -1
        assert random_checked is True

    def test_random_checkbox_unchecked_sets_seed_zero(self):
        """Should set seed to 0 when random checkbox unchecked from -1."""
        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.ctx") as mock_ctx:
            mock_ctx.triggered_id = "ollama-seed-random-check"

            seed, random_checked = handle_seed_controls(
                decrease_clicks=0,
                increase_clicks=0,
                random_checked=False,
                current_seed=-1,  # Was in random mode
            )

        assert seed == 0
        assert random_checked is False

    def test_random_checkbox_unchecked_keeps_current_seed(self):
        """Should keep current seed when unchecking if not -1."""
        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.ctx") as mock_ctx:
            mock_ctx.triggered_id = "ollama-seed-random-check"

            seed, random_checked = handle_seed_controls(
                decrease_clicks=0,
                increase_clicks=0,
                random_checked=False,
                current_seed=42,  # Already had a valid seed
            )

        assert seed == 42
        assert random_checked is False

    def test_increase_button_increments_seed(self):
        """Should increment seed when + button clicked."""
        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.ctx") as mock_ctx:
            mock_ctx.triggered_id = "ollama-seed-increase"

            seed, random_checked = handle_seed_controls(
                decrease_clicks=0,
                increase_clicks=1,
                random_checked=False,
                current_seed=10,
            )

        assert seed == 11
        assert random_checked is False

    def test_decrease_button_decrements_seed(self):
        """Should decrement seed when - button clicked."""
        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.ctx") as mock_ctx:
            mock_ctx.triggered_id = "ollama-seed-decrease"

            seed, random_checked = handle_seed_controls(
                decrease_clicks=1,
                increase_clicks=0,
                random_checked=False,
                current_seed=10,
            )

        assert seed == 9
        assert random_checked is False

    def test_decrease_button_stops_at_zero(self):
        """Should not go below 0 when decrementing."""
        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.ctx") as mock_ctx:
            mock_ctx.triggered_id = "ollama-seed-decrease"

            seed, random_checked = handle_seed_controls(
                decrease_clicks=1,
                increase_clicks=0,
                random_checked=False,
                current_seed=0,
            )

        assert seed == 0  # Stays at 0, doesn't go to -1
        assert random_checked is False

    def test_buttons_ignored_in_random_mode(self):
        """Should not change seed when in random mode (seed=-1)."""
        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.ctx") as mock_ctx:
            mock_ctx.triggered_id = "ollama-seed-increase"

            seed, random_checked = handle_seed_controls(
                decrease_clicks=0,
                increase_clicks=1,
                random_checked=True,
                current_seed=-1,
            )

        assert seed == -1  # Stays in random mode
        assert random_checked is True


# =============================================================================
# Test Seed Isolation (Critical for Determinism)
# =============================================================================


class TestSeedIsolation:
    """Tests verifying that random seed generation doesn't affect global state.

    This is critical because other parts of the application (e.g., name
    generation, character issuance) rely on deterministic random generation.
    The Ollama callback must use an ISOLATED Random instance to avoid
    poisoning the global random state.
    """

    @pytest.fixture
    def mock_chat_response(self):
        """Create a mock response for /api/chat endpoint."""
        return {
            "model": "llama3.2:latest",
            "message": {
                "role": "assistant",
                "content": "Generated content.",
            },
            "done": True,
        }

    def test_random_seed_does_not_affect_global_state(self, mock_chat_response):
        """Generating with seed=-1 should not affect global random state.

        This test verifies that the isolated RNG approach is working:
        1. Set up a known global random state
        2. Call generate_description with seed=-1 (triggers random seed)
        3. Verify the global random state wasn't changed
        """
        # Set up a known global random state
        random.seed(42)
        expected_values = [random.randint(0, 1000) for _ in range(5)]

        # Reset to the same state
        random.seed(42)

        # Now call generate_description with random seed
        mock_response = MagicMock()
        mock_response.json.return_value = mock_chat_response
        mock_response.raise_for_status = MagicMock()

        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            generate_description(
                n_clicks=1,
                server_url="http://localhost:11434",
                model="llama3.2:latest",
                system_prompt="Test",
                user_prompt="Test",
                seed=-1,  # Random mode - should use isolated RNG
                temperature=0.7,
                top_k=40,
                top_p=0.9,
                num_ctx=4096,
                num_predict=512,
                template_id="__custom__",
                target_words=DEFAULT_TARGET_WORDS,
            )

        # After the call, global random state should still produce expected values
        actual_values = [random.randint(0, 1000) for _ in range(5)]
        assert actual_values == expected_values, (
            "Global random state was modified by generate_description! "
            "This breaks determinism in other parts of the application."
        )

    def test_multiple_random_calls_dont_accumulate_state_changes(self, mock_chat_response):
        """Multiple calls with seed=-1 should not accumulate state changes.

        Even after many calls, the global random state should be unaffected.
        """
        # Set up a known global random state
        random.seed(123)
        expected_value = random.randint(0, 10000)

        # Reset to the same state
        random.seed(123)

        # Make multiple calls with random seed
        mock_response = MagicMock()
        mock_response.json.return_value = mock_chat_response
        mock_response.raise_for_status = MagicMock()

        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            for _ in range(10):  # Multiple calls
                generate_description(
                    n_clicks=1,
                    server_url="http://localhost:11434",
                    model="llama3.2:latest",
                    system_prompt="Test",
                    user_prompt="Test",
                    seed=-1,
                    temperature=0.7,
                    top_k=40,
                    top_p=0.9,
                    num_ctx=4096,
                    num_predict=512,
                    template_id="__custom__",
                    target_words=DEFAULT_TARGET_WORDS,
                )

        # Global state should still produce expected value
        actual_value = random.randint(0, 10000)
        assert actual_value == expected_value


# =============================================================================
# Test handle_template_selection with new behavior
# =============================================================================


class TestHandleTemplateSelectionNewBehavior:
    """Tests for handle_template_selection with updated collapse behavior.

    The template selection now keeps the system prompt collapse CLOSED
    by default (changed from previous behavior where it opened).
    """

    def test_template_selection_keeps_collapse_closed(self):
        """Should keep system prompt collapse closed when template selected."""
        mock_template = MagicMock()
        mock_template.template_name = "Test Template"
        mock_template.version = "1.0.0"
        mock_template.theme.name = "Test Realm"

        with (
            patch("pipeworks_mud_mapper.services.template_service.load_template") as mock_load,
            patch(
                "pipeworks_mud_mapper.services.template_service.compile_system_prompt"
            ) as mock_compile,
        ):
            mock_load.return_value = mock_template
            mock_compile.return_value = "Compiled system prompt"

            prompt, read_only, is_open, chevron, status = handle_template_selection(
                template_id="test_template", target_words=300
            )

        # Template mode should keep collapse CLOSED (is_open=False)
        assert is_open is False
        assert "chevron-right" in chevron  # Closed state icon

    def test_custom_mode_opens_collapse(self):
        """Should open collapse when 'Custom' mode selected."""
        prompt, read_only, is_open, chevron, status = handle_template_selection(
            template_id="__custom__", target_words=300
        )

        # Custom mode should open collapse for editing
        assert is_open is True
        assert "chevron-down" in chevron  # Open state icon
