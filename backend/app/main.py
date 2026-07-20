"""Commitment Keeper — minimal FastAPI backend (Hermes-backed extraction).

Exposes:
  GET  /health   -> {"status": "healthy"}
  POST /extract  -> extraction via the Hermes CLI, validated against the real
                    commitment schema

The /extract endpoint builds a controlled prompt and invokes the `hermes` CLI in
non-interactive mode (app.services.hermes_service). Output is validated against
~/.hermes/skills/commitment-keeper/schemas/commitment.schema.json and a 500/502
is returned on extraction failure. Invalid input yields 422.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Commitment Keeper API",
    description="Hermes-backed extraction API for the commitment-keeper skill.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {"service": "commitment-keeper", "status": "ok", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)
