# Evolution Orchestrator: Engine & Operators

**Modules:** `snackPersona/orchestrator/engine.py`, `snackPersona/orchestrator/operators.py`

This module orchestrates the entire evolutionary process, managing the selection, crossover, and mutation of personas.

## Evolution Loop Sequence

```mermaid
sequenceDiagram
    participant Engine
    participant Store
    participant Environment
    participant Evaluator
    participant Operators

    Engine->>Store: Load previous generation (optional)
    loop For each Generation
        Engine->>Environment: Run Simulation (Episodes)
        Environment-->>Engine: Transcripts
        
        loop For each Agent
            Engine->>Evaluator: Evaluate Transcript
            Evaluator-->>Engine: Fitness Scores
        end
        
        Engine->>Store: Save Generation Stats
        
        Engine->>Engine: Select Elites
        loop Until Population Full
            Engine->>Operators: Crossover(ParentA, ParentB)
            Operators-->>Engine: Child
            Engine->>Operators: Mutate(Child)
            Operators-->>Engine: Mutated Child
        end
    end
```

## Operators Class Diagram

```mermaid
classDiagram
    class MutationOperator {
        <<Abstract>>
        +mutate(genotype) PersonaGenotype
    }
    class SimpleFieldMutator {
        +mutate(...) PersonaGenotype
    }
    class LLMMutator {
        -llm_client: LLMClient
        +mutate(...) PersonaGenotype
    }

    class CrossoverOperator {
        <<Abstract>>
        +crossover(parent_a, parent_b) PersonaGenotype
    }
    class MixTraitsCrossover {
        +crossover(...) PersonaGenotype
    }

    MutationOperator <|-- SimpleFieldMutator
    MutationOperator <|-- LLMMutator
    CrossoverOperator <|-- MixTraitsCrossover
```

## Implementation Details

- **EvolutionEngine**: The core controller class. It initializes, evaluates, selects, and evolves the population.
- **MutationOperator**: Abstract base for mutation logic.
    - **SimpleFieldMutator**: Randomly perturbs fields.
    - **LLMMutator**: Uses LLM to create semantically meaningful mutations.
- **CrossoverOperator**: Abstract base for crossover logic.
    - **MixTraitsCrossover**: Randomly selects traits from two parents to form a child.
