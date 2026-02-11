# Evolution Orchestrator — Engine & Genetic Operators

**Source files:** `snackPersona/orchestrator/engine.py`, `snackPersona/orchestrator/operators.py`

## Overview

The Orchestrator is the heart of the evolutionary algorithm. It consists of two files:

- **`engine.py`**: `EvolutionEngine` — controls the entire evolutionary loop
- **`operators.py`**: Mutation and Crossover genetic operators

## EvolutionEngine

### Full Evolution Loop

```mermaid
graph TD
    A["initialize_population()"] --> B["run_evolution_loop()"]
    
    B --> C["Generation loop starts"]
    C --> D["Step 1: _evaluate_population()"]
    D --> D1["Group agents (4 per group)"]
    D1 --> D2["Run SimulationEnvironment for conversation"]
    D2 --> D3["Score with Evaluator"]
    D3 --> E["Step 2: save_generation()"]
    E --> F{"Last generation?"}
    F -- No --> G["Step 3: _produce_next_generation()"]
    G --> G1["Sort by fitness"]
    G1 --> G2["Elite selection (keep top N)"]
    G2 --> G3["Tournament selection: pick 2 parents"]
    G3 --> G4["Crossover to create child"]
    G4 --> G5{"Mutation probability 20%?"}
    G5 -- Yes --> G6["Apply mutation"]
    G5 -- No --> G7["Add to next generation"]
    G6 --> G7
    G7 --> G8{"Population size reached?"}
    G8 -- No --> G3
    G8 -- Yes --> C
    F -- Yes --> H["Complete"]
```

### Constructor Parameters

```python
engine = EvolutionEngine(
    llm_client=mock_client,        # LLM backend
    store=persona_store,           # Generation data storage
    evaluator=basic_evaluator,     # Evaluation engine
    mutation_op=simple_mutator,    # Mutation operator
    crossover_op=mix_crossover,    # Crossover operator
    population_size=10,            # Population size
    generations=5,                 # Number of generations
    elite_count=2                  # Number of elites to preserve
)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `population_size` | `int` | `10` | Number of personas per generation |
| `generations` | `int` | `5` | Number of generations to evolve |
| `elite_count` | `int` | `2` | Top individuals carried over unchanged |

### Population Initialization Logic

```mermaid
graph LR
    Seeds["Seed Genotypes"] --> Check{"Seeds >= pop_size?"}
    Check -- Yes --> Pop["Use as population"]
    Check -- No --> Mutate["Fill remaining slots via mutation of seeds"]
    Mutate --> Pop
    Pop --> Compile["compile_persona() for each Genotype"]
    Compile --> Individuals["List[Individual]"]
```

### Selection Strategy

Currently uses **Tournament Selection (size 3)**:

1. Randomly sample 3 individuals from the population
2. Pick the one with the highest `engagement` score as a parent
3. Repeat to select a second parent (p1, p2)

**Fitness weighting:**
```python
# Currently uses a simple sum of engagement + conversation_quality for sorting
key = ind.scores.engagement + ind.scores.conversation_quality
```

## Genetic Operators

### Class Hierarchy

```mermaid
classDiagram
    class MutationOperator {
        <<Abstract>>
        +mutate(genotype) PersonaGenotype
    }
    class SimpleFieldMutator {
        +mutate(genotype) PersonaGenotype
    }
    class LLMMutator {
        -llm_client: LLMClient
        +mutate(genotype) PersonaGenotype
    }

    class CrossoverOperator {
        <<Abstract>>
        +crossover(parent_a, parent_b) PersonaGenotype
    }
    class MixTraitsCrossover {
        +crossover(parent_a, parent_b) PersonaGenotype
    }

    MutationOperator <|-- SimpleFieldMutator : Random perturbation
    MutationOperator <|-- LLMMutator : Semantically meaningful
    CrossoverOperator <|-- MixTraitsCrossover : Trait mixing
```

### SimpleFieldMutator (Simple Mutation)

Randomly selects one field and applies a small change:

| Mutation Type | Probability | Operation |
|---|---|---|
| `name` | 33% | Appends `" II"` to the name |
| `age` | 33% | Changes age by ±1 |
| `backstory` | 33% | Appends `"[Recently changed perspective.]"` to backstory |

```python
mutated = SimpleFieldMutator().mutate(alice_genotype)
# alice_genotype.name = "Alice" → mutated.name = "Alice II"
```

### LLMMutator (LLM-Based Mutation)

Sends the original persona JSON to an LLM and asks it to generate a "slightly different variation."

```mermaid
sequenceDiagram
    participant Engine
    participant LMut as LLMMutator
    participant LLM as LLMClient

    Engine->>LMut: mutate(genotype)
    LMut->>LLM: "Mutate this persona... maintain core identity"
    LLM-->>LMut: Mutated JSON
    LMut->>LMut: Parse JSON → PersonaGenotype
    LMut-->>Engine: Mutated persona

    alt JSON parse failure
        LMut->>LMut: Fall back to SimpleFieldMutator
        LMut-->>Engine: Simple mutation result
    end
```

**Advantage:** Produces "meaningful" mutations — e.g., changing hobbies or slightly adjusting values, rather than just appending strings.

### MixTraitsCrossover (Trait-Mixing Crossover)

Selects field values from two parents, each with a 50% probability:

```mermaid
graph LR
    subgraph ParentA["Parent A: Alice"]
        A_name["name: Alice"]
        A_occ["occupation: Artist"]
        A_val["core_values: creativity"]
        A_style["communication: enthusiastic"]
    end

    subgraph ParentB["Parent B: Bob"]
        B_name["name: Bob"]
        B_occ["occupation: Engineer"]
        B_val["core_values: logic"]
        B_style["communication: concise"]
    end

    subgraph Child["Child: Mixed"]
        C_name["name: Alice (50%)"]
        C_occ["occupation: Artist (from A)"]
        C_val["core_values: creativity (from A)"]
        C_style["communication: concise (from B)"]
    end

    ParentA --> Child
    ParentB --> Child
```

**Field assignment rules:**

| Field | Source | Selection |
|---|---|---|
| `name` | A or B | 50/50 random |
| `age` | A or B | 50/50 random |
| `occupation` | Always A | — |
| `backstory` | Always B | — |
| `core_values` | Always A | — |
| `hobbies` | Always B | — |
| `personality_traits` | Always A | — |
| `communication_style` | Always B | — |
| `topical_focus` | Always A | — |
| `interaction_policy` | Always B | — |
| `goals` | First half of A + second half of B | List merge |

## Evolution Walkthrough (Example: 3 generations, 4 personas)

```
Generation 0: [Alice, Bob, Charlie, Dana]
  ↓ Simulation & Evaluation
  ↓ Alice=0.9, Dana=0.7, Bob=0.5, Charlie=0.3
  ↓ Elites: Alice, Dana preserved
  ↓ Crossover: Alice×Dana → Child1, Bob×Alice → Child2
  ↓ Mutation: Child2 mutated with 20% probability

Generation 1: [Alice, Dana, Child1, Child2(mutated)]
  ↓ Simulation & Evaluation
  ↓ Child1=0.95, Alice=0.85, Child2=0.6, Dana=0.55
  ↓ Elites: Child1, Alice preserved
  ...

Generation 2: [Child1, Alice, Grandchild1, Grandchild2]
  ↓ Saved as final generation
```

## Extension Points

- **Multi-objective selection**: Replace simple sum with Pareto-optimal selection (e.g., NSGA-II)
- **Adaptive mutation rate**: Decrease mutation rate as generations progress
- **LLM crossover**: Use an LLM for semantically meaningful crossover (like `LLMMutator`)
- **Island model**: Evolve multiple populations in parallel and periodically exchange individuals
