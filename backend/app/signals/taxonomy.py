"""The fixed vocabulary of conversational signals this service detects.

Keeping the taxonomy as a single enum (rather than free-text labels from the
LLM) is what makes downstream code -- the UI badges, the recommendation
router, the eval framework in the companion repo -- able to reason about
labels as a closed set instead of parsing arbitrary strings. When you need a
new label, add it here and nowhere else has to change its type, only its
behavior.
"""

from __future__ import annotations

from enum import StrEnum


class Signal(StrEnum):
    OBJECTION = "OBJECTION"
    BUYING_SIGNAL = "BUYING_SIGNAL"
    COMPLIANCE_RISK = "COMPLIANCE_RISK"
    QUESTION = "QUESTION"
    ACTION_ITEM = "ACTION_ITEM"
    NEUTRAL = "NEUTRAL"


# Signals that should trigger a RAG-grounded recommendation lookup. NEUTRAL
# utterances (small talk, acknowledgements) deliberately don't -- generating
# a "recommendation" for "sounds good, thanks" wastes an LLM call and adds
# noise to the reviewer's screen. QUESTION is included because a question is
# exactly when a grounded, cited answer is most useful.
RECOMMENDATION_TRIGGERS: frozenset[Signal] = frozenset(
    {Signal.OBJECTION, Signal.BUYING_SIGNAL, Signal.QUESTION, Signal.COMPLIANCE_RISK}
)
