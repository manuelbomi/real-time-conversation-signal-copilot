"""Wire-format schemas for the session API and WebSocket event stream.

Kept separate from the SQLAlchemy models (there are none in this minimal
reference backend -- sessions are in-memory, see `docs/PRODUCTION.md` for
what persisting them for audit/replay would add) so the wire contract can
evolve independently of storage.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class CreateSessionResponse(BaseModel):
    session_id: str


class UtteranceIn(BaseModel):
    """One inbound conversation turn, sent as a WebSocket text frame.

    This shape is the documented compatibility contract with an upstream
    ASR/diarization service: `speaker`, `text`, `ts` (unix seconds, float),
    and `is_final` (a streaming ASR emits interim partials before a final
    transcript; only finals are classified, to avoid wasting LLM calls on
    text that's about to change).
    """

    speaker: str
    text: str
    ts: float
    is_final: bool = True


class SignalEvent(BaseModel):
    type: Literal["signal"] = "signal"
    utterance: str
    speaker: str
    labels: list[str]
    confidence: dict[str, float]
    rationale: str


class RecommendationEvent(BaseModel):
    type: Literal["recommendation"] = "recommendation"
    utterance: str
    text: str
    citations: list[str]
    is_grounded: bool


class GuardrailBlockEvent(BaseModel):
    type: Literal["guardrail_block"] = "guardrail_block"
    utterance: str
    reason: str
    blocked_by: str


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    detail: str


OutboundEvent = SignalEvent | RecommendationEvent | GuardrailBlockEvent | ErrorEvent
