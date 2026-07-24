"""API v1 router for Urja Meter Ops endpoints."""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.client import UrjaPortalClient
from app.dependencies import get_portal_client
from app.models import (
    ConsumptionReading,
    MeterBase,
    MeterDetail,
    PaginatedMeters,
    Transformer,
)
from app.parser import (
    parse_meters_list,
    parse_meter_detail,
    parse_consumption,
    parse_transformers,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["meters"])


@router.get(
    "/health",
    summary="Health check",
    description="Check service health and portal connectivity.",
    responses={
        200: {
            "description": "Service is healthy",
            "content": {"application/json": {"example": {"status": "healthy", "version": "1.0.0", "portal_reachable": False}}},
        },
    },
)
async def health_check() -> dict[str, Any]:
    """Return service health status.

    Returns:
        dict[str, Any]: Health status with portal reachability.
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "portal_reachable": False,
    }


@router.get(
    "/meters",
    response_model=PaginatedMeters,
    summary="List meters",
    description="Retrieve a paginated list of meters from the portal.",
    responses={
        200: {
            "description": "Paginated list of meters",
            "content": {"application/json": {"example": {"total": 150, "page": 1, "page_size": 25, "items": []}}},
        },
        502: {
            "description": "Portal unreachable",
            "content": {"application/json": {"example": {"error": "portal_error", "message": "Connection refused"}}},
        },
    },
)
async def list_meters(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(25, ge=1, le=1000, description="Items per page"),
    client: UrjaPortalClient = Depends(get_portal_client),
) -> PaginatedMeters:
    """Retrieve a paginated list of meters.

    Args:
        page: Page number (1-indexed).
        page_size: Number of items per page.
        client: Portal HTTP client.

    Returns:
        PaginatedMeters: Paginated meter list response.

    Raises:
        HTTPException: If the portal is unreachable or returns an error.
    """
    try:
        html = await client.get_meters_html(page=page)
        meters = parse_meters_list(html)
        total = len(meters)

        start = (page - 1) * page_size
        end = start + page_size
        page_items = meters[start:end]

        return PaginatedMeters(
            total=total,
            page=page,
            page_size=page_size,
            items=page_items,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch meter list: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "portal_error", "message": str(exc)},
        ) from exc


@router.get(
    "/meters/{meter_id}",
    response_model=MeterDetail,
    summary="Get meter details",
    description="Retrieve detailed information for a specific meter.",
    responses={
        200: {
            "description": "Meter detail information",
        },
        404: {
            "description": "Meter not found",
        },
        502: {
            "description": "Portal unreachable",
        },
    },
)
async def get_meter(
    meter_id: str,
    client: UrjaPortalClient = Depends(get_portal_client),
) -> MeterDetail:
    """Retrieve detailed information for a specific meter.

    Args:
        meter_id: The unique meter identifier.
        client: Portal HTTP client.

    Returns:
        MeterDetail: Detailed meter information.

    Raises:
        HTTPException: If the meter is not found or portal is unreachable.
    """
    try:
        html = await client.get_meter_detail_html(meter_id)
        return parse_meter_detail(html, meter_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch meter %s: %s", meter_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "portal_error", "message": str(exc)},
        ) from exc


@router.get(
    "/meters/{meter_id}/consumption",
    response_model=list[ConsumptionReading],
    summary="Get meter consumption",
    description="Retrieve consumption readings for a specific meter.",
    responses={
        200: {
            "description": "List of consumption readings",
        },
        502: {
            "description": "Portal unreachable",
        },
    },
)
async def get_meter_consumption(
    meter_id: str,
    client: UrjaPortalClient = Depends(get_portal_client),
) -> list[ConsumptionReading]:
    """Retrieve consumption readings for a specific meter.

    Args:
        meter_id: The unique meter identifier.
        client: Portal HTTP client.

    Returns:
        list[ConsumptionReading]: List of consumption readings.

    Raises:
        HTTPException: If the portal is unreachable or returns an error.
    """
    try:
        html = await client.get_consumption_html(meter_id)
        return parse_consumption(html)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch consumption for meter %s: %s", meter_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "portal_error", "message": str(exc)},
        ) from exc


@router.get(
    "/transformers",
    response_model=list[Transformer],
    summary="List transformers",
    description="Retrieve all transformers from the portal.",
    responses={
        200: {
            "description": "List of transformers",
        },
        502: {
            "description": "Portal unreachable",
        },
    },
)
async def list_transformers(
    client: UrjaPortalClient = Depends(get_portal_client),
) -> list[Transformer]:
    """Retrieve all transformers from the portal.

    Args:
        client: Portal HTTP client.

    Returns:
        list[Transformer]: List of transformer objects.

    Raises:
        HTTPException: If the portal is unreachable or returns an error.
    """
    try:
        html = await client.get_transformers_html()
        return parse_transformers(html)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch transformers: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "portal_error", "message": str(exc)},
        ) from exc


@router.get(
    "/hierarchy",
    response_model=list[Transformer],
    summary="Get meter hierarchy",
    description="Retrieve the transformer-to-meter hierarchy from the portal.",
    responses={
        200: {
            "description": "Hierarchy of transformers and their meters",
        },
        502: {
            "description": "Portal unreachable",
        },
    },
)
async def get_hierarchy(
    client: UrjaPortalClient = Depends(get_portal_client),
) -> list[Transformer]:
    """Retrieve the transformer-to-meter hierarchy.

    Args:
        client: Portal HTTP client.

    Returns:
        list[Transformer]: List of transformers with associated meters.

    Raises:
        HTTPException: If the portal is unreachable or returns an error.
    """
    try:
        html = await client.get_transformers_html()
        transformers = parse_transformers(html)
        return transformers
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch hierarchy: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "portal_error", "message": str(exc)},
        ) from exc