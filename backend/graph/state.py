"""
Defines the shared state object passed between nodes.
Section 7 contract: class RAGState(TypedDict)
Base fields match Section 4: query, documents, generation, is_safe.
is_grounded lets the conditional edge after check_output route to a
general-knowledge fallback when the PDF doesn't contain the answer.
summary is the running conversation summary (see generation/summarizer.py):
because the graph is compiled with a Postgres checkpointer keyed by
session_id (server/memory.py), this field persists across turns in the same
session automatically — no separate lookup needed to carry it forward.
"""

from typing import Annotated, NotRequired, TypedDict


def _keep_summary(existing: str | None, new: str | None) -> str:
    """Preserve the running summary unless a node writes a real update.

    Default last-value channels would otherwise let an empty/missing write
    wipe memory between turns.
    """
    if new:
        return new
    return existing or ""


class ConversationState(TypedDict):
    """Compact metadata for routing and continuity; intentionally separate from summary."""

    query_type: NotRequired[str]
    last_action: NotRequired[str]
    refusal_reason: NotRequired[str]
    rag_used: NotRequired[bool]


def _keep_conversation_state(
    existing: ConversationState | None, new: ConversationState | None
) -> ConversationState:
    """Preserve prior structured state unless a node explicitly updates it."""
    if new is None:
        return existing or {}

    merged = dict(existing or {})
    merged.update(new)
    return merged


class RAGState(TypedDict):
    query: str
    documents: NotRequired[list[str]]
    generation: NotRequired[str]
    is_safe: NotRequired[bool]
    is_grounded: NotRequired[bool]
    summary: Annotated[str, _keep_summary]
    conversation_state: Annotated[ConversationState, _keep_conversation_state]
