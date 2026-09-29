"""Provider-agnostic chat model access.

Every LLM call in this codebase goes through `chat()` below -- never
directly through `openai` or `anthropic` SDK objects elsewhere in the app.
That gives us three things for free: (1) PII is redacted at one enforced
choke point, (2) tests can run against `MockProvider` with zero network
calls and zero API keys, and (3) swapping providers is a one-line config
change (`LLM_PROVIDER=openai|anthropic|mock`), not a code change.

`chat()` takes and returns plain strings/dicts, not provider SDK types --
callers describe *what* they want (a system prompt, a user message, an
optional JSON schema to steer structured output) and don't know or care
which vendor answers.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

from app.config import settings
from app.pii import redact_pii


class LLMProvider(ABC):
    """A chat completion backend. Implementations must be safe to call
    concurrently and must not raise on empty input."""

    @abstractmethod
    async def complete(self, system: str, user: str, *, temperature: float = 0.0) -> str:
        """Return the raw text completion for a single-turn system+user prompt."""


class MockProvider(LLMProvider):
    """Deterministic, network-free provider used by default and by every
    unit test. Behavior is intentionally simple and rule-based rather than
    a canned string, so tests can assert on *meaningful* variation (e.g.
    different inputs produce different mock signal tags) without needing a
    real model.
    """

    async def complete(self, system: str, user: str, *, temperature: float = 0.0) -> str:
        text = user.lower()

        # The signal detector's system prompt asks for a JSON object shaped
        # like {"labels": [...], "rationale": "..."}. We recognize that
        # shape via a marker the detector includes and respond in kind, so
        # MockProvider can stand in for a real model end-to-end in tests.
        if "respond with json" in system.lower() and "labels" in system.lower():
            labels = _mock_signal_labels(text)
            return json.dumps({"labels": labels, "rationale": "mock heuristic classification"})

        if "compliance reviewer" in system.lower():
            # Guardrail judge: flag anything that smells like a guarantee
            # or advice phrased as certainty -- a conservative mock
            # heuristic, not a real policy engine.
            risky = any(
                phrase in text
                for phrase in ("guarantee", "i promise", "risk-free", "definitely will")
            )
            verdict = {
                "pass": not risky,
                "reason": (
                    "contains an absolute guarantee-style claim"
                    if risky
                    else "no policy concerns detected"
                ),
            }
            return json.dumps(verdict)

        # Default: a short generic recommendation, for RAG generation calls.
        return "Based on the available reference material, acknowledge the concern and confirm next steps with the customer."


def _mock_signal_labels(text: str) -> list[str]:
    labels: list[str] = []
    if any(w in text for w in ("too expensive", "not sure", "hesitant", "concerned about")):
        labels.append("OBJECTION")
    if any(w in text for w in ("sign up", "ready to", "let's do it", "how do i start")):
        labels.append("BUYING_SIGNAL")
    if any(w in text for w in ("guarantee", "promise", "risk-free")):
        labels.append("COMPLIANCE_RISK")
    if "?" in text:
        labels.append("QUESTION")
    if any(w in text for w in ("i will send", "i'll follow up", "next step")):
        labels.append("ACTION_ITEM")
    if not labels:
        labels.append("NEUTRAL")
    return labels


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        from openai import (
            AsyncOpenAI,  # imported lazily so `mock` mode needs no SDK installed correctly
        )

        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def complete(self, system: str, user: str, *, temperature: float = 0.0) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or ""


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        from anthropic import AsyncAnthropic

        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    async def complete(self, system: str, user: str, *, temperature: float = 0.0) -> str:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in response.content if block.type == "text")


def get_provider() -> LLMProvider:
    """Factory selecting the configured provider. Called once per process
    (see `app.api.deps`) and injected everywhere else, so tests can swap in
    `MockProvider()` without touching global state.
    """
    if settings.llm_provider == "openai":
        return OpenAIProvider(settings.openai_api_key, settings.openai_model)
    if settings.llm_provider == "anthropic":
        return AnthropicProvider(settings.anthropic_api_key, settings.anthropic_model)
    return MockProvider()


async def chat(
    provider: LLMProvider,
    system: str,
    user: str,
    *,
    temperature: float = 0.0,
) -> str:
    """The one function every caller in this app uses to reach an LLM.

    PII redaction happens here, unconditionally, so no call site can
    accidentally forget it.
    """
    return await provider.complete(system, redact_pii(user), temperature=temperature)


def parse_json_response(raw: str) -> dict[str, Any]:
    """Best-effort JSON parse of an LLM completion that was asked to return
    JSON. Real models occasionally wrap JSON in prose or code fences; this
    strips the common cases before giving up.
    """
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM did not return valid JSON: {raw!r}") from exc
