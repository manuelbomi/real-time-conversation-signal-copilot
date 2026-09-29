"""Regex-based PII redaction.

This runs on every utterance BEFORE it is sent to any LLM provider (signal
detection, RAG recommendation generation, or the compliance guardrail
judge). It is deliberately simple and deliberately placed at a single choke
point (`llm.py`'s chat functions all call this) rather than scattered across
call sites, so a security reviewer only has to check one place to know PII
handling is enforced, not "probably enforced everywhere someone remembered."

Regex redaction is a floor, not a ceiling: it catches well-formed patterns
(SSNs, card numbers, emails, phone numbers) but will miss PII that doesn't
match a pattern (a spoken-out full name, a street address). Production
systems layer a trained PII/NER model or a vendor DLP API on top of this for
that reason -- see docs/PRODUCTION.md.
"""

from __future__ import annotations

import re

# Order matters: card numbers must be checked before phone numbers, since a
# 16-digit card number without separators can otherwise look like two phone
# numbers glued together. Each pattern is anchored loosely on purpose --
# conversational transcripts are messy (extra spaces, dashes, parentheses).
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    (
        "CARD_NUMBER",
        re.compile(r"\b(?:\d[ -]?){13,19}\b"),
    ),
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    (
        "PHONE",
        re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    ),
]


def redact_pii(text: str) -> str:
    """Replace recognizable PII substrings with `[REDACTED_<TYPE>]` tags.

    Idempotent and order-sensitive: a card number is replaced before the
    phone-number pattern gets a chance to partially match inside it.
    """
    redacted = text
    for label, pattern in _PATTERNS:
        redacted = pattern.sub(f"[REDACTED_{label}]", redacted)
    return redacted


def contains_pii(text: str) -> bool:
    """True if `text` has at least one recognizable PII pattern."""
    return any(pattern.search(text) for _, pattern in _PATTERNS)
