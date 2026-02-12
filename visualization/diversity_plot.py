"""
Diversity analysis visualizations for free-form personas.

Generates:
  - diversity_heatmap.png          : pairwise genotype distance heatmap (last gen)
  - description_wordcloud.png      : word cloud of persona descriptions (last gen)
  - description_length_dist.png    : description length distribution across generations
"""

import json
import os
from typing import List, Optional

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.cm as cm

from snackPersona.utils.data_models import PersonaGenotype
from snackPersona.evaluation.diversity.genotype import calculate_genotype_distance
from snackPersona.utils.logger import logger


def _load_generation(store_dir: str, gen_id: int) -> List[PersonaGenotype]:
    path = os.path.join(store_dir, f"gen_{gen_id}.json")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        data = json.load(f)
    return [PersonaGenotype(**item) for item in data]


def _available_gens(store_dir: str) -> List[int]:
    gens = []
    for fname in os.listdir(store_dir):
        if fname.startswith("gen_") and fname.endswith(".json"):
            try:
                gens.append(int(fname.split("_")[1].split(".")[0]))
            except ValueError:
                continue
    return sorted(gens)


# ------------------------------------------------------------------ #
#  Heatmap
# ------------------------------------------------------------------ #

def plot_diversity_heatmap(store_dir: str, output_dir: Optional[str] = None) -> str:
    """Pairwise genotype distance heatmap of the last generation."""
    gens = _available_gens(store_dir)
    if not gens:
        return ""
    personas = _load_generation(store_dir, gens[-1])
    if len(personas) < 2:
        return ""

    n = len(personas)
    dist_matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            d = calculate_genotype_distance(personas[i], personas[j])
            dist_matrix[i, j] = d
            dist_matrix[j, i] = d

    names = [p.name for p in personas]

    out = output_dir or os.path.join(store_dir, "plots")
    os.makedirs(out, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(dist_matrix, cmap="YlOrRd", vmin=0, vmax=1)
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(names, rotation=45, ha="right", fontsize=9)
    ax.set_yticklabels(names, fontsize=9)
    ax.set_title(f"Genotype Distance (Gen {gens[-1]})", fontsize=14, fontweight="bold")
    fig.colorbar(im, ax=ax, label="Distance", shrink=0.8)

    # Annotate cells
    for i in range(n):
        for j in range(n):
            ax.text(j, i, f"{dist_matrix[i, j]:.2f}",
                    ha="center", va="center", fontsize=7,
                    color="white" if dist_matrix[i, j] > 0.5 else "black")

    fig.tight_layout()
    path = os.path.join(out, "diversity_heatmap.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    logger.info(f"Saved diversity heatmap → {path}")
    return path


# ------------------------------------------------------------------ #
#  Description length distribution
# ------------------------------------------------------------------ #

def plot_description_length(store_dir: str, output_dir: Optional[str] = None) -> str:
    """Description character-length distribution across generations."""
    gens = _available_gens(store_dir)
    if len(gens) < 2:
        return ""

    out = output_dir or os.path.join(store_dir, "plots")
    os.makedirs(out, exist_ok=True)

    lengths_by_gen = {}
    for g in gens:
        personas = _load_generation(store_dir, g)
        if not personas:
            continue
        lengths_by_gen[g] = [len(p.description) for p in personas]

    fig, ax = plt.subplots(figsize=(10, 5))
    data = [lengths_by_gen.get(g, []) for g in gens]
    bp = ax.boxplot(data, labels=[f"Gen {g}" for g in gens], patch_artist=True)
    for patch in bp["boxes"]:
        patch.set_facecolor("#90CAF9")
    ax.set_title("Persona Description Length", fontsize=13, fontweight="bold")
    ax.set_ylabel("Characters")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    path = os.path.join(out, "description_length_dist.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    logger.info(f"Saved description length plot → {path}")
    return path


# ------------------------------------------------------------------ #
#  Word cloud (optional — requires wordcloud library)
# ------------------------------------------------------------------ #

def plot_description_wordcloud(store_dir: str, output_dir: Optional[str] = None) -> str:
    """Word cloud of persona descriptions from the last generation."""
    try:
        from wordcloud import WordCloud
    except ImportError:
        logger.debug("wordcloud library not installed, skipping word cloud")
        return ""

    gens = _available_gens(store_dir)
    if not gens:
        return ""
    personas = _load_generation(store_dir, gens[-1])
    if not personas:
        return ""

    text = " ".join(p.description for p in personas)

    out = output_dir or os.path.join(store_dir, "plots")
    os.makedirs(out, exist_ok=True)

    wc = WordCloud(width=800, height=400, background_color="white").generate(text)

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    ax.set_title(f"Persona Descriptions (Gen {gens[-1]})", fontsize=14, fontweight="bold")
    fig.tight_layout()

    path = os.path.join(out, "description_wordcloud.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    logger.info(f"Saved description word cloud → {path}")
    return path


# Keep backward compatibility for report.py
plot_trait_radar = lambda *a, **kw: ""
plot_attribute_distribution = lambda *a, **kw: ""
