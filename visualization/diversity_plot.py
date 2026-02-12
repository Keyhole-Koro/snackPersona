"""
Diversity analysis visualizations.

Generates:
  - diversity_heatmap.png     : pairwise genotype distance heatmap (last gen)
  - trait_radar.png           : radar chart of personality traits (last gen)
  - attribute_distribution.png: age and trait distributions across generations
"""

import json
import os
import math
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
#  Radar chart
# ------------------------------------------------------------------ #

def plot_trait_radar(store_dir: str, output_dir: Optional[str] = None) -> str:
    """Radar chart of personality traits for the last generation."""
    gens = _available_gens(store_dir)
    if not gens:
        return ""
    personas = _load_generation(store_dir, gens[-1])
    if not personas:
        return ""

    # Collect all trait keys
    all_keys = sorted({k for p in personas for k in p.personality_traits})
    if not all_keys:
        return ""

    n_traits = len(all_keys)
    angles = [i / n_traits * 2 * math.pi for i in range(n_traits)]
    angles += angles[:1]  # close polygon

    out = output_dir or os.path.join(store_dir, "plots")
    os.makedirs(out, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

    cmap = cm.get_cmap("Set2", len(personas))

    for idx, persona in enumerate(personas):
        values = [persona.personality_traits.get(k, 0) for k in all_keys]
        values += values[:1]
        ax.plot(angles, values, "o-", label=persona.name,
                color=cmap(idx), linewidth=1.5)
        ax.fill(angles, values, alpha=0.1, color=cmap(idx))

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(all_keys, fontsize=9)
    ax.set_ylim(0, 1)
    ax.set_title(f"Personality Traits (Gen {gens[-1]})", fontsize=14,
                 fontweight="bold", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=8)
    fig.tight_layout()

    path = os.path.join(out, "trait_radar.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    logger.info(f"Saved trait radar → {path}")
    return path


# ------------------------------------------------------------------ #
#  Attribute distributions over generations
# ------------------------------------------------------------------ #

def plot_attribute_distribution(store_dir: str, output_dir: Optional[str] = None) -> str:
    """Age and mean trait distributions across generations."""
    gens = _available_gens(store_dir)
    if len(gens) < 2:
        return ""

    out = output_dir or os.path.join(store_dir, "plots")
    os.makedirs(out, exist_ok=True)

    ages_by_gen = {}
    mean_trait_by_gen = {}

    for g in gens:
        personas = _load_generation(store_dir, g)
        if not personas:
            continue
        ages_by_gen[g] = [p.age for p in personas]
        trait_means = []
        for p in personas:
            if p.personality_traits:
                trait_means.append(
                    sum(p.personality_traits.values()) / len(p.personality_traits)
                )
        mean_trait_by_gen[g] = trait_means

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Age box plot
    ax1 = axes[0]
    data_ages = [ages_by_gen.get(g, []) for g in gens]
    bp1 = ax1.boxplot(data_ages, labels=[f"Gen {g}" for g in gens], patch_artist=True)
    for patch in bp1["boxes"]:
        patch.set_facecolor("#90CAF9")
    ax1.set_title("Age Distribution", fontsize=13, fontweight="bold")
    ax1.set_ylabel("Age")
    ax1.grid(True, alpha=0.3)

    # Mean trait box plot
    ax2 = axes[1]
    data_traits = [mean_trait_by_gen.get(g, []) for g in gens]
    bp2 = ax2.boxplot(data_traits, labels=[f"Gen {g}" for g in gens], patch_artist=True)
    for patch in bp2["boxes"]:
        patch.set_facecolor("#A5D6A7")
    ax2.set_title("Mean Personality Trait", fontsize=13, fontweight="bold")
    ax2.set_ylabel("Mean Trait Value (0–1)")
    ax2.set_ylim(0, 1)
    ax2.grid(True, alpha=0.3)

    fig.suptitle("Attribute Distributions Across Generations", fontsize=14, fontweight="bold")
    fig.tight_layout()

    path = os.path.join(out, "attribute_distribution.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    logger.info(f"Saved attribute distribution → {path}")
    return path
