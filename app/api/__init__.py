"""API package initialization."""

from __future__ import annotations

from app.api.v1 import router as v1_router

__all__ = ["v1_router"]