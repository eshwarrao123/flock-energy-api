"""Tests for the UrjaPortalClient."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.client import UrjaPortalClient
from app.config import Settings


class TestUrjaPortalClientInit:
    """Tests for UrjaPortalClient initialization."""

    def test_default_settings(self) -> None:
        """Test client uses default settings when no args provided."""
        client = UrjaPortalClient()
        assert client.base_url == "https://urja-ops.flockenergy.tech"
        assert client.timeout == 30

    def test_custom_settings(self) -> None:
        """Test client with custom settings."""
        client = UrjaPortalClient(
            base_url="https://custom.example.com",
            username="testuser",
            password="testpass",
            timeout=15,
        )
        assert client.base_url == "https://custom.example.com"
        assert client.username == "testuser"
        assert client.timeout == 15

    def test_client_is_not_authenticated_initially(self) -> None:
        """Test that client starts unauthenticated."""
        client = UrjaPortalClient()
        assert not client._authenticated


class TestUrjaPortalClientClose:
    """Tests for UrjaPortalClient close method."""

    def test_close_without_client(self) -> None:
        """Test closing when no client exists."""
        client = UrjaPortalClient()
        # Should not raise
        client.close()


class TestUrjaPortalClientContextManager:
    """Tests for async context manager support."""

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Test client works as async context manager."""
        async with UrjaPortalClient() as client:
            assert client._client is None


class TestUrjaPortalClientAuthenticate:
    """Tests for UrjaPortalClient.authenticate method."""

    @pytest.mark.asyncio
    async def test_authenticate_sets_flag(self) -> None:
        """Test authenticate sets _authenticated flag."""
        client = UrjaPortalClient()
        # Stub - always returns True
        result = await client.authenticate()
        assert result is True
        assert client._authenticated is True

    @pytest.mark.asyncio
    async def test_authenticate_idempotent(self) -> None:
        """Test authenticate is idempotent when already authenticated."""
        client = UrjaPortalClient()
        client._authenticated = True
        result = await client.authenticate()
        assert result is True


class TestUrjaPortalClientFetchPage:
    """Tests for UrjaPortalClient.fetch_page method."""

    @pytest.mark.asyncio
    async def test_fetch_page_requires_auth(self) -> None:
        """Test that fetch_page triggers authentication."""
        client = UrjaPortalClient()
        with patch.object(client, "authenticate", new=AsyncMock(return_value=True)) as mock_auth:
            with patch.object(client, "_get_client", new=AsyncMock()) as mock_get_client:
                mock_client_instance = AsyncMock()
                mock_response = MagicMock()
                mock_response.text = "<html><body>OK</body></html>"
                mock_response.raise_for_status = MagicMock()
                mock_client_instance.get.return_value = mock_response
                mock_get_client.return_value = mock_client_instance

                result = await client.fetch_page("/meters")
                assert result == "<html><body>OK</body></html>"
                mock_auth.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_page_raises_on_http_error(self) -> None:
        """Test that fetch_page raises on HTTP errors."""
        client = UrjaPortalClient()
        with patch.object(client, "authenticate", new=AsyncMock(return_value=True)):
            with patch.object(client, "_get_client", new=AsyncMock()) as mock_get_client:
                mock_client_instance = AsyncMock()
                mock_response = MagicMock()
                mock_response.raise_for_status.side_effect = Exception("Not Found")
                mock_client_instance.get.return_value = mock_response
                mock_get_client.return_value = mock_client_instance

                with pytest.raises(Exception, match="Not Found"):
                    await client.fetch_page("/meters")