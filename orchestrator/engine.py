from typing import List, Callable, Optional
import random
from snackPersona.utils.data_models import PersonaGenotype, Individual, MediaItem
from snackPersona.simulation.agent import SimulationAgent
from snackPersona.simulation.environment import SimulationEnvironment
from snackPersona.evaluation.evaluator import Evaluator
from snackPersona.orchestrator.operators import MutationOperator, CrossoverOperator
from snackPersona.persona_store.store import PersonaStore
from snackPersona.llm.llm_client import LLMClient
from snackPersona.compiler.compiler import compile_persona
from snackPersona.utils.media_dataset import MediaDataset

class EvolutionEngine:
    """
    Orchestrates the evolutionary loop:
    PopGen -> Simulation -> Evaluation -> Selection -> Reproduction -> NextGen
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
            
    def run_evolution_loop(self):
        """
        Runs the full evolution process.
        """
        for gen in range(self.generations):
            self.current_generation = gen
            print(f"--- Generation {gen} ---")
            
            # 1. Simulate & Evaluate
            self._evaluate_population()
            
            # 2. Log & Save Stats
            self.store.save_generation(gen, [ind.genotype for ind in self.population])
            
            # Check stopping condition
            if gen == self.generations - 1:
                break
                
            # 3. Selection & Reproduction
            next_generation = self._produce_next_generation()
            self.population = next_generation

    def _evaluate_population(self):
        """
        Runs simulation episodes and assigns fitness scores.
        """
        # Batch agents into groups for simulation (e.g. groups of 4)
        group_size = 4
        
        # Shuffle for randomness
        indices = list(range(len(self.population)))
        random.shuffle(indices)
        
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
                # Combine transcripts
                transcript.extend(media_transcript)
            
            # Evaluate each individual based on the transcript
            for ind, transcript_data in zip(group_individuals, [transcript]*len(group_individuals)):
                 # Note: in a real implementation we might segment transcript per agent view 
                 # or pass the whole transcript. Passing whole for context.
                 scores = self.evaluator.evaluate(ind.genotype, transcript_data)
                 ind.scores = scores
                 
                 # Print a quick summary
                 print(f"Agent {ind.genotype.name}: Engagement={scores.engagement:.2f}, Coherence={scores.conversation_quality:.2f}, Diversity={scores.diversity:.2f}")

    def _produce_next_generation(self) -> List[Individual]:
        """
        Selects parents and creates offspring.
        """
        # Sort by a weighted fitness score (simple sum for now)
        sorted_pop = sorted(
            self.population, 
            key=lambda ind: ind.scores.engagement + ind.scores.conversation_quality, 
            reverse=True
        )
        
        # Elitism
        next_gen = sorted_pop[:self.elite_count]
        
        # Fill the rest
        while len(next_gen) < self.population_size:
            # Tournament Selection (size 3)
            parents = random.sample(sorted_pop, 2) # Should be tournament logic, simplifying to random selection from top half for brevity
            # Actually let's do a simple tournament
            p1 = max(random.sample(self.population, 3), key=lambda i: i.scores.engagement).genotype
            p2 = max(random.sample(self.population, 3), key=lambda i: i.scores.engagement).genotype
            
            # Crossover
            child_genotype = self.crossover_op.crossover(p1, p2)
            
            # Mutation (small chance)
            if random.random() < 0.2:
                child_genotype = self.mutation_op.mutate(child_genotype)
                
            next_gen.append(Individual(genotype=child_genotype, phenotype=compile_persona(child_genotype)))
            
        return next_gen
