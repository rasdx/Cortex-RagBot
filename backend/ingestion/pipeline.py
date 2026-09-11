"""
Runs loader -> chunker -> both indexers together (asyncio.gather).
Section 7 contract: run_ingestion(dir) -> None
Mirrors the async def ingest_documents example in Section 1.
"""

import asyncio

from ingestion.loader import load_documents
from ingestion.chunker import split_documents
from ingestion.dense_indexer import embed_and_store
from ingestion.sparse_indexer import build_bm25_index


async def run_ingestion(dir: str) -> None:
    """Load raw documents, chunk them, then build the dense and sparse indexes concurrently."""
    documents = load_documents(dir)
    chunks = split_documents(documents)

    await asyncio.gather(
        embed_and_store(chunks),
        build_bm25_index(chunks),
    )
