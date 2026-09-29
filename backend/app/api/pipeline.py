"""The per-utterance processing pipeline: signal -> (maybe) recommend -> guardrail.

This is the one function that ties every module in `app/` together. It is
intentionally a plain async function (not a class, not a framework
abstraction) so it's trivially unit-testable with fakes and trivially
readable top-to-bottom -- the WebSocket route below is a thin adapter that
calls this and forwards whatever events it yields.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator

from app.api.schemas import GuardrailBlockEvent, OutboundEvent, RecommendationEvent, SignalEvent
from app.context import ConversationContext, Turn
from app.guardrails import ComplianceGuardrail
from app.metrics import (
    GUARDRAIL_BLOCKS_TOTAL,
    GUARDRAIL_LATENCY,
    RECOMMENDATION_LATENCY,
    SIGNAL_DETECTION_LATENCY,
    UTTERANCES_PROCESSED_TOTAL,
)
from app.rag import RecommendationEngine
from app.signals import SignalDetector
from app.signals.taxonomy import RECOMMENDATION_TRIGGERS, Signal


async def process_utterance(
    *,
    speaker: str,
    text: str,
    ts: float,
    context: ConversationContext,
    detector: SignalDetector,
    recommender: RecommendationEngine,
    guardrail: ComplianceGuardrail,
) -> AsyncIterator[OutboundEvent]:
    context.add(Turn(speaker=speaker, text=text, ts=ts))
    context_text = context.as_prompt_text()

    with SIGNAL_DETECTION_LATENCY.time():
        result = await detector.detect(text, context=context_text)

    yield SignalEvent(
        utterance=text,
        speaker=speaker,
        labels=[label.value for label in result.labels],
        confidence={label.value: score for label, score in result.confidence.items()},
        rationale=result.rationale,
    )
    UTTERANCES_PROCESSED_TOTAL.inc()

    should_recommend = any(Signal(label) in RECOMMENDATION_TRIGGERS for label in result.labels)
    if not should_recommend:
        return

    with RECOMMENDATION_LATENCY.time():
        recommendation = await recommender.recommend(text, context=context_text)

    with GUARDRAIL_LATENCY.time():
        verdict = await guardrail.review(recommendation.text)

    if not verdict.passed:
        GUARDRAIL_BLOCKS_TOTAL.labels(blocked_by=verdict.blocked_by).inc()
        yield GuardrailBlockEvent(
            utterance=text, reason=verdict.reason, blocked_by=verdict.blocked_by
        )
        return

    yield RecommendationEvent(
        utterance=text,
        text=recommendation.text,
        citations=list(recommendation.citations),
        is_grounded=recommendation.is_grounded,
    )


def now() -> float:
    return time.time()
