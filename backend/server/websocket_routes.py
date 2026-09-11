"""
WebSocket chat endpoint.

On connect: if the client passes ?session_id=..., that session is resumed
(LangGraph's Postgres checkpointer restores its state by thread_id); otherwise
a new session_id is generated. Either way the session_id is sent to the
client first.

Per message: streams the query through the memory-backed LangGraph pipeline
using stream_mode=["custom", "values"] —
  - "custom" chunks are the stage/notice/token events nodes emit via
    get_stream_writer() (see graph/nodes.py), forwarded to the client live.
  - "values" chunks are the full state after each step; the last one is the
    final state, used to persist the turn once streaming finishes.
"""

import json
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from server.memory import get_rag_app
from server.db import save_turn
from server.models import ConversationTurn
from config import INPUT_REJECTION_MSG

router = APIRouter()


async def _send_json(websocket: WebSocket, payload: dict) -> bool:
    try:
        await websocket.send_json(payload)
        return True
    except Exception:
        return False


@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket, session_id: str | None = None) -> None:
    await websocket.accept()

    session_id = session_id or str(uuid.uuid4())
    await websocket.send_json({"type": "session", "session_id": session_id})

    rag_app = get_rag_app()
    thread_config = {"configurable": {"thread_id": session_id}}

    try:
        while True:
            raw_message = await websocket.receive_text()
            payload = json.loads(raw_message)
            query = payload.get("query", "")

            final_state: dict = {}
            try:
                async for mode, chunk in rag_app.astream(
                    {"query": query},
                    config=thread_config,
                    stream_mode=["custom", "values"],
                ):
                    if mode == "custom":
                        if not await _send_json(websocket, chunk):
                            return
                    elif mode == "values":
                        final_state = chunk
            except Exception:
                if not final_state.get("generation"):
                    await _send_json(
                        websocket,
                        {
                            "type": "error",
                            "text": "Something went wrong answering that. Please try again.",
                        },
                    )
                    continue

            is_safe = final_state.get("is_safe", False)
            generation = (
                INPUT_REJECTION_MSG
                if not is_safe
                else (final_state.get("generation") or INPUT_REJECTION_MSG)
            )
            documents = final_state.get("documents") or []

            turn = ConversationTurn(
                session_id=session_id,
                query=query,
                documents=documents,
                generation=generation,
                is_safe=is_safe,
            )
            await save_turn(turn)

            await _send_json(
                websocket,
                {"type": "done", "generation": generation, "is_safe": is_safe},
            )
    except WebSocketDisconnect:
        pass
