// Hand-written mirror of backend/app/api/schemas.py. Kept in sync manually
// for this reference repo; a larger codebase would generate this file from
// the FastAPI OpenAPI schema (e.g. `openapi-typescript`) instead -- noted
// in docs/PRODUCTION.md as the recommended upgrade once the schema churns
// often enough that manual sync becomes error-prone.

export type SignalLabel =
  | "OBJECTION"
  | "BUYING_SIGNAL"
  | "COMPLIANCE_RISK"
  | "QUESTION"
  | "ACTION_ITEM"
  | "NEUTRAL";

export interface SignalEvent {
  type: "signal";
  utterance: string;
  speaker: string;
  labels: SignalLabel[];
  confidence: Record<string, number>;
  rationale: string;
}

export interface RecommendationEvent {
  type: "recommendation";
  utterance: string;
  text: string;
  citations: string[];
  is_grounded: boolean;
}

export interface GuardrailBlockEvent {
  type: "guardrail_block";
  utterance: string;
  reason: string;
  blocked_by: string;
}

export interface ErrorEvent {
  type: "error";
  detail: string;
}

export type OutboundEvent = SignalEvent | RecommendationEvent | GuardrailBlockEvent | ErrorEvent;

export interface TranscriptTurn {
  id: string;
  speaker: string;
  text: string;
  ts: number;
  signal?: SignalEvent;
  recommendation?: RecommendationEvent;
  guardrailBlock?: GuardrailBlockEvent;
}
