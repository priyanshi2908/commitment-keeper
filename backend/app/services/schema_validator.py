"""Validate generated extraction output against the real commitment schema.

Loads the JSON Schema from the commitment-keeper skill and checks that any
object the extractor produces conforms to it (decision enum, required fields,
missing_fields enum, confidence range, etc.).
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Tuple

from jsonschema import Draft7Validator

from app.config import get_settings


def load_schema(schema_path: str | None = None) -> Dict[str, Any]:
    """Load the commitment JSON Schema from disk."""
    path = schema_path or get_settings().schema_path
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Commitment schema not found at: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_extraction(obj: Dict[str, Any], schema: Dict[str, Any] | None = None) -> None:
    """Raise jsonschema.ValidationError if ``obj`` violates the commitment schema."""
    if schema is None:
        schema = load_schema()
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(obj), key=lambda e: e.path)
    if errors:
        # Surface the first error message; collect all for detail.
        detail = "; ".join(f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}"
                           for e in errors)
        raise ValueError(f"Output failed commitment schema validation: {detail}")


def is_valid(obj: Dict[str, Any], schema: Dict[str, Any] | None = None) -> Tuple[bool, str]:
    """Return (ok, message). Never raises."""
    try:
        validate_extraction(obj, schema)
        return True, ""
    except Exception as exc:  # noqa: BLE001 - we want a string message, not a raise
        return False, str(exc)
