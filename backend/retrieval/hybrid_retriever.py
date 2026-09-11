"""
Orchestrates dense+sparse concurrently, then fusion.
Section 7 contract: hybrid_retrieve(query) -> list[Chunk]
Mirrors the async def hybrid_retrieve example in Section 2.
Note: per Section 7, this file stops at fusion; reranking is a separate graph node
that calls retrieval/reranker.py directly (see graph/nodes.py).
"""

import asyncio

from retrieval.dense_search import dense_search
from retrieval.sparse_search import bm25_search
from retrieval.fusion import reciprocal_rank_fusion

from config import DENSE_TOP_K, SPARSE_TOP_K, RRF_K, FUSED_TOP_N


async def hybrid_retrieve(query: str) -> list[str]:
    """Run dense and BM25 search concurrently, then fuse the two ranked lists."""
    dense_hits, sparse_hits = await asyncio.gather(
        dense_search(query, top_k=DENSE_TOP_K),
        bm25_search(query, top_k=SPARSE_TOP_K),
    )

    fused = reciprocal_rank_fusion(dense_hits, sparse_hits, k=RRF_K)
    return fused[:FUSED_TOP_N]
