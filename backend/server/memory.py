"""
LangGraph conversation memory.

Compiles the RAG graph with `AsyncPostgresSaver` — LangGraph's checkpointer
("memory saver") — so per-session graph state is durably persisted in
Postgres rather than lost between requests. Each chat session's session_id
is used as the LangGraph `thread_id`.

The checkpointer's connection must stay open for the lifetime of the app
(closing it invalidates the compiled graph), so it's opened and closed
explicitly from server/main.py's lifespan rather than via a short-lived
`async with` block.
"""

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from graph.workflow import build_workflow
from config import DATABASE_URL

_checkpointer_cm = None
_compiled_app = None


async def init_memory() -> None:
    """Open the Postgres checkpointer and compile the graph with it."""
    global _checkpointer_cm, _compiled_app

    _checkpointer_cm = AsyncPostgresSaver.from_conn_string(DATABASE_URL)
    checkpointer = await _checkpointer_cm.__aenter__()
    await checkpointer.setup()  # creates the checkpoint tables on first run

    _compiled_app = build_workflow(checkpointer=checkpointer)


async def close_memory() -> None:
    """Close the Postgres checkpointer connection on shutdown."""
    if _checkpointer_cm is not None:
        await _checkpointer_cm.__aexit__(None, None, None)


def get_rag_app():
    """Return the compiled graph (with Postgres-backed memory) for the websocket route."""
    return _compiled_app
