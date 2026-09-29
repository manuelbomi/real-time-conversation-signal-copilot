import pytest

from app.guardrails.compliance import _load_blocklist


@pytest.mark.asyncio
async def test_blocklist_catches_guarantee_language(guardrail):
    verdict = await guardrail.review("I can guarantee you will not lose money on this account.")
    assert verdict.passed is False
    assert verdict.blocked_by == "blocklist"


@pytest.mark.asyncio
async def test_blocklist_catches_risk_free_claim(guardrail):
    verdict = await guardrail.review("This investment is completely risk-free.")
    assert verdict.passed is False
    assert verdict.blocklist_hit is not None


@pytest.mark.asyncio
async def test_llm_judge_passes_compliant_text(guardrail):
    verdict = await guardrail.review(
        "All disclosed products carry some risk; let's review the official risk disclosure together."
    )
    assert verdict.passed is True
    assert verdict.blocked_by == "none"


@pytest.mark.asyncio
async def test_llm_judge_catches_promise_language_not_in_blocklist(guardrail):
    # "I promise this..." is not a literal blocklist phrase (the blocklist
    # only matches the exact phrase "i promise you") but the MockProvider's
    # judge heuristic flags any "i promise" substring -- this exercises the
    # second guardrail layer specifically, not the first.
    verdict = await guardrail.review("I promise this account will perform well for you.")
    assert verdict.passed is False
    assert verdict.blocked_by == "llm_judge"


def test_blocklist_loader_ignores_comments_and_blank_lines(tmp_path):
    path = tmp_path / "blocklist.txt"
    path.write_text("# comment\n\nguarantee you will\n  risk-free  \n", encoding="utf-8")
    loaded = _load_blocklist(path)
    assert loaded == ["guarantee you will", "risk-free"]


def test_blocklist_loader_handles_missing_file(tmp_path):
    assert _load_blocklist(tmp_path / "does_not_exist.txt") == []
