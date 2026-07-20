"""HTTP routes for the Commitment Keeper API."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.schemas import ExtractionRequest, ExtractionResponse, HealthResponse
from app.services.hermes_service import HermesError, extract as hermes_extract

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="healthy")


@router.post("/extract", response_model=ExtractionResponse)
def extract(req: ExtractionRequest) -> ExtractionResponse:
    # Real extraction via the Hermes adapter (subprocess-based, schema-checked).
    try:
        raw = hermes_extract(req)
    except HermesError as exc:
        # Map the controlled error to the appropriate HTTP status.
        raise HTTPException(
            status_code=exc.status_code, detail=str(exc)
        ) from exc

    return ExtractionResponse(**raw)


from typing import Optional

from app.repositories import commitments as commitments_repo
from fastapi.responses import Response


@router.get("/commitments")
def get_commitments(status: Optional[str] = None):
    return commitments_repo.list_commitments(status)


@router.post("/commitments/{commitment_id}/approve")
def approve_commitment(commitment_id: int):
    row = commitments_repo.update_status(commitment_id, "approved")
    if not row:
        raise HTTPException(status_code=404, detail="Commitment not found")
    return row


@router.post("/commitments/{commitment_id}/dismiss")
def dismiss_commitment(commitment_id: int):
    row = commitments_repo.update_status(commitment_id, "dismissed")
    if not row:
        raise HTTPException(status_code=404, detail="Commitment not found")
    return row


@router.post("/commitments/{commitment_id}/complete")
def complete_commitment(commitment_id: int):
    row = commitments_repo.update_status(commitment_id, "completed")
    if not row:
        raise HTTPException(status_code=404, detail="Commitment not found")
    return row


@router.patch("/commitments/{commitment_id}")
def patch_commitment(commitment_id: int, fields: dict):
    row = commitments_repo.edit_commitment(commitment_id, fields)
    if not row:
        raise HTTPException(status_code=404, detail="Commitment not found")
    return row


@router.get("/commitments/export")
def export_commitments(status: Optional[str] = None):
    xlsx_bytes = commitments_repo.export_to_xlsx(status)
    filename = "commitments.xlsx" if not status else f"commitments_{status}.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
