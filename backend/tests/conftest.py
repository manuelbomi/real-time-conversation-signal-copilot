from pathlib import Path

import pytest

from app.guardrails import ComplianceGuardrail
from app.llm import MockProvider
from app.rag import KnowledgeBaseStore, RecommendationEngine
from app.rag.embeddings import HashingEmbedder
from app.signals import SignalDetector

KB_DIR = Path(__file__).resolve().parent.parent / "kb"
BLOCKLIST_PATH = Path(__file__).resolve().parent.parent / "app" / "guardrails" / "blocklist.txt"


@pytest.fixture
def provider():
    return MockProvider()


@pytest.fixture
def detector(provider):
    return SignalDetector(provider, samples=3)


@pytest.fixture
async def kb_store(provider):
    store = KnowledgeBaseStore(HashingEmbedder(dim=256))
    await store.build(KB_DIR)
    return store


@pytest.fixture
def recommender(provider, kb_store):
    return RecommendationEngine(provider, kb_store, top_k=3)


@pytest.fixture
def guardrail(provider):
    return ComplianceGuardrail(provider, BLOCKLIST_PATH)
