"""
Persona space dimensionality reduction and visualization.

Generates:
  - persona_space_pca.png   : PCA 2-D projection of genotype vectors
  - persona_space_tsne.png  : t-SNE 2-D projection of genotype vectors

Each dot is an individual persona coloured by generation.
"""

import json
import os
from typing import List, Dict, Optional, Tuple

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.cm as cm

from snackPersona.utils.data_models import PersonaGenotype
from snackPersona.utils.logger import logger


# ------------------------------------------------------------------ #
#  Feature extraction
# ------------------------------------------------------------------ #

# Categorical vocabularies built on first call
_VOCAB_CACHE: Dict[str, Dict[str, int]] = {}


def _build_vocab(values: List[str], name: str) -> Dict[str, int]:
    if name not in _VOCAB_CACHE:
        unique = sorted(set(values))
        _VOCAB_CACHE[name] = {v: i for i, v in enumerate(unique)}
    return _VOCAB_CACHE[name]


def _persona_to_vector(
    g: PersonaGenotype,
    all_hobbies: List[str],
    all_values: List[str],
    all_goals: List[str],
    style_vocab: Dict[str, int],
    topic_vocab: Dict[str, int],
) -> np.ndarray:
    """Convert a PersonaGenotype into a fixed-length numeric vector."""
    features: List[float] = []

    # Age — normalised
    features.append((g.age - 18) / 62.0)

    # Personality traits (sorted keys for consistency)
    trait_keys = sorted({
        "openness", "conscientiousness", "extraversion",
        "agreeableness", "neuroticism",
    })
    for k in trait_keys:
        features.append(g.personality_traits.get(k, 0.5))

    # Multi-hot: hobbies
    hobby_set = set(g.hobbies)
    for h in all_hobbies:
        features.append(1.0 if h in hobby_set else 0.0)

    # Multi-hot: core values
    val_set = set(g.core_values)
    for v in all_values:
        features.append(1.0 if v in val_set else 0.0)

    # Multi-hot: goals
    goal_set = set(g.goals)
    for gl in all_goals:
        features.append(1.0 if gl in goal_set else 0.0)

    # One-hot: communication style
    n_styles = len(style_vocab)
    style_vec = [0.0] * n_styles
    idx = style_vocab.get(g.communication_style, -1)
    if idx >= 0:
        style_vec[idx] = 1.0
    features.extend(style_vec)

    # One-hot: topical focus
    n_topics = len(topic_vocab)
    topic_vec = [0.0] * n_topics
    idx = topic_vocab.get(g.topical_focus, -1)
    if idx >= 0:
        topic_vec[idx] = 1.0
    features.extend(topic_vec)

    return np.array(features, dtype=np.float64)


def _load_all_personas(store_dir: str) -> Tuple[List[PersonaGenotype], List[int]]:
    """Load all personas from all generation files. Returns (personas, gen_ids)."""
    personas: List[PersonaGenotype] = []
    gen_ids: List[int] = []

    gen_files = sorted(
        f for f in os.listdir(store_dir)
        if f.startswith("gen_") and f.endswith(".json")
    )

    for fname in gen_files:
        try:
            gen_id = int(fname.split("_")[1].split(".")[0])
        except ValueError:
            continue
        path = os.path.join(store_dir, fname)
        with open(path) as f:
            data = json.load(f)
        for item in data:
            personas.append(PersonaGenotype(**item))
            gen_ids.append(gen_id)

    return personas, gen_ids


# ------------------------------------------------------------------ #
#  Vectorise all personas
# ------------------------------------------------------------------ #

def _vectorise(personas: List[PersonaGenotype]) -> np.ndarray:
    """Convert a list of personas to a feature matrix (N × D)."""
    # Collect vocabularies
    all_hobbies = sorted({h for p in personas for h in p.hobbies})
    all_values = sorted({v for p in personas for v in p.core_values})
    all_goals = sorted({g for p in personas for g in p.goals})

    style_vocab = _build_vocab(
        [p.communication_style for p in personas], "style"
    )
    topic_vocab = _build_vocab(
        [p.topical_focus for p in personas], "topic"
    )

    vecs = [
        _persona_to_vector(p, all_hobbies, all_values, all_goals, style_vocab, topic_vocab)
        for p in personas
    ]
    return np.vstack(vecs)


# ------------------------------------------------------------------ #
#  Plotting
# ------------------------------------------------------------------ #

def _scatter_plot(
    coords: np.ndarray,
    gen_ids: List[int],
    names: List[str],
    title: str,
    path: str,
):
    """Scatter plot with generation colouring and name labels."""
    unique_gens = sorted(set(gen_ids))
    n_gens = max(len(unique_gens), 1)
    cmap = cm.get_cmap("viridis", n_gens)
    gen_to_idx = {g: i for i, g in enumerate(unique_gens)}

    fig, ax = plt.subplots(figsize=(10, 8))

    for gen in unique_gens:
        mask = [i for i, g in enumerate(gen_ids) if g == gen]
        ax.scatter(
            coords[mask, 0],
            coords[mask, 1],
            c=[cmap(gen_to_idx[gen])],
            label=f"Gen {gen}",
            s=80,
            alpha=0.75,
            edgecolors="white",
            linewidth=0.5,
        )

    # Labels (avoid overlap for large pops by only labelling last gen)
    last_gen = max(unique_gens)
    for i, (x, y) in enumerate(coords):
        if gen_ids[i] == last_gen:
            ax.annotate(
                names[i],
                (x, y),
                fontsize=7,
                alpha=0.8,
                textcoords="offset points",
                xytext=(5, 5),
            )

    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.legend(fontsize=9, loc="best")
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    logger.info(f"Saved persona space plot → {path}")


def plot_persona_space_pca(store_dir: str, output_dir: Optional[str] = None) -> str:
    """PCA 2-D projection of persona genotype space."""
    from sklearn.decomposition import PCA

    personas, gen_ids = _load_all_personas(store_dir)
    if len(personas) < 3:
        logger.warning("Not enough personas for PCA plot")
        return ""

    X = _vectorise(personas)
    pca = PCA(n_components=2)
    coords = pca.fit_transform(X)

    out = output_dir or os.path.join(store_dir, "plots")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "persona_space_pca.png")

    var = pca.explained_variance_ratio_
    title = f"Persona Space (PCA) — {var[0]:.1%} + {var[1]:.1%} variance"
    _scatter_plot(coords, gen_ids, [p.name for p in personas], title, path)
    return path


def plot_persona_space_tsne(store_dir: str, output_dir: Optional[str] = None) -> str:
    """t-SNE 2-D projection of persona genotype space."""
    from sklearn.manifold import TSNE

    personas, gen_ids = _load_all_personas(store_dir)
    if len(personas) < 4:
        logger.warning("Not enough personas for t-SNE plot (need ≥ 4)")
        return ""

    X = _vectorise(personas)

    perplexity = min(30, len(personas) - 1)
    tsne = TSNE(n_components=2, perplexity=perplexity, random_state=42, max_iter=1000)
    coords = tsne.fit_transform(X)

    out = output_dir or os.path.join(store_dir, "plots")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "persona_space_tsne.png")

    _scatter_plot(
        coords, gen_ids, [p.name for p in personas],
        "Persona Space (t-SNE)", path,
    )
    return path
