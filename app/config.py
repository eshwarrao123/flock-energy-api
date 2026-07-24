"""
Application configuration using os.getenv with defaults.

All portal credentials and connection settings are loaded from environment
variables with sensible fallback defaults for local development.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def _get_env(key: str, default: str = "") -> str:
    """Retrieve an environment variable with logging.

    Args:
        key: Environment variable name.
        default: Fallback value if the variable is not set.

    Returns:
        The environment variable value or the default.
    """
    value = os.getenv(key, default)
    if not value and default:
        logger.warning("Environment variable %s is not set; using default", key)
    return value


def _get_env_secret(key: str, default: str = "") -> str:
    """Retrieve a secret environment variable, masking its value in logs.

    Args:
        key: Environment variable name.
        default: Fallback value if the variable is not set.

    Returns:
        The environment variable value or the default.
    """
    value = os.getenv(key, default)
    if value:
        logger.debug("Secret %s loaded successfully", key)
    else:
        logger.warning("Secret environment variable %s is not set", key)
    return value


class Settings:
    """Application settings loaded from environment variables.

    Attributes:
        base_url: Base URL of the Urja Meter Ops portal.
        username: Portal login username.
        password: Portal login password.
        request_timeout: HTTP request timeout in seconds.
    """

    base_url: str = _get_env("PORTAL_BASE_URL", "https://urja-ops.flockenergy.tech")
    username: str = _get_env("PORTAL_USERNAME", "")
    password: str = _get_env_secret("PORTAL_PASSWORD", "")
    request_timeout: int = int(_get_env("REQUEST_TIMEOUT", "30"))

    def __repr__(self) -> str:
        """Return a string representation of the settings (masking secrets).

        Returns:
            str: String representation with sensitive values redacted.
        """
        return (
            f"Settings(base_url={self.base_url!r}, "
            f"username={self.username!r}, "
            f"password='***', "
            f"request_timeout={self.request_timeout!r})"
        )


settings = Settings()

logger.info("Settings loaded: %s", settings)