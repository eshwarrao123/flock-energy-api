"""
Async HTTP client for the Urja Meter Ops legacy portal.

Uses httpx.AsyncClient for connection pooling and session management.
Handles authentication, retries, and graceful error recovery.
All methods are async-compatible for use with FastAPI dependency injection.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class UrjaPortalClient:
    """Async HTTP client wrapping the Urja Meter Ops legacy portal.

    Manages authentication, session cookies, and HTML retrieval from the
    legacy portal. Supports async context manager usage for resource cleanup.

    Attributes:
        base_url: Portal base URL (trailing slash stripped).
        username: Portal login username.
        password: Portal login password.
        timeout: HTTP request timeout in seconds.
        _client: Internal httpx.AsyncClient instance.
        _authenticated: Whether the client has an active authenticated session.
    """

    def __init__(self, base_url: str, username: str, password: str, timeout: float = 30.0) -> None:
        """Initialize the portal client with explicit credentials.

        Args:
            base_url: Portal base URL (e.g., https://urja-ops.flockenergy.tech).
            username: Portal login username.
            password: Portal login password.
            timeout: HTTP request timeout in seconds. Defaults to 30.0.
        """
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None
        self._authenticated: bool = False

    async def _get_client(self) -> httpx.AsyncClient:
        """Return the HTTP client instance, creating it if needed or closed.

        Returns:
            httpx.AsyncClient: The active async HTTP client with session cookies.
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
            logger.debug("HTTP client closed")
        self._client = None
        self._authenticated = False

    async def __aenter__(self) -> UrjaPortalClient:
        """Async context manager entry.

        Returns:
            UrjaPortalClient: The client instance.
        """
        return self

    async def __aexit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        """Async context manager exit.

        Ensures the HTTP client is closed even if an exception occurred.

        Args:
            exc_type: Exception type, if an exception was raised.
            exc_val: Exception value, if an exception was raised.
            exc_tb: Exception traceback, if an exception was raised.
        """
        await self.close()

    async def login(self) -> bool:
        """Authenticate with the portal by POSTing credentials to /login.

        Submits username and password as form data to the portal login endpoint.
        Follows redirects and stores session cookies in the httpx client.

        Returns:
            bool: True if authentication succeeded and session is established.

        Raises:
            httpx.HTTPStatusError: If the login request fails with a non-2xx status.
            httpx.RequestError: If the portal is unreachable or times out.
        """
        if self._authenticated:
            logger.debug("Already authenticated, skipping login")
            return True

        client = await self._get_client()
        login_url = f"{self.base_url}/login"

        logger.info("Submitting login request to %s", login_url)

        try:
            response = await client.post(
                login_url,
                data={
                    "username": self.username,
                    "password": self.password,
                },
                follow_redirects=True,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error("Login failed with HTTP %d: %s", exc.response.status_code, exc)
            raise
        except httpx.RequestError as exc:
            logger.error("Login request failed: %s", exc)
            raise

        if "login" in str(response.url).lower() and response.status_code != 200:
            logger.warning("Login response still points to login page")
            return False

        self._authenticated = True
        logger.info("Login successful, session established")
        return True

    async def _ensure_auth(self) -> None:
        """Ensure the client has an active authenticated session.

        Sends a GET request to /meters to verify authentication. If the
        response is a redirect to the login page (302/303), re-authenticates
        once. If re-authentication also fails, raises an error.

        Raises:
            httpx.HTTPStatusError: If authentication fails after retry.
            httpx.RequestError: If the portal is unreachable.
        """
        if self._authenticated:
            logger.debug("Already authenticated, skipping auth check")
            return

        client = await self._get_client()
        meters_url = f"{self.base_url}/meters"

        logger.debug("Checking authentication by fetching %s", meters_url)

        try:
            response = await client.get(meters_url)
        except httpx.RequestError as exc:
            logger.error("Auth check request failed: %s", exc)
            raise

        if response.status_code == 200:
            self._authenticated = True
            logger.debug("Auth check passed (HTTP 200)")
            return

        if response.status_code in (301, 302, 303, 307, 308):
            logger.warning("Auth check redirected (HTTP %d), attempting login", response.status_code)
            login_success = await self.login()
            if login_success:
                return

        if response.status_code in (401, 403):
            logger.warning("Auth check returned %d, attempting re-authentication", response.status_code)
            self._authenticated = False
            login_success = await self.login()
            if login_success:
                return

        logger.error("Auth check failed with HTTP %d", response.status_code)
        raise httpx.HTTPStatusError(
            f"Authentication check failed with status {response.status_code}",
            request=response.request,
            response=response,
        )

    async def get_meters_html(self, page: int = 1) -> str:
        """Fetch the meter list page HTML from the portal.

        Args:
            page: Page number for pagination (1-indexed). Defaults to 1.

        Returns:
            str: Raw HTML response body of the meter list page.

        Raises:
            httpx.HTTPStatusError: If the request fails after authentication retry.
            httpx.TimeoutException: If the request times out.
            httpx.RequestError: If the portal is unreachable.
        """
        await self._ensure_auth()

        client = await self._get_client()
        url = f"{self.base_url}/meters"
        params = {"page": page}

        logger.debug("Fetching meters page %d from %s", page, url)

        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.text
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (401, 403):
                logger.warning("Got %d on meters page, re-authenticating once", exc.response.status_code)
                self._authenticated = False
                await self.login()
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.text
            logger.error("Failed to fetch meters page %d: HTTP %d", page, exc.response.status_code)
            raise
        except httpx.TimeoutException as exc:
            logger.error("Timeout fetching meters page %d after %.0fs", page, self.timeout)
            raise
        except httpx.RequestError as exc:
            logger.error("Request error fetching meters page %d: %s", page, exc)
            raise

    async def get_meter_detail_html(self, meter_id: str) -> str:
        """Fetch a single meter's detail page HTML from the portal.

        Args:
            meter_id: The unique meter identifier.

        Returns:
            str: Raw HTML response body of the meter detail page.

        Raises:
            httpx.HTTPStatusError: If the request fails after authentication retry.
            httpx.TimeoutException: If the request times out.
            httpx.RequestError: If the portal is unreachable.
        """
        await self._ensure_auth()

        client = await self._get_client()
        url = f"{self.base_url}/meters/{meter_id}"

        logger.debug("Fetching meter detail for %s from %s", meter_id, url)

        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.text
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (401, 403):
                logger.warning("Got %d on meter detail, re-authenticating once", exc.response.status_code)
                self._authenticated = False
                await self.login()
                response = await client.get(url)
                response.raise_for_status()
                return response.text
            logger.error("Failed to fetch meter detail %s: HTTP %d", meter_id, exc.response.status_code)
            raise
        except httpx.TimeoutException as exc:
            logger.error("Timeout fetching meter detail %s after %.0fs", meter_id, self.timeout)
            raise
        except httpx.RequestError as exc:
            logger.error("Request error fetching meter detail %s: %s", meter_id, exc)
            raise

    async def get_consumption_html(self, meter_id: str) -> str:
        """Fetch consumption readings HTML for a specific meter.

        Args:
            meter_id: The unique meter identifier.

        Returns:
            str: Raw HTML response body of the consumption data page.

        Raises:
            httpx.HTTPStatusError: If the request fails after authentication retry.
            httpx.TimeoutException: If the request times out.
            httpx.RequestError: If the portal is unreachable.
        """
        await self._ensure_auth()

        client = await self._get_client()
        url = f"{self.base_url}/meters/{meter_id}/consumption"

        logger.debug("Fetching consumption data for meter %s from %s", meter_id, url)

        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.text
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (401, 403):
                logger.warning("Got %d on consumption data, re-authenticating once", exc.response.status_code)
                self._authenticated = False
                await self.login()
                response = await client.get(url)
                response.raise_for_status()
                return response.text
            logger.error("Failed to fetch consumption for meter %s: HTTP %d", meter_id, exc.response.status_code)
            raise
        except httpx.TimeoutException as exc:
            logger.error("Timeout fetching consumption for meter %s after %.0fs", meter_id, self.timeout)
            raise
        except httpx.RequestError as exc:
            logger.error("Request error fetching consumption for meter %s: %s", meter_id, exc)
            raise

    async def get_transformers_html(self) -> str:
        """Fetch the transformers list page HTML from the portal.

        Returns:
            str: Raw HTML response body of the transformers page.

        Raises:
            httpx.HTTPStatusError: If the request fails after authentication retry.
            httpx.TimeoutException: If the request times out.
            httpx.RequestError: If the portal is unreachable.
        """
        await self._ensure_auth()

        client = await self._get_client()
        url = f"{self.base_url}/transformers"

        logger.debug("Fetching transformers from %s", url)

        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.text
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (401, 403):
                logger.warning("Got %d on transformers page, re-authenticating once", exc.response.status_code)
                self._authenticated = False
                await self.login()
                response = await client.get(url)
                response.raise_for_status()
                return response.text
            logger.error("Failed to fetch transformers page: HTTP %d", exc.response.status_code)
            raise
        except httpx.TimeoutException as exc:
            logger.error("Timeout fetching transformers after %.0fs", self.timeout)
            raise
        except httpx.RequestError as exc:
            logger.error("Request error fetching transformers page: %s", exc)
            raise
