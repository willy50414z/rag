# -*- coding: utf-8 -*-
"""
Embedding generation layer for datasheet records.

This module decides WHAT TEXT each record contributes to its embedding, then
batch-encodes the lot through SentenceTransformer. It does not touch
PostgreSQL, MinIO, or any PDF parser — its only job is text → vector.

Public API:
    EmbeddingsBundle       — dataclass holding 5 lists of vectors
    EmbeddingGenerator     — wraps SentenceTransformer, lazy-loads model
"""

from dataclasses import dataclass, field

from sentence_transformers import SentenceTransformer

EMBED_MODEL = "all-MiniLM-L6-v2"   # dim=384; change schema vector() if swapping model
EMBED_DIM   = 384


# ---------------------------------------------------------------------------
# Per-record text representations
# ---------------------------------------------------------------------------

def _text_max_rating(r: dict) -> str:
    cond = f", {r['condition_raw']}" if r["condition_raw"] else ""
    return f"{r['symbol']} {r['parameter']}: {r['value_raw']} {r['unit']}{cond}"


def _text_thermal(r: dict) -> str:
    return f"{r['symbol']} {r['parameter']}: {r['typ']} {r['unit']}"


def _text_electrical(r: dict) -> str:
    nums = []
    if r["typ"] is not None: nums.append(f"typ={r['typ']}")
    if r["max"] is not None: nums.append(f"max={r['max']}")
    if r["min"] is not None: nums.append(f"min={r['min']}")
    cond = f", {r['condition_raw']}" if r["condition_raw"] else ""
    return (
        f"[{r['section']}] {r['symbol']} {r['parameter']}{cond}: "
        f"{' '.join(nums)} {r['unit']}"
    )


def _text_chart(r: dict) -> str:
    return r["caption"]


def _text_footnote(marker: str, text: str) -> str:
    return f"Note {marker}: {text}"


# ---------------------------------------------------------------------------
# Low-level batch encode
# ---------------------------------------------------------------------------

def embed_texts(model: SentenceTransformer, texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    return model.encode(texts, show_progress_bar=False, batch_size=64).tolist()


# ---------------------------------------------------------------------------
# Bundle + Generator
# ---------------------------------------------------------------------------

@dataclass
class EmbeddingsBundle:
    """Embedding vectors aligned with parsed record lists."""
    max_ratings: list[list[float]] = field(default_factory=list)
    thermal:     list[list[float]] = field(default_factory=list)
    electrical:  list[list[float]] = field(default_factory=list)
    charts:      list[list[float]] = field(default_factory=list)
    footnotes:   list[list[float]] = field(default_factory=list)


class EmbeddingGenerator:
    """Lazy-loaded SentenceTransformer wrapper that produces an EmbeddingsBundle."""

    def __init__(self, model_name: str = EMBED_MODEL):
        self.model_name = model_name
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode_bundle(self, parsed: dict) -> EmbeddingsBundle:
        """
        Encode all embeddable text from a parser result in one batched call.

        Args:
            parsed: dict from parser.parse() — {tables: {...}, footnotes: {...}}
        """
        tables    = parsed["tables"]
        max_rat   = tables["max_ratings"]
        thermal   = tables["thermal_characteristics"]
        electrical= tables["electrical_characteristics"]
        charts    = tables["typical_charts"]
        footnotes = parsed["footnotes"]

        max_texts   = [_text_max_rating(r)  for r in max_rat]
        therm_texts = [_text_thermal(r)     for r in thermal]
        elec_texts  = [_text_electrical(r)  for r in electrical]
        chart_texts = [_text_chart(r)       for r in charts]
        fn_items    = list(footnotes.items())
        fn_texts    = [_text_footnote(m, t) for m, t in fn_items]

        all_texts = max_texts + therm_texts + elec_texts + chart_texts + fn_texts
        all_embs  = embed_texts(self.model, all_texts)

        idx = 0
        max_embs   = all_embs[idx: idx + len(max_texts)];   idx += len(max_texts)
        therm_embs = all_embs[idx: idx + len(therm_texts)]; idx += len(therm_texts)
        elec_embs  = all_embs[idx: idx + len(elec_texts)];  idx += len(elec_texts)
        chart_embs = all_embs[idx: idx + len(chart_texts)]; idx += len(chart_texts)
        fn_embs    = all_embs[idx: idx + len(fn_texts)]

        return EmbeddingsBundle(
            max_ratings=max_embs,
            thermal=therm_embs,
            electrical=elec_embs,
            charts=chart_embs,
            footnotes=fn_embs,
        )
