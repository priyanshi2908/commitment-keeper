# Commitment Keeper — Backend

Minimal FastAPI backend for the **Commitment Keeper** extraction skill. It detects
commitment candidates in conversation text and returns a structured object that
conforms to the commitment schema at
`~/.hermes/skills/commitment-keeper/schemas/commitment.schema.json`.

This is **v1 (mock)**: extraction is a deterministic placeholder
(`app/services/extraction_service.py`). It does **not** call Hermes. The Hermes
wiring point is isolated in `app/services/hermes_service.py` for a future version.

## Layout

```
backend/
├── app/
│   ├── main.py              # FastAPI app, CORS, router wiring
│   ├── config.py            # env-based settings
│   ├── schemas.py           # Pydantic request/response models
│   ├── api/
│   │   └── routes.py        # /health, /extract
│   └── services/
│       ├── extraction_service.py  # deterministic mock extractor
│       ├── hermes_service.py      # reserved Hermes interface (not used in v1)
│       └── schema_validator.py    # validates output vs the real schema
├── tests/
│   ├── test_health.py
│   └── test_extract.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## API

### GET /health
```json
{ "status": "healthy" }
```

### POST /extract
Request:
```json
{
  "authenticated_user": "Priyanshi",
  "current_datetime": "2026-07-17T18:30:00+05:30",
  "existing_commitment": null,
  "conversation": [
    { "speaker": "Rahul", "text": "Can you send the report today?" },
    { "speaker": "Priyanshi", "text": "Okay." }
  ]
}
```
Response (matches the commitment schema):
```json
{
  "decision": "stage",
  "task_title": "Okay.",
  "actor": { "type": "user", "name": "Priyanshi" },
  "beneficiary": null,
  "due_at": null,
  "due_text": "today",
  "confidence": 0.9,
  "source_evidence": "Okay.",
  "signals": { "actionable_verb": false, "actor_identified": true, "timeline_present": true, "explicit_acceptance": true },
  "missing_fields": ["action"]
}
```

## Validation & error handling

- **Input validation (Pydantic):** `conversation` must contain ≥1 message;
  `speaker`/`text` non-empty; `authenticated_user` non-empty;
  `current_datetime` must be timezone-aware; `existing_commitment` may be null.
  Failures return **HTTP 422**.
- **Output validation (jsonschema):** the generated object is checked against the
  real commitment schema. If it fails (shouldn't with the mock, but guards future
  extractors), the endpoint returns **HTTP 500**.

## Run locally

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# (optional) cp .env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Interactive docs: http://127.0.0.1:8000/docs

## Tests

```bash
source .venv/bin/activate
pytest -q
```

## Constraints (this version)

- No database.
- No Slack / Gmail integrations.
- No Docker.
- No automatic long-running server in this project's setup steps.
- Hermes is **not** invoked (mock only).
