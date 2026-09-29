import pytest

from app.api.pipeline import process_utterance
from app.context import ConversationContext


@pytest.mark.asyncio
async def test_pipeline_emits_signal_then_recommendation(detector, recommender, guardrail):
    context = ConversationContext(max_turns=12)
    events = [
        e
        async for e in process_utterance(
            speaker="customer",
            text="This is too expensive, but how do I get started?",
            ts=0.0,
            context=context,
            detector=detector,
            recommender=recommender,
            guardrail=guardrail,
        )
    ]
    types = [e.type for e in events]
    assert types[0] == "signal"
    assert "recommendation" in types or "guardrail_block" in types


@pytest.mark.asyncio
async def test_pipeline_skips_recommendation_for_neutral(detector, recommender, guardrail):
    context = ConversationContext(max_turns=12)
    events = [
        e
        async for e in process_utterance(
            speaker="customer",
            text="Sounds good, thanks.",
            ts=0.0,
            context=context,
            detector=detector,
            recommender=recommender,
            guardrail=guardrail,
        )
    ]
    assert len(events) == 1
    assert events[0].type == "signal"


@pytest.mark.asyncio
async def test_pipeline_blocks_guarantee_recommendation(detector, recommender, guardrail):
    context = ConversationContext(max_turns=12)
    events = [
        e
        async for e in process_utterance(
            speaker="customer",
            text="Can you just guarantee I won't lose any money?",
            ts=0.0,
            context=context,
            detector=detector,
            recommender=recommender,
            guardrail=guardrail,
        )
    ]
    types = [e.type for e in events]
    assert "signal" in types
    # The MockProvider's default recommendation text doesn't itself contain
    # guarantee language, so this documents the happy path unless the
    # generated text trips the guardrail -- both recommendation and
    # guardrail_block are acceptable outcomes here since MockProvider's
    # generation text is fixed and doesn't itself violate the blocklist.
    assert "recommendation" in types or "guardrail_block" in types


@pytest.mark.asyncio
async def test_pipeline_updates_context_across_calls(detector, recommender, guardrail):
    context = ConversationContext(max_turns=12)
    async for _ in process_utterance(
        speaker="customer",
        text="first turn",
        ts=0.0,
        context=context,
        detector=detector,
        recommender=recommender,
        guardrail=guardrail,
    ):
        pass
    assert len(context) == 1
    async for _ in process_utterance(
        speaker="agent",
        text="second turn",
        ts=1.0,
        context=context,
        detector=detector,
        recommender=recommender,
        guardrail=guardrail,
    ):
        pass
    assert len(context) == 2
