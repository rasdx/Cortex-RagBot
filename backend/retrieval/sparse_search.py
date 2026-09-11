"""
Searches the BM25 index, returns ranked chunk ids.
Section 7 contract: bm25_search(query, top_k) -> list[Hit]
A "Hit" here is (chunk_id, chunk_text), matching dense_search's shape.
"""

import asyncio
import pickle
from pathlib import Path

from config import BM25_INDEX_PATH


def _search(query: str, top_k: int) -> list[tuple[str, str]]:
    index_path = Path(BM25_INDEX_PATH)
    if not index_path.exists():
        return []

    try:
        with index_path.open("rb") as f:
            data = pickle.load(f)
    except Exception:
        return []

    bm25 = data.get("bm25")
    chunk_ids = data.get("chunk_ids", [])
    chunk_texts = data.get("chunk_texts", [])

    if bm25 is None or not chunk_ids or not chunk_texts:
        return []

    scores = bm25.get_scores(query.split())
    ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    top_indices = ranked_indices[:top_k]

    return [(chunk_ids[i], chunk_texts[i]) for i in top_indices]


async def bm25_search(query: str, top_k: int) -> list[tuple[str, str]]:
    """Return the top_k chunks ranked by BM25 keyword relevance to the query."""
    # Pickle load + scoring is blocking I/O/CPU work; offload to a thread.
    return await asyncio.to_thread(_search, query, top_k)
