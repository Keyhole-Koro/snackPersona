# MAP-Elites Implementation (`map_elites/elite_map.py`)

The core of the system's diversity preservation mechanism is the **MAP-Elites** algorithm, implemented in the `EliteMap` class. This algorithm is what allows the system to "illuminate" the search space by finding the best possible solution for many different types of behaviors, rather than just finding a single overall best solution.

## The "Map of Elites"

The `EliteMap` can be visualized as a grid (in our case, a 2D grid). Each axis of the grid represents a dimension of behavior, as defined by the `FeatureDescriptors`.

- **Axis 1**: `concreteness` (e.g., from 0.0 to 1.0)
- **Axis 2**: `authority` (e.g., from 0.0 to 1.0)

Each cell in this grid represents a specific **niche** of behavior. For example, the cell at coordinates `(0.9, 0.1)` would contain agents that perform highly *specific* searches using low-*authority* sources (e.g., drilling down into a topic on forums).

The `EliteMap` stores only **one** individual per cell: the **"elite"**. The elite is the best-performing individual ever found for that specific behavioral niche.

## How it Works

The `EliteMap` class manages this process through its main method, `add_individual`.

1.  **Calculate Niche**: When a new `EvaluatedTraveler` is passed to the map, its feature descriptors (e.g., `concreteness=0.92`, `authority=0.15`) are first discretized into grid coordinates (e.g., `(9, 1)` for a 10x10 grid).

2.  **Compare to Existing Elite**:
    - If the corresponding cell `(9, 1)` is empty, the new individual automatically becomes the elite for that niche.
    - If the cell already contains an elite, the new individual is compared to the existing one.

3.  **The `_is_better` Rule**: The comparison uses the rank and crowding distance from the NSGA-II evaluation:
    - If `new.rank < old.rank`, the new individual wins.
    - If `new.rank == old.rank` and `new.crowding_distance > old.crowding_distance`, the new individual wins.
    - Otherwise, the old elite is kept.

If the new individual wins, it replaces the old one in the cell.

## The Benefit

This simple process has a powerful outcome:
- **Diversity is Guaranteed**: Because the system maintains a champion for every single niche, it cannot converge to a single strategy. Even if a "generalist" strategy is very strong, it cannot wipe out a "specialist" strategy that is the best in its own niche.
- **Continuous Improvement**: The performance of the elites in the map can only ever improve or stay the same. A niche is never updated with a worse-performing individual.
- **Source for Innovation**: The collection of diverse elites serves as the breeding ground for new strategies. The `generation_scheduler_handler` picks parents from this map to create the next generation of offspring, combining and mutating high-performing, diverse strategies.
