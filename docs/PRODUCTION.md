# Taking this to production

This repo runs as a single backend process with in-memory sessions and a
locally-embedded knowledge base -- fine for a demo, not for a real deployment
serving concurrent live calls. This document is the concrete list of what
changes, in the order you'd actually hit these problems.

## 1. Latency budget

There is no GPU or real LLM provider available in the environment this repo
was built and tested in, so no end-to-end latency numbers below are
measurements -- they are a **target design budget**, stated as such, that a
real deployment should validate with its own load test (see the companion
`low-latency-llm-serving-optimization` repo for a load-testing harness and
methodology you can point at this service).

Target budget for "signal appears on screen" (the latency that matters most,
since it drives the recommendation panel appearing next):

| Stage | Target p95 | Why |
|---|---|---|
| Network in (audio->text already done upstream) | <50ms | same-region WebSocket |
| Signal detection (N=3 sampled LLM calls, run concurrently via `asyncio.gather`) | <900ms | dominated by the slowest of 3 concurrent calls to a fast model (e.g. gpt-4o-mini class); see ADR 0002 for why 3 samples |
| Recommendation (retrieval + 1 generation call) | <700ms | retrieval is local (FAISS, sub-10ms at this KB scale); generation is 1 LLM call |
| Guardrail review (blocklist + 1 LLM judge call) | <400ms | blocklist is near-instant; judge is 1 short LLM call |
| **Total, signal only** | **<1s** | |
| **Total, signal + recommendation + guardrail** | **<2s** | |

If real measurement shows the self-consistency sampling (N=3) blows this
budget, the first lever to pull is dropping to N=1 for low-stakes calls and
reserving N=3 for calls already flagged as higher-risk (e.g. by account
type) -- a good example of confidence-vs-latency being a genuine trade-off,
not a free upgrade.

## 2. Horizontal scaling of WebSocket fanout

A single backend process holding all sessions in memory (as this reference
implementation does, see `app/api/deps.py`'s `AppState.sessions` dict) does
not scale past one pod, and loses every in-flight session on restart. Two
changes are needed together:

1. **Session state in Redis**, not an in-process dict: `ConversationContext`
   serialized as a short JSON list of recent turns, keyed by session id,
   with a TTL slightly longer than a typical call. Any pod can then handle
   any WebSocket connection for a session, statelessly, by reading from
   Redis at the start of each utterance.
2. **Redis pub/sub (or a lightweight message broker) for fanout** if a
   session's producer (e.g. a separate ASR ingestion service) and its
   WebSocket consumer (the browser client) can land on different pods:
   publish outbound events to a per-session channel, and have the pod
   holding that WebSocket connection subscribe and forward. This is the
   standard pattern for scaling WebSocket services horizontally behind a
   load balancer that doesn't guarantee sticky routing.

At the scale of "one financial-services front office," sticky sessions
(the load balancer routes a given session id to the same pod for its
lifetime) plus Redis-backed state is usually simpler to operate than full
pub/sub fanout, and is the recommended starting point before reaching for
pub/sub.

## 3. Kubernetes deployment (`deploy/k8s/`)

`backend-deployment.yaml` has a real Deployment + Service + HorizontalPodAutoscaler
+ PodDisruptionBudget. Notable choices:

- **HPA scales on active session count (a custom Prometheus metric), not
  CPU%.** This workload is I/O-bound -- most wall-clock time per request is
  spent waiting on an LLM API call, not computing -- so CPU usage stays low
  even when the service is saturated with concurrent sessions. A CPU-based
  HPA would under-scale exactly when you need more replicas. Expose
  `copilot_active_sessions` (a gauge you'd add alongside the histograms in
  `app/metrics.py`) and scale on that instead.
- **Secrets via a Kubernetes `Secret`** (`deploy/k8s/secrets.example.yaml`),
  referenced with `secretKeyRef`, never baked into the image or committed.
  In a real environment, prefer an external-secrets operator syncing from
  your cloud KMS/secrets manager over `kubectl create secret` by hand.
- **A PodDisruptionBudget with `minAvailable: 2`** so a rolling update or
  node drain never drops below 2 replicas -- important specifically because
  WebSocket connections are long-lived; killing every pod near-simultaneously
  during a deploy would drop every active call's connection at once.
- **Ingress must support WebSocket upgrade** and a long enough proxy timeout
  for the lifetime of a call (not shown here, cluster/ingress-controller
  specific -- e.g. `nginx.ingress.kubernetes.io/proxy-read-timeout` raised
  from its short default).

## 4. Observability

- **Metrics** (`app/metrics.py`, `GET /metrics`): separate histograms for
  signal detection, recommendation, and guardrail review latency, plus a
  guardrail-block counter labeled by which layer blocked
  (`blocklist`/`llm_judge`) -- this labeling matters because a rising
  `llm_judge` block rate with a flat `blocklist` rate tells you the judge
  is catching things the blocklist should be updated to catch directly
  (faster, cheaper, more auditable).
- **Structured JSON logs** (`app/main.py`, via `python-json-logger`) so
  log aggregation (CloudWatch/Datadog/ELK) can filter/alert on fields
  rather than grepping text.
- **Distributed tracing**: `opentelemetry-api`/`sdk` are in
  `requirements.txt` as the intended integration point -- wrap
  `process_utterance`'s three stages (`app/api/pipeline.py`) in spans with
  an OTel exporter configured for your backend (Jaeger/Tempo/X-Ray/etc.) so
  a slow call can be traced to exactly which stage was slow, not just that
  the whole pipeline was slow. Not wired up by default in this reference
  repo to avoid requiring a tracing backend just to run the demo.

## 5. PII and guardrail audit trail

`app/pii.py`'s `redact_pii()` runs on every string before it reaches an LLM
call (enforced centrally in `app/llm.py::chat()`). In production, add:

- **A trained PII/NER pass on top of the regex floor** -- regex only
  catches well-formed patterns; a spoken full name or street address slips
  through. A vendor DLP API or a fine-tuned NER model closes that gap.
- **Persisted, queryable guardrail block audit log** (this reference repo
  only emits the block as a WebSocket event and a JSON log line): a table
  of `(session_id, utterance, blocked_by, reason, timestamp)` with a
  retention period matching your compliance requirements, reviewable by a
  compliance officer to check the guardrail's precision/recall over time
  (see ADR 0003).

## 6. Blue/green model or prompt rollout

Changing the signal-detection or recommendation prompt (or swapping the
underlying model) changes behavior in ways that are hard to fully predict
from reading the diff. Recommended rollout:

1. Run the new prompt/model as a shadow: process the same utterances
   through both old and new, log both outputs, only serve the old one.
2. Compare shadow output against the golden dataset in the companion
   `conversational-ai-eval-golden-dataset-framework` repo's evaluation
   pipeline -- gate promotion on no regression in per-label F1 or
   calibration.
3. Canary: route a small percentage of real sessions to the new version,
   watch the guardrail-block rate and (if collected) agent thumbs-up/down
   feedback for a divergence from baseline.
4. Full rollout, with the previous prompt/model version kept ready for
   immediate rollback (a config value, not a code change) if the block
   rate or feedback signal regresses.

## 7. What's deliberately out of scope here

- **Real ASR/telephony ingestion** -- this repo accepts `{speaker, text,
  ts, is_final}` events over its WebSocket and includes a transcript
  replay script (`backend/scripts/replay_transcript.py`) to demo the
  pipeline without live audio. The companion `streaming-asr-diarization-pipeline`
  repo produces events in this exact shape from real audio.
- **Persisted session history / call recordings** -- sessions are in-memory
  for this reference implementation. A real deployment needs a persistence
  layer (Postgres is the natural choice, with `session_id` as the
  partition key) for post-call review, audit, and the golden-dataset
  pipeline above to have real transcripts to sample from.
