"""
Fitness curve plots from generation_stats.jsonl.

Generates:
  - fitness_curves.png       : mean / max / min fitness over generations
  - fitness_components.png   : per-component fitness breakdown
  - population_diversity.png : population diversity over generations
"""

import json
import os
from typing import List, Dict, Optional

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from snackPersona.utils.logger import logger


def _load_stats(store_dir: str) -> List[Dict]:
    """Load all generation records from the JSONL stats file."""
    path = os.path.join(store_dir, "generation_stats.jsonl")
    if not os.path.exists(path):
        logger.warning(f"Stats file not found: {path}")
        return []
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def plot_fitness_curves(store_dir: str, output_dir: Optional[str] = None) -> str:
    """
    Plot mean / max / min fitness across generations.

    Returns path to the saved PNG.
    """
    records = _load_stats(store_dir)
    if not records:
        logger.warning("No stats to plot")
        return ""

    out = output_dir or os.path.join(store_dir, "plots")
    os.makedirs(out, exist_ok=True)

    gens = [r["generation"] for r in records]
    means = [r["fitness_mean"] for r in records]
    maxes = [r["fitness_max"] for r in records]
    mins = [r["fitness_min"] for r in records]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(gens, means, "o-", label="Mean", color="#2196F3", linewidth=2)
    ax.plot(gens, maxes, "^-", label="Max", color="#4CAF50", linewidth=1.5, alpha=0.8)
    ax.plot(gens, mins, "v-", label="Min", color="#FF5722", linewidth=1.5, alpha=0.8)
    ax.fill_between(gens, mins, maxes, alpha=0.1, color="#2196F3")

    ax.set_xlabel("Generation", fontsize=12)
    ax.set_ylabel("Fitness", fontsize=12)
    ax.set_title("Fitness Progression", fontsize=14, fontweight="bold")
    ax.legend(fontsize=11)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    path = os.path.join(out, "fitness_curves.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    logger.info(f"Saved fitness curves → {path}")
    return path


def plot_fitness_components(store_dir: str, output_dir: Optional[str] = None) -> str:
    """
    Plot per-component fitness averages across generations.

    Returns path to the saved PNG.
    """
    records = _load_stats(store_dir)
    if not records:
        return ""

    out = output_dir or os.path.join(store_dir, "plots")
    os.makedirs(out, exist_ok=True)

    components = ["post_quality", "reply_quality", "engagement", "authenticity", "diversity"]
    colors = ["#2196F3", "#4CAF50", "#FF9800", "#9C27B0", "#E91E63"]

    gens = [r["generation"] for r in records]

    fig, ax = plt.subplots(figsize=(10, 6))

    for comp, color in zip(components, colors):
        values = []
        for r in records:
            agents = r.get("agents", [])
            if agents:
                avg = sum(a.get(comp, 0) for a in agents) / len(agents)
            else:
                avg = 0.0
            values.append(avg)
        ax.plot(gens, values, "o-", label=comp.replace("_", " ").title(),
                color=color, linewidth=2)

    ax.set_xlabel("Generation", fontsize=12)
    ax.set_ylabel("Score", fontsize=12)
    ax.set_title("Fitness Components Breakdown", fontsize=14, fontweight="bold")
    ax.legend(fontsize=10)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    path = os.path.join(out, "fitness_components.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    logger.info(f"Saved fitness components → {path}")
    return path


def plot_population_diversity(store_dir: str, output_dir: Optional[str] = None) -> str:
    """
    Plot population diversity score over generations.

    Returns path to the saved PNG.
    """
    records = _load_stats(store_dir)
    if not records:
        return ""

    out = output_dir or os.path.join(store_dir, "plots")
    os.makedirs(out, exist_ok=True)

    gens = [r["generation"] for r in records]
    divs = [r.get("population_diversity", 0) for r in records]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(gens, divs, "s-", color="#009688", linewidth=2, markersize=8)
    ax.fill_between(gens, 0, divs, alpha=0.15, color="#009688")

    ax.set_xlabel("Generation", fontsize=12)
    ax.set_ylabel("Population Diversity", fontsize=12)
    ax.set_title("Population Diversity Over Generations", fontsize=14, fontweight="bold")
    ax.set_ylim(0, 1)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    path = os.path.join(out, "population_diversity.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    logger.info(f"Saved population diversity → {path}")
    return path
