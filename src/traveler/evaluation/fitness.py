from typing import List, Dict
from operator import attrgetter

from snackPersona.traveler.utils.data_models import (
    ExecutionResult,
    Fitness,
    EvaluatedTraveler,
)

def calculate_fitness(result: ExecutionResult) -> Fitness:
    """
    Calculates the multi-objective fitness scores from execution results.
    """
    # ... (Metrics 2-5 are roughly same, just shifting logic)
    
    # 1. Novelty (Simulated for now)
    novelty = 0.5 

    # 2. Coverage
    from urllib.parse import urlparse
    unique_domains = set()
    for url in result.retrieved_urls:
        try:
            unique_domains.add(urlparse(url).netloc)
        except:
            pass
    coverage = min(1.0, len(unique_domains) / 10.0)

    # 3. Reliability
    authority_scores = {'ac.jp': 0.9, 'gov': 0.9, 'go.jp': 0.9, 'nikkei.com': 0.8, 'reuters.com': 0.8}
    rel_score = 0
    for d in unique_domains:
        val = 0.5
        for k, v in authority_scores.items():
            if k in d:
                val = v
                break
        rel_score += val
    reliability = (rel_score / len(unique_domains)) if unique_domains else 0.5

    # 5. Downstream Value
    downstream_value = 0.5

    return Fitness(
        novelty=novelty,
        coverage=coverage,
        reliability=reliability,
        uniqueness=0.0, # Calculated in batch step
        downstream_value=downstream_value,
    )


def non_dominated_sort(population: List[EvaluatedTraveler]) -> List[List[EvaluatedTraveler]]:
    """
    Performs non-dominated sorting on a population (NSGA-II algorithm).

    Returns a list of fronts, where each front is a list of individuals.
    Front 0 is the best (non-dominated) front.
    """
    fronts = [[]]
    for individual in population:
        individual.domination_count = 0
        individual.dominated_solutions = []
        for other_individual in population:
            if individual.dominates(other_individual):
                individual.dominated_solutions.append(other_individual)
            elif other_individual.dominates(individual):
                individual.domination_count += 1
        
        if individual.domination_count == 0:
            individual.rank = 0
            fronts[0].append(individual)

    i = 0
    while len(fronts[i]) > 0:
        next_front = []
        for individual in fronts[i]:
            for other_individual in individual.dominated_solutions:
                other_individual.domination_count -= 1
                if other_individual.domination_count == 0:
                    other_individual.rank = i + 1
                    next_front.append(other_individual)
        i += 1
        if next_front:
            fronts.append(next_front)
        else:
            break
            
    # Clean up temporary attributes
    for ind in population:
        del ind.domination_count
        del ind.dominated_solutions

    return fronts


def calculate_crowding_distance(front: List[EvaluatedTraveler]):
    """
    Calculates the crowding distance for each individual in a front (NSGA-II).
    """
    if not front:
        return

    num_objectives = len(Fitness.model_fields)
    front_size = len(front)
    
    for ind in front:
        ind.crowding_distance = 0

    # Note: This assumes all objectives are in the Fitness model.
    # 'cost' is a minimization objective, others are maximization.
    objective_names = list(Fitness.model_fields.keys())

    for name in objective_names:
        # Sort by the current objective
        # For minimization objectives (like 'cost'), we sort ascending.
        # For maximization, we sort descending to use the same logic, or handle it explicitly.
        # Here, we sort ascending and use absolute differences.
        reverse_sort = name != 'cost'
        front.sort(key=lambda x: attrgetter(f"fitness.{name}")(x), reverse=reverse_sort)
        
        # Set boundary points to infinity
        front[0].crowding_distance = float('inf')
        front[-1].crowding_distance = float('inf')

        if front_size > 2:
            min_val = attrgetter(f"fitness.{name}")(front[-1])
            max_val = attrgetter(f"fitness.{name}")(front[0])
            val_range = max_val - min_val
            if val_range == 0:
                continue

            # Add distance from neighbors
            for i in range(1, front_size - 1):
                prev_val = attrgetter(f"fitness.{name}")(front[i+1])
                next_val = attrgetter(f"fitness.{name}")(front[i-1])
                front[i].crowding_distance += (next_val - prev_val) / val_range


def calculate_population_uniqueness(population: List[EvaluatedTraveler]):
    """
    Calculates the 'uniqueness' score for each traveler in a population.
    Uniqueness is defined as 1.0 - (average Jaccard index of retrieved domains with other travelers).
    """
    if len(population) < 2:
        for ind in population:
            ind.fitness.uniqueness = 1.0
        return

    # Convert retrieved_domains to sets for faster operations
    domain_sets = [set(ind.retrieved_domains) for ind in population]
    
    for i, ind in enumerate(population):
        total_similarity = 0.0
        comparisons = 0
        
        my_domains = domain_sets[i]
        if not my_domains:
            ind.fitness.uniqueness = 0.0 # No content = not unique (or irrelevant)
            continue
            
        for j, other_domains in enumerate(domain_sets):
            if i == j:
                continue
                
            if not other_domains:
                similarity = 0.0
            else:
                intersection = len(my_domains.intersection(other_domains))
                union = len(my_domains.union(other_domains))
                similarity = intersection / union if union > 0 else 0.0
            
            total_similarity += similarity
            comparisons += 1
            
        avg_similarity = total_similarity / comparisons if comparisons > 0 else 0.0
        ind.fitness.uniqueness = 1.0 - avg_similarity
