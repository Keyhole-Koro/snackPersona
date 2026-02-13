"""
Persona space dimensionality reduction and visualization.

Uses sentence embeddings of persona descriptions for meaningful
2-D projections via PCA and t-SNE.

Generates:
  - persona_space_pca.png   : PCA 2-D projection
  - persona_space_tsne.png  : t-SNE 2-D projection

Each dot is an individual persona coloured by generation.
"""

import json
import os
from typing import List, Optional, Tuple

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.cm as cm

from snackPersona.utils.data_models import PersonaGenotype
from snackPersona.utils.logger import logger


# ------------------------------------------------------------------ #
#  Feature extraction via sentence embeddings
# ------------------------------------------------------------------ #

_MODEL_CACHE = None


def _get_embedding_model():
    """Lazy-load sentence-transformers model."""
    global _MODEL_CACHE
    if _MODEL_CACHE is None:
        try:
            from sentence_transformers import SentenceTransformer
            _MODEL_CACHE = SentenceTransformer("all-MiniLM-L6-v2")
        except ImportError:
            logger.warning("sentence-transformers not installed, using fallback vectorization")
            return None
    return _MODEL_CACHE


def _persona_to_vector_embedding(personas: List[PersonaGenotype]) -> np.ndarray:
    """Convert personas to vectors using sentence embeddings."""
    model = _get_embedding_model()
    if model is None:
        return _persona_to_vector_fallback(personas)
    texts = [f"{p.name}: {p.bio}" for p in personas]
    embeddings = model.encode(texts, show_progress_bar=False)
    return np.array(embeddings, dtype=np.float64)


def _persona_to_vector_fallback(personas: List[PersonaGenotype]) -> np.ndarray:
    """Fallback: simple character-level frequency vector."""
    chars = "abcdefghijklmnopqrstuvwxyz0123456789 "
    vectors = []
    for p in personas:
        text = (p.name + " " + p.bio).lower()
        total = max(len(text), 1)
        vec = [text.count(c) / total for c in chars]
        vectors.append(vec)
    return np.array(vectors, dtype=np.float64)


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
    return _persona_to_vector_embedding(personas)


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
    """PCA 2-D projection of persona description space."""
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
    """t-SNE 2-D projection of persona description space."""
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
