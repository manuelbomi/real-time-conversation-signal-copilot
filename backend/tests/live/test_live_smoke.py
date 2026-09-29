"""Opt-in smoke test against a REAL LLM provider.

Excluded from the default `pytest` run (see `pyproject.toml`'s
`asyncio_mode`/markers and the `-m "not live"` in CI) because it needs a
real `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` and costs real money/time.
Run explicitly with:

    LLM_PROVIDER=openai OPENAI_API_KEY=sk-... pytest -m live tests/live
"""

from __future__ import annotations

import os

import pytest

from app.config import settings
from app.llm import get_provider
from app.signals import SignalDetector

pytestmark = pytest.mark.live


@pytest.mark.skipif(
    not (os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")),
    reason="no real LLM API key configured",
)
@pytest.mark.asyncio
async def test_real_provider_detects_objection():
    provider = get_provider()
    detector = SignalDetector(provider, samples=settings.signal_self_consistency_samples)
    result = await detector.detect("Honestly this feels way too expensive for what I'm getting.")
    assert result.labels  # a real model should return at least one label
