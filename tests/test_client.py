"""Tests for the UrjaPortalClient."""

from __future__ import annotations

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

from app.client import UrjaPortalClient


class TestUrjaPortalClientInit:
    """Tests for UrjaPortalClient initialization."""

    def test_init_with_required_args(self) -> None:
        """Test client initialization with required arguments."""
        client = UrjaPortalClient(
            base_url="https://urja-ops.flockenergy.tech",
            username="testuser",
            password="testpass",
        )
        assert client.base_url == "https://urja-ops.flockenergy.tech"
        assert client.username == "testuser"
        assert client.password == "testpass"
        assert client.timeout == 30.0

    def test_init_with_custom_timeout(self) -> None:
        """Test client initialization with custom timeout."""
        client = UrjaPortalClient(
            base_url="https://custom.example.com",
            username="testuser",
            password="testpass",
            timeout=15.0,
        )
        assert client.base_url == "https://custom.example.com"
        assert client.timeout == 15.0

    def test_init_strips_trailing_slash(self) -> None:
        """Test that base_url trailing slash is stripped."""
        client = UrjaPortalClient(
            base_url="https://urja-ops.flockenergy.tech/",
            username="testuser",
            password="testpass",
        )
        assert client.base_url == "https://urja-ops.flockenergy.tech"

    def test_client_is_not_authenticated_initially(self) -> None:
        """Test that client starts unauthenticated."""
        client = UrjaPortalClient(
            base_url="https://urja-ops.flockenergy.tech",
            username="testuser",
            password="testpass",
        )
        assert not client._authenticated


class TestUrjaPortalClientClose:
    """Tests for UrjaPortalClient close method."""

    def test_close_without_client(self) -> None:
        """Test closing when no client exists."""
        client = UrjaPortalClient(
            base_url="https://urja-ops.flockenergy.tech",
            username="testuser",
            password="testpass",
        )
        # Should not raise
        client.close()


class TestUrjaPortalClientContextManager:
    """Tests for async context manager support."""

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Test client works as async context manager."""
        async with UrjaPortalClient(
            base_url="https://urja-ops.flockenergy.tech",
            username="testuser",
            password="testpass",
        ) as client:
            assert client._client is None


class TestUrjaPortalClientLogin:
    """Tests for UrjaPortalClient.login method."""

    @pytest.mark.asyncio
    async def test_login_sets_authenticated_flag(self) -> None:
        """Test login sets _authenticated flag."""
        client = UrjaPortalClient(
            base_url="https://urja-ops.flockenergy.tech",
            username="testuser",
            password="testpass",
        )
        with patch.object(client, "_get_client", new_callable=AsyncMock) as mock_get_client:
            mock_client_instance = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.url = "https://urja-ops.flockenergy.tech/dashboard"
            mock_response.raise_for_status = MagicMock()
            mock_client_instance.post.return_value = mock_response
            mock_get_client.return_value = mock_client_instance

            result = await client.login()
            assert result is True
            assert client._authenticated is True

    @pytest.mark.asyncio
    async def test_login_is_idempotent_when_authenticated(self) -> None:
        """Test login is idempotent when already authenticated."""
        client = UrjaPortalClient(
            base_url="https://urja-ops.flockenergy.tech",
            username="testuser",
            password="testpass",
        )
        client._authenticated = True

        result = await client.login()
        assert result is True

    @pytest.mark.asyncio
    async def test_login_raises_on_http_error(self) -> None:
        """Test login raises on HTTP error."""
        client = UrjaPortalClient(
            base_url="https://urja-ops.flockenergy.tech",
            username="testuser",
            password="wrongpass",
        )
        with patch.object(client, "_get_client", new_callable=AsyncMock) as mock_get_client:
            mock_client_instance = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.raise_for_status.side_effect = Exception("Unauthorized")
            mock_client_instance.post.return_value = mock_response
            mock_get_client.return_value = mock_client_instance

            with pytest.raises(Exception, match="Unauthorized"):
                await client.login()


class TestUrjaPortalClientEnsureAuth:
    """Tests for UrjaPortalClient._ensure_auth method."""

    @pytest.mark.asyncio
    async def test_ensure_auth_passes_when_authenticated(self) -> None:
        """Test _ensure_auth does nothing when already authenticated."""
        client = UrjaPortalClient(
            base_url="https://urja-ops.flockenergy.tech",
            username="testuser",
            password="testpass",
        )
        client._authenticated = True
        await client._ensure_auth()
        # Should not raise, no HTTP calls made

    @pytest.mark.asyncio
    async def test_ensure_auth_calls_login_on_redirect(self) -> None:
        """Test _ensure_auth calls login when redirected."""
        client = UrjaPortalClient(
            base_url="https://urja-ops.flockenergy.tech",
            username="testuser",
            password="testpass",
        )
        with patch.object(client, "_get_client", new_callable=AsyncMock) as mock_get_client:
            mock_client_instance = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 302
            mock_response.url = "https://urja-ops.flockenergy.tech/login"
            mock_get_client.return_value = mock_client_instance
            mock_client_instance.get.return_value = mock_response

            with patch.object(client, "login", new=AsyncMock(return_value=True)) as mock_login:
                await client._ensure_auth()
                mock_login.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_auth_raises_after_failed_reauth(self) -> None:
        """Test _ensure_auth raises when re-auth fails."""
        client = UrjaPortalClient(
            base_url="https://urja-ops.flockenergy.tech",
            username="testuser",
            password="testpass",
        )
        with patch.object(client, "_get_client", new_callable=AsyncMock) as mock_get_client:
            mock_client_instance = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.url = "https://urja-ops.flockenergy.tech/meters"
            mock_response.request = MagicMock()
            mock_get_client.return_value = mock_client_instance
            mock_client_instance.get.return_value = mock_response

            with patch.object(client, "login", new=AsyncMock(return_value=False)):
                with pytest.raises(Exception):
                    await client._ensure_auth()


class TestUrjaPortalClientGetMetersHtml:
    """Tests for UrjaPortalClient.get_meters_html method."""

    @pytest.mark.asyncio
    async def test_get_meters_html_returns_html(self) -> None:
        """Test get_meters_html returns raw HTML."""
        client = UrjaPortalClient(
            base_url="https://urja-ops.flockenergy.tech",
            username="testuser",
            password="testpass",
        )
        with patch.object(client, "_ensure_auth", new=AsyncMock()) as mock_auth:
            with patch.object(client, "_get_client", new_callable=AsyncMock) as mock_get_client:
                mock_client_instance = AsyncMock()
                mock_response = MagicMock()
                mock_response.text = "<html><body><table>...</table></body></html>"
                mock_response.raise_for_status = MagicMock()
                mock_client_instance.get.return_value = mock_response
                mock_get_client.return_value = mock_client_instance

                result = await client.get_meters_html(page=1)
                assert "<html>" in result
                mock_auth.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_meters_html_reauths_on_401(self) -> None:
        """Test get_meters_html re-authenticates on 401."""
        client = UrjaPortalClient(
            base_url="https://urja-ops.flockenergy.tech",
            username="testuser",
            password="testpass",
        )
        with patch.object(client, "_ensure_auth", new=AsyncMock()) as mock_auth:
            with patch.object(client, "_get_client", new_callable=AsyncMock) as mock_get_client:
                mock_client_instance = AsyncMock()
                mock_response_401 = MagicMock()
                mock_response_401.status_code = 401
                mock_response_401.raise_for_status.side_effect = httpx.HTTPStatusError(
                    "Unauthorized", request=MagicMock(), response=mock_response_401,
                )
                mock_response_200 = MagicMock()
                mock_response_200.text = "<html><body>OK</body></html>"
                mock_response_200.raise_for_status = MagicMock()
                mock_client_instance.get.side_effect = [mock_response_401, mock_response_200]
                mock_get_client.return_value = mock_client_instance

                with patch.object(client, "login", new=AsyncMock(return_value=True)):
                    result = await client.get_meters_html(page=1)
                    assert "<html>" in result

    @pytest.mark.asyncio
    async def test_get_meters_html_raises_on_timeout(self) -> None:
        """Test get_meters_html raises on timeout."""
        client = UrjaPortalClient(
            base_url="https://urja-ops.flockenergy.tech",
            username="testuser",
            password="testpass",
        )
        with patch.object(client, "_ensure_auth", new=AsyncMock()) as mock_auth:
            with patch.object(client, "_get_client", new_callable=AsyncMock) as mock_get_client:
                mock_client_instance = AsyncMock()
                mock_client_instance.get.side_effect = httpx.TimeoutException("Timeout")
                mock_get_client.return_value = mock_client_instance

                with pytest.raises(httpx.TimeoutException):
                    await client.get_meters_html(page=1)


class TestUrjaPortalClientGetMeterDetailHtml:
    """Tests for UrjaPortalClient.get_meter_detail_html method."""

    @pytest.mark.asyncio
    async def test_get_meter_detail_html_returns_html(self) -> None:
        """Test get_meter_detail_html returns raw HTML."""
        client = UrjaPortalClient(
            base_url="https://urja-ops.flockenergy.tech",
            username="testuser",
            password="testpass",
        )
        with patch.object(client, "_ensure_auth", new=AsyncMock()) as mock_auth:
            with patch.object(client, "_get_client", new_callable=AsyncMock) as mock_get_client:
                mock_client_instance = AsyncMock()
                mock_response = MagicMock()
                mock_response.text = "<html><body>Meter J100001</body></html>"
                mock_response.raise_for_status = MagicMock()
                mock_client_instance.get.return_value = mock_response
                mock_get_client.return_value = mock_client_instance

                result = await client.get_meter_detail_html("J100001")
                assert "J100001" in result
                mock_auth.assert_called_once()


class TestUrjaPortalClientGetConsumptionHtml:
    """Tests for UrjaPortalClient.get_consumption_html method."""

    @pytest.mark.asyncio
    async def test_get_consumption_html_returns_html(self) -> None:
        """Test get_consumption_html returns raw HTML."""
        client = UrjaPortalClient(
            base_url="https://urja-ops.flockenergy.tech",
            username="testuser",
            password="testpass",
        )
        with patch.object(client, "_ensure_auth", new=AsyncMock()) as mock_auth:
            with patch.object(client, "_get_client", new_callable=AsyncMock) as mock_get_client:
                mock_client_instance = AsyncMock()
                mock_response = MagicMock()
                mock_response.text = "<html><body>Consumption data</body></html>"
                mock_response.raise_for_status = MagicMock()
                mock_client_instance.get.return_value = mock_response
                mock_get_client.return_value = mock_client_instance

                result = await client.get_consumption_html("J100001")
                assert "Consumption data" in result
                mock_auth.assert_called_once()


class TestUrjaPortalClientGetTransformersHtml:
    """Tests for UrjaPortalClient.get_transformers_html method."""

    @pytest.mark.asyncio
    async def test_get_transformers_html_returns_html(self) -> None:
        """Test get_transformers_html returns raw HTML."""
        client = UrjaPortalClient(
            base_url="https://urja-ops.flockenergy.tech",
            username="testuser",
            password="testpass",
        )
        with patch.object(client, "_ensure_auth", new=AsyncMock()) as mock_auth:
            with patch.object(client, "_get_client", new_callable=AsyncMock) as mock_get_client:
                mock_client_instance = AsyncMock()
                mock_response = MagicMock()
                mock_response.text = "<html><body>Transformers</body></html>"
                mock_response.raise_for_status = MagicMock()
                mock_client_instance.get.return_value = mock_response
                mock_get_client.return_value = mock_client_instance

                result = await client.get_transformers_html()
                assert "Transformers" in result
                mock_auth.assert_called_once()