"""Tests for the Ollama HTTP client wrapper."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from pipeworks_mud_mapper.services.ollama_client import chat, list_models


class TestListModels:
    """Tests for list_models helper."""

    def test_list_models_returns_models(self):
        """Should return the models list from /api/tags."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"models": [{"name": "llama"}]}
        mock_response.raise_for_status = MagicMock()

        with patch("pipeworks_mud_mapper.services.ollama_client.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            result = list_models("http://localhost:11434")

        assert result == [{"name": "llama"}]

    def test_list_models_normalizes_url(self):
        """Should strip trailing slash before calling /api/tags."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"models": []}
        mock_response.raise_for_status = MagicMock()

        with patch("pipeworks_mud_mapper.services.ollama_client.httpx.Client") as mock_client:
            mock_instance = mock_client.return_value.__enter__.return_value
            mock_instance.get.return_value = mock_response

            list_models("http://localhost:11434/")

        mock_instance.get.assert_called_once_with("http://localhost:11434/api/tags")

    def test_list_models_raises_http_errors(self):
        """Should propagate HTTP status errors for callers to handle."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch("pipeworks_mud_mapper.services.ollama_client.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = httpx.HTTPStatusError(
                "Server error", request=MagicMock(), response=mock_response
            )

            with pytest.raises(httpx.HTTPStatusError):
                list_models("http://localhost:11434")


class TestChat:
    """Tests for chat helper."""

    def test_chat_returns_json(self):
        """Should return parsed JSON from /api/chat."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"message": {"content": "hi"}}
        mock_response.raise_for_status = MagicMock()

        with patch("pipeworks_mud_mapper.services.ollama_client.httpx.Client") as mock_client:
            mock_instance = mock_client.return_value.__enter__.return_value
            mock_instance.post.return_value = mock_response

            result = chat(
                server_url="http://localhost:11434",
                model="llama",
                messages=[{"role": "user", "content": "hi"}],
                options={"temperature": 0.7},
            )

        assert result == {"message": {"content": "hi"}}

    def test_chat_normalizes_url(self):
        """Should strip trailing slash before calling /api/chat."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"message": {"content": "hi"}}
        mock_response.raise_for_status = MagicMock()

        with patch("pipeworks_mud_mapper.services.ollama_client.httpx.Client") as mock_client:
            mock_instance = mock_client.return_value.__enter__.return_value
            mock_instance.post.return_value = mock_response

            chat(
                server_url="http://localhost:11434/",
                model="llama",
                messages=[{"role": "user", "content": "hi"}],
                options={"temperature": 0.7},
            )

        mock_instance.post.assert_called_once()
        assert mock_instance.post.call_args.args[0] == "http://localhost:11434/api/chat"

    def test_chat_raises_connection_error(self):
        """Should propagate connection errors for callers to handle."""
        with patch("pipeworks_mud_mapper.services.ollama_client.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.side_effect = httpx.ConnectError(
                "Connection refused"
            )

            with pytest.raises(httpx.ConnectError):
                chat(
                    server_url="http://localhost:11434",
                    model="llama",
                    messages=[{"role": "user", "content": "hi"}],
                    options={"temperature": 0.7},
                )
