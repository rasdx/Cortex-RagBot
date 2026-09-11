"""
Central configuration: paths, model names, and pipeline constants.
Every other module imports its constants from here — no magic numbers elsewhere.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = str(Path(BASE_DIR).resolve().parent)
# Prefer backend/.env, then the repo-root .env used during local setup.
load_dotenv(os.path.join(REPO_ROOT, ".env"))
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)
RAW_DATA_DIR = os.path.join(BASE_DIR, "data", "raw")
VECTOR_STORE_DIR = os.path.join(BASE_DIR, "data", "vector_store")
BM25_INDEX_PATH = os.path.join(BASE_DIR, "data", "bm25_index", "bm25_index.pkl")

# --- Chunking (Section 1) ---
CHUNK_SIZE = 700          # ~500-800 tokens per PDF spec
CHUNK_OVERLAP = 90        # ~10-15% overlap

# --- Dense embeddings (Section 1 / Tech Stack) ---
# Multilingual model (swapped from bge-small-en-v1.5) so non-English text — e.g. Hindi —
# embeds meaningfully. bge-m3 supports 100+ languages including Hindi.
DENSE_EMBEDDING_MODEL = "BAAI/bge-m3"

# --- Embedding batching (ingestion performance) ---
# feature_extraction supports a LIST of texts in one HTTP call, not just one
# text per call. Ingestion was slow because embed_documents made one
# sequential network round-trip per chunk; batching fixes the root cause,
# and running batches concurrently (via a thread pool) adds parallelism on
# top of that. See ingestion/dense_indexer.py.
EMBEDDING_BATCH_SIZE = 32
EMBEDDING_MAX_CONCURRENCY = 4

# --- Reranker (Section 2 / Tech Stack) ---
# Reuses the multilingual BGE-M3 model (sentence-similarity task) for reranking
# via the HF Inference API. The previous choice (cross-encoder/mmarco-...) was
# a true cross-encoder, but huggingface_hub removed the API path for cross-encoder
# / sentence-pair scoring, so we drop down to bi-encoder sentence similarity.
# Same model as DENSE_EMBEDDING_MODEL, so retrieval and reranking share weights.
CROSS_ENCODER_MODEL = "BAAI/bge-m3"

# --- Retrieval (Section 2) ---
DENSE_TOP_K = 20
SPARSE_TOP_K = 20
RRF_K = 60                # RRF constant: score = sum(1 / (k + rank))
FUSED_TOP_N = 20          # top-N passed from fusion into reranker
RERANK_TOP_K = 5          # final top-k chunks passed to generation

# --- LLM generation (Section 5 / Tech Stack) ---
# HuggingFace Inference Providers, via huggingface_hub's OpenAI-compatible
# chat completions API (huggingface_hub.AsyncInferenceClient). Uses the same
# HUGGINGFACE_API_KEY as the embeddings/reranker calls below.
#
# The model string encodes the provider after a colon, e.g. "meta-llama/
# Llama-3.1-8B-Instruct:novita" routes to the "novita" inference provider for
# that model. See https://huggingface.co/docs/inference-providers for the
# full list of models/providers.
#
# Two separate constants (rather than one shared model) so the grounded-RAG
# answer and the general-knowledge fallback answer can each be pointed at a
# different model later just by editing this file — no code changes needed
# anywhere else.
GENERATION_MODEL = "meta-llama/Llama-3.1-8B-Instruct:novita"
FALLBACK_GENERATION_MODEL = "meta-llama/Llama-3.1-8B-Instruct:novita"

# --- Conversation summarization (Section: multi-turn memory) ---
# A separate, cheap OpenRouter model handles ONLY conversation summarization —
# folding each (question, answer) pair into a short running summary so the
# main generation models (above) are aware of earlier turns without needing
# the full raw history in every prompt. This is deliberately a *different*
# provider from GENERATION_MODEL/FALLBACK_GENERATION_MODEL: summarization is
# cheap/small enough to hand to a free-tier model, while the main answers stay
# on HuggingFace. If OPENROUTER_API_KEY isn't set, summarization is skipped
# quietly (see generation/summarizer.py) rather than breaking the app.
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
SUMMARIZATION_MODEL = "meta-llama/llama-3.2-3b-instruct:free"

# --- Guardrails (Section 3) ---
# Shown when the PDF doesn't contain the answer and we fall back to the
# model's general knowledge instead of a grounded-only answer.
NOT_IN_PDF_NOTICE = (
    "This answer isn't in the uploaded PDF — here's a general-knowledge answer instead."
)
INPUT_REJECTION_MSG = (
    "I'm sorry, but I can't process that request. Please rephrase your question."
)

# --- HuggingFace Inference API (embeddings + reranker are called via API, not downloaded) ---
HUGGINGFACE_API_KEY = os.environ.get("HUGGINGFACE_API_KEY", "")

# --- Postgres (conversation persistence) ---
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/hybrid_rag"
)
