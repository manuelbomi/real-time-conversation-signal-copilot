"""FAISS-backed vector store over the approved knowledge base.

The knowledge base is a directory of Markdown files (`kb/` by default) --
each file is a self-contained policy or product reference doc. We chunk by
Markdown heading (`##`) rather than by fixed character count, because a
fixed-size chunk can split a policy statement mid-sentence and hand the LLM
half a rule to cite, which is exactly the failure mode a compliance-grounded
recommendation system can't afford. Each chunk keeps its source filename and
heading so a citation can point a human reviewer at the exact paragraph.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import faiss

from app.rag.embeddings import Embedder

_HEADING_RE = re.compile(r"^##\s+(.*)$", re.MULTILINE)


@dataclass(frozen=True)
class Chunk:
    source: str
    heading: str
    text: str

    @property
    def citation(self) -> str:
        return f"{self.source} § {self.heading}"


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: Chunk
    score: float


def load_chunks(kb_dir: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(kb_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        headings = list(_HEADING_RE.finditer(text))
        if not headings:
            chunks.append(Chunk(source=path.name, heading="(document)", text=text.strip()))
            continue
        for i, match in enumerate(headings):
            start = match.end()
            end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
            body = text[start:end].strip()
            if body:
                chunks.append(Chunk(source=path.name, heading=match.group(1).strip(), text=body))
    return chunks


class KnowledgeBaseStore:
    """Builds and queries an in-memory FAISS index over the KB chunks.

    Cosine similarity is implemented as inner product over L2-normalized
    vectors (`IndexFlatIP`), which is both exact (no approximate-NN
    accuracy loss -- fine at this KB's scale of dozens to low-thousands of
    chunks) and avoids a second normalization step at query time.
    """

    def __init__(self, embedder: Embedder) -> None:
        self._embedder = embedder
        self._index: faiss.IndexFlatIP | None = None
        self._chunks: list[Chunk] = []

    @property
    def size(self) -> int:
        return len(self._chunks)

    async def build(self, kb_dir: Path) -> None:
        self._chunks = load_chunks(kb_dir)
        if not self._chunks:
            raise ValueError(f"No knowledge base chunks found under {kb_dir}")
        vectors = await self._embedder.embed([c.text for c in self._chunks])
        index = faiss.IndexFlatIP(self._embedder.dim)
        index.add(vectors)
        self._index = index

    async def search(self, query: str, k: int = 3) -> list[RetrievedChunk]:
        if self._index is None:
            raise RuntimeError("KnowledgeBaseStore.build() must be called before search()")
        query_vec = await self._embedder.embed([query])
        scores, indices = self._index.search(query_vec, min(k, self.size))
        results: list[RetrievedChunk] = []
        for score, idx in zip(scores[0], indices[0], strict=True):
            if idx < 0:
                continue
            results.append(RetrievedChunk(chunk=self._chunks[idx], score=float(score)))
        return results
