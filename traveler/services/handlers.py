import random
import copy
from typing import List

from snackPersona.traveler.utils.data_models import (
    TravelerGenome,
    SourceBias,
    ExecutionResult,
    EvaluatedTraveler
)
from snackPersona.traveler.evaluation.fitness import calculate_fitness
from snackPersona.traveler.evaluation.features import calculate_feature_descriptors
from snackPersona.traveler.map_elites.elite_map import EliteMap
# --- Handler 1: Evaluation and Map Management ---

def evaluation_and_map_management_handler(
    result: ExecutionResult, 
    elite_map: EliteMap,
    bandit_allocator: BanditAllocator = None,
    is_bandit_run: bool = False,
    feedback_reward: float = None  # New argument
) -> EvaluatedTraveler:
    """
    Simulates the service that evaluates a result and updates the elite map.
    If it was a bandit run, it also updates the bandit model.
    """
    # 1. Calculate fitness and features
    fitness = calculate_fitness(result)
    features = calculate_feature_descriptors(result)

    # Extract domains for uniqueness calculation
    from urllib.parse import urlparse
    domains = set()
    for url in result.retrieved_urls:
        try:
            domains.add(urlparse(url).netloc)
        except:
            pass
    domain_list = list(domains)
    
    # Override downstream_value if feedback is provided
    if feedback_reward is not None:
        fitness.downstream_value = feedback_reward
    
    # This part would require fetching the original genome from a database
    # For simulation, we assume we have it or can reconstruct it.
    # Here, we'll just create a placeholder genome.
    # In the main script, we will pass the actual genome.
    temp_genome = TravelerGenome(
        genome_id=result.genome_id,
        query_diversity=0.5, query_template_id="template_v1_broad",
        language_mix=0.5, source_bias=SourceBias(academic=0, news=0, official=0, blogs=0),
        search_depth=1, novelty_weight=0.5
    )

    evaluated_traveler = EvaluatedTraveler(
        genome=temp_genome, # This will be replaced in the main loop
        fitness=fitness,
        features=features,
        retrieved_domains=domain_list
    )
    
    # 2. Add to elite map (this logic will be external to the handler in the main loop)
    # elite_map.add_individual(evaluated_traveler)

    # 3. If this run was triggered by the bandit, update the bandit model
    if is_bandit_run and bandit_allocator:
        coords = evaluated_traveler.get_feature_tuple(elite_map.resolution)
        # Use the (potentially overridden) downstream_value as reward
        reward = evaluated_traveler.fitness.downstream_value
        bandit_allocator.update_arm(coords, reward)
        
    return evaluated_traveler


# --- Handler 2: Generation Scheduler ---

def _mutate_genome(genome: TravelerGenome) -> TravelerGenome:
    """Applies a small mutation to a genome to create a child."""
    new_genome = copy.deepcopy(genome)
    new_genome.genome_id = None # Let the model assign a new one
    
    # Example mutation operators
    mutation_type = random.choice(['diversity', 'template', 'bias', 'depth'])
    
    if mutation_type == 'diversity':
        new_genome.query_diversity = max(0.0, min(1.0, new_genome.query_diversity + random.uniform(-0.1, 0.1)))
    elif mutation_type == 'template':
        templates = ["template_v1_broad", "template_v2_specific", "template_v3_questioning", "template_v4_news_focused"]
        new_genome.query_template_id = random.choice(templates)
    elif mutation_type == 'bias':
        bias_to_change = random.choice(['academic', 'news', 'official', 'blogs'])
        current_bias = getattr(new_genome.source_bias, bias_to_change)
        new_bias = max(-1.0, min(1.0, current_bias + random.uniform(-0.2, 0.2)))
        setattr(new_genome.source_bias, bias_to_change, new_bias)
    elif mutation_type == 'depth':
        new_genome.search_depth = 1 if new_genome.search_depth == 2 else 2
        
    return TravelerGenome.model_validate(new_genome.model_dump(exclude_none=True)) # Re-validate and get new UUID

def generation_scheduler_handler(elite_map: EliteMap, num_offspring: int) -> List[TravelerGenome]:
    """
    Simulates the periodic job that creates new individuals for exploration.
    """
    parents = elite_map.get_random_elites(k=num_offspring)
    if not parents:
        return []
    
    offspring = []
    for _ in range(num_offspring):
        parent = random.choice(parents)
        child_genome = _mutate_genome(parent.genome)
        offspring.append(child_genome)
        
    return offspring

# --- Handler 3: Bandit Allocator ---

def bandit_allocator_handler(bandit_allocator: BanditAllocator, elite_map: EliteMap) -> TravelerGenome:
    """
    Simulates a request to get the best traveler for a production task.
    """
    # 1. Select the most promising niche
    chosen_coords = bandit_allocator.select_arm()
    
    # 2. Get the elite from that niche
    elite = elite_map.get_elite(chosen_coords)
    
    if elite:
        return elite.genome
    else:
        # If the chosen niche has no elite (e.g., at the beginning),
        # fall back to a random elite from the map, or create a random genome.
        random_elites = elite_map.get_random_elites(k=1)
        if random_elites:
            return random_elites[0].genome
        else:
            # Absolute fallback: create a default/random genome
            return TravelerGenome(
                query_diversity=0.5,
                query_template_id="template_v1_broad",
                language_mix=random.random(),
                source_bias=SourceBias(academic=0, news=0, official=0, blogs=0),
                search_depth=1,
                novelty_weight=0.5
            )

