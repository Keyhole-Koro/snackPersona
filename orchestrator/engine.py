from typing import List, Callable, Optional, Dict
import random
import math
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

# Fitness weight configuration
FITNESS_WEIGHTS = {
    'engagement': 0.35,
    'conversation_quality': 0.35,
    'diversity': 0.20,
    'persona_fidelity': 0.10,
}

# Niching parameters
NICHE_SIGMA = 0.5   # Niche radius — individuals closer than this share fitness
NICHE_ALPHA = 1.0   # Shape parameter for sharing function


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
        media_dataset: Optional[MediaDataset] = None
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
        
        self.population: List[Individual] = []
        self.current_generation = 0

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

    # ------------------------------------------------------------------ #
    #  Fitness calculation
    # ------------------------------------------------------------------ #

    @staticmethod
    def _raw_fitness(ind: Individual) -> float:
        """Weighted fitness score from individual's FitnessScores."""
        s = ind.scores
        return (
            FITNESS_WEIGHTS['engagement'] * s.engagement
            + FITNESS_WEIGHTS['conversation_quality'] * s.conversation_quality
            + FITNESS_WEIGHTS['diversity'] * s.diversity
            + FITNESS_WEIGHTS['persona_fidelity'] * s.persona_fidelity
        )

    @staticmethod
    def _sharing_function(distance: float) -> float:
        """
        Fitness sharing function.
        Returns 1 when distance=0, 0 when distance>=sigma.
        """
        if distance >= NICHE_SIGMA:
            return 0.0
        return 1.0 - (distance / NICHE_SIGMA) ** NICHE_ALPHA

    def _apply_fitness_sharing(self):
        """
        Niching via fitness sharing.
        Each individual's fitness is divided by its niche count,
        penalising clusters of similar genotypes.
        """
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
            
            # Niche count = sum of sharing function values with all others (+ 1 for self)
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
        """
        Runs the full evolution process.
        """
        for gen in range(self.generations):
            self.current_generation = gen
            print(f"--- Generation {gen} ---")
            
            # 1. Simulate & Evaluate
            self._evaluate_population()
            
            # 2. Apply niching / fitness sharing
            self._apply_fitness_sharing()
            
            # 3. Log & Save Stats
            self.store.save_generation(gen, [ind.genotype for ind in self.population])
            self._print_generation_summary()
            
            # Check stopping condition
            if gen == self.generations - 1:
                break
                
            # 4. Selection & Reproduction
            next_generation = self._produce_next_generation()
            self.population = next_generation

    def _evaluate_population(self):
        """
        Runs simulation episodes and assigns fitness scores.
        Also computes and prints population-level diversity.
        """
        # Batch agents into groups for simulation (e.g. groups of 4)
        group_size = 4
        
        # Shuffle for randomness
        indices = list(range(len(self.population)))
        random.shuffle(indices)
        
        # Collect all posts per agent for population diversity later
        all_agent_posts: Dict[str, List[str]] = {}
        
        for i in range(0, len(indices), group_size):
            group_indices = indices[i : i+group_size]
            group_individuals = [self.population[idx] for idx in group_indices]
            
            # Create Simulation Agents
            sim_agents = [SimulationAgent(ind.genotype, self.llm_client) for ind in group_individuals]
            
            # Run Simulation
            env = SimulationEnvironment(sim_agents)
            
            # Run both traditional episode and media episode if dataset available
            transcript = env.run_episode(rounds=2)
            
            # If media dataset is available, also run a media-based episode
            if self.media_dataset and len(self.media_dataset) > 0:
                media_items = self.media_dataset.get_all_media_items()
                selected_media = random.choice(media_items)
                media_transcript = env.run_media_episode(selected_media, rounds=1)
                transcript.extend(media_transcript)
            
            # Evaluate each individual and collect posts
            for ind in group_individuals:
                scores = self.evaluator.evaluate(ind.genotype, transcript)
                ind.scores = scores
                
                # Collect posts for population-level diversity
                my_posts = [
                    e.get('content', '')
                    for e in transcript
                    if e.get('author') == ind.genotype.name
                ]
                all_agent_posts[ind.genotype.name] = my_posts
        
        # Compute population-level diversity
        pop_diversity = DiversityEvaluator.calculate_population_diversity(all_agent_posts)
        print(f"  Population diversity: {pop_diversity:.3f}")

    def _print_generation_summary(self):
        """Print per-agent summary after fitness sharing."""
        for ind in self.population:
            s = ind.scores
            print(
                f"  {ind.genotype.name}: "
                f"Eng={s.engagement:.2f} Qual={s.conversation_quality:.2f} "
                f"Div={s.diversity:.2f} Fid={s.persona_fidelity:.2f} | "
                f"Raw={self._raw_fitness(ind):.3f} Shared={ind.shared_fitness:.3f}"
            )

    def _produce_next_generation(self) -> List[Individual]:
        """
        Selects parents and creates offspring.
        Uses shared_fitness (diversity-adjusted) for selection.
        """
        # Sort by shared fitness (niching-adjusted)
        sorted_pop = sorted(
            self.population, 
            key=lambda ind: ind.shared_fitness, 
            reverse=True
        )
        
        # Elitism — keep top individuals by shared fitness
        next_gen = [
            Individual(genotype=ind.genotype, phenotype=ind.phenotype)
            for ind in sorted_pop[:self.elite_count]
        ]
        
        # Fill the rest via tournament selection on shared_fitness
        while len(next_gen) < self.population_size:
            # Tournament selection (size 3), using shared_fitness
            p1 = max(
                random.sample(self.population, min(3, len(self.population))),
                key=lambda i: i.shared_fitness
            ).genotype
            p2 = max(
                random.sample(self.population, min(3, len(self.population))),
                key=lambda i: i.shared_fitness
            ).genotype
            
            # Crossover
            child_genotype = self.crossover_op.crossover(p1, p2)
            
            # Mutation (20% chance)
            if random.random() < 0.2:
                child_genotype = self.mutation_op.mutate(child_genotype)
                
            next_gen.append(Individual(genotype=child_genotype, phenotype=compile_persona(child_genotype)))
            
        return next_gen
