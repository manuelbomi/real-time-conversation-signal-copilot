"""Text embedding for the knowledge-base vector store.

Two implementations:

- `HashingEmbedder`: a fully local, deterministic, network-free embedding
  using the classic "hashing trick" (character n-grams hashed into a fixed
  number of buckets, TF-weighted, L2-normalized). This is what runs by
  default and in every test -- it needs no API key and no model download,
  which matters for a tutorial repo people clone and run immediately. Its
  retrieval quality is meaningfully worse than a real embedding model (it
  has no semantic understanding, only surface n-gram overlap), which is an
  honest, documented limitation -- see docs/PRODUCTION.md.
- `OpenAIEmbedder`: real semantic embeddings via `text-embedding-3-small`,
  the recommended production swap. Same interface, so `KnowledgeBaseStore`
  doesn't know or care which one it's handed.
"""

from __future__ import annotations

import hashlib
import re
from abc import ABC, abstractmethod

import numpy as np

_TOKEN_RE = re.compile(r"[a-z0-9]+")


class Embedder(ABC):
    dim: int

    @abstractmethod
    async def embed(self, texts: list[str]) -> np.ndarray:
        """Return an (len(texts), dim) float32 array of L2-normalized vectors."""


class HashingEmbedder(Embedder):
    def __init__(self, dim: int = 512, ngram_range: tuple[int, int] = (3, 5)) -> None:
        self.dim = dim
        self._ngram_range = ngram_range

    def _ngrams(self, text: str) -> list[str]:
        tokens = _TOKEN_RE.findall(text.lower())
        joined = " " + " ".join(tokens) + " "
        grams: list[str] = []
        for n in range(self._ngram_range[0], self._ngram_range[1] + 1):
            grams.extend(joined[i : i + n] for i in range(len(joined) - n + 1))
        return grams

    def _vector(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        for gram in self._ngrams(text):
            # A stable hash (md5, not Python's salted `hash()`) so the same
            # n-gram always lands in the same bucket across processes --
            # required for an index built in one process to be queryable
            # from another.
            digest = hashlib.md5(gram.encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:4], "little") % self.dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0  # signed hashing reduces collision bias
            vec[bucket] += sign
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec

    async def embed(self, texts: list[str]) -> np.ndarray:
        return (
            np.stack([self._vector(t) for t in texts])
            if texts
            else np.zeros((0, self.dim), dtype=np.float32)
        )


class OpenAIEmbedder(Embedder):
    def __init__(
        self, api_key: str, model: str = "text-embedding-3-small", dim: int = 1536
    ) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self.dim = dim

    async def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        response = await self._client.embeddings.create(model=self._model, input=texts)
        vectors = np.array([item.embedding for item in response.data], dtype=np.float32)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vectors / norms
