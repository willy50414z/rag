# -*- coding: utf-8 -*-
"""
Embedding layer: text → vectors.

Wraps SentenceTransformer with a lazy-loaded module-level singleton.
Text representation logic lives in db.text_representations.

Public API:
    embed(texts: list[str]) -> list[list[float]]
    EmbeddingsBundle   — dataclass holding 5 lists of vectors
    EmbeddingGenerator — lazy-load wrapper (use embed() for typical calls)
"""

from dataclasses import dataclass, field

from sentence_transformers import SentenceTransformer

EMBED_MODEL = "all-MiniLM-L6-v2"   # dim=384; update schema vector() if swapping model
EMBED_DIM   = 384


@dataclass
class EmbeddingsBundle:
    """Embedding vectors aligned with parsed record lists."""
    max_ratings: list[list[float]] = field(default_factory=list)
    thermal:     list[list[float]] = field(default_factory=list)
    electrical:  list[list[float]] = field(default_factory=list)
    charts:      list[list[float]] = field(default_factory=list)
    footnotes:   list[list[float]] = field(default_factory=list)


class EmbeddingGenerator:
    """Lazy-loaded SentenceTransformer wrapper."""

    def __init__(self, model_name: str = EMBED_MODEL):
        self.model_name = model_name
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model


def _encode(model: SentenceTransformer, texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    return model.encode(texts, show_progress_bar=False, batch_size=64).tolist()


_default_generator: EmbeddingGenerator | None = None


def embed(texts: list[str]) -> list[list[float]]:
    """Encode *texts* into vectors using the shared lazy-loaded model."""
    global _default_generator
    if _default_generator is None:
        _default_generator = EmbeddingGenerator()
    return _encode(_default_generator.model, texts)
