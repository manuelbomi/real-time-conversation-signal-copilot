"""Process-wide singletons, built once at app startup.

`AppState` holds the LLM provider, the built KB vector store, and the three
pipeline components that wrap them -- all expensive-ish to construct
(especially the KB store, which embeds every chunk) so they're built once
in `main.py`'s lifespan and handed to routes via FastAPI's dependency
injection, not rebuilt per-request.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.config import settings
from app.context import ConversationContext
from app.guardrails import ComplianceGuardrail
from app.llm import LLMProvider, get_provider
from app.rag import KnowledgeBaseStore, RecommendationEngine
from app.rag.embeddings import Embedder, HashingEmbedder, OpenAIEmbedder
from app.signals import SignalDetector


@dataclass
class AppState:
    provider: LLMProvider
    detector: SignalDetector
    recommender: RecommendationEngine
    guardrail: ComplianceGuardrail
    sessions: dict[str, ConversationContext]


async def build_app_state() -> AppState:
    provider = get_provider()

    embedder: Embedder
    if settings.llm_provider == "openai" and settings.openai_api_key:
        embedder = OpenAIEmbedder(settings.openai_api_key)
    else:
        # The hashing embedder needs no API key or network call, which is
        # what lets this repo's KB search run fully offline in `mock` mode
        # and in CI. See app/rag/embeddings.py for the accuracy trade-off.
        embedder = HashingEmbedder()

    store = KnowledgeBaseStore(embedder)
    await store.build(Path(settings.kb_path))

    detector = SignalDetector(provider, samples=settings.signal_self_consistency_samples)
    recommender = RecommendationEngine(provider, store, top_k=settings.rag_top_k)
    guardrail = ComplianceGuardrail(provider, Path(settings.guardrail_blocklist_path))

    return AppState(
        provider=provider,
        detector=detector,
        recommender=recommender,
        guardrail=guardrail,
        sessions={},
    )
