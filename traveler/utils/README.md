## Utils Component (Data Models)

### ExecutionResult
```mermaid
graph TD
    subgraph ExecutionResult
        A[genome_id: string]
        B[retrieved_urls: List[string]]
        C[generated_queries: List[string]]
        D[log: string]
        E[api_calls: int]
        F[execution_time: float]
    end
```

### Fitness
```mermaid
graph TD
    subgraph Fitness
        A[novelty: float]
        B[coverage: float]
        C[reliability: float]
        D[cost: float]
        E[downstream_value: float]
    end
```

### FeatureDescriptors
```mermaid
graph TD
    subgraph FeatureDescriptors
        A[concreteness: float]
        B[authority: float]
    end
```

### EvaluatedTraveler
```mermaid
graph TD
    subgraph EvaluatedTraveler
        A[genome: TravelerGenome]
        B[fitness: Fitness]
        C[features: FeatureDescriptors]
        D[rank: int]
        E[crowding_distance: float]
    end

    A --> TravelerGenome
    B --> Fitness
    C --> FeatureDescriptors
```
