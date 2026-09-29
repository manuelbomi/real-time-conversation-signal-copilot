import pytest

from app.signals.taxonomy import Signal


@pytest.mark.asyncio
async def test_detects_objection(detector):
    result = await detector.detect("This just feels too expensive for what I get.")
    assert Signal.OBJECTION in result.labels


@pytest.mark.asyncio
async def test_detects_buying_signal(detector):
    result = await detector.detect("Okay, I'm ready to sign up, how do I start?")
    assert Signal.BUYING_SIGNAL in result.labels


@pytest.mark.asyncio
async def test_detects_compliance_risk(detector):
    result = await detector.detect("Can you just guarantee I won't lose any money?")
    assert Signal.COMPLIANCE_RISK in result.labels


@pytest.mark.asyncio
async def test_detects_question(detector):
    result = await detector.detect("What happens if I close the account early?")
    assert Signal.QUESTION in result.labels


@pytest.mark.asyncio
async def test_falls_back_to_neutral(detector):
    result = await detector.detect("Sounds good, thanks.")
    assert result.labels == (Signal.NEUTRAL,)


@pytest.mark.asyncio
async def test_confidence_reflects_sample_agreement(detector):
    result = await detector.detect("This is way too expensive, I'm hesitant.")
    assert 0.0 <= result.top_confidence <= 1.0
    assert result.raw_sample_count == 3


@pytest.mark.asyncio
async def test_multi_label_detection(detector):
    # Contains both an objection and a compliance-risk-triggering guarantee ask.
    result = await detector.detect("It's too expensive -- can you guarantee I won't lose money?")
    assert Signal.OBJECTION in result.labels
    assert Signal.COMPLIANCE_RISK in result.labels
