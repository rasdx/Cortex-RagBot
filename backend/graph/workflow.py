"""
Builds the StateGraph, wires nodes + edges, compiles it.
Section 7 contract: app = build_workflow()
Base structure matches Section 4; two branches were added since:

1. check_output no longer decides "show it or refuse" — it only reports
   groundedness (is_grounded). The conditional edge routes to
   fallback_generate (a general-knowledge answer) when the PDF-grounded
   answer wasn't grounded, instead of ending with a refusal.
2. update_summary runs after either branch produces a final answer, folding
   this turn into the running conversation summary (generation/summarizer.py)
   before the graph ends, so the next turn in this session has it available.

build_workflow() accepts an optional `checkpointer` so the server can
compile a Postgres-memory-backed instance (see server/memory.py) while this
module still exposes an uncheckpointed `app` for direct/local use.
"""

from langgraph.graph import StateGraph, END

from graph.state import RAGState
from config import INPUT_REJECTION_MSG
from graph.nodes import (
    check_input_node,
    classify_query_node,
    retrieve_node,
    rerank_node,
    generate_node,
    refusal_followup_node,
    conversation_followup_node,
    general_query_node,
    check_output_node,
    fallback_generate_node,
    update_summary_node,
)


def build_workflow(checkpointer=None):
    workflow = StateGraph(RAGState)

    workflow.add_node("check_input", check_input_node)
    workflow.add_node("classify_query", classify_query_node)
    workflow.add_node("refuse", lambda state: {"generation": INPUT_REJECTION_MSG, "conversation_state": {"last_action": "refused", "rag_used": False, "query_type": "safety_request"}})
    workflow.add_node("refusal_followup", refusal_followup_node)
    workflow.add_node("conversation_followup", conversation_followup_node)
    workflow.add_node("general_query", general_query_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("rerank", rerank_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("check_output", check_output_node)
    workflow.add_node("fallback_generate", fallback_generate_node)
    workflow.add_node("update_summary", update_summary_node)

    workflow.set_entry_point("check_input")
    workflow.add_edge("check_input", "classify_query")
    workflow.add_conditional_edges(
        "classify_query",
        lambda s: (
            "refuse"
            if s.get("conversation_state", {}).get("query_type") == "safety_request"
            else "refusal_followup"
            if s.get("conversation_state", {}).get("query_type") == "refusal_followup"
            else "conversation_followup"
            if s.get("conversation_state", {}).get("query_type") == "conversation_followup"
            else "general_query"
            if s.get("conversation_state", {}).get("query_type") == "general_query"
            else "retrieve"
        ),
    )
    workflow.add_edge("refuse", "update_summary")
    workflow.add_edge("refusal_followup", "update_summary")
    workflow.add_edge("conversation_followup", "update_summary")
    workflow.add_edge("general_query", "update_summary")
    workflow.add_edge("retrieve", "rerank")
    workflow.add_edge("rerank", "generate")
    workflow.add_edge("generate", "check_output")
    workflow.add_conditional_edges(
        "check_output", lambda s: "update_summary" if s["is_grounded"] else "fallback_generate"
    )
    workflow.add_edge("fallback_generate", "update_summary")
    workflow.add_edge("update_summary", END)

    return workflow.compile(checkpointer=checkpointer)


app = build_workflow()

if __name__ == "__main__":
    app.invoke({"query": "What is the capital of France?"})