# Simulation: Environment & Agents

**Modules:** `snackPersona/simulation/agent.py`, `snackPersona/simulation/environment.py`

This module manages the SNS simulation, handling the interactions between agents. It encapsulates the persona (genotype), the compiled prompt (phenotype), and orchestrates rounds of posting and replying to create conversation threads.

## Agent Interaction Sequence

```mermaid
sequenceDiagram
    participant Environment
    participant Agent
    participant LLMClient

    Environment->>Agent: generate_post(topic)
    Agent->>LLMClient: generate_text(system_prompt, user_prompt)
    LLMClient-->>Agent: "My thoughts on [topic]..."
    Agent->>Agent: unexpected memory update
    Agent-->>Environment: Post Content

    Environment->>Agent: generate_reply(post_content)
    Agent->>LLMClient: generate_text(system_prompt, reply_prompt)
    LLMClient-->>Agent: "Great point!"
    Agent-->>Environment: Reply Content
```

## Simulation Episode Flow

```mermaid
graph TD
    A[Start Episode] --> B[Select Active Posters]
    B --> C[Posters Generate Posts]
    C --> D[Add Posts to Feed]
    D --> E{More Rounds?}
    E -- Yes --> F[Select Replier]
    F --> G[Select Target Post]
    G --> H[Generate Reply]
    H --> I[Add Reply to Feed]
    I --> E
    E -- No --> J[End Episode]
    J --> K[Return Transcript]
```

## Implementation Details

- **SimulationAgent**:
    - Wraps a `PersonaGenotype` and compiles it into a `PersonaPhenotype`.
    - Holds a reference to the `LLMClient`.
    - Maintains a short-term memory of its own actions and relevant context.
- **SimulationEnvironment**:
    - Holds a list of active `SimulationAgent` instances.
    - Manages the global `feed` (list of events).
    - Exposes `run_episode` to execute a round of simulation based on a topic.
