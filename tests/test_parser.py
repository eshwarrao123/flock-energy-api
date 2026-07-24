"""Tests for BeautifulSoup parser functions."""

from __future__ import annotations

import pytest
from bs4 import BeautifulSoup

from app.parser import (
    normalize_key,
    parse_html_table,
    parse_meters_list,
    parse_meter_detail,
    parse_consumption,
    parse_transformers,
)

HTML_METERS_TABLE = """
<html>
<body>
<table>
<tr><th>METER</th><th>SERIAL</th><th>MAKE</th><th>PHASE</th><th>STATUS</th><th>DT</th></tr>
<tr><td>J100001</td><td>SN-2024-001</td><td>Electra</td><td>Three</td><td>Installed</td><td>DT-5001</td></tr>
<tr><td>J100002</td><td>SN-2024-002</td><td>Siemens</td><td>Single</td><td>Faulty</td><td>DT-5002</td></tr>
</table>
</body>
</html>
"""

HTML_NO_TABLE = "<html><body><p>No data</p></body></html>"

HTML_METER_DETAIL = """
<html>
<body>
<table>
<tr><td>Location</td><td>Sector 12, Plot 45</td></tr>
<tr><td>Installation Date</td><td>2024-03-15</td></tr>
<tr><td>Last Reading</td><td>12450.5</td></tr>
<tr><td>Last Reading At</td><td>2026-07-23T10:30:00</td></tr>
</table>
</body>
</html>
"""

HTML_CONSUMPTION = """
<html>
<body>
<table>
<tr><th>Timestamp</th><th>kwh_import</th><th>kwh_export</th><th>kvah</th></tr>
<tr><td>2026-07-23T10:30:00</td><td>12450.5</td><td>500.0</td><td>13000.0</td></tr>
<tr><td>2026-07-22T10:30:00</td><td>12000.0</td><td>450.0</td><td>12500.0</td></tr>
</table>
</body>
</html>
"""

HTML_TRANSFORMERS = """
<html>
<body>
<table>
<tr><th>Transformer ID</th><th>Name</th><th>Capacity (kVA)</th><th>Meter Count</th></tr>
<tr><td>XFMR-2001</td><td>TFR-SECTOR-12</td><td>500</td><td>25</td></tr>
<tr><td>XFMR-2002</td><td>TFR-SECTOR-13</td><td>250</td><td>10</td></tr>
</table>
</body>
</html>
"""


class TestNormalizeKey:
    """Tests for normalize_key function."""

    def test_simple_header(self) -> None:
        """Test normalizing a simple header."""
        assert normalize_key("METER") == "meter"

    def test_special_characters(self) -> None:
        """Test normalizing headers with special characters."""
        assert normalize_key("Capacity (kVA)") == "capacity_kva"
        assert normalize_key("Meter Count") == "meter_count"

    def test_leading_trailing_spaces(self) -> None:
        """Test normalizing headers with extra whitespace."""
        assert normalize_key("  Status  ") == "status"


class TestParseHtmlTable:
    """Tests for parse_html_table function."""

    def test_basic_table(self) -> None:
        """Test parsing a basic HTML table."""
        rows = parse_html_table(HTML_METERS_TABLE, table_index=0)
        assert len(rows) == 2
        assert rows[0]["meter"] == "J100001"
        assert rows[0]["serial"] == "SN-2024-001"
        assert rows[0]["make"] == "Electra"
        assert rows[0]["status"] == "Installed"

    def test_no_table(self) -> None:
        """Test parsing when no table is present."""
        rows = parse_html_table(HTML_NO_TABLE, table_index=0)
        assert rows == []

    def test_out_of_range_index(self) -> None:
        """Test parsing with out-of-range table index."""
        rows = parse_html_table(HTML_METERS_TABLE, table_index=99)
        assert rows == []

    def test_empty_table(self) -> None:
        """Test parsing an empty table."""
        rows = parse_html_table("<html><body><table></table></body></html>")
        assert rows == []


class TestParseMetersList:
    """Tests for parse_meters_list function."""

    def test_parse_valid_meters_list(self) -> None:
        """Test parsing a valid meters list HTML."""
        meters = parse_meters_list(HTML_METERS_TABLE)
        assert len(meters) == 2
        assert meters[0].meter_id == "J100001"
        assert meters[0].serial_number == "SN-2024-001"
        assert meters[0].make == "Electra"
        assert meters[0].phase == "Three"
        assert meters[0].status.value == "Installed"
        assert meters[0].dt_id == "DT-5001"

    def test_parse_empty_meters_list(self) -> None:
        """Test parsing HTML with no table."""
        meters = parse_meters_list(HTML_NO_TABLE)
        assert meters == []

    def test_parse_meters_list_with_malformed_row(self) -> None:
        """Test parsing gracefully skips malformed rows."""
        html = "<html><body><table><tr><th>METER</th></tr><tr><td></td></tr></table></body></html>"
        meters = parse_meters_list(html)
        assert isinstance(meters, list)


class TestParseMeterDetail:
    """Tests for parse_meter_detail function."""

    def test_parse_valid_meter_detail(self) -> None:
        """Test parsing a valid meter detail HTML."""
        detail = parse_meter_detail(HTML_METER_DETAIL, "J100001")
        assert detail.meter_id == "J100001"
        assert detail.location == "Sector 12, Plot 45"
        assert detail.last_reading == 12450.5

    def test_parse_meter_detail_with_missing_data(self) -> None:
        """Test parsing meter detail with missing fields."""
        html = "<html><body><p>No detail data</p></body></html>"
        detail = parse_meter_detail(html, "J100001")
        assert detail.meter_id == "J100001"
        assert detail.location is None
        assert detail.last_reading is None


class TestParseConsumption:
    """Tests for parse_consumption function."""

    def test_parse_valid_consumption(self) -> None:
        """Test parsing a valid consumption table."""
        readings = parse_consumption(HTML_CONSUMPTION)
        assert len(readings) == 2
        assert readings[0].kwh_import == 12450.5
        assert readings[0].kwh_export == 500.0
        assert readings[0].kvah == 13000.0

    def test_parse_empty_consumption(self) -> None:
        """Test parsing HTML with no table."""
        readings = parse_consumption(HTML_NO_TABLE)
        assert readings == []


class TestParseTransformers:
    """Tests for parse_transformers function."""

    def test_parse_valid_transformers(self) -> None:
        """Test parsing a valid transformers table."""
        transformers = parse_transformers(HTML_TRANSFORMERS)
        assert len(transformers) == 2
        assert transformers[0].transformer_id == "XFMR-2001"
        assert transformers[0].name == "TFR-SECTOR-12"
        assert transformers[0].capacity_kva == 500.0
        assert transformers[0].meter_count == 25

    def test_parse_empty_transformers(self) -> None:
        """Test parsing HTML with no table."""
        transformers = parse_transformers(HTML_NO_TABLE)
        assert transformers == []