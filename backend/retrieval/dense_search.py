"""
Embeds the query, searches VectorDB, returns ranked chunk ids.
Section 7 contract: dense_search(query, top_k) -> list[Hit]
Query embeddings are computed via the HuggingFace Inference API (huggingface_hub.InferenceClient)
so no model weights are downloaded to this machine.

Mirrors ingestion/dense_indexer.py's _HFAPIEmbeddings (including the batched
embed_documents), kept duplicated deliberately so each file stays
self-contained. embed_documents isn't actually on the hot path here --
Chroma's similarity_search only calls embed_query -- but the class matches
its sibling file for consistency.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor

from huggingface_hub import InferenceClient
from langchain_chroma import Chroma

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
    shape to a flat list."""
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
    output = _client.feature_extraction(texts, model=DENSE_EMBEDDING_MODEL)
    return _normalize_batch_embeddings(output)


class _HFAPIEmbeddings:
    """Minimal LangChain-compatible embeddings interface (embed_documents/embed_query)
    backed by the HuggingFace Inference API instead of a locally loaded model."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        batches = _chunk_list(texts, EMBEDDING_BATCH_SIZE)
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


def _search(query: str, top_k: int) -> list[tuple[str, str]]:
    vector_store = _get_vector_store()
    results = vector_store.similarity_search(query, k=top_k)
    return [(doc.metadata["chunk_id"], doc.page_content) for doc in results]


async def dense_search(query: str, top_k: int) -> list[tuple[str, str]]:
    """Return the top_k chunks ranked by dense (embedding) similarity to the query."""
    # similarity_search (and the API call inside embed_query) is blocking; offload to a thread.
    return await asyncio.to_thread(_search, query, top_k)
