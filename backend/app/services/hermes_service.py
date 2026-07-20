"""Hermes-backed extraction service for Commitment Keeper.

Invokes the `hermes` CLI non-interactively to run the commitment-keeper skill
and returns a structured extraction. ALL subprocess logic lives in this module.

Safety model (per requirements):
- The prompt is passed as a `subprocess` argv element. We never use shell=True
  and never string-interpolate unsanitised user text into a shell command.
- A timeout is enforced; stdout and stderr are captured.
- Empty responses are rejected.
- The JSON object is extracted defensively; markdown fences / explanatory prose
  are stripped, and the call is rejected when no JSON object can be parsed.
- Every response is validated against the real commitment schema, and a
  controlled application error is raised on any failure.
"""
from __future__ import annotations

import json
import re
import subprocess
from typing import Any, Dict, List

from app.config import get_settings
from app.schemas import ExtractionRequest
from app.services.schema_validator import load_schema, validate_extraction


class HermesError(Exception):
    """Base controlled error for Hermes extraction failures.

    Carries an HTTP ``status_code`` the route can map to a response.
    """

    status_code: int = 500


class HermesInvocationError(HermesError):
    """Hermes could not be invoked (timeout, non-zero exit, empty output)."""

    status_code = 502


class HermesOutputError(HermesError):
    """Hermes ran but produced no usable JSON or schema-invalid output."""

    status_code = 500


def build_prompt(req: ExtractionRequest) -> str:
    """Build a controlled prompt containing all required context.

    The prompt embeds only the structured request fields; it never embeds raw
    shell syntax, and is delivered to Hermes as a single argv element.
    """
    lines: List[str] = []
    lines.append("You are operating as the commitment-keeper skill.")
    lines.append("")
    lines.append(f"Authenticated user: {req.authenticated_user}")
    lines.append(f"Current date and time: {req.current_datetime}")
    if req.existing_commitment:
        lines.append(
            f"Existing commitment under review: {req.existing_commitment}"
        )
    lines.append("")
    lines.append("Conversation:")
    for msg in req.conversation:
        lines.append(f"{msg.speaker}: {msg.text}")
    lines.append("")
    lines.append(
        "Use the commitment-keeper skill's decision rules to classify this "
        "conversation."
    )
    lines.append(
        "Return ONLY a single JSON object conforming to the commitment schema."
    )
    lines.append("Do not create, modify, delete, or append any files.")
    return "\n".join(lines)


def _extract_json_object(text: str) -> Dict[str, Any]:
    """Safely extract a JSON object from Hermes output.

    Tries, in order: the whole string, a fenced ```json block, then the first
    balanced-looking {...} span. Raises HermesOutputError if nothing parses.
    """
    text = text.strip()

    # 1. Whole string is JSON.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Fenced code block (```json ... ``` or ``` ... ```).
    m = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 3. First {...} substring.
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    raise HermesOutputError(
        "Hermes response did not contain a parseable JSON object."
    )


def extract(req: ExtractionRequest) -> Dict[str, Any]:
    """Invoke Hermes and return a schema-valid extraction dict.

    Raises HermesInvocationError (502) on timeout / non-zero exit / empty
    output, and HermesOutputError (500) on unparseable or schema-invalid output.
    """
    settings = get_settings()
    prompt = build_prompt(req)

    # Safe mechanism: prompt delivered as a single argv element; no shell.
    cmd = [
        settings.hermes_command,
        "chat",
        "-q", prompt,
        "-s", settings.hermes_skill_name,
        "-Q",            # quiet: emit only the final response
        "--cli",         # force non-interactive classic mode
        "--max-turns", "1",
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=settings.hermes_timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise HermesInvocationError(
            f"Hermes timed out after {settings.hermes_timeout_seconds}s"
        ) from exc

    if proc.returncode != 0:
        raise HermesInvocationError(
            f"Hermes exited with {proc.returncode}: "
            f"{(proc.stderr or '').strip()[:500]}"
        )

    if not proc.stdout or not proc.stdout.strip():
        raise HermesInvocationError("Hermes returned empty output.")

    obj = _extract_json_object(proc.stdout)
    if not isinstance(obj, dict):
        raise HermesOutputError("Hermes response JSON was not an object.")

    # Validate against the real commitment schema.
    try:
        schema = load_schema(settings.schema_path)
    except FileNotFoundError as exc:
        raise HermesOutputError(f"Commitment schema unavailable: {exc}") from exc
    try:
        validate_extraction(obj, schema)
    except ValueError as exc:
        raise HermesOutputError(
            f"Hermes output failed schema validation: {exc}"
        ) from exc

    return obj
