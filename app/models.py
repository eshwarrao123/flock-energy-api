"""
Pydantic v2 data models for the Urja Meter Ops API.

All models include Field descriptions and JSON schema examples for
OpenAPI documentation and validation.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Annotated, Optional

from pydantic import BaseModel, Field, field_validator


class MeterStatus(str, Enum):
    """Operational status of a meter."""

    INSTALLED = "Installed"
    FAULTY = "Faulty"
    DECOMMISSIONED = "Decommissioned"


class MeterBase(BaseModel):
    """Base model for meter data with common fields.

    Attributes:
        meter_id: Unique identifier for the meter.
        serial_number: Manufacturer serial number.
        make: Meter manufacturer name.
        phase: Phase configuration (e.g., Single, Three).
        status: Current operational status of the meter.
        dt_id: Distribution transformer identifier.
    """

    model_config = {
        "json_schema_extra": {
            "example": {
                "meter_id": "J100001",
                "serial_number": "SN-2024-001",
                "make": "Electra",
                "phase": "Three",
                "status": "Installed",
                "dt_id": "DT-5001",
            }
        }
    }

    meter_id: str = Field(..., description="Unique identifier for the meter")
    serial_number: str = Field(..., description="Manufacturer serial number")
    make: str = Field(..., description="Meter manufacturer name")
    phase: str = Field(..., description="Phase configuration (e.g., Single, Three)")
    status: MeterStatus = Field(..., description="Current operational status of the meter")
    dt_id: str = Field(..., description="Distribution transformer identifier")


class MeterDetail(MeterBase):
    """Detailed meter information including location and readings.

    Attributes:
        location: Physical location or address of the meter installation.
        installation_date: Date when the meter was installed.
        last_reading: Most recent meter reading value.
        last_reading_at: Timestamp of the most recent reading.
    """

    model_config = {
        "json_schema_extra": {
            "example": {
                "meter_id": "J100001",
                "serial_number": "SN-2024-001",
                "make": "Electra",
                "phase": "Three",
                "status": "Installed",
                "dt_id": "DT-5001",
                "location": "Sector 12, Plot 45",
                "installation_date": "2024-03-15",
                "last_reading": 12450.5,
                "last_reading_at": "2026-07-23T10:30:00",
            }
        }
    }

    location: Optional[str] = Field(None, description="Meter installation location")
    installation_date: Optional[date] = Field(None, description="Date when the meter was installed")
    last_reading: Optional[float] = Field(None, description="Most recent meter reading value")
    last_reading_at: Optional[datetime] = Field(None, description="Timestamp of the most recent reading")


    @field_validator("last_reading")
    @classmethod
    def last_reading_must_be_non_negative(cls, v: Optional[float]) -> Optional[float]:
        """Ensure last_reading is non-negative.

        Args:
            v: The reading value to validate.

        Returns:
            The validated reading value.

        Raises:
            ValueError: If the reading value is negative.
        """
        if v is not None and v < 0:
            raise ValueError("Reading value must be non-negative")
        return v

    @classmethod
    def from_base(cls, base: MeterBase) -> MeterDetail:
        """Create a MeterDetail from a MeterBase instance.

        Args:
            base: Base meter model to convert.

        Returns:
            MeterDetail with fields populated from the base model.
        """
        return MeterDetail(
            meter_id=base.meter_id,
            serial_number=base.serial_number,
            make=base.make,
            phase=base.phase,
            status=base.status,
            dt_id=base.dt_id,
        )


class ConsumptionReading(BaseModel):
    """Model for a single consumption reading entry.

    Attributes:
        timestamp: Date and time when the reading was recorded.
        kwh_import: Imported energy in kilowatt-hours.
        kwh_export: Exported energy in kilowatt-hours (optional).
        kvah: Apparent energy in kilovolt-ampere-hours (optional).
    """

    model_config = {
        "json_schema_extra": {
            "example": {
                "timestamp": "2026-07-23T10:30:00",
                "kwh_import": 12450.5,
                "kwh_export": 500.0,
                "kvah": 13000.0,
            }
        }
    }

    timestamp: datetime = Field(..., description="Date and time when the reading was recorded")
    kwh_import: float = Field(..., description="Imported energy in kilowatt-hours")
    kwh_export: Optional[float] = Field(None, description="Exported energy in kilowatt-hours")
    kvah: Optional[float] = Field(None, description="Apparent energy in kilovolt-ampere-hours")

    @field_validator("kwh_import")
    @classmethod
    def kwh_import_must_be_non_negative(cls, v: float) -> float:
        """Ensure kwh_import is non-negative.

        Args:
            v: The kwh_import value to validate.

        Returns:
            The validated value.

        Raises:
            ValueError: If the value is negative.
        """
        if v < 0:
            raise ValueError("kwh_import must be non-negative")
        return v


class Transformer(BaseModel):
    """Model for transformer data associated with meters.

    Attributes:
        transformer_id: Unique identifier for the transformer.
        name: Human-readable name of the transformer.
        capacity_kva: Rated capacity in kilovolt-amperes.
        meter_count: Number of meters served by this transformer.
    """

    model_config = {
        "json_schema_extra": {
            "example": {
                "transformer_id": "XFMR-2001",
                "name": "TFR-SECTOR-12",
                "capacity_kva": 500.0,
                "meter_count": 25,
            }
        }
    }

    transformer_id: str = Field(..., description="Unique transformer identifier")
    name: str = Field(..., description="Human-readable name of the transformer")
    capacity_kva: Optional[float] = Field(None, description="Rated capacity in kilovolt-amperes")
    meter_count: int = Field(..., description="Number of meters served by this transformer")

    @field_validator("meter_count")
    @classmethod
    def meter_count_must_be_positive(cls, v: int) -> int:
        """Ensure meter_count is positive.

        Args:
            v: The meter_count value to validate.

        Returns:
            The validated value.

        Raises:
            ValueError: If the value is not positive.
        """
        if v <= 0:
            raise ValueError("meter_count must be positive")
        return v


class PaginatedMeters(BaseModel):
    """Paginated response model for meter list endpoints.

    Attributes:
        items: List of meter base objects for the current page.
        total: Total number of meters matching the query.
        page: Current page number (1-indexed).
        page_size: Number of items per page.
    """

    model_config = {
        "json_schema_extra": {
            "example": {
                "items": [
                    {
                        "meter_id": "J100001",
                        "serial_number": "SN-2024-001",
                        "make": "Electra",
                        "phase": "Three",
                        "status": "Installed",
                        "dt_id": "DT-5001",
                    }
                ],
                "total": 150,
                "page": 1,
                "page_size": 25,
            }
        }
    }

    items: list[MeterBase] = Field(..., description="List of meter base objects for the current page")
    total: int = Field(..., description="Total number of meters matching the query")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of items per page")