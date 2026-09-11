"""
Async wrapper(s) around HuggingFace Inference Providers chat completions.
Section 7 contract: generate_answer(prompt) -> str

Uses huggingface_hub.AsyncInferenceClient's OpenAI-compatible chat.completions
API, which supports real async streaming natively (no manual SSE parsing,
no wrapping a sync client in a thread).

Both functions take an explicit `model` argument (defaulting to config's
per-purpose constants) so different call sites — the grounded-RAG answer vs.
the general-knowledge fallback — can each use a different model, or the
caller can override it directly, without touching this file.

generate_answer() is used for the RAG-grounded answer, which must be fully
generated before the output guardrail can decide whether to show it.

stream_answer() is used for the general-knowledge fallback (when the PDF
doesn't contain the answer): it streams real tokens as they're generated,
for the frontend to render incrementally.
"""

from typing import AsyncGenerator

from huggingface_hub import AsyncInferenceClient

from config import HUGGINGFACE_API_KEY, GENERATION_MODEL, FALLBACK_GENERATION_MODEL

_client = AsyncInferenceClient(api_key=HUGGINGFACE_API_KEY)


async def generate_answer(prompt: str, model: str = GENERATION_MODEL) -> str:
    """Send the prompt to the given model and return the full answer text."""
    response = await _client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        stream=False,
    )
    return response.choices[0].message.content


async def stream_answer(
    prompt: str, model: str = FALLBACK_GENERATION_MODEL
) -> AsyncGenerator[str, None]:
    """Stream the completion token-by-token as it's generated."""
    stream = await _client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )

    async for chunk in stream:
        # Some providers emit empty/heartbeat chunks with no choices; those
        # used to IndexError and abort the fallback path (WebSocket drop).
        choices = getattr(chunk, "choices", None) or []
        if not choices:
            continue
        delta = getattr(choices[0], "delta", None)
        content = getattr(delta, "content", None) if delta is not None else None
        if content:
            yield content
