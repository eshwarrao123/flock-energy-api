"""Tests for Pydantic data models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models import (
    ConsumptionReading,
    MeterBase,
    MeterDetail,
    MeterStatus,
    PaginatedMeters,
    Transformer,
)


class TestMeterBase:
    """Tests for MeterBase model."""

    def test_valid_meter_base(self) -> None:
        """Test creating a valid MeterBase instance."""
        meter = MeterBase(
            meter_id="J100001",
            serial_number="SN-2024-001",
            make="Electra",
            phase="Three",
            status=MeterStatus.INSTALLED,
            dt_id="DT-5001",
        )
        assert meter.meter_id == "J100001"
        assert meter.status == MeterStatus.INSTALLED

    def test_meter_base_with_string_status(self) -> None:
        """Test MeterBase accepts string status values."""
        meter = MeterBase(
            meter_id="J100002",
            serial_number="SN-2024-002",
            make="Siemens",
            phase="Single",
            status="Faulty",
            dt_id="DT-5002",
        )
        assert meter.status == MeterStatus.FAULTY

    def test_meter_base_missing_required(self) -> None:
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError):
            MeterBase(serial_number="SN-2024-001")

    def test_meter_base_json_schema_example(self) -> None:
        """Test that MeterBase has a JSON schema example."""
        schema = MeterBase.model_json_schema()
        assert "example" in schema


class TestMeterDetail:
    """Tests for MeterDetail model."""

    def test_valid_meter_detail(self) -> None:
        """Test creating a valid MeterDetail instance."""
        detail = MeterDetail(
            meter_id="J100001",
            serial_number="SN-2024-001",
            make="Electra",
            phase="Three",
            status=MeterStatus.INSTALLED,
            dt_id="DT-5001",
            location="Sector 12, Plot 45",
            installation_date="2024-03-15",
            last_reading=12450.5,
            last_reading_at="2026-07-23T10:30:00",
        )
        assert detail.last_reading == 12450.5
        assert detail.location == "Sector 12, Plot 45"

    def test_meter_detail_optional_fields_default_to_none(self) -> None:
        """Test that optional fields default to None."""
        detail = MeterDetail(
            meter_id="J100001",
            serial_number="SN-2024-001",
            make="Electra",
            phase="Three",
            status=MeterStatus.INSTALLED,
            dt_id="DT-5001",
        )
        assert detail.location is None
        assert detail.installation_date is None
        assert detail.last_reading is None
        assert detail.last_reading_at is None

    def test_meter_detail_from_base(self) -> None:
        """Test creating MeterDetail from MeterBase."""
        base = MeterBase(
            meter_id="J100001",
            serial_number="SN-2024-001",
            make="Electra",
            phase="Three",
            status=MeterStatus.INSTALLED,
            dt_id="DT-5001",
        )
        detail = MeterDetail.from_base(base)
        assert detail.meter_id == base.meter_id
        assert detail.serial_number == base.serial_number

    def test_meter_detail_negative_reading_raises(self) -> None:
        """Test that negative last_reading is rejected."""
        with pytest.raises(ValidationError):
            MeterDetail(
                meter_id="J100001",
                serial_number="SN-2024-001",
                make="Electra",
                phase="Three",
                status=MeterStatus.INSTALLED,
                dt_id="DT-5001",
                last_reading=-100.0,
            )


class TestConsumptionReading:
    """Tests for ConsumptionReading model."""

    def test_valid_reading(self) -> None:
        """Test creating a valid ConsumptionReading instance."""
        reading = ConsumptionReading(
            timestamp="2026-07-23T10:30:00",
            kwh_import=12450.5,
        )
        assert reading.kwh_import == 12450.5
        assert reading.kwh_export is None
        assert reading.kvah is None

    def test_reading_with_optional_fields(self) -> None:
        """Test ConsumptionReading with all optional fields."""
        reading = ConsumptionReading(
            timestamp="2026-07-23T10:30:00",
            kwh_import=12450.5,
            kwh_export=500.0,
            kvah=13000.0,
        )
        assert reading.kwh_export == 500.0
        assert reading.kvah == 13000.0

    def test_reading_negative_import_raises(self) -> None:
        """Test that negative kwh_import is rejected."""
        with pytest.raises(ValidationError):
            ConsumptionReading(
                timestamp="2026-07-23T10:30:00",
                kwh_import=-1.0,
            )


class TestTransformer:
    """Tests for Transformer model."""

    def test_valid_transformer(self) -> None:
        """Test creating a valid Transformer instance."""
        xfmr = Transformer(
            transformer_id="XFMR-2001",
            name="TFR-SECTOR-12",
            capacity_kva=500.0,
            meter_count=25,
        )
        assert xfmr.capacity_kva == 500.0
        assert xfmr.meter_count == 25

    def test_transformer_optional_capacity(self) -> None:
        """Test Transformer with no capacity."""
        xfmr = Transformer(
            transformer_id="XFMR-2002",
            name="TFR-SECTOR-13",
            meter_count=10,
        )
        assert xfmr.capacity_kva is None

    def test_transformer_zero_count_raises(self) -> None:
        """Test that zero meter_count is rejected."""
        with pytest.raises(ValidationError):
            Transformer(
                transformer_id="XFMR-2001",
                name="TFR-SECTOR-12",
                meter_count=0,
            )


class TestPaginatedMeters:
    """Tests for PaginatedMeters model."""

    def test_valid_pagination(self) -> None:
        """Test creating a valid PaginatedMeters instance."""
        pagination = PaginatedMeters(
            items=[],
            total=150,
            page=1,
            page_size=25,
        )
        assert pagination.total == 150

    def test_pagination_with_items(self) -> None:
        """Test PaginatedMeters with actual meter items."""
        meter = MeterBase(
            meter_id="J100001",
            serial_number="SN-2024-001",
            make="Electra",
            phase="Three",
            status=MeterStatus.INSTALLED,
            dt_id="DT-5001",
        )
        pagination = PaginatedMeters(
            items=[meter],
            total=1,
            page=1,
            page_size=25,
        )
        assert len(pagination.items) == 1
        assert pagination.items[0].meter_id == "J100001"