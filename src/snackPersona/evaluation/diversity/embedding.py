from typing import List, Dict
from itertools import combinations
import numpy as np

# Lazy-load sentence-transformers to avoid import cost when not used
_model = None


def _get_model():
    """Lazily load the sentence-transformers model on first use."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm == 0:
        return 0.0
    return float(dot / norm)


def calculate_embedding_diversity(texts: List[str]) -> float:
    """
    Diversity of a set of texts via pairwise cosine distance of embeddings.

    Returns:
        0.0 (all identical) to 1.0 (all completely different).
    """
    if not texts or len(texts) < 2:
        return 0.0

    texts = [t for t in texts if t.strip()]
    if len(texts) < 2:
        return 0.0

    model = _get_model()
    embeddings = model.encode(texts, convert_to_numpy=True)

    similarities = []
    for i, j in combinations(range(len(embeddings)), 2):
        sim = cosine_similarity(embeddings[i], embeddings[j])
        similarities.append(sim)

    if not similarities:
        return 0.0

    mean_similarity = sum(similarities) / len(similarities)
    return max(0.0, min(1.0, 1.0 - mean_similarity))


def calculate_population_diversity(agent_posts: Dict[str, List[str]]) -> float:
    """
    Measure how different agents are from each other based on their
    combined post embeddings.

    Args:
        agent_posts: {agent_name: [post_text, ...]} for every agent.

    Returns:
        0.0 (all agents say the same things) to 1.0 (agents are very distinct).
    """
    agents = list(agent_posts.keys())
    if len(agents) < 2:
        return 0.0

    model = _get_model()

    # One representative embedding per agent (mean of post embeddings)
    agent_embeddings = {}
    for name, posts in agent_posts.items():
        posts = [p for p in posts if p.strip()]
        if not posts:
            continue
        embs = model.encode(posts, convert_to_numpy=True)
        agent_embeddings[name] = np.mean(embs, axis=0)

    if len(agent_embeddings) < 2:
        return 0.0

    embeddings_list = list(agent_embeddings.values())
    similarities = []
    for i, j in combinations(range(len(embeddings_list)), 2):
        sim = cosine_similarity(embeddings_list[i], embeddings_list[j])
        similarities.append(sim)

    mean_sim = sum(similarities) / len(similarities)
    return max(0.0, min(1.0, 1.0 - mean_sim))
