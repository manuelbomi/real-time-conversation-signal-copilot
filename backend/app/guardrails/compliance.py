"""Compliance guardrail: the last line of defense before a recommendation
reaches a human reviewer's screen.

Two independent checks run in sequence:

1. A deterministic blocklist/regex pass (`_blocklist_hit`) -- fast, free,
   and impossible to argue a model into ignoring, but only catches phrases
   someone thought to list in advance.
2. An LLM-as-judge pass -- catches phrasing the blocklist autfr didn't
   anticipate, at the cost of being another model call that could itself be
   wrong.

Either check failing blocks the recommendation. On failure, the response is
**withheld and flagged for human review** -- it is never silently rewritten
or "softened" by the system. Auto-rewriting a compliance-risky recommendation
would mean a machine is deciding what IS compliant, which is exactly the
judgment call this system is supposed to escalate to a human, not make
itself. See docs/adr/0003-guardrail-withhold-not-rewrite.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.llm import LLMProvider, chat, parse_json_response

_JUDGE_SYSTEM_PROMPT = """\
You are a compliance reviewer for a regulated financial-services front
office. You will be shown a single recommended response a front-office
employee is about to say to a customer. Decide if it is safe to say as-is.

Flag it as failing if it contains: an absolute guarantee of outcome, advice
that requires a license the employee may not hold, a claim not attributable
to approved reference material, or pressure/urgency tactics.

Respond with JSON ONLY: {"pass": true|false, "reason": "one short sentence"}
"""


@dataclass(frozen=True)
class GuardrailVerdict:
    passed: bool
    reason: str
    blocklist_hit: str | None = None

    @property
    def blocked_by(self) -> str:
        if self.blocklist_hit:
            return "blocklist"
        return "llm_judge" if not self.passed else "none"


class ComplianceGuardrail:
    def __init__(self, provider: LLMProvider, blocklist_path: Path) -> None:
        self._provider = provider
        self._blocklist = _load_blocklist(blocklist_path)

    async def review(self, recommendation_text: str) -> GuardrailVerdict:
        hit = self._blocklist_hit(recommendation_text)
        if hit:
            return GuardrailVerdict(
                passed=False, reason=f"blocklist phrase matched: '{hit}'", blocklist_hit=hit
            )

        raw = await chat(self._provider, _JUDGE_SYSTEM_PROMPT, recommendation_text, temperature=0.0)
        try:
            parsed = parse_json_response(raw)
        except ValueError:
            # A judge that fails to return parseable JSON is treated as a
            # FAIL, not a pass -- guardrails must fail closed, never open.
            return GuardrailVerdict(
                passed=False, reason="guardrail judge returned unparseable output; failing closed"
            )

        return GuardrailVerdict(
            passed=bool(parsed.get("pass", False)), reason=str(parsed.get("reason", ""))
        )

    def _blocklist_hit(self, text: str) -> str | None:
        lowered = text.lower()
        for phrase in self._blocklist:
            if phrase in lowered:
                return phrase
        return None


def _load_blocklist(path: Path) -> list[str]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [
        line.strip().lower() for line in lines if line.strip() and not line.strip().startswith("#")
    ]
