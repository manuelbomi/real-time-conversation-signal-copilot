# ADR 0003: Guardrail failures withhold the response; they never rewrite it

## Status

Accepted.

## Context

When the compliance guardrail (`app/guardrails/compliance.py`) flags a
generated recommendation as risky, the system needs to decide what the
agent sees instead. Two options: (a) ask the model to rewrite the
recommendation into a compliant version and show that, or (b) withhold the
recommendation entirely and show that it was blocked, with the reason.

## Decision

Withhold and flag (option b). A blocked recommendation is never shown, not
even in a "softened" or auto-rewritten form. `GuardrailBlockEvent` carries
the reason and which layer blocked it (`blocklist` or `llm_judge`) so the
event is auditable.

## Consequences

- A human reviewer always sees either a fully-cleared recommendation or an
  explicit block notice -- never an ambiguous, machine-edited "safer"
  version they might trust more than they should.
- Auto-rewriting would mean an LLM decides what compliant phrasing IS --
  which is precisely the judgment this system is supposed to escalate to a
  human (a compliance officer defining the blocklist/policy, or a human
  reviewer handling the specific case), not make itself. Automating that
  judgment silently would undermine the entire reason a guardrail layer
  exists.
- The cost is a worse "always show something" user experience: sometimes
  the agent gets nothing useful in the moment and has to fall back to
  their own judgment. This is treated as acceptable -- a missing
  recommendation is a known, visible gap; a wrong one delivered with
  confidence is a much worse failure mode in a regulated context.
- Blocked recommendations should be logged for audit and periodic human
  review of the blocklist/judge's precision (are we over-blocking
  legitimate responses?) -- see docs/PRODUCTION.md's audit-log retention
  section. This reference implementation logs the block event over the
  WebSocket and via structured JSON logs but does not yet persist a
  queryable audit table; that's the natural next step for a real
  deployment.
