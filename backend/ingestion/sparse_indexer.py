"""
Builds and persists the BM25 index from raw chunk text.
Section 7 contract: build_bm25_index(chunks) -> None
BM25 is built from raw text (not embeddings) for exact keyword recall (Section 1).
"""

import asyncio
import pickle

from rank_bm25 import BM25Okapi
from langchain_core.documents import Document

from config import BM25_INDEX_PATH


def _build_and_persist(chunks: list[Document]) -> None:
    tokenized_corpus = [chunk.page_content.split() for chunk in chunks]
    bm25 = BM25Okapi(tokenized_corpus)

    chunk_ids = [chunk.metadata["chunk_id"] for chunk in chunks]
    chunk_texts = [chunk.page_content for chunk in chunks]

    with open(BM25_INDEX_PATH, "wb") as f:
        pickle.dump(
            {"bm25": bm25, "chunk_ids": chunk_ids, "chunk_texts": chunk_texts},
            f,
        )


async def build_bm25_index(chunks: list[Document]) -> None:
    """Build a BM25 index from chunk text and persist it to disk."""
    # BM25Okapi construction and pickling are CPU-bound/blocking; offload to a thread.
    await asyncio.to_thread(_build_and_persist, chunks)
