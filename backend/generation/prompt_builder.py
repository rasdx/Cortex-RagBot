"""
Formats query + top-k chunks (+ conversation summary) into the final LLM prompt.
Section 7 contract: build_prompt(query, chunks) -> str

Both prompt builders now optionally take a `history_summary` — the running
conversation summary maintained by generation/summarizer.py — so the model
is aware of earlier questions/answers in the same session without needing
the full raw history in every call.
"""


def _summary_block(history_summary: str = "") -> str:
    return (
        f"Summary of the conversation so far:\n{history_summary}\n\n"
        if history_summary
        else ""
    )


def build_prompt(query: str, chunks: list[str], history_summary: str = "") -> str:
    """Build a grounded RAG prompt from the query and retrieved context chunks."""
    context = "\n\n".join(chunks)

    return (
        f"{_summary_block(history_summary)}"
        "Answer the question using only the context provided below. "
        "If the context does not contain the answer, say you don't know.\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {query}\n\n"
        "Answer:"
    )


def build_general_prompt(query: str, history_summary: str = "") -> str:
    """Build a plain prompt with no PDF context, for when the retrieved
    documents don't contain the answer and we fall back to the model's
    own general knowledge."""
    return (
        f"{_summary_block(history_summary)}"
        "Answer the following question directly and concisely, using your "
        "own general knowledge.\n\n"
        f"Question: {query}\n\n"
        "Answer:"
    )


def build_refusal_followup_prompt(
    query: str,
    refusal_reason: str,
    history_summary: str = "",
) -> str:
    """Build a concise prompt for a follow-up that asks why a previous refusal happened."""
    return (
        f"{_summary_block(history_summary)}"
        "Explain the previous refusal decision to the user based on the guardrail context below. "
        "Do not perform any retrieval or inspect the document corpus for this reply.\n\n"
        f"Previous refusal reason: {refusal_reason}\n\n"
        f"Current user query: {query}\n\n"
        "Answer:"
    )


def build_conversation_followup_prompt(
    query: str,
    history_summary: str = "",
) -> str:
    """Build a prompt for non-RAG conversational follow-ups that should use summary context only."""
    return (
        f"{_summary_block(history_summary)}"
        "Answer the user’s follow-up question using the prior conversation context only. "
        "Do not retrieve or rely on the uploaded document corpus unless the question clearly needs domain knowledge.\n\n"
        f"Current user query: {query}\n\n"
        "Answer:"
    )
