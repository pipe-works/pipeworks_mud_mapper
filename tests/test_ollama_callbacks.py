"""Comprehensive tests for Ollama LLM integration callbacks.

This module tests the Ollama callbacks that handle communication with
a local Ollama server for generating room descriptions, including
the template-based system prompt system.

Test Organization
-----------------
Tests are grouped by callback function:

- **TestRefreshOllamaModels**: Model list fetching from server
- **TestGenerateDescription**: LLM text generation via /api/chat
- **TestSendToDescription**: Sending response to room description
- **TestHandleClipboardCopy**: Clipboard feedback handling
- **TestPopulatePromptFromDescription**: Populating prompt from room description
- **TestLoadTemplateOptions**: Template dropdown population
- **TestHandleTemplateSelection**: Template selection and compilation
- **TestToggleSystemPromptCollapse**: System prompt collapse toggle
- **TestCopySystemPrompt**: System prompt clipboard feedback

Design Notes
------------
These tests mock the httpx client to avoid requiring an actual
Ollama server. We test:

- Successful API responses (using /api/chat endpoint)
- Network errors (connection refused, timeout)
- HTTP errors (4xx, 5xx)
- Edge cases (empty responses, missing data)
- Template loading, compilation, and UI state management

API Migration
-------------
The generate_description callback uses Ollama's ``/api/chat`` endpoint
instead of ``/api/generate`` for proper system/user message separation.
Tests verify the messages array format with distinct roles.

See Also
--------
- ``callbacks/ollama_callbacks.py``: The callbacks being tested
- ``test_layout.py``: Tests for the Ollama UI components
- ``test_template_service.py``: Tests for template loading/compilation
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest
from dash import no_update

from pipeworks_mud_mapper.callbacks.ollama_callbacks import (
    copy_system_prompt,
    generate_description,
    handle_clipboard_copy,
    handle_template_selection,
    load_template_options,
    populate_prompt_from_description,
    refresh_ollama_models,
    send_to_description,
    toggle_system_prompt_collapse,
)

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
    """Tests for the generate_description callback."""

    def test_no_clicks_returns_no_update(self):
        """Should return no_update when button not clicked."""
        result = generate_description(
            n_clicks=0,
            server_url="http://localhost:11434",
            model="llama3.2:latest",
            system_prompt="You are helpful.",
            user_prompt="Describe a room.",
        )
        assert result == (no_update, no_update)

    def test_empty_server_url(self):
        """Should return warning when server URL is empty."""
        response, status = generate_description(
            n_clicks=1,
            server_url="",
            model="llama3.2:latest",
            system_prompt="You are helpful.",
            user_prompt="Describe a room.",
        )
        assert response == ""
        assert "Please enter a server URL" in str(status)

    def test_no_model_selected(self):
        """Should return warning when no model selected."""
        response, status = generate_description(
            n_clicks=1,
            server_url="http://localhost:11434",
            model=None,
            system_prompt="You are helpful.",
            user_prompt="Describe a room.",
        )
        assert response == ""
        assert "Please select a model" in str(status)

    def test_empty_model_selected(self):
        """Should return warning when model is empty string."""
        response, status = generate_description(
            n_clicks=1,
            server_url="http://localhost:11434",
            model="",
            system_prompt="You are helpful.",
            user_prompt="Describe a room.",
        )
        assert response == ""
        assert "Please select a model" in str(status)

    def test_empty_user_prompt(self):
        """Should return warning when user prompt is empty."""
        response, status = generate_description(
            n_clicks=1,
            server_url="http://localhost:11434",
            model="llama3.2:latest",
            system_prompt="You are helpful.",
            user_prompt="",
        )
        assert response == ""
        assert "Please enter a user prompt" in str(status)

    def test_successful_generation(self, mock_chat_response):
        """Should return generated text on successful API call."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_chat_response
        mock_response.raise_for_status = MagicMock()

        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            response, status = generate_description(
                n_clicks=1,
                server_url="http://localhost:11434",
                model="llama3.2:latest",
                system_prompt="You are a creative writer.",
                user_prompt="Describe a medieval hall.",
            )

        assert "ancient stone hall" in response
        assert "Generated successfully" in str(status)

    def test_generation_without_system_prompt(self, mock_chat_response):
        """Should work without a system prompt using /api/chat."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_chat_response
        mock_response.raise_for_status = MagicMock()

        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.httpx.Client") as mock_client:
            mock_instance = mock_client.return_value.__enter__.return_value
            mock_instance.post.return_value = mock_response

            response, status = generate_description(
                n_clicks=1,
                server_url="http://localhost:11434",
                model="llama3.2:latest",
                system_prompt="",  # No system prompt
                user_prompt="Describe a medieval hall.",
            )

        assert response != ""
        # Verify messages array has only user message (no system)
        call_args = mock_instance.post.call_args
        sent_json = call_args[1]["json"]
        assert "messages" in sent_json
        assert len(sent_json["messages"]) == 1
        assert sent_json["messages"][0]["role"] == "user"
        assert sent_json["messages"][0]["content"] == "Describe a medieval hall."

    def test_generation_with_system_prompt(self, mock_chat_response):
        """Should send system and user messages separately via /api/chat."""
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
                system_prompt="Be creative.",
                user_prompt="Describe a hall.",
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

    def test_empty_response_from_model(self):
        """Should handle empty response from model via /api/chat."""
        mock_response = MagicMock()
        # /api/chat returns empty content under message.content
        mock_response.json.return_value = {"message": {"role": "assistant", "content": ""}}
        mock_response.raise_for_status = MagicMock()

        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            response, status = generate_description(
                n_clicks=1,
                server_url="http://localhost:11434",
                model="llama3.2:latest",
                system_prompt="",
                user_prompt="Describe a room.",
            )

        assert response == ""
        assert "Empty response" in str(status)

    def test_connection_error(self):
        """Should handle connection refused error."""
        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.side_effect = httpx.ConnectError(
                "Connection refused"
            )

            response, status = generate_description(
                n_clicks=1,
                server_url="http://localhost:11434",
                model="llama3.2:latest",
                system_prompt="",
                user_prompt="Describe a room.",
            )

        assert response == ""
        assert "Cannot connect to server" in str(status)

    def test_timeout_error(self):
        """Should handle request timeout."""
        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.side_effect = (
                httpx.TimeoutException("Request timed out")
            )

            response, status = generate_description(
                n_clicks=1,
                server_url="http://localhost:11434",
                model="llama3.2:latest",
                system_prompt="",
                user_prompt="Describe a room.",
            )

        assert response == ""
        assert "Request timed out" in str(status)

    def test_http_status_error(self):
        """Should handle HTTP error responses."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.side_effect = (
                httpx.HTTPStatusError("Not found", request=MagicMock(), response=mock_response)
            )

            response, status = generate_description(
                n_clicks=1,
                server_url="http://localhost:11434",
                model="nonexistent:model",
                system_prompt="",
                user_prompt="Describe a room.",
            )

        assert response == ""
        assert "Server error: 404" in str(status)


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

    def test_no_clicks_returns_no_update(self, sample_zone_data):
        """Should return no_update when button not clicked."""
        result = send_to_description(
            n_clicks=0,
            response_text="Some text",
            selected_room="spawn",
            zone_data=sample_zone_data,
        )
        assert result == (no_update, no_update, no_update, no_update)

    def test_none_clicks_returns_no_update(self, sample_zone_data):
        """Should return no_update when n_clicks is None."""
        result = send_to_description(
            n_clicks=None,
            response_text="Some text",
            selected_room="spawn",
            zone_data=sample_zone_data,
        )
        assert result == (no_update, no_update, no_update, no_update)

    def test_empty_response_text(self, sample_zone_data):
        """Should show 'Nothing to send' when response is empty."""
        description, zone, unsaved, status = send_to_description(
            n_clicks=1,
            response_text="",
            selected_room="spawn",
            zone_data=sample_zone_data,
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
        )

        # Original should be unchanged
        assert sample_zone_data["rooms"]["spawn"]["description"] == original_description
        # New zone should have updated description
        assert zone["rooms"]["spawn"]["description"] == test_text


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

            response, status = generate_description(
                n_clicks=1,
                server_url="http://localhost:11434",
                model=selected_model,
                system_prompt="You are a creative writer.",
                user_prompt="Describe a dark dungeon.",
            )

        assert "ancient stone hall" in response

    def test_generate_and_send_workflow(self, mock_chat_response):
        """Test workflow: generate text, then send to description."""
        # Generate text
        mock_response = MagicMock()
        mock_response.json.return_value = mock_chat_response
        mock_response.raise_for_status = MagicMock()

        with patch("pipeworks_mud_mapper.callbacks.ollama_callbacks.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            response, status = generate_description(
                n_clicks=1,
                server_url="http://localhost:11434",
                model="llama3.2:latest",
                system_prompt="",
                user_prompt="Describe a room.",
            )

        # Send to description (without room selection - just updates form field)
        description, zone, unsaved, send_status = send_to_description(
            n_clicks=1,
            response_text=response,
            selected_room=None,
            zone_data=None,
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
    """

    def test_no_selection_returns_no_update(self):
        """Should return no_update when nothing selected."""
        result = handle_template_selection(template_id=None)
        assert result == (no_update, no_update, no_update, no_update)

    def test_custom_mode_enables_editing(self):
        """Should enable editing when 'Custom' is selected."""
        prompt, read_only, is_open, status = handle_template_selection(template_id="__custom__")

        # Custom mode should be editable
        assert read_only is False
        # Collapse should be open
        assert is_open is True
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

            prompt, read_only, is_open, status = handle_template_selection(
                template_id="test_template"
            )

        # Template mode should be read-only
        assert read_only is True
        # Collapse should be open to show the prompt
        assert is_open is True
        # Should have compiled prompt
        assert prompt == "Compiled system prompt"

    def test_missing_template_shows_error(self):
        """Should show error when template not found."""
        with patch("pipeworks_mud_mapper.services.template_service.load_template") as mock_load:
            mock_load.return_value = None

            prompt, read_only, is_open, status = handle_template_selection(
                template_id="nonexistent"
            )

        # Should not update prompt when template missing
        assert prompt is no_update
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
