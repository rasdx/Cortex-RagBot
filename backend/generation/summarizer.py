"""
Conversation summarization via a cheap OpenRouter model.

This plays the same role as LangChain's `SummarizationMiddleware`, but that
class is built for LangChain's `create_agent` tool-calling agent loop, not a
hand-built LangGraph StateGraph like this project's — so rather than force a
mismatched abstraction in, this reimplements the same idea directly as a
graph node's dependency: a small, cheap model folds each (question, answer)
turn into a short running summary, and the main generation models receive
that summary instead of raw conversation history.

Deliberately a separate provider from generation/llm_client.py: summarization
is cheap/small enough for a free-tier model, so it stays on OpenRouter while
the main answers stay on HuggingFace (config.GENERATION_MODEL /
FALLBACK_GENERATION_MODEL).
"""

import httpx

from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, SUMMARIZATION_MODEL

_SUMMARY_PROMPT_TEMPLATE = (
    "You maintain a running summary of an ongoing conversation between a "
    "user and an assistant. Update the summary below to fold in the new "
    "exchange. Stay concise (3-5 sentences), keep concrete facts and topics "
    "discussed, drop small talk.\n\n"
    "Existing summary:\n{summary}\n\n"
    "New exchange:\nUser: {query}\nAssistant: {answer}\n\n"
    "Updated summary:"
)

_MAX_LOCAL_SUMMARY_CHARS = 1500
_MAX_ANSWER_SNIPPET = 400


def _local_summary(existing_summary: str, query: str, answer: str) -> str:
    """Deterministic fallback so a failed LLM call still carries context forward."""
    snippet = " ".join((answer or "").split())[:_MAX_ANSWER_SNIPPET]
    piece = f"User asked: {query}. Assistant: {snippet}".strip()
    existing = (existing_summary or "").strip()
    combined = f"{existing} {piece}".strip() if existing else piece
    return combined[:_MAX_LOCAL_SUMMARY_CHARS]


async def update_summary(existing_summary: str, query: str, answer: str) -> str:
    """Fold one new (query, answer) turn into the running conversation summary.

    Never raises: OpenRouter timeouts, rate limits, and missing keys used to
    abort the LangGraph turn (which dropped the WebSocket and skipped saving
    the chat). If the model call fails, a local extractive summary is used
    so the next turn still has conversation memory.
    """
    existing = existing_summary or ""
    if not OPENROUTER_API_KEY:
        return _local_summary(existing, query, answer)

    prompt = _SUMMARY_PROMPT_TEMPLATE.format(
        summary=existing or "(none yet)", query=query, answer=answer
    )

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "http://localhost:5173",
        "X-Title": "Hybrid RAG Assistant",
        "Content-Type": "application/json",
    }
    payload = {
        "model": SUMMARIZATION_MODEL,
        "messages": [{"role": "user", "content": prompt}],
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                OPENROUTER_BASE_URL, headers=headers, json=payload
            )
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"].strip()
        return content or _local_summary(existing, query, answer)
    except Exception:
        return _local_summary(existing, query, answer)
