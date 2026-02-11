from typing import List, Callable, Optional, Dict
import random
import json
import os
from snackPersona.utils.data_models import PersonaGenotype, Individual, MediaItem
from snackPersona.simulation.agent import SimulationAgent
from snackPersona.simulation.environment import SimulationEnvironment
from snackPersona.evaluation.evaluator import Evaluator
from snackPersona.evaluation.diversity import DiversityEvaluator
from snackPersona.orchestrator.operators import MutationOperator, CrossoverOperator
from snackPersona.persona_store.store import PersonaStore
from snackPersona.llm.llm_client import LLMClient
from snackPersona.compiler.compiler import compile_persona
from snackPersona.utils.media_dataset import MediaDataset
from snackPersona.utils.logger import logger, EvolutionLogger

# Default config — overridden by JSON config if provided
DEFAULT_CONFIG = {
    "fitness_weights": {
        "engagement": 0.35,
        "conversation_quality": 0.35,
        "diversity": 0.20,
        "persona_fidelity": 0.10,
    },
    "niching": {
        "sigma": 0.5,
        "alpha": 1.0,
    },
    "simulation": {
        "group_size": 4,
        "reply_rounds": 3,
        "mutation_rate": 0.2,
    },
}


class EvolutionEngine:
    """
    Orchestrates the evolutionary loop:
    PopGen -> Simulation -> Evaluation -> Fitness Sharing -> Selection -> Reproduction -> NextGen
    """
    def __init__(
        self,
        llm_client: LLMClient,
        store: PersonaStore,
        evaluator: Evaluator,
        mutation_op: MutationOperator,
        crossover_op: CrossoverOperator,
        population_size: int = 10,
        generations: int = 5,
        elite_count: int = 2,
        media_dataset: Optional[MediaDataset] = None,
        config: Optional[Dict] = None,
    ):
        self.llm_client = llm_client
        self.store = store
        self.evaluator = evaluator
        self.mutation_op = mutation_op
        self.crossover_op = crossover_op
        self.population_size = population_size
        self.generations = generations
        self.elite_count = elite_count
        self.media_dataset = media_dataset

        # Merge user config with defaults
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        self.fitness_weights = self.config["fitness_weights"]
        self.niche_sigma = self.config["niching"]["sigma"]
        self.niche_alpha = self.config["niching"]["alpha"]
        self.sim_config = self.config["simulation"]

        self.population: List[Individual] = []
        self.current_generation = 0

        # Structured logger
        self.evo_logger = EvolutionLogger(store.storage_dir)

    def initialize_population(self, seed_genotypes: List[PersonaGenotype]):
        """
        Initializes the population from seed genotypes.
        If seeds < pop_size, we mutate the seeds to fill the population.
        """
        self.population = []
        for g in seed_genotypes:
            self.population.append(Individual(genotype=g, phenotype=compile_persona(g)))

        while len(self.population) < self.population_size and self.population:
            parent = random.choice(self.population).genotype
            mutant = self.mutation_op.mutate(parent)
            self.population.append(Individual(genotype=mutant, phenotype=compile_persona(mutant)))

        logger.info(f"Population initialized with {len(self.population)} individuals")

    # ------------------------------------------------------------------ #
    #  Fitness calculation
    # ------------------------------------------------------------------ #

    def _raw_fitness(self, ind: Individual) -> float:
        """Weighted fitness score from individual's FitnessScores."""
        s = ind.scores
        w = self.fitness_weights
        return (
            w['engagement'] * s.engagement
            + w['conversation_quality'] * s.conversation_quality
            + w['diversity'] * s.diversity
            + w['persona_fidelity'] * s.persona_fidelity
        )

    def _sharing_function(self, distance: float) -> float:
        """Fitness sharing function. Returns 1 when d=0, 0 when d>=sigma."""
        if distance >= self.niche_sigma:
            return 0.0
        return 1.0 - (distance / self.niche_sigma) ** self.niche_alpha

    def _apply_fitness_sharing(self):
        """Niching via fitness sharing — penalises clusters of similar genotypes."""
        n = len(self.population)

        # Precompute pairwise genotype distances
        distances: Dict[tuple, float] = {}
        for i in range(n):
            for j in range(i + 1, n):
                d = DiversityEvaluator.calculate_genotype_distance(
                    self.population[i].genotype,
                    self.population[j].genotype
                )
                distances[(i, j)] = d
                distances[(j, i)] = d

        for i in range(n):
            raw = self._raw_fitness(self.population[i])
            niche_count = 1.0  # self
            for j in range(n):
                if i == j:
                    continue
                niche_count += self._sharing_function(distances.get((i, j), 1.0))

            self.population[i].shared_fitness = raw / niche_count

    # ------------------------------------------------------------------ #
    #  Main loop
    # ------------------------------------------------------------------ #

    def run_evolution_loop(self):
        """Runs the full evolution process."""
        for gen in range(self.generations):
            self.current_generation = gen
            logger.info(f"{'=' * 40}")
            logger.info(f"Generation {gen}")
            logger.info(f"{'=' * 40}")

            # 1. Simulate & Evaluate
            pop_diversity = self._evaluate_population()

            # 2. Apply niching / fitness sharing
            self._apply_fitness_sharing()

            # 3. Log & Save
            self.store.save_generation(gen, [ind.genotype for ind in self.population])
            self.evo_logger.log_generation(
                generation=gen,
                individuals=self.population,
                population_diversity=pop_diversity,
                raw_fitness_fn=self._raw_fitness,
            )

            if gen == self.generations - 1:
                break

            # 4. Selection & Reproduction
            next_generation = self._produce_next_generation()
            self.population = next_generation

    def _evaluate_population(self) -> float:
        """Runs simulation episodes and assigns fitness scores. Returns population diversity."""
        group_size = self.sim_config.get("group_size", 4)
        reply_rounds = self.sim_config.get("reply_rounds", 3)

        indices = list(range(len(self.population)))
        random.shuffle(indices)

        all_agent_posts: Dict[str, List[str]] = {}

        for i in range(0, len(indices), group_size):
            group_indices = indices[i : i + group_size]
            group_individuals = [self.population[idx] for idx in group_indices]

            sim_agents = [SimulationAgent(ind.genotype, self.llm_client) for ind in group_individuals]
            env = SimulationEnvironment(sim_agents)

            transcript = env.run_episode(rounds=reply_rounds)

            # Optional media episode
            if self.media_dataset and len(self.media_dataset) > 0:
                media_items = self.media_dataset.get_all_media_items()
                selected_media = random.choice(media_items)
                media_transcript = env.run_media_episode(selected_media, rounds=1)
                transcript.extend(media_transcript)

            # Evaluate
            for ind in group_individuals:
                scores = self.evaluator.evaluate(ind.genotype, transcript)
                ind.scores = scores

                my_posts = [
                    e.get('content', '')
                    for e in transcript
                    if e.get('author') == ind.genotype.name and e.get('type') != 'pass'
                ]
                all_agent_posts[ind.genotype.name] = my_posts

        pop_diversity = DiversityEvaluator.calculate_population_diversity(all_agent_posts)
        return pop_diversity

    def _produce_next_generation(self) -> List[Individual]:
        """Selects parents and creates offspring using shared_fitness."""
        mutation_rate = self.sim_config.get("mutation_rate", 0.2)

        sorted_pop = sorted(
            self.population,
            key=lambda ind: ind.shared_fitness,
            reverse=True
        )

        # Elitism
        next_gen = [
            Individual(genotype=ind.genotype, phenotype=ind.phenotype)
            for ind in sorted_pop[:self.elite_count]
        ]

        # Fill via tournament selection on shared_fitness
        while len(next_gen) < self.population_size:
            p1 = max(
                random.sample(self.population, min(3, len(self.population))),
                key=lambda i: i.shared_fitness
            ).genotype
            p2 = max(
                random.sample(self.population, min(3, len(self.population))),
                key=lambda i: i.shared_fitness
            ).genotype

            child_genotype = self.crossover_op.crossover(p1, p2)

            if random.random() < mutation_rate:
                child_genotype = self.mutation_op.mutate(child_genotype)

            next_gen.append(Individual(genotype=child_genotype, phenotype=compile_persona(child_genotype)))

        logger.info(f"Next generation: {len(next_gen)} individuals produced")
        return next_gen
