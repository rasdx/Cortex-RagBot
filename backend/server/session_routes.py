"""
REST endpoints backing the frontend sidebar and session explorer.
GET /sessions            -> one summary row per chat, for the chat list.
GET /sessions/{id}/messages -> full turn history for one chat, to render it.
GET /chat-sessions       -> explorer-friendly list of stored sessions.
GET /chat-sessions/{id}  -> full session payload for inspection.
DELETE /chat-sessions/{id} -> permanently remove one stored session.
"""

from fastapi import APIRouter, HTTPException

from server.db import delete_session, get_session_detail, list_sessions, get_session_messages
from server.models import ConversationTurn, SessionDetail, SessionSummary

router = APIRouter()


@router.get("/sessions", response_model=list[SessionSummary])
async def get_sessions() -> list[SessionSummary]:
    return await list_sessions()


@router.get("/sessions/{session_id}/messages", response_model=list[ConversationTurn])
async def get_messages(session_id: str) -> list[ConversationTurn]:
    return await get_session_messages(session_id)


@router.get("/chat-sessions", response_model=list[SessionSummary])
async def get_chat_sessions() -> list[SessionSummary]:
    return await list_sessions()


@router.get("/chat-sessions/{session_id}", response_model=SessionDetail)
async def get_chat_session(session_id: str) -> SessionDetail:
    session = await get_session_detail(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/chat-sessions/{session_id}")
async def delete_chat_session(session_id: str) -> dict[str, str]:
    deleted = await delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted", "session_id": session_id}
