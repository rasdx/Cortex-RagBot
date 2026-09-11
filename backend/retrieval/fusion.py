"""
Merges two ranked lists using Reciprocal Rank Fusion.
Section 7 contract: reciprocal_rank_fusion(a, b, k) -> list[Hit]
Formula (Section 2): score(doc) = sum(1 / (k + rank_in_list))
"""


def reciprocal_rank_fusion(
    a: list[tuple[str, str]],
    b: list[tuple[str, str]],
    k: int,
) -> list[tuple[str, str]]:
    """Fuse two ranked (chunk_id, chunk_text) lists via RRF, without needing
    comparable similarity scores between the two ranking methods."""
    scores: dict[str, float] = {}
    texts: dict[str, str] = {}

    for ranked_list in (a, b):
        for rank, (chunk_id, chunk_text) in enumerate(ranked_list):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)
            texts[chunk_id] = chunk_text

    ranked_ids = sorted(scores, key=lambda cid: scores[cid], reverse=True)
    return [(chunk_id, texts[chunk_id]) for chunk_id in ranked_ids]
