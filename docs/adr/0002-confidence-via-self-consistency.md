# ADR 0002: Confidence via self-consistency, not calibrated probability

## Status

Accepted, with a known and documented limitation.

## Context

The UI shows a confidence percentage next to each detected signal. A
trained classifier can expose a calibrated softmax probability for this. An
LLM asked to emit a JSON label doesn't have an equivalent built-in
confidence signal -- it either returns a label or it doesn't.

## Decision

Sample the model `N` times (`SIGNAL_SELF_CONSISTENCY_SAMPLES`, default 3)
at temperature > 0 for samples after the first, and report the fraction of
samples that agreed on each label as its "confidence." See
`app/signals/detector.py`.

## Consequences

- This is cheap to implement and gives a genuinely useful *relative*
  signal: an utterance where 3/3 samples agree is more reliably that label
  than one where 2/3 do.
- It is **not** calibrated probability. A model that is consistently,
  confidently wrong about a specific phrasing pattern will show high
  "confidence" via this method despite being wrong every time --
  self-consistency measures the model's agreement with itself, not its
  agreement with ground truth.
- It costs `N`x the LLM calls of a single sample, which matters for
  latency and cost at scale (see docs/PRODUCTION.md's latency budget
  discussion).
- The companion evaluation-framework repo (golden-dataset annotation +
  Expected Calibration Error against human-adjudicated labels) is the
  correct tool for actually measuring this detector's real-world
  reliability. This repo's confidence score should be read as "how
  internally consistent was the model," and the eval framework's ECE score
  should be read as "how much should a human actually trust that number" --
  they answer different questions and neither substitutes for the other.
- An alternative considered: use the log-probability of the generated
  tokens (available from some providers) as confidence. Rejected for this
  reference implementation because it's provider-specific (not available
  uniformly across OpenAI/Anthropic chat completion APIs at the time of
  writing) and would break the provider-agnostic `LLMProvider` abstraction
  in `app/llm.py`.
