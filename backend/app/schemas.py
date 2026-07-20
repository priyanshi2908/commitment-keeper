"""Pydantic request/response models for the Commitment Keeper API.

These mirror the extraction schema defined in
~/.hermes/skills/commitment-keeper/schemas/commitment.schema.json.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

Decision = Literal["stage", "ignore", "requires_acceptance", "possible_completion"]
ActorType = Literal["user", "other", "team", "unknown"]
MissingField = Literal["actor", "action", "deadline", "beneficiary"]


class Message(BaseModel):
    """A single turn in the conversation."""

    speaker: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)

    @field_validator("speaker")
    @classmethod
    def speaker_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("speaker must not be empty or whitespace")
        return v

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text must not be empty or whitespace")
        return v


class ExtractionRequest(BaseModel):
    """Request body for POST /extract."""

    authenticated_user: str = Field(..., min_length=1)
    current_datetime: datetime  # Pydantic requires timezone-aware ISO-8601
    existing_commitment: Optional[str] = None
    conversation: List[Message] = Field(..., min_length=1)

    @field_validator("authenticated_user")
    @classmethod
    def user_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("authenticated_user must not be empty or whitespace")
        return v

    @field_validator("current_datetime")
    @classmethod
    def dt_must_be_tz_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("current_datetime must be timezone-aware")
        return v


class Actor(BaseModel):
    type: ActorType
    name: Optional[str] = None


class Signals(BaseModel):
    actionable_verb: bool
    actor_identified: bool
    timeline_present: bool
    explicit_acceptance: bool


class ExtractionResponse(BaseModel):
    """Response body for POST /extract (matches the commitment schema)."""

    decision: Decision
    task_title: str = ""
    actor: Actor
    beneficiary: Optional[str] = None
    due_at: Optional[str] = None
    due_text: str = ""
    confidence: float = Field(..., ge=0.0, le=1.0)
    source_evidence: str = ""
    signals: Signals
    missing_fields: List[MissingField] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
