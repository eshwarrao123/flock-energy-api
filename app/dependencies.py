"""
FastAPI dependency injection for the UrjaPortalClient.

Provides request-scoped client instances that are automatically
managed via async context managers.
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator

from fastapi import Depends

from app.client import UrjaPortalClient
from app.config import settings

logger = logging.getLogger(__name__)


async def get_portal_client() -> AsyncGenerator[UrjaPortalClient, None]:
    """Provide a request-scoped UrjaPortalClient instance.

    Yields:
        UrjaPortalClient: An async client configured from environment settings.

    The client is automatically closed after the request completes,
    even if an exception occurs during processing.
    """
    client = UrjaPortalClient()
    logger.debug("Created new portal client for request")
    try:
        yield client
    finally:
        await client.close()
        logger.debug("Portal client closed after request")


async def get_authenticated_client(
    client: UrjaPortalClient = Depends(get_portal_client),
) -> AsyncGenerator[UrjaPortalClient, None]:
    """Provide an authenticated portal client.

    Args:
        client: The portal client from dependency injection.

    Yields:
        UrjaPortalClient: An authenticated client ready for requests.

    Raises:
        RuntimeError: If authentication fails.
    """
    authenticated = await client.authenticate()
    if not authenticated:
        logger.error("Failed to authenticate portal client")
        raise RuntimeError("Portal authentication failed")
    yield client