"""
Async Postgres connection pool + conversation persistence.
One row per conversation turn: session_id, query, documents, generation, is_safe.
Reads/writes go through the Pydantic models in server/models.py.
"""

import json

import asyncpg

from config import DATABASE_URL
from server.models import ConversationTurn, SessionDetail, SessionSummary

_pool: asyncpg.Pool | None = None

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS conversation_turns (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    query TEXT NOT NULL,
    documents JSONB NOT NULL,
    generation TEXT NOT NULL,
    is_safe BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


async def init_db() -> None:
    """Create the connection pool and the conversation_turns table if it doesn't exist."""
    global _pool
    _pool = await asyncpg.create_pool(DATABASE_URL)
    async with _pool.acquire() as conn:
        await conn.execute(_CREATE_TABLE_SQL)


async def close_db() -> None:
    """Close the connection pool on shutdown."""
    if _pool is not None:
        await _pool.close()


async def save_turn(turn: ConversationTurn) -> None:
    """Persist one conversation turn."""
    async with _pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO conversation_turns (session_id, query, documents, generation, is_safe)
            VALUES ($1, $2, $3, $4, $5)
            """,
            turn.session_id,
            turn.query,
            json.dumps(turn.documents),
            turn.generation,
            turn.is_safe,
        )


async def list_sessions() -> list[SessionSummary]:
    """Return one summary row per session, newest activity first, for the sidebar."""
    async with _pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT session_id,
                   (array_agg(query ORDER BY created_at ASC))[1] AS title,
                   MAX(created_at) AS last_message_at,
                   COUNT(*) AS message_count
            FROM conversation_turns
            GROUP BY session_id
            ORDER BY last_message_at DESC
            """
        )

    return [
        SessionSummary(
            session_id=row["session_id"],
            title=row["title"][:60],
            last_message_at=row["last_message_at"],
            message_count=row["message_count"],
        )
        for row in rows
    ]


async def get_session_messages(session_id: str) -> list[ConversationTurn]:
    """Return every turn for one session, oldest first, to render a chat when opened."""
    async with _pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT session_id, query, documents, generation, is_safe, created_at
            FROM conversation_turns
            WHERE session_id = $1
            ORDER BY created_at ASC
            """,
            session_id,
        )

    return [
        ConversationTurn(
            session_id=row["session_id"],
            query=row["query"],
            documents=json.loads(row["documents"]),
            generation=row["generation"],
            is_safe=row["is_safe"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


async def delete_session(session_id: str) -> bool:
    """Permanently delete all persisted turns for one session."""
    async with _pool.acquire() as conn:
        deleted = await conn.fetchval(
            """
            DELETE FROM conversation_turns
            WHERE session_id = $1
            RETURNING session_id
            """,
            session_id,
        )

    return deleted is not None


async def get_session_detail(session_id: str) -> SessionDetail | None:
    """Return a full session payload, including all turns, for the session explorer."""
    async with _pool.acquire() as conn:
        summary_row = await conn.fetchrow(
            """
            SELECT session_id,
                   (array_agg(query ORDER BY created_at ASC))[1] AS title,
                   MAX(created_at) AS last_message_at,
                   COUNT(*) AS message_count
            FROM conversation_turns
            WHERE session_id = $1
            GROUP BY session_id
            """,
            session_id,
        )

        if summary_row is None:
            return None

        turns = await get_session_messages(session_id)

    return SessionDetail(
        session_id=summary_row["session_id"],
        title=(summary_row["title"] or "New chat")[:60],
        last_message_at=summary_row["last_message_at"],
        message_count=summary_row["message_count"],
        turns=turns,
    )
