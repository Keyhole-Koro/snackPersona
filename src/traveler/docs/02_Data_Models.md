# Data Models (`utils/data_models.py`)

The system relies on a set of well-defined Pydantic models to ensure data consistency and type safety between components. These models act as the data contracts for our event-driven architecture.

## `TravelerGenome`

This is the "DNA" of a Traveler agent. It contains all the parameters that define an agent's exploration strategy. New agents are created by "mutating" these genomes.

**Schema (`genomes/traveler_genome_schema.json`)**:
```json
{
  "genome_id": "uuid",
  "query_diversity": "float (0.0-1.0)",
  "query_template_id": "string (enum)",
  "language_mix": "float (0.0-1.0)",
  "source_bias": {
    "academic": "float (-1.0-1.0)",
    "news": "float (-1.0-1.0)",
    "official": "float (-1.0-1.0)",
    "blogs": "float (-1.0-1.0)"
  },
  "search_depth": "integer",
  "novelty_weight": "float (0.0-1.0)"
}
```

## `ExecutionResult`

This model represents the raw output from a `Traveler Executor` after it has finished a run. It contains all the necessary information for the `Evaluation Service` to assess the agent's performance and behavior.

**Fields**:
- `genome_id`: The ID of the agent that ran.
- `retrieved_urls`: A list of URLs the agent visited.
- `generated_queries`: The search queries the agent used.
- `api_calls`: The number of external API calls made (for cost calculation).
- `execution_time`: The duration of the run (for cost calculation).

## `Fitness`

This model holds the multi-objective fitness scores calculated by the `Evaluation Service`. A key design choice is that there is no single, scalar "fitness score." Instead, performance is represented as a vector of objectives.

**Objectives**:
- **`novelty`** (maximize): How new or surprising were the results compared to past explorations?
- **`coverage`** (maximize): Did the results cover topics or areas not seen before?
- **`reliability`** (maximize): How authoritative were the information sources?
- **`cost`** (minimize): How many resources (API calls, time) were consumed?
- **`downstream_value`** (maximize): How useful were the results for a downstream task (e.g., user clicks)?

## `FeatureDescriptors`

This model holds the calculated behavioral descriptors of an agent's run. These values determine the agent's coordinates in the MAP-Elites grid.

**Descriptors**:
- **`concreteness`** (0.0-1.0): Were the queries and results abstract and general, or specific and detailed?
- **`authority`` (0.0-1.0): Did the agent rely on official/academic sources, or on blogs/forums?

## `EvaluatedTraveler`

This is a container object that bundles an agent's `genome` with its calculated `fitness` and `features`. It also holds metadata used by the NSGA-II sorting algorithm (`rank` and `crowding_distance`). This is the primary object used for selection and mapping into the `EliteMap`.
