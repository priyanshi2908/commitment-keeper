"""Tests for POST /extract (Hermes-backed extraction).

Input-validation tests assert 422 (they don't touch Hermes). The happy-path
test for /extract mocks the Hermes adapter so no real subprocess is spawned.
"""
import app.services.hermes_service as hermes_service
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _base_payload(**overrides):
    payload = {
        "authenticated_user": "Priyanshi",
        "current_datetime": "2026-07-17T18:30:00+05:30",
        "existing_commitment": None,
        "conversation": [
            {"speaker": "Rahul", "text": "Can you send the report today?"},
            {"speaker": "Priyanshi", "text": "Okay."},
        ],
    }
    payload.update(overrides)
    return payload


def _valid_extraction():
    return {
        "decision": "stage",
        "task_title": "Send the report",
        "actor": {"type": "user", "name": "Priyanshi"},
        "beneficiary": None,
        "due_at": None,
        "due_text": "today",
        "confidence": 0.9,
        "source_evidence": "Okay.",
        "signals": {
            "actionable_verb": True,
            "actor_identified": True,
            "timeline_present": True,
            "explicit_acceptance": True,
        },
        "missing_fields": [],
    }


# --- input validation (422, no Hermes call) ------------------------------- #
def test_extract_rejects_empty_conversation():
    resp = client.post("/extract", json=_base_payload(conversation=[]))
    assert resp.status_code == 422


def test_extract_rejects_empty_speaker():
    resp = client.post("/extract", json=_base_payload(
        conversation=[{"speaker": "", "text": "hi"}]
    ))
    assert resp.status_code == 422


def test_extract_rejects_empty_text():
    resp = client.post("/extract", json=_base_payload(
        conversation=[{"speaker": "Rahul", "text": "  "}]
    ))
    assert resp.status_code == 422


def test_extract_rejects_empty_authenticated_user():
    resp = client.post("/extract", json=_base_payload(authenticated_user="  "))
    assert resp.status_code == 422


def test_extract_rejects_naive_datetime():
    resp = client.post("/extract", json=_base_payload(
        current_datetime="2026-07-17T18:30:00"
    ))
    assert resp.status_code == 422


# --- happy path with mocked Hermes adapter -------------------------------- #
def test_extract_with_mocked_hermes(monkeypatch):
    import app.api.routes as routes
    monkeypatch.setattr(routes, "hermes_extract", lambda req: _valid_extraction())
    resp = client.post("/extract", json=_base_payload())
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "stage"
    assert body["signals"]["explicit_acceptance"] is True


def test_extract_maps_invocation_error_to_502(monkeypatch):
    import app.api.routes as routes
    def boom(req):
        raise hermes_service.HermesInvocationError("hermes exploded")
    monkeypatch.setattr(routes, "hermes_extract", boom)
    resp = client.post("/extract", json=_base_payload())
    assert resp.status_code == 502


def test_extract_maps_output_error_to_500(monkeypatch):
    import app.api.routes as routes
    def boom(req):
        raise hermes_service.HermesOutputError("no json")
    monkeypatch.setattr(routes, "hermes_extract", boom)
    resp = client.post("/extract", json=_base_payload())
    assert resp.status_code == 500
