"""
FastAPI application entry point for the Urja Meter Ops API.

Wraps the legacy Urja Meter Ops portal with a production-grade
REST API layer using FastAPI, Pydantic v2, and async httpx.
"""

from __future__ import annotations

import logging
import sys

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette import status

from app import __version__
from app.api.v1 import router as v1_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Flock Energy - Urja Meter Ops API",
    description="Production-grade FastAPI service wrapping the legacy Urja Meter Ops portal.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTP exceptions and return standardized JSON error responses.

    Args:
        request: The incoming request.
        exc: The HTTP exception raised.

    Returns:
        JSONResponse: Standardized error response with error details.
    """
    logger.error("HTTP %d on %s: %s", exc.status_code, request.url.path, exc.detail)
    if isinstance(exc.detail, dict):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": f"http_{exc.status_code}",
            "message": str(exc.detail),
            "details": None,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors with structured error details.

    Args:
        request: The incoming request.
        exc: The validation error.

    Returns:
        JSONResponse: Standardized validation error response.
    """
    logger.error("Validation error on %s: %s", request.url.path, exc.errors())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "validation_error",
            "message": "Request validation failed",
            "details": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unexpected exceptions.

    Args:
        request: The incoming request.
        exc: The unhandled exception.

    Returns:
        JSONResponse: Standardized internal server error response.
    """
    logger.exception("Unhandled exception on %s", request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "details": str(exc) if app.debug else None,
        },
    )


app.include_router(v1_router)


@app.get("/", tags=["root"], summary="Root endpoint")
async def root() -> dict[str, str]:
    """Return service metadata and API documentation link.

    Returns:
        dict[str, str]: Welcome message, version, and docs URL.
    """
    return {
        "service": "Flock Energy - Urja Meter Ops API",
        "version": __version__,
        "docs": "/docs",
        "openapi": "/openapi.json",
    }