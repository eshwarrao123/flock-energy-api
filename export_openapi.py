"""
Script to export the OpenAPI schema to a JSON file without running the server.

Usage:
    python export_openapi.py [--output openapi.json]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys

from app.main import app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def export_schema(output_path: str = "openapi.json") -> None:
    """Generate and export the OpenAPI schema to a JSON file.

    Args:
        output_path: File path for the exported schema.
    """
    schema = app.openapi()
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
    logger.info("OpenAPI schema exported to %s", output_path)


def main() -> None:
    """CLI entry point for the export_openapi script."""
    parser = argparse.ArgumentParser(
        description="Export the OpenAPI schema to a JSON file.",
    )
    parser.add_argument(
        "--output",
        default="openapi.json",
        help="Output file path (default: openapi.json)",
    )
    args = parser.parse_args()
    export_schema(args.output)


if __name__ == "__main__":
    main()