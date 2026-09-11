"""
Reranker: rescores fused candidates via the HuggingFace Inference API.

Section 7 contract: rerank(query, candidates) -> list[Chunk].

NOTE: huggingface_hub removed `InferenceClient.post()` for cross-encoder /
sentence-pair scoring (huggingface_hub issue #3055). The remaining stable
option on the Inference API is `sentence_similarity`, a bi-encoder that
embeds the query and each candidate independently and returns cosine
similarities. Quality is slightly lower than a true cross-encoder but it
keeps the "no model download" constraint from config.py.

If you want cross-encoder quality back, install `sentence-transformers` and
swap _score_and_sort for `CrossEncoder(CROSS_ENCODER_MODEL).predict(pairs)`.
"""

import asyncio

from huggingface_hub import InferenceClient

from config import CROSS_ENCODER_MODEL, HUGGINGFACE_API_KEY, RERANK_TOP_K

_client = InferenceClient(provider="hf-inference", api_key=HUGGINGFACE_API_KEY)


def _score_and_sort(query: str, candidates: list[tuple[str, str]]) -> list[str]:
    if not candidates:
        return []

    texts = [chunk_text for _, chunk_text in candidates]

    # sentence_similarity returns one float per candidate, in input order.
    scores = _client.sentence_similarity(
        sentence=query,
        other_sentences=texts,
        model=CROSS_ENCODER_MODEL,
    )

    ranked = sorted(zip(scores, texts), key=lambda pair: pair[0], reverse=True)
    return [text for _, text in ranked][:RERANK_TOP_K]


async def rerank(query: str, candidates: list[tuple[str, str]]) -> list[str]:
    """Rescore fused candidates via the HF Inference API and return the top-k chunk texts."""
    # The API call is blocking; offload to a thread so this stays non-blocking.
    return await asyncio.to_thread(_score_and_sort, query, candidates)
