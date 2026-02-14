# Evaluation Engine (`evaluation/`)

The evaluation engine is responsible for taking the raw `ExecutionResult` from a traveler and transforming it into actionable performance and behavioral metrics. This process is central to the system's ability to learn and adapt.

The engine has two main responsibilities:
1.  **Calculate Fitness**: Determine how *good* the run was.
2.  **Calculate Feature Descriptors**: Determine what *kind* of run it was.

## Multi-Objective Fitness (`evaluation/fitness.py`)

A key design principle of SnackTraveler is to avoid a single, scalar fitness score. We don't want to manually decide if "novelty is twice as important as cost." Instead, we treat fitness as a multi-dimensional vector and use techniques from the **NSGA-II** algorithm to compare individuals.

### 1. Non-Dominated Sorting

The primary comparison mechanism is "dominance."
> An individual **A** *dominates* an individual **B** if **A** is no worse than **B** on all objectives, and strictly better than **B** on at least one objective.

The `non_dominated_sort` function takes a population of `EvaluatedTraveler`s and sorts them into "Pareto fronts":
- **Front 1**: Contains all individuals that are not dominated by any other individual in the population. These are the "best" solutions in a multi-objective sense.
- **Front 2**: Contains individuals that are only dominated by individuals in Front 1.
- ...and so on.

Each individual is assigned a `rank` corresponding to its front number. This rank is the primary criterion for selection.

### 2. Crowding Distance

What if two individuals are on the same front (i.e., have the same rank)? How do we choose between them? This is where crowding distance comes in.

The `calculate_crowding_distance` function measures how "isolated" an individual is from its neighbors within the same front. It calculates the average distance to its neighbors along each objective dimension.

- Individuals at the boundaries of the objective space (e.g., the one with the absolute lowest cost, or the one with the absolute highest novelty) are given an infinite crowding distance to ensure they are preserved.
- Individuals in a "crowded" part of the solution space get a low score, while those in a "sparse" region get a high score.

When comparing two individuals with the same rank, the one with the **higher crowding distance is preferred**. This creates selection pressure that favors diversity and pushes the population to cover the entire Pareto front, not just cluster in one spot.

## Feature Descriptors (`evaluation/features.py`)

While fitness tells us how good an agent is, feature descriptors tell us what the agent *did*. The `calculate_feature_descriptors` function analyzes the `ExecutionResult` to produce a vector that characterizes the agent's behavior. This vector is then used to place the agent in the correct niche in the `EliteMap`.

In our implementation, the features are:
- **`concreteness`**: How specific vs. general was the search?
- **`authority`**: How much did the agent rely on authoritative sources?

These descriptors are normalized to a `[0.0, 1.0]` range, which directly maps to the coordinates of the elite map.
