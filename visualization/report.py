"""
Report generator — runs all visualization modules and produces a complete
set of plots in ``{store_dir}/plots/``.
"""

import os
from typing import List

from snackPersona.utils.logger import logger


def generate_report(store_dir: str) -> List[str]:
    """
    Generate all available plots from evolution data.

    Parameters
    ----------
    store_dir : str
        Directory containing generation JSON files and ``generation_stats.jsonl``.

    Returns
    -------
    list[str]
        Paths to all generated plot PNGs (empty strings filtered out).
    """
    output_dir = os.path.join(store_dir, "plots")
    os.makedirs(output_dir, exist_ok=True)

    logger.info(f"Generating visualisation report → {output_dir}")

    paths: List[str] = []

    # Fitness plots
    from snackPersona.visualization.fitness_plot import (
        plot_fitness_curves,
        plot_fitness_components,
        plot_population_diversity,
    )
    paths.append(plot_fitness_curves(store_dir, output_dir))
    paths.append(plot_fitness_components(store_dir, output_dir))
    paths.append(plot_population_diversity(store_dir, output_dir))

    # Persona space
    from snackPersona.visualization.persona_space import (
        plot_persona_space_pca,
        plot_persona_space_tsne,
    )
    paths.append(plot_persona_space_pca(store_dir, output_dir))
    paths.append(plot_persona_space_tsne(store_dir, output_dir))

    # Diversity
    from snackPersona.visualization.diversity_plot import (
        plot_diversity_heatmap,
        plot_description_length,
        plot_description_wordcloud,
    )
    paths.append(plot_diversity_heatmap(store_dir, output_dir))
    paths.append(plot_description_length(store_dir, output_dir))
    paths.append(plot_description_wordcloud(store_dir, output_dir))

    paths = [p for p in paths if p]

    logger.info(f"Report complete — {len(paths)} plots generated")
    return paths
