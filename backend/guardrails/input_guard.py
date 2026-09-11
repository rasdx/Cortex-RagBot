"""
Validates and screens the raw user query before retrieval.
Section 7 contract: check_input(query) -> bool
Section 3: validates the query isn't empty/malformed and screens for toxic/unsafe content.
"""

# A small, explicit blocklist stands in for "a small classifier or moderation
# endpoint" per Section 3. Swap this for a real moderation call if one becomes available.
_BLOCKED_TERM_REASONS = {
    "kill": "violent_harm",
    "bomb": "explosive_harm",
    "hack into": "unauthorized_access",
}


def get_refusal_reason(query: str) -> str | None:
    """Return a compact guardrail reason for a blocked or unsafe query."""
    if not query or not query.strip():
        return None

    lowered = query.lower()
    for term, reason in _BLOCKED_TERM_REASONS.items():
        if term in lowered:
            return reason

    return None


async def check_input(query: str) -> bool:
    """Return True if the query is non-empty and passes the toxicity/safety screen."""
    return get_refusal_reason(query) is None and bool(query and query.strip())
