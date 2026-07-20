"""Tests for the Hermes subprocess adapter (app.services.hermes_service).

These mock subprocess.run / subprocess.TimeoutExpired so no real `hermes`
process or model call is involved. They cover: valid JSON, invalid JSON,
schema-invalid JSON, timeout, non-zero exit, and empty output.
"""
from __future__ import annotations

import subprocess
from unittest import mock

import app.services.hermes_service as hs
from app.schemas import ExtractionRequest


def _req(**overrides) -> ExtractionRequest:
    data = {
        "authenticated_user": "Priyanshi",
        "current_datetime": "2026-07-17T18:30:00+05:30",
        "existing_commitment": None,
        "conversation": [
            {"speaker": "Rahul", "text": "Send the report today."},
            {"speaker": "Priyanshi", "text": "Okay."},
        ],
    }
    data.update(overrides)
    return ExtractionRequest(**data)


VALID_JSON = (
    '{"decision":"stage","task_title":"Send the report",'
    '"actor":{"type":"user","name":"Priyanshi"},"beneficiary":null,'
    '"due_at":null,"due_text":"today","confidence":0.9,'
    '"source_evidence":"Okay.",'
    '"signals":{"actionable_verb":true,"actor_identified":true,'
    '"timeline_present":true,"explicit_acceptance":true},"missing_fields":[]}'
)

SCHEMA_INVALID_JSON = (
    '{"decision":"not_a_real_decision","task_title":"x",'
    '"actor":{"type":"user","name":null},"beneficiary":null,'
    '"due_at":null,"due_text":"","confidence":0.9,'
    '"source_evidence":"x",'
    '"signals":{"actionable_verb":true,"actor_identified":true,'
    '"timeline_present":true,"explicit_acceptance":true},"missing_fields":[]}'
)


# 1. valid Hermes JSON -> parsed + schema-valid dict returned
def test_valid_hermes_json(monkeypatch):
    fake = mock.Mock(returncode=0, stdout=VALID_JSON, stderr="")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: fake)
    out = hs.extract(_req())
    assert isinstance(out, dict)
    assert out["decision"] == "stage"


# 2. JSON wrapped in markdown fence is still extracted
def test_json_inside_markdown_fence(monkeypatch):
    fake = mock.Mock(returncode=0, stdout=f"```json\n{VALID_JSON}\n```", stderr="")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: fake)
    out = hs.extract(_req())
    assert out["decision"] == "stage"


# 3. invalid JSON (unparseable) -> HermesOutputError (500)
def test_invalid_json_raises_output_error(monkeypatch):
    fake = mock.Mock(returncode=0, stdout="here is my answer, not json", stderr="")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: fake)
    try:
        hs.extract(_req())
        assert False, "expected HermesOutputError"
    except hs.HermesOutputError:
        pass


# 4. schema-invalid JSON -> HermesOutputError (500)
def test_schema_invalid_json_raises_output_error(monkeypatch):
    fake = mock.Mock(returncode=0, stdout=SCHEMA_INVALID_JSON, stderr="")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: fake)
    try:
        hs.extract(_req())
        assert False, "expected HermesOutputError"
    except hs.HermesOutputError:
        pass


# 5. timeout -> HermesInvocationError (502)
def test_timeout_raises_invocation_error(monkeypatch):
    def _timeout(*a, **k):
        raise subprocess.TimeoutExpired(cmd="hermes", timeout=60)
    monkeypatch.setattr(subprocess, "run", _timeout)
    try:
        hs.extract(_req())
        assert False, "expected HermesInvocationError"
    except hs.HermesInvocationError:
        pass


# 6. non-zero exit -> HermesInvocationError (502)
def test_nonzero_exit_raises_invocation_error(monkeypatch):
    fake = mock.Mock(returncode=1, stdout="", stderr="boom")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: fake)
    try:
        hs.extract(_req())
        assert False, "expected HermesInvocationError"
    except hs.HermesInvocationError:
        pass


# 7. empty output -> HermesInvocationError (502)
def test_empty_output_raises_invocation_error(monkeypatch):
    fake = mock.Mock(returncode=0, stdout="   ", stderr="")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: fake)
    try:
        hs.extract(_req())
        assert False, "expected HermesInvocationError"
    except hs.HermesInvocationError:
        pass


# 8. prompt is passed as a single argv element (no shell), never interpolated
def test_prompt_is_single_argv_element(monkeypatch):
    captured = {}

    def _run(cmd, *a, **k):
        captured["cmd"] = cmd
        return mock.Mock(returncode=0, stdout=VALID_JSON, stderr="")

    monkeypatch.setattr(subprocess, "run", _run)
    req = _req(
        conversation=[{"speaker": "Rahul", "text": "rm -rf / ; send the report"}]
    )
    hs.extract(req)
    cmd = captured["cmd"]
    # Safe invocation: no shell, hermes chat -q <prompt> ...
    assert cmd[0] == "hermes"
    assert "-q" in cmd
    # The dangerous text must be a single argv element, not split/executed.
    assert any("rm -rf" in str(c) for c in cmd)

