"""Tests for BeautifulSoup parser functions."""

from __future__ import annotations

import pytest
from bs4 import BeautifulSoup

from app.parser import (
    normalize_key,
    parse_html_table,
    parse_meter_list,
    parse_consumption_table,
    parse_transformer_info,
)

HTML_TABLE = """
<html>
<body>
<table>
<tr><th>Meter ID</th><th>Serial Number</th><th>Make</th><th>Phase</th><th>Status</th><th>DT ID</th></tr>
<tr><td>J100001</td><td>SN-2024-001</td><td>Electra</td><td>Three</td><td>Installed</td><td>DT-5001</td></tr>
<tr><td>J100002</td><td>SN-2024-002</td><td>Siemens</td><td>Single</td><td>Faulty</td><td>DT-5002</td></tr>
</table>
</body>
</html>
"""

HTML_NO_TABLE = "<html><body><p>No data</p></body></html>"

HTML_TRANSFORMER = """
<html>
<body>
<table>
<tr><td>Transformer ID</td><td>XFMR-2001</td></tr>
<tr><td>Name</td><td>TFR-SECTOR-12</td></tr>
<tr><td>Capacity (kVA)</td><td>500</td></tr>
<tr><td>Meter Count</td><td>25</td></tr>
</table>
</body>
</html>
"""


class TestNormalizeKey:
    """Tests for normalize_key function."""

    def test_simple_header(self) -> None:
        """Test normalizing a simple header."""
        assert normalize_key("Meter ID") == "meter_id"

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
        rows = parse_html_table(HTML_TABLE, table_index=0)
        assert len(rows) == 2
        assert rows[0]["meter_id"] == "J100001"
        assert rows[0]["serial_number"] == "SN-2024-001"
        assert rows[0]["make"] == "Electra"
        assert rows[0]["status"] == "Installed"

    def test_no_table(self) -> None:
        """Test parsing when no table is present."""
        rows = parse_html_table(HTML_NO_TABLE, table_index=0)
        assert rows == []

    def test_out_of_range_index(self) -> None:
        """Test parsing with out-of-range table index."""
        rows = parse_html_table(HTML_TABLE, table_index=99)
        assert rows == []

    def test_empty_table(self) -> None:
        """Test parsing an empty table."""
        rows = parse_html_table("<html><body><table></table></body></html>")
        assert rows == []


class TestParseMeterList:
    """Tests for parse_meter_list function."""

    def test_parse_valid_meter_list(self) -> None:
        """Test parsing a valid meter list HTML."""
        meters = parse_meter_list(HTML_TABLE)
        assert len(meters) == 2
        assert meters[0].meter_id == "J100001"
        assert meters[0].serial_number == "SN-2024-001"
        assert meters[0].make == "Electra"
        assert meters[0].phase == "Three"
        assert meters[0].status.value == "Installed"
        assert meters[0].dt_id == "DT-5001"

    def test_parse_empty_meter_list(self) -> None:
        """Test parsing HTML with no table."""
        meters = parse_meter_list(HTML_NO_TABLE)
        assert meters == []


class TestParseConsumptionTable:
    """Tests for parse_consumption_table function."""

    def test_parse_valid_consumption(self) -> None:
        """Test parsing a valid consumption table."""
        html = """
        <html><body>
        <table>
        <tr><th>Timestamp</th><th>kwh_import</th><th>kwh_export</th><th>kvah</th></tr>
        <tr><td>2026-07-23T10:30:00</td><td>12450.5</td><td>500.0</td><td>13000.0</td></tr>
        </table>
        </body></html>
        """
        readings = parse_consumption_table(html)
        assert len(readings) == 1
        assert readings[0].timestamp.year == 2026
        assert readings[0].kwh_import == 12450.5
        assert readings[0].kwh_export == 500.0
        assert readings[0].kvah == 13000.0

    def test_parse_empty_consumption(self) -> None:
        """Test parsing HTML with no table."""
        readings = parse_consumption_table(HTML_NO_TABLE)
        assert readings == []


class TestParseTransformerInfo:
    """Tests for parse_transformer_info function."""

    def test_parse_valid_transformer(self) -> None:
        """Test parsing valid transformer HTML."""
        xfmr = parse_transformer_info(HTML_TRANSFORMER)
        assert xfmr is not None
        assert xfmr.transformer_id == "XFMR-2001"
        assert xfmr.name == "TFR-SECTOR-12"
        assert xfmr.capacity_kva == 500.0
        assert xfmr.meter_count == 25

    def test_parse_no_transformer_data(self) -> None:
        """Test parsing HTML with no transformer data."""
        xfmr = parse_transformer_info(HTML_NO_TABLE)
        assert xfmr is None