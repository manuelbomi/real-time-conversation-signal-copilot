# ADR 0001: WebSocket streaming instead of request/response

## Status

Accepted.

## Context

The copilot needs to react to a conversation *as it happens* -- a customer
raises an objection, and the recommendation should appear on the agent's
screen within a couple of seconds, not after the call ends. Two shapes were
considered: (1) the client POSTs each utterance and polls or waits for a
response, or (2) a persistent WebSocket per session that both sides push
events over.

## Decision

Use a WebSocket per session (`WS /ws/sessions/{id}`). The client sends
`UtteranceIn` frames as they occur; the server pushes `signal`,
`recommendation`, and `guardrail_block` events back on the same connection
as they're produced -- multiple events per utterance, streamed as soon as
each pipeline stage finishes, rather than one combined response at the end.

## Consequences

- Lower perceived latency: the signal badge can appear before the (slower)
  RAG recommendation is ready, instead of the UI waiting for the whole
  pipeline before showing anything.
- The server must manage connection lifecycle (reconnect, backpressure) --
  handled minimally here (see `app/api/routes.py`); a production deployment
  needs a heartbeat/ping and a defined reconnect-with-session-resume
  behavior (see docs/PRODUCTION.md).
- Horizontal scaling requires a fanout mechanism (a client's WebSocket may
  land on a different pod than a later request for the same session in a
  naive round-robin setup) -- addressed via sticky sessions + Redis pub/sub
  in docs/PRODUCTION.md, not needed at this repo's single-process demo scale.
- A plain request/response endpoint (`POST /sessions/{id}/utterances`)
  would have been simpler to test and reason about, at the cost of the
  agent-facing UI feeling laggy. For a use case where the value is entirely
  in speed (a recommendation arriving after the moment has passed is much
  less useful), that trade wasn't worth it.
