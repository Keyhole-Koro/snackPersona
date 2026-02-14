# Simulation — SNS Agent Simulation

**Source files:** `simulation/agent.py`, `simulation/environment.py`

## Overview

The Simulation module simulates how AI personas behave on a social network. Each persona is wrapped as a `SimulationAgent`, and a `SimulationEnvironment` manages the shared feed where agents post, decide whether to engage, and reply.

Topics for each episode are provided by the `EvolutionEngine` via LLM-driven topic generation. The output (Transcript) is passed to the evaluation engine for fitness scoring and saved to disk for analysis.

## Architecture

```mermaid
graph TB
    subgraph Engine["EvolutionEngine"]
        Topics["LLM-generated topics"]
    end

    subgraph Environment["SimulationEnvironment"]
        Feed["Feed (Timeline)"]
        RunEp["run_episode_async(topic)"]
    end

    subgraph AgentA["SimulationAgent: PixelForge"]
        GA["Genotype"]
        PA["Phenotype"]
        MA["Memory"]
        PostA["generate_post_async()"]
        EngageA["should_engage_async()"]
        ReplyA["generate_reply_async()"]
    end

    Topics --> RunEp
    RunEp --> PostA
    PostA --> Feed
    Feed --> EngageA
    EngageA -->|yes| ReplyA
    ReplyA --> Feed

    GA -->|compile_persona| PA
    PA -->|system_prompt| PostA
```

## SimulationAgent

### Key Methods

| Method | Purpose |
|---|---|
| `generate_post(topic)` / `generate_post_async(topic)` | Creates a new SNS post based on persona and topic |
| `should_engage(post, author)` / `should_engage_async(...)` | **LLM-based decision**: "Would this persona reply?" Returns `True`/`False` |
| `generate_reply(post, author)` / `generate_reply_async(...)` | Generates a reply to another agent's post |
| `generate_media_reaction(media_item)` | Reacts to an article/media content |

### `should_engage()` — Persona-Driven Engagement

The agent uses the LLM to decide whether its persona would reply, considering:
- **Topical interest** (`topical_focus`)
- **Interaction style** (`interaction_policy`)
- **Content relevance**

```mermaid
sequenceDiagram
    participant Env as Environment
    participant Agent as Agent
    participant LLM as LLMClient

    Env->>Agent: should_engage_async(post, author)
    Agent->>LLM: "Would you reply? Consider interests, style..."
    LLM-->>Agent: "yes" / "no"
    Agent-->>Env: True / False
```

All actions are logged via structured logger (`utils/logger.py`).

## SimulationEnvironment

### Episode Flow (Persona-Driven)

```mermaid
graph TD
    A["run_episode_async(rounds=3, topic)"] --> B["Phase 1: Posting"]
    B --> B1["ALL agents generate posts on topic"]
    B1 --> B2["Add posts to Feed"]
    B2 --> C["Phase 2: Engagement (repeated 'rounds' times)"]
    C --> C1["Shuffle agents"]
    C1 --> C2["Each agent picks a post from Feed"]
    C2 --> C3{"should_engage()?"}
    C3 -- Yes --> C4["Generate reply → add to Feed"]
    C3 -- No --> C5["Log as 'pass' event"]
    C4 --> C6{More agents?}
    C5 --> C6
    C6 -- Yes --> C2
    C6 -- No --> C7{More rounds?}
    C7 -- Yes --> C1
    C7 -- No --> D["Return Transcript"]
```

### Transcript Structure

```python
transcript = [
    {"type": "post", "author": "PixelForge", "content": "..."},
    {"type": "reply", "author": "DataNinja", "target_author": "PixelForge",
     "content": "...", "reply_to": "..."},
    {"type": "pass", "author": "EcoSage", "target_author": "PixelForge"}
]
```

| Type | Fields | Description |
|---|---|---|
| `post` | `author`, `content` | Agent's initial post |
| `reply` | `author`, `target_author`, `content`, `reply_to` | Agent's reply to another post |
| `pass` | `author`, `target_author` | Agent decided NOT to engage |

## Design Decisions

- **LLM-driven topics**: Topics are generated per generation by the engine, not hardcoded
- **Persona-driven engagement**: Agents use LLM to decide whether to reply, producing more realistic interaction patterns
- **Pass events in transcript**: Logged so evaluators can measure selectivity and engagement quality
- **All-post-first**: Every agent posts before any replies begin, ensuring a rich feed for engagement decisions
- **Feed reset**: Feed is cleared between group episodes to prevent cross-contamination

## Extension Points

- **Thread structure**: Manage replies as a tree for natural conversation flow
- **Memory in prompts**: Feed agent memory into LLM context for more consistent conversations
- **Reactions**: Add "like," "retweet," and other social actions
- **Multi-turn topics**: Let topics evolve within an episode
