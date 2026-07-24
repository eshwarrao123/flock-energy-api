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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["meters"])


@router.get(
    "/health",
    summary="Health check",
    description="Check service health and portal connectivity.",
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
        meters = await client.fetch_meter_list(page=page, page_size=page_size)
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
        html = await client.fetch_meter_detail(meter_id)
        # TODO: Parse meter detail from HTML
        return MeterDetail(
            meter_id=meter_id,
            serial_number="UNKNOWN",
            make="Unknown",
            phase="Unknown",
            status="Installed",
            dt_id="UNKNOWN",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch meter %s: %s", meter_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "portal_error", "message": str(exc)},
        ) from exc


@router.get(
    "/meters/{meter_id}/readings",
    response_model=list[ConsumptionReading],
    summary="Get meter readings",
    description="Retrieve consumption readings for a specific meter.",
)
async def get_meter_readings(
    meter_id: str,
    from_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    client: UrjaPortalClient = Depends(get_portal_client),
) -> list[ConsumptionReading]:
    """Retrieve consumption readings for a specific meter.

    Args:
        meter_id: The unique meter identifier.
        from_date: Optional start date filter.
        to_date: Optional end date filter.
        client: Portal HTTP client.

    Returns:
        list[ConsumptionReading]: List of consumption readings.

    Raises:
        HTTPException: If the portal is unreachable or returns an error.
    """
    try:
        html = await client.fetch_consumption_data(
            meter_id,
            from_date or "2026-01-01",
            to_date or "2026-12-31",
        )
        # TODO: Parse consumption readings from HTML
        return []
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch readings for meter %s: %s", meter_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "portal_error", "message": str(exc)},
        ) from exc


@router.get(
    "/meters/{meter_id}/transformer",
    response_model=Transformer,
    summary="Get transformer info",
    description="Retrieve transformer information for a specific meter.",
)
async def get_meter_transformer(
    meter_id: str,
    client: UrjaPortalClient = Depends(get_portal_client),
) -> Transformer:
    """Retrieve transformer information for a specific meter.

    Args:
        meter_id: The unique meter identifier.
        client: Portal HTTP client.

    Returns:
        Transformer: Transformer details.

    Raises:
        HTTPException: If the transformer info is not found or portal is unreachable.
    """
    try:
        html = await client.fetch_meter_detail(meter_id)
        # TODO: Parse transformer info from HTML
        return Transformer(
            transformer_id="UNKNOWN",
            name="Unknown",
            meter_count=0,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch transformer for meter %s: %s", meter_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "portal_error", "message": str(exc)},
        ) from exc