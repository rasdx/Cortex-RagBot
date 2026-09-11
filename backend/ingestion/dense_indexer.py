"""
Embeds chunks with the HuggingFace model, writes to VectorDB.
Section 7 contract: embed_and_store(chunks) -> None
Vector store: ChromaDB (Section 1 / Tech Stack).
Embeddings are computed via the HuggingFace Inference API (huggingface_hub.InferenceClient)
so no model weights are downloaded to this machine.

PERFORMANCE NOTE: embed_documents used to call feature_extraction once PER
CHUNK, sequentially -- for a 150-chunk document that's 150 sequential
network round-trips, which is what made ingestion slow. feature_extraction
actually supports a batch (list[str]) in a single request, so chunks are now
grouped into batches of EMBEDDING_BATCH_SIZE and those batches are fired
concurrently (up to EMBEDDING_MAX_CONCURRENCY at a time) via a thread pool.
This turns N sequential requests into ~N/batch_size requests running in
parallel -- the dominant fix for ingestion latency, well ahead of any model
choice.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor

from huggingface_hub import InferenceClient
from langchain_chroma import Chroma
from langchain_core.documents import Document

from config import (
    DENSE_EMBEDDING_MODEL,
    HUGGINGFACE_API_KEY,
    VECTOR_STORE_DIR,
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_MAX_CONCURRENCY,
)

_client = InferenceClient(provider="hf-inference", api_key=HUGGINGFACE_API_KEY)


def _flatten_single_embedding(output) -> list[float]:
    """feature_extraction on ONE text can return a flat vector or a
    batch-shaped array depending on the model backend; normalize either
    shape to a flat list. Used only by embed_query (a single string)."""
    output = output.tolist() if hasattr(output, "tolist") else list(output)
    if output and isinstance(output[0], (list, tuple)):
        return list(output[0])
    return list(output)


def _normalize_batch_embeddings(output) -> list[list[float]]:
    """feature_extraction on a LIST of texts returns one vector per input,
    in order; normalize to a plain list of float vectors."""
    output = output.tolist() if hasattr(output, "tolist") else list(output)
    return [list(vector) for vector in output]


def _chunk_list(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _embed_batch(texts: list[str]) -> list[list[float]]:
    """One HTTP call embedding an entire batch of texts at once."""
    output = _client.feature_extraction(texts, model=DENSE_EMBEDDING_MODEL)
    return _normalize_batch_embeddings(output)


class _HFAPIEmbeddings:
    """Minimal LangChain-compatible embeddings interface (embed_documents/embed_query)
    backed by the HuggingFace Inference API instead of a locally loaded model."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        batches = _chunk_list(texts, EMBEDDING_BATCH_SIZE)

        # ThreadPoolExecutor (not asyncio) because this method must stay sync
        # to satisfy LangChain's Embeddings interface -- it's called from
        # inside embed_and_store's asyncio.to_thread below. Threads still
        # parallelize these calls correctly since they're I/O-bound (the
        # GIL releases during the network wait).
        with ThreadPoolExecutor(max_workers=EMBEDDING_MAX_CONCURRENCY) as pool:
            batch_results = list(pool.map(_embed_batch, batches))

        embeddings: list[list[float]] = []
        for batch_result in batch_results:
            embeddings.extend(batch_result)
        return embeddings

    def embed_query(self, text: str) -> list[float]:
        return _flatten_single_embedding(_client.feature_extraction(text, model=DENSE_EMBEDDING_MODEL))


_embeddings = _HFAPIEmbeddings()


def _get_vector_store() -> Chroma:
    return Chroma(
        collection_name="hybrid_rag_chunks",
        embedding_function=_embeddings,
        persist_directory=VECTOR_STORE_DIR,
    )


async def embed_and_store(chunks: list[Document]) -> None:
    """Embed chunks (batched + concurrent, see module docstring) and persist
    them to the vector store."""
    vector_store = _get_vector_store()
    ids = [chunk.metadata["chunk_id"] for chunk in chunks]

    # Chroma's add_documents (and the batched API calls inside embed_documents)
    # are blocking; run off the event loop so this async function never blocks.
    await asyncio.to_thread(vector_store.add_documents, documents=chunks, ids=ids)
