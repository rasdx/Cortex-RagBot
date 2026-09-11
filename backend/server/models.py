"""
Pydantic models for conversation data stored in Postgres.
Used both when writing (validates shape before insert) and reading
(structures rows for the API responses the frontend sidebar consumes).
"""

from datetime import datetime

from pydantic import BaseModel


class ConversationTurn(BaseModel):
    """One query/answer exchange within a session."""

    session_id: str
    query: str
    documents: list[str]
    generation: str
    is_safe: bool
    created_at: datetime | None = None  # set by Postgres on insert


class SessionSummary(BaseModel):
    """One row in the sidebar's chat list."""

    session_id: str
    title: str
    last_message_at: datetime
    message_count: int


class SessionDetail(BaseModel):
    """Full session payload for the session explorer detail view."""

    session_id: str
    title: str
    last_message_at: datetime
    message_count: int
    turns: list[ConversationTurn] = []
