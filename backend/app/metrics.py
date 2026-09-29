"""Prometheus instrumentation.

Exported at `GET /metrics` in the standard Prometheus text exposition
format (via `prometheus_client`'s `generate_latest`). Every histogram here
answers a question an on-call engineer will actually ask during an
incident: "is signal detection slow, or is RAG slow, or is the guardrail
judge slow?" -- hence three separate stage histograms instead of one
end-to-end number, which would tell you *that* something is slow but not
*what*.
"""

from __future__ import annotations

from prometheus_client import Counter, Histogram

SIGNAL_DETECTION_LATENCY = Histogram(
    "copilot_signal_detection_seconds",
    "Time to classify one utterance's conversational signals.",
)
RECOMMENDATION_LATENCY = Histogram(
    "copilot_recommendation_seconds",
    "Time to retrieve + generate a grounded recommendation.",
)
GUARDRAIL_LATENCY = Histogram(
    "copilot_guardrail_review_seconds",
    "Time for the compliance guardrail to review a recommendation.",
)
GUARDRAIL_BLOCKS_TOTAL = Counter(
    "copilot_guardrail_blocks_total",
    "Recommendations withheld by the compliance guardrail, by reason.",
    labelnames=("blocked_by",),
)
UTTERANCES_PROCESSED_TOTAL = Counter(
    "copilot_utterances_processed_total",
    "Utterances that completed the full signal-detection pipeline.",
)
