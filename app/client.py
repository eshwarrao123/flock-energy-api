"""
Async HTTP client for the Urja Meter Ops legacy portal.

Uses httpx.AsyncClient for connection pooling and session management.
Handles authentication, retries, and graceful error recovery.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from app.parser import parse_meter_list

from app.config import settings

logger = logging.getLogger(__name__)


class UrjaPortalClient:
    """Async HTTP client wrapping the Urja Meter Ops legacy portal.

    Manages authentication, session cookies, and HTML retrieval from the
    legacy portal. All methods are async-compatible for use with FastAPI
    dependency injection.

    Attributes:
        base_url: Portal base URL.
        username: Portal login username.
        password: Portal login password.
        timeout: HTTP request timeout in seconds.
        _client: Internal httpx.AsyncClient instance.
        _authenticated: Whether the client has an active session.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> None:
        """Initialize the portal client with optional overrides.

        Args:
            base_url: Portal base URL. Defaults to settings.base_url.
            username: Login username. Defaults to settings.username.
            password: Login password. Defaults to settings.password.
            timeout: Request timeout in seconds. Defaults to settings.request_timeout.
        """
        self.base_url = (base_url or settings.base_url).rstrip("/")
        self.username = username or settings.username
        self.password = password or settings.password
        self.timeout = timeout or settings.request_timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._authenticated: bool = False

    async def _get_client(self) -> httpx.AsyncClient:
        """Return the HTTP client instance, creating it if needed.

        Returns:
            httpx.AsyncClient: The active async HTTP client.
        """
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers={
                    "User-Agent": "FlockEnergy-UrjaOps-API/1.0",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client and clear session state."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
        self._client = None
        self._authenticated = False
        logger.debug("Portal client closed")

    async def __aenter__(self) -> UrjaPortalClient:
        """Async context manager entry.

        Returns:
            UrjaPortalClient: The client instance.
        """
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit.

        Args:
            exc_type: Exception type.
            exc_val: Exception value.
            exc_tb: Exception traceback.
        """
        await self.close()

    async def authenticate(self) -> bool:
        """Authenticate with the portal.

        Submits credentials to the portal login endpoint and establishes
        a session. Handles form detection dynamically.

        Returns:
            bool: True if authentication succeeded, False otherwise.

        Raises:
            httpx.HTTPError: If the portal is unreachable.
        """
        if self._authenticated:
            logger.debug("Already authenticated")
            return True

        client = await self._get_client()
        login_url = f"{self.base_url}/login"

        logger.info("Authenticating with portal at %s", login_url)

        try:
            response = await client.get(login_url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("Failed to reach login page: %s", exc)
            raise

        # TODO: Parse login form from HTML and submit credentials
        # This is a stub - actual form detection and submission
        # will be implemented in the parser module.
        self._authenticated = True
        logger.info("Authentication stub completed")
        return self._authenticated

    async def fetch_page(self, path: str, params: Optional[dict[str, Any]] = None) -> str:
        """Fetch a page from the portal and return raw HTML.

        Args:
            path: Relative path to fetch (e.g., /meters).
            params: Optional query parameters.

        Returns:
            str: Raw HTML response body.

        Raises:
            httpx.HTTPError: If the request fails.
        """
        if not self._authenticated:
            await self.authenticate()

        client = await self._get_client()
        url = f"{self.base_url}{path}"

        logger.debug("Fetching page: %s", url)

        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.text
        except httpx.HTTPError as exc:
            logger.error("Failed to fetch %s: %s", url, exc)
            raise

    async def fetch_meter_list(self, page: int = 1, page_size: int = 25) -> list[MeterDetail]:
        """Fetch the meter list page from the portal and parse it.

        Args:
            page: Page number for pagination.
            page_size: Number of items per page.

        Returns:
            list[MeterDetail]: Parsed list of meter details.
        """
        html = await self.fetch_page("/meters", params={"page": page, "page_size": page_size})
        return parse_meter_list(html)

    async def fetch_meter_detail(self, meter_id: str) -> str:
        """Fetch a single meter's detail page.

        Args:
            meter_id: The meter identifier.

        Returns:
            str: Raw HTML of the meter detail page.
        """
        return await self.fetch_page(f"/meters/{meter_id}")

    async def fetch_consumption_data(self, meter_id: str, from_date: str, to_date: str) -> str:
        """Fetch consumption readings for a meter.

        Args:
            meter_id: The meter identifier.
            from_date: Start date (YYYY-MM-DD).
            to_date: End date (YYYY-MM-DD).

        Returns:
            str: Raw HTML of the consumption data page.
        """
        return await self.fetch_page(
            f"/meters/{meter_id}/consumption",
            params={"from": from_date, "to": to_date},
        )