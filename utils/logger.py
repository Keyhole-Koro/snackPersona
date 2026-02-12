"""
Structured logger for the evolution system.

Outputs both human-readable console logs and machine-readable JSONL files
for later analysis and visualization.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional


def setup_logger(name: str = "snackPersona", level: int = logging.INFO) -> logging.Logger:
    """Create a console logger with a clean format."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s  %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger


logger = setup_logger()


class EvolutionLogger:
    """
    Logs generation-level statistics to a JSONL file and to the console.
    Each line in the JSONL file is one generation's full snapshot.
    """

    def __init__(self, store_dir: str):
        self.store_dir = store_dir
        self.stats_path = os.path.join(store_dir, "generation_stats.jsonl")
        os.makedirs(store_dir, exist_ok=True)

    def log_generation(
        self,
        generation: int,
        individuals: list,
        population_diversity: float,
        raw_fitness_fn=None,
    ):
        """
        Log a complete generation snapshot.

        Args:
            generation: Generation number.
            individuals: List of Individual objects.
            population_diversity: Population-level diversity score.
            raw_fitness_fn: Callable to compute raw fitness from an Individual.
        """
        agents_data = []
        fitnesses = []

        for ind in individuals:
            s = ind.scores
            raw = raw_fitness_fn(ind) if raw_fitness_fn else 0.0
            fitnesses.append(raw)

            agents_data.append({
                "name": ind.genotype.name,
                "post_quality": round(s.post_quality, 4),
                "reply_quality": round(s.reply_quality, 4),
                "engagement": round(s.engagement, 4),
                "authenticity": round(s.authenticity, 4),
                "diversity": round(s.diversity, 4),
                "safety": round(s.safety, 4),
                "raw_fitness": round(raw, 4),
                "shared_fitness": round(ind.shared_fitness, 4),
            })

        record = {
            "timestamp": datetime.now().isoformat(),
            "generation": generation,
            "population_size": len(individuals),
            "population_diversity": round(population_diversity, 4),
            "fitness_mean": round(sum(fitnesses) / max(len(fitnesses), 1), 4),
            "fitness_max": round(max(fitnesses, default=0), 4),
            "fitness_min": round(min(fitnesses, default=0), 4),
            "agents": agents_data,
        }

        # Append to JSONL
        with open(self.stats_path, "a") as f:
            f.write(json.dumps(record) + "\n")

        # Console summary
        logger.info(
            f"Gen {generation} | "
            f"PopDiv={population_diversity:.3f} | "
            f"Fitness mean={record['fitness_mean']:.3f} "
            f"max={record['fitness_max']:.3f} min={record['fitness_min']:.3f}"
        )
        for a in agents_data:
            logger.info(
                f"  {a['name']:>14s}: "
                f"Post={a['post_quality']:.2f} Reply={a['reply_quality']:.2f} "
                f"Auth={a['authenticity']:.2f} Div={a['diversity']:.2f} | "
                f"Raw={a['raw_fitness']:.3f} Shared={a['shared_fitness']:.3f}"
            )

    def log_simulation_event(self, event_type: str, agent_name: str, detail: str):
        """Log a simulation-level event to console."""
        logger.debug(f"[SIM] {event_type:>16s} | {agent_name:>12s} | {detail[:80]}")

    def log_engagement_decision(self, agent_name: str, target_author: str, engaged: bool):
        """Log whether an agent decided to engage with a post."""
        decision = "ENGAGE" if engaged else "PASS"
        logger.debug(f"[SIM] {'decision':>16s} | {agent_name:>12s} | {decision} on {target_author}'s post")
