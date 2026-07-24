"""
BeautifulSoup HTML parser functions for the Urja Meter Ops portal.

Provides functions to extract structured data from the legacy portal's
HTML tables and forms. All functions are designed to be resilient to
format variations in the portal's HTML output and never crash on
unexpected HTML.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from bs4 import BeautifulSoup, Tag

from app.models import MeterBase, MeterDetail, ConsumptionReading, Transformer, MeterStatus

logger = logging.getLogger(__name__)


def parse_html_table(html_content: str, table_index: int = 0) -> list[dict[str, str]]:
    """Parse an HTML table into a list of row dictionaries.

    Extracts headers from the first row (th or td elements) and maps
    each subsequent row to a dictionary with lowercase, underscore-separated
    keys. Returns an empty list if no tables are found or on any error.

    Args:
        html_content: Raw HTML string containing tables.
        table_index: Index of the table to parse (default: 0).

    Returns:
        list[dict[str, str]]: List of row dictionaries with normalized keys.
    """
    try:
        soup = BeautifulSoup(html_content, "html.parser")
    except Exception:
        logger.warning("Failed to parse HTML content")
        return []

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


def parse_meters_list(html_content: str) -> list[MeterBase]:
    """Parse a meters list HTML table into MeterBase objects.

    Expects table columns: METER, SERIAL, MAKE, PHASE, STATUS, DT.
    Handles missing or malformed data gracefully by using defaults.

    Args:
        html_content: Raw HTML containing a meters list table.

    Returns:
        list[MeterBase]: List of parsed meter base objects.
    """
    rows = parse_html_table(html_content, table_index=0)
    meters: list[MeterBase] = []

    for row in rows:
        try:
            meter = _row_to_meter_base(row)
            meters.append(meter)
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning("Skipping invalid meter row: %s", exc)
            continue

    logger.debug("Parsed %d meters from HTML", len(meters))
    return meters


def parse_meter_detail(html_content: str, meter_id: str) -> MeterDetail:
    """Parse a meter detail HTML page into a MeterDetail object.

    Extracts location, installation date, last reading, and last reading
    timestamp from the HTML. Handles missing data gracefully.

    Args:
        html_content: Raw HTML containing meter detail information.
        meter_id: The meter identifier for fallback.

    Returns:
        MeterDetail: Parsed meter detail object.
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # Try to find a detail table or key-value pairs
    detail_data: dict[str, str] = {}

    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) >= 2:
                key = normalize_key(cells[0].get_text(strip=True))
                value = cells[1].get_text(strip=True)
                detail_data[key] = value

    # Also look for common detail patterns in the page text
    if not detail_data:
        body = soup.find("body")
        if body:
            for p in body.find_all(["p", "div", "span"]):
                text = p.get_text(strip=True)
                if ":" in text:
                    parts = text.split(":", 1)
                    if len(parts) == 2:
                        key = normalize_key(parts[0].strip())
                        detail_data[key] = parts[1].strip()

    location = detail_data.get("location", detail_data.get("address", detail_data.get("addr")))
    installation_date_str = detail_data.get("installation_date", detail_data.get("installed", detail_data.get("install_date")))
    last_reading_str = detail_data.get("last_reading", detail_data.get("reading", detail_data.get("current_reading")))
    last_reading_at_str = detail_data.get("last_reading_at", detail_data.get("reading_date", detail_data.get("last_updated")))

    installation_date = None
    if installation_date_str:
        try:
            from datetime import date
            installation_date = date.fromisoformat(installation_date_str)
        except (ValueError, TypeError):
            pass

    last_reading = None
    if last_reading_str:
        try:
            last_reading = float(last_reading_str)
        except (ValueError, TypeError):
            pass

    last_reading_at = None
    if last_reading_at_str:
        try:
            from datetime import datetime
            last_reading_at = datetime.fromisoformat(last_reading_at_str)
        except (ValueError, TypeError):
            pass

    status_str = detail_data.get("status", "Installed")
    try:
        status = MeterStatus(status_str)
    except ValueError:
        status = MeterStatus.INSTALLED

    return MeterDetail(
        meter_id=meter_id,
        serial_number=detail_data.get("serial_number", detail_data.get("serial", detail_data.get("meter_number", "UNKNOWN"))),
        make=detail_data.get("make", "Unknown"),
        phase=detail_data.get("phase", "Unknown"),
        status=status,
        dt_id=detail_data.get("dt_id", detail_data.get("dt", "UNKNOWN")),
        location=location,
        installation_date=installation_date,
        last_reading=last_reading,
        last_reading_at=last_reading_at,
    )


def parse_consumption(html_content: str) -> list[ConsumptionReading]:
    """Parse a consumption readings HTML table into ConsumptionReading objects.

    Expects table columns with timestamp, kwh_import, kwh_export, kvah.
    Handles missing or malformed data gracefully.

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
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning("Skipping invalid consumption row: %s", exc)
            continue

    logger.debug("Parsed %d consumption readings from HTML", len(readings))
    return readings


def parse_transformers(html_content: str) -> list[Transformer]:
    """Parse a transformers list HTML table into Transformer objects.

    Expects table columns with transformer_id, name, capacity_kva, meter_count.
    Handles missing or malformed data gracefully.

    Args:
        html_content: Raw HTML containing a transformers table.

    Returns:
        list[Transformer]: List of parsed transformer objects.
    """
    rows = parse_html_table(html_content, table_index=0)
    transformers: list[Transformer] = []

    for row in rows:
        try:
            transformer = _row_to_transformer(row)
            transformers.append(transformer)
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning("Skipping invalid transformer row: %s", exc)
            continue

    logger.debug("Parsed %d transformers from HTML", len(transformers))
    return transformers


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
        meter_id=row.get("meter_id", row.get("meter", row.get("id", "UNKNOWN"))),
        serial_number=row.get("serial_number", row.get("serial", row.get("meter_number", "UNKNOWN"))),
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


def _row_to_transformer(row: dict[str, str]) -> Transformer:
    """Map a parsed table row to a Transformer object.

    Args:
        row: Parsed row dictionary from the portal HTML.

    Returns:
        Transformer: Validated transformer object.
    """
    meter_count_str = row.get("meter_count", row.get("meters", row.get("count", "0")))
    capacity_str = row.get("capacity_kva", row.get("capacity", row.get("kva")))

    return Transformer(
        transformer_id=row.get("transformer_id", row.get("id", "UNKNOWN")),
        name=row.get("name", row.get("transformer_name", "Unknown")),
        capacity_kva=float(capacity_str) if capacity_str else None,
        meter_count=int(meter_count_str) if meter_count_str else 0,
    )