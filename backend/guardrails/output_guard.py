"""
Checks whether the generated answer is grounded in the retrieved documents.
Section 7 contract (updated): check_output(generation, documents) -> bool

Previously this swapped ungrounded answers for a generic fallback message.
Now it only reports groundedness; the graph decides what to do with an
ungrounded answer (see graph/nodes.py:fallback_generate_node), since the
product behavior is now "fall back to general LLM knowledge with a notice"
rather than "refuse to answer".
"""

_MIN_OVERLAP_RATIO = 0.15


def _is_grounded(answer: str, chunks: list[str]) -> bool:
    context = " ".join(chunks).lower()
    context_words = set(context.split())

    answer_words = [w for w in answer.lower().split() if len(w) > 3]
    if not answer_words:
        return False

    overlap = sum(1 for w in answer_words if w in context_words)
    return (overlap / len(answer_words)) >= _MIN_OVERLAP_RATIO


async def check_output(generation: str, documents: list[str]) -> bool:
    """Return True if `generation` is grounded in the retrieved documents."""
    return _is_grounded(generation, documents)
