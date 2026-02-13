"""
Genotype distance for free-form description-based personas.

Uses sentence embeddings to compute semantic distance between descriptions.
"""
from snackPersona.evaluation.diversity.embedding import _get_model


def calculate_genotype_distance(g1, g2) -> float:
    """
    Semantic distance between two PersonaGenotype instances.

    Uses sentence embeddings of their bios to compute
    cosine distance. Falls back to simple string comparison if
    the embedding model is unavailable.

    Returns:
        0.0 (identical) to 1.0 (completely different).
    """
    try:
        model = _get_model()
        embeddings = model.encode([g1.bio, g2.bio])
        # Cosine similarity → distance
        from numpy import dot
        from numpy.linalg import norm
        cos_sim = dot(embeddings[0], embeddings[1]) / (
            norm(embeddings[0]) * norm(embeddings[1]) + 1e-8
        )
        return float(max(0.0, min(1.0, 1.0 - cos_sim)))
    except Exception:
        # Fallback: simple string comparison
        if g1.bio == g2.bio:
            return 0.0
        # Rough character-level similarity
        common = sum(1 for a, b in zip(g1.bio, g2.bio) if a == b)
        max_len = max(len(g1.bio), len(g2.bio), 1)
        return 1.0 - (common / max_len)
