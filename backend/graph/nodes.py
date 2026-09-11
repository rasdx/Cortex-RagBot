"""
One thin async function per graph node; each calls exactly one module
function for its actual work — no business logic of its own.
Section 7 contract: check_input_node / retrieve_node / rerank_node /
generate_node / check_output_node, plus fallback_generate_node (new).

Each node also emits a small progress event via LangGraph's stream writer
(get_stream_writer) so the websocket layer can forward live "thinking"
updates and streamed tokens to the frontend. This is UI plumbing, not
pipeline logic, so it doesn't count against the "one job per node" rule —
the actual work in every node is still exactly one call into
ingestion/retrieval/generation/guardrails.
"""

import asyncio

from langgraph.config import get_stream_writer

from graph.state import RAGState
from guardrails.input_guard import check_input, get_refusal_reason
from retrieval.hybrid_retriever import hybrid_retrieve
from retrieval.reranker import rerank
from generation.prompt_builder import (
    build_prompt,
    build_general_prompt,
    build_refusal_followup_prompt,
    build_conversation_followup_prompt,
)
from generation.llm_client import generate_answer, stream_answer
from generation.summarizer import update_summary
from guardrails.output_guard import check_output
from config import (
    NOT_IN_PDF_NOTICE,
    GENERATION_MODEL,
    FALLBACK_GENERATION_MODEL,
    INPUT_REJECTION_MSG,
)

_REPLAY_WORDS_PER_CHUNK = 4
_REPLAY_DELAY_SECONDS = 0.03
_REFUSAL_FOLLOWUP_PATTERNS = (
    "why can't you",
    "why cant you",
    "why couldn't you",
    "why couldn't you process",
    "why can't you process",
    "why did you refuse",
    "why was that refused",
    "what was the previous decision",
    "why was my previous request refused",
    "why not",
)
_CONVERSATION_FOLLOWUP_PATTERNS = (
    "above",
    "earlier",
    "previous",
    "before",
    "that",
    "this",
    "it",
    "you said",
    "you mentioned",
)
_KNOWLEDGE_QUERY_PATTERNS = (
    "what is",
    "how does",
    "how do",
    "explain",
    "compare",
    "who is",
    "when did",
    "where is",
    "why is",
    "summarize",
    "list",
)


async def _replay_as_stream(writer, text: str) -> None:
    """Reveal an already-generated answer to the frontend a few words at a
    time, so a fully-formed (grounded) answer still 'streams in' instead of
    appearing all at once."""
    words = text.split(" ")
    for i in range(0, len(words), _REPLAY_WORDS_PER_CHUNK):
        chunk = " ".join(words[i : i + _REPLAY_WORDS_PER_CHUNK]) + " "
        writer({"type": "token", "text": chunk})
        await asyncio.sleep(_REPLAY_DELAY_SECONDS)


def _is_refusal_followup(query: str, previous_refusal_reason: str | None) -> bool:
    if not previous_refusal_reason:
        return False

    lowered = query.lower()
    return any(pattern in lowered for pattern in _REFUSAL_FOLLOWUP_PATTERNS)


def _is_conversation_followup(query: str, summary: str) -> bool:
    lowered = query.lower()
    has_summary = bool((summary or "").strip())
    if not has_summary:
        return False

    return any(pattern in lowered for pattern in _CONVERSATION_FOLLOWUP_PATTERNS)


def _is_knowledge_query(query: str) -> bool:
    lowered = query.lower()
    return any(pattern in lowered for pattern in _KNOWLEDGE_QUERY_PATTERNS)


async def check_input_node(state: RAGState) -> dict:
    writer = get_stream_writer()
    writer({"type": "stage", "stage": "Checking your question..."})

    query = state["query"]
    is_safe = await check_input(query)
    refusal_reason = get_refusal_reason(query)

    if is_safe:
        return {
            "is_safe": True,
            "documents": [],
            "generation": "",
            "conversation_state": {
                "query_type": "general_query",
                "last_action": "checked",
                "rag_used": False,
            },
        }

    return {
        "is_safe": False,
        "documents": [],
        "generation": "",
        "conversation_state": {
            "query_type": "safety_request",
            "last_action": "refused",
            "refusal_reason": refusal_reason or "unsafe_input",
            "rag_used": False,
        },
    }


async def classify_query_node(state: RAGState) -> dict:
    query = state["query"]
    conversation_state = state.get("conversation_state") or {}
    previous_refusal_reason = conversation_state.get("refusal_reason")

    if not state.get("is_safe", True):
        query_type = "safety_request"
    elif _is_refusal_followup(query, previous_refusal_reason):
        query_type = "refusal_followup"
    elif _is_knowledge_query(query):
        query_type = "knowledge_query"
    elif _is_conversation_followup(query, state.get("summary") or ""):
        query_type = "conversation_followup"
    else:
        query_type = "general_query"

    return {
        "conversation_state": {
            "query_type": query_type,
            "rag_used": False,
            "last_action": conversation_state.get("last_action", "checked"),
            "refusal_reason": previous_refusal_reason,
        }
    }


async def retrieve_node(state: RAGState) -> dict:
    writer = get_stream_writer()
    writer({"type": "stage", "stage": "Searching the document..."})

    documents = await hybrid_retrieve(state["query"])
    return {
        "documents": documents,
        "conversation_state": {
            "rag_used": True,
            "query_type": "knowledge_query",
            "last_action": "retrieved",
        },
    }


async def rerank_node(state: RAGState) -> dict:
    writer = get_stream_writer()
    writer({"type": "stage", "stage": "Ranking the best matches..."})

    documents = await rerank(state["query"], state["documents"])
    return {"documents": documents}


async def generate_node(state: RAGState) -> dict:
    writer = get_stream_writer()
    writer({"type": "stage", "stage": "Drafting an answer..."})

    # Generated fully (not streamed to the user yet): check_output_node needs
    # the complete text to decide whether it's grounded before anything is shown.
    prompt = build_prompt(state["query"], state["documents"], state.get("summary") or "")
    generation = await generate_answer(prompt, model=GENERATION_MODEL)
    return {"generation": generation}


async def refusal_followup_node(state: RAGState) -> dict:
    writer = get_stream_writer()
    writer({"type": "stage", "stage": "Explaining the previous refusal..."})

    refusal_reason = (state.get("conversation_state") or {}).get("refusal_reason") or "unsafe_input"
    prompt = build_refusal_followup_prompt(
        state["query"],
        refusal_reason,
        state.get("summary") or "",
    )
    generation = await generate_answer(prompt, model=GENERATION_MODEL)
    return {
        "generation": generation,
        "documents": [],
        "conversation_state": {
            "rag_used": False,
            "last_action": "explained_refusal",
            "query_type": "refusal_followup",
        },
    }


async def conversation_followup_node(state: RAGState) -> dict:
    writer = get_stream_writer()
    writer({"type": "stage", "stage": "Answering follow-up question..."})

    prompt = build_conversation_followup_prompt(
        state["query"],
        state.get("summary") or "",
    )
    generation = await generate_answer(prompt, model=GENERATION_MODEL)
    return {
        "generation": generation,
        "documents": [],
        "conversation_state": {
            "rag_used": False,
            "last_action": "answered_followup",
            "query_type": "conversation_followup",
        },
    }


async def general_query_node(state: RAGState) -> dict:
    writer = get_stream_writer()
    writer({"type": "stage", "stage": "Answering question..."})

    prompt = build_general_prompt(state["query"], state.get("summary") or "")
    generation = await generate_answer(prompt, model=GENERATION_MODEL)
    return {
        "generation": generation,
        "documents": [],
        "conversation_state": {
            "rag_used": False,
            "last_action": "answered_general_query",
            "query_type": "general_query",
        },
    }


async def check_output_node(state: RAGState) -> dict:
    writer = get_stream_writer()
    writer({"type": "stage", "stage": "Double-checking the answer..."})

    is_grounded = await check_output(state["generation"], state["documents"])

    if is_grounded:
        await _replay_as_stream(writer, state["generation"])

    return {"is_grounded": is_grounded}


async def fallback_generate_node(state: RAGState) -> dict:
    """Runs only when check_output found the PDF-grounded answer ungrounded.
    Tells the user up front, then streams a real general-knowledge answer."""
    writer = get_stream_writer()
    writer({"type": "notice", "text": NOT_IN_PDF_NOTICE})
    writer({"type": "stage", "stage": "Consulting general knowledge..."})

    prompt = build_general_prompt(state["query"], state.get("summary") or "")

    full_answer = ""
    try:
        async for token in stream_answer(prompt, model=FALLBACK_GENERATION_MODEL):
            full_answer += token
            writer({"type": "token", "text": token})
    except Exception:
        if not full_answer:
            full_answer = (
                "I couldn't reach the general-knowledge model just now. "
                "Please try asking again."
            )
            writer({"type": "token", "text": full_answer})

    generation = f"{NOT_IN_PDF_NOTICE}\n\n{full_answer}"
    return {"generation": generation}


async def update_summary_node(state: RAGState) -> dict:
    """Runs after completed answers to fold this turn into the running
    conversation summary, unless the turn was a refusal that should remain
    tracked in structured state only."""
    conversation_state = state.get("conversation_state") or {}
    if conversation_state.get("query_type") == "safety_request":
        return {"summary": state.get("summary") or ""}

    summary = await update_summary(
        state.get("summary") or "",
        state["query"],
        state.get("generation") or "",
    )
    return {"summary": summary}
