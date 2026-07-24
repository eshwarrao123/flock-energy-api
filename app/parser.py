"""
BeautifulSoup HTML parser functions for the Urja Meter Ops portal.

Provides functions to extract structured data from the legacy portal's
HTML tables and forms. All functions are designed to be resilient to
format variations in the portal's HTML output.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from bs4 import BeautifulSoup, Tag

from app.models import MeterBase, ConsumptionReading, Transformer, MeterStatus

logger = logging.getLogger(__name__)


def parse_html_table(html_content: str, table_index: int = 0) -> list[dict[str, str]]:
    """Parse an HTML table into a list of row dictionaries.

    Extracts headers from the first row (th or td elements) and maps
    each subsequent row to a dictionary with lowercase, underscore-separated
    keys.

    Args:
        html_content: Raw HTML string containing tables.
        table_index: Index of the table to parse (default: 0).

    Returns:
        list[dict[str, str]]: List of row dictionaries with normalized keys.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    tables = soup.find_all("table")

    if not tables:
        logger.warning("No tables found in HTML content")
        return []

    if table_index >= len(tables):
        logger.warning("Table index %d out of range (found %d tables)", table_index, len(tables))
        return []

    table = tables[table_index]
    rows = table.find_all("tr")
    if not rows:
        return []

    header_cells = rows[0].find_all(["th", "td"])
    headers = [normalize_key(cell.get_text(strip=True)) for cell in header_cells]

    data: list[dict[str, str]] = []
    for row in rows[1:]:
        cells = row.find_all(["td", "th"])
        if not cells:
            continue
        row_dict: dict[str, str] = {}
        for i, cell in enumerate(cells):
            if i < len(headers):
                row_dict[headers[i]] = cell.get_text(strip=True)
        if row_dict:
            data.append(row_dict)

    logger.debug("Parsed %d rows from table at index %d", len(data), table_index)
    return data


def normalize_key(key: str) -> str:
    """Normalize a table header string to a snake_case key.

    Converts spaces, hyphens, and special characters to underscores,
    collapses multiple underscores, lowercases the result, and strips
    leading/trailing underscores.

    Args:
        key: Raw header text from an HTML table.

    Returns:
        str: Normalized snake_case key.
    """
    normalized = re.sub(r"[^a-zA-Z0-9]", "_", key)
    normalized = re.sub(r"_+", "_", normalized)
    return normalized.strip("_").lower()


def parse_meter_list(html_content: str) -> list[MeterBase]:
    """Parse a meter list HTML table into MeterBase objects.

    Args:
        html_content: Raw HTML containing a meter list table.

    Returns:
        list[MeterBase]: List of parsed meter base objects.
    """
    rows = parse_html_table(html_content, table_index=0)
    meters: list[MeterBase] = []

    for row in rows:
        try:
            meter = _row_to_meter_base(row)
            meters.append(meter)
        except (KeyError, ValueError) as exc:
            logger.warning("Skipping invalid meter row: %s", exc)
            continue

    logger.debug("Parsed %d meters from HTML", len(meters))
    return meters


def parse_consumption_table(html_content: str) -> list[ConsumptionReading]:
    """Parse a consumption readings HTML table into ConsumptionReading objects.

    Args:
        html_content: Raw HTML containing a consumption table.

    Returns:
        list[ConsumptionReading]: List of parsed consumption reading objects.
    """
    rows = parse_html_table(html_content, table_index=0)
    readings: list[ConsumptionReading] = []

    for row in rows:
        try:
            reading = _row_to_consumption_reading(row)
            readings.append(reading)
        except (KeyError, ValueError) as exc:
            logger.warning("Skipping invalid consumption row: %s", exc)
            continue

    logger.debug("Parsed %d consumption readings from HTML", len(readings))
    return readings


def parse_transformer_info(html_content: str) -> Optional[Transformer]:
    """Parse transformer information from an HTML page.

    Args:
        html_content: Raw HTML containing transformer details.

    Returns:
        Optional[Transformer]: Parsed transformer object, or None if not found.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    transformer_data: dict[str, Any] = {}

    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) >= 2:
                key = normalize_key(cells[0].get_text(strip=True))
                value = cells[1].get_text(strip=True)
                transformer_data[key] = value

    if not transformer_data:
        logger.debug("No transformer data found in HTML")
        return None

    try:
        transformer = Transformer(
            transformer_id=transformer_data.get("transformer_id", "UNKNOWN"),
            name=transformer_data.get("name", transformer_data.get("transformer_name", "Unknown")),
            capacity_kva=float(transformer_data["capacity_kva"]) if transformer_data.get("capacity_kva") else None,
            meter_count=int(transformer_data.get("meter_count", 0)),
        )
        return transformer
    except (ValueError, TypeError) as exc:
        logger.warning("Failed to parse transformer data: %s", exc)
        return None


def _row_to_meter_base(row: dict[str, str]) -> MeterBase:
    """Map a parsed table row to a MeterBase object.

    Args:
        row: Parsed row dictionary from the portal HTML.

    Returns:
        MeterBase: Validated meter base object.
    """
    status_str = row.get("status", "Installed")
    try:
        status = MeterStatus(status_str)
    except ValueError:
        status = MeterStatus.INSTALLED

    return MeterBase(
        meter_id=row.get("meter_id", row.get("id", "UNKNOWN")),
        serial_number=row.get("serial_number", row.get("serial_no", row.get("meter_number", "UNKNOWN"))),
        make=row.get("make", "Unknown"),
        phase=row.get("phase", "Unknown"),
        status=status,
        dt_id=row.get("dt_id", row.get("dt", "UNKNOWN")),
    )


def _row_to_consumption_reading(row: dict[str, str]) -> ConsumptionReading:
    """Map a parsed table row to a ConsumptionReading object.

    Args:
        row: Parsed row dictionary from the portal HTML.

    Returns:
        ConsumptionReading: Validated consumption reading object.
    """
    kwh_import_str = row.get("kwh_import") or row.get("kwh") or row.get("value") or "0"
    kwh_export_str = row.get("kwh_export") or row.get("kwh_export")
    kvah_str = row.get("kvah")

    return ConsumptionReading(
        timestamp=row.get("timestamp") or row.get("date") or "2026-01-01T00:00:00",
        kwh_import=float(kwh_import_str),
        kwh_export=float(kwh_export_str) if kwh_export_str else None,
        kvah=float(kvah_str) if kvah_str else None,
    )