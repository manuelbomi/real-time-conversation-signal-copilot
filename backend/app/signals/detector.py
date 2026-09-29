"""Multi-label conversational signal detection via structured LLM output.

## Why self-consistency for confidence, not a softmax probability

A single LLM completion doesn't expose a trustworthy per-label probability
the way a trained classifier's softmax does -- an LLM asked to emit JSON
either produces a label or it doesn't, with no calibrated confidence
attached. Instead, this detector samples the model `N` times (default 3,
temperature > 0) and treats the fraction of samples that agree on a given
label as an approximate confidence: an utterance where all 3 samples say
"OBJECTION" is more reliably an objection than one where only 1 of 3 does.

This is a *pragmatic approximation*, not calibrated probability -- it will
systematically overstate confidence for a model that is consistently wrong
in the same way every time (self-consistency measures agreement, not
correctness). For real calibration (Expected Calibration Error against a
human-labeled golden set), see the companion evaluation-framework repo,
which measures this detector's actual reliability against adjudicated
ground truth rather than the model's agreement with itself. See also
docs/adr/0002-confidence-via-self-consistency.md.
"""

from __future__ import annotations

import asyncio
from collections import Counter
from dataclasses import dataclass

from app.llm import LLMProvider, chat, parse_json_response
from app.signals.taxonomy import Signal

_SYSTEM_PROMPT = """\
You are a conversation-signal classifier for live sales/support/advisory calls.
Read a single utterance (with brief prior-turn context) and decide which of
these labels apply. Multiple labels may apply to one utterance.

Labels:
- OBJECTION: the speaker raises a concern, hesitation, or pushback.
- BUYING_SIGNAL: the speaker signals readiness to proceed or commit.
- COMPLIANCE_RISK: the utterance contains or invites an absolute guarantee,
  unlicensed advice, or a claim that needs a compliance-approved response.
- QUESTION: the speaker is asking something that needs an answer.
- ACTION_ITEM: a concrete next step or follow-up is mentioned.
- NEUTRAL: none of the above (small talk, acknowledgement, filler).

Respond with JSON ONLY, no other text, in this exact shape:
{"labels": ["LABEL_ONE", "LABEL_TWO"], "rationale": "one short sentence"}
"""


@dataclass(frozen=True)
class SignalResult:
    labels: tuple[Signal, ...]
    confidence: dict[Signal, float]
    rationale: str
    raw_sample_count: int

    @property
    def top_confidence(self) -> float:
        return max(self.confidence.values(), default=0.0)


class SignalDetector:
    def __init__(self, provider: LLMProvider, *, samples: int = 3) -> None:
        self._provider = provider
        self._samples = max(1, samples)

    async def detect(self, utterance: str, *, context: str = "") -> SignalResult:
        """Classify one utterance. `context` is a short window of prior
        turns (see app.context) that helps disambiguate short utterances
        like "yeah, maybe" which are meaningless in isolation.
        """
        user_prompt = (
            f"Recent context:\n{context}\n\nUtterance to classify:\n{utterance}"
            if context
            else f"Utterance to classify:\n{utterance}"
        )

        samples = await asyncio.gather(
            *(
                chat(self._provider, _SYSTEM_PROMPT, user_prompt, temperature=0.7 if i > 0 else 0.0)
                for i in range(self._samples)
            )
        )

        label_votes: Counter[Signal] = Counter()
        rationale = ""
        parsed_count = 0
        for raw in samples:
            try:
                parsed = parse_json_response(raw)
                sample_labels = _coerce_labels(parsed.get("labels", []))
            except ValueError:
                # A malformed sample doesn't crash detection -- it just
                # doesn't vote. If every sample is malformed we fall back
                # to NEUTRAL with zero confidence below.
                continue
            parsed_count += 1
            for label in sample_labels:
                label_votes[label] += 1
            rationale = rationale or str(parsed.get("rationale", ""))

        if parsed_count == 0:
            return SignalResult(
                labels=(Signal.NEUTRAL,),
                confidence={Signal.NEUTRAL: 0.0},
                rationale="all samples failed to parse; defaulting to NEUTRAL",
                raw_sample_count=0,
            )

        confidence = {label: count / parsed_count for label, count in label_votes.items()}
        # A label only counts as "detected" if a majority of parsed samples
        # agreed on it -- this is what turns noisy per-sample votes into a
        # stable multi-label decision.
        agreed_labels = tuple(
            sorted(
                (label for label, conf in confidence.items() if conf >= 0.5),
                key=lambda s: -confidence[s],
            )
        )
        if not agreed_labels:
            agreed_labels = (Signal.NEUTRAL,)
            confidence.setdefault(Signal.NEUTRAL, 1.0 / parsed_count)

        return SignalResult(
            labels=agreed_labels,
            confidence=confidence,
            rationale=rationale,
            raw_sample_count=parsed_count,
        )


def _coerce_labels(raw_labels: list[str]) -> list[Signal]:
    result = []
    for raw in raw_labels:
        try:
            result.append(Signal(str(raw).strip().upper()))
        except ValueError:
            continue  # an LLM inventing a label outside the taxonomy is dropped, not trusted
    return result or [Signal.NEUTRAL]
