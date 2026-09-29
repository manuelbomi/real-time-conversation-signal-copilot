"""Grounded recommendation generation: retrieve, then generate with citations.

The generation prompt is deliberately strict: the model is told to answer
*only* from the retrieved chunks and to cite each claim, and to say it
doesn't know rather than invent an answer when the retrieved material
doesn't cover the question. This doesn't eliminate hallucination risk (no
prompt does), which is exactly why the guardrail layer (`app/guardrails/`)
independently re-checks the output before it ever reaches a human -- RAG
grounding and guardrails are two different, complementary lines of defense,
not substitutes for each other.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.llm import LLMProvider, chat
from app.rag.store import KnowledgeBaseStore, RetrievedChunk

_SYSTEM_PROMPT = """\
You are a call-assist recommendation engine. You will be given retrieved
reference material and a live conversation moment. Write ONE short (1-3
sentence) recommended response the front-office employee could say next.

Rules:
- Base your recommendation ONLY on the retrieved reference material below.
- If the reference material does not cover this situation, say so plainly
  instead of guessing.
- Do not make guarantees, promises, or absolute claims not present in the
  reference material.
"""


@dataclass(frozen=True)
class Recommendation:
    text: str
    citations: tuple[str, ...]
    retrieved: tuple[RetrievedChunk, ...]

    @property
    def is_grounded(self) -> bool:
        """False when retrieval found nothing relevant -- callers should
        treat an ungrounded recommendation as lower-trust and say so in the
        UI rather than presenting it with the same confidence as a cited one.
        """
        return len(self.citations) > 0


class RecommendationEngine:
    def __init__(self, provider: LLMProvider, store: KnowledgeBaseStore, *, top_k: int = 3) -> None:
        self._provider = provider
        self._store = store
        self._top_k = top_k

    @property
    def kb_size(self) -> int:
        return self._store.size

    async def recommend(self, utterance: str, *, context: str = "") -> Recommendation:
        retrieved = await self._store.search(utterance, k=self._top_k)
        if not retrieved:
            return Recommendation(
                text="No relevant guidance found in the knowledge base.", citations=(), retrieved=()
            )

        reference_block = "\n\n".join(
            f"[{i+1}] ({r.chunk.citation})\n{r.chunk.text}" for i, r in enumerate(retrieved)
        )
        user_prompt = (
            f"Retrieved reference material:\n{reference_block}\n\n"
            f"Recent context:\n{context}\n\n"
            f"Live moment to respond to:\n{utterance}"
        )
        text = await chat(self._provider, _SYSTEM_PROMPT, user_prompt, temperature=0.2)
        citations = tuple(r.chunk.citation for r in retrieved)
        return Recommendation(text=text.strip(), citations=citations, retrieved=tuple(retrieved))
