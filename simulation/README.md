# Simulation — SNS Agent Simulation

**Source files:** `simulation/agent.py`, `simulation/environment.py`

## Overview

The Simulation module simulates how AI personas behave on a social network. Each persona is wrapped as a `SimulationAgent`, and a `SimulationEnvironment` manages the shared feed where agents post, decide whether to engage, and reply.

The output (Transcript) is passed to the evaluation engine for fitness scoring.

## Architecture

```mermaid
graph TB
    subgraph Environment["SimulationEnvironment"]
        Feed["Feed (Timeline)"]
        RunEp["run_episode()"]
    end

    subgraph AgentA["SimulationAgent: Alice"]
        GA["Genotype"]
        PA["Phenotype"]
        MA["Memory"]
        PostA["generate_post()"]
        EngageA["should_engage()"]
        ReplyA["generate_reply()"]
    end

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
| `generate_post(topic)` | Creates a new SNS post based on persona and topic |
| `should_engage(post, author)` | **LLM-based decision**: "Would this persona reply?" Returns `True`/`False` |
| `generate_reply(post, author)` | Generates a reply to another agent's post |
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

    Env->>Agent: should_engage(post, author)
    Agent->>LLM: "Would you reply? Consider interests, style..."
    LLM-->>Agent: "yes" / "no"
    Agent-->>Env: True / False
```

All actions are logged via structured logger (`utils/logger.py`).

## SimulationEnvironment

### Episode Flow (Persona-Driven)

```mermaid
graph TD
    A["run_episode(rounds=3, topic)"] --> B["Phase 1: Posting"]
    B --> B1["ALL agents generate posts"]
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
    {"type": "post", "author": "Alice", "content": "..."},
    {"type": "reply", "author": "Bob", "target_author": "Alice",
     "content": "...", "reply_to": "..."},
    {"type": "pass", "author": "Charlie", "target_author": "Alice"}
]
```

| Type | Fields | Description |
|---|---|---|
| `post` | `author`, `content` | Agent's initial post |
| `reply` | `author`, `target_author`, `content`, `reply_to` | Agent's reply to another post |
| `pass` | `author`, `target_author` | Agent decided NOT to engage |

## Design Decisions

- **Persona-driven engagement**: Agents use LLM to decide whether to reply, producing more realistic interaction patterns
- **Pass events in transcript**: Logged so evaluators can measure selectivity and engagement quality
- **All-post-first**: Every agent posts before any replies begin, ensuring a rich feed for engagement decisions

## Extension Points

- **Thread structure**: Manage replies as a tree for natural conversation flow
- **Memory in prompts**: Feed agent memory into LLM context for more consistent conversations
- **Reactions**: Add "like," "retweet," and other social actions
- **Topic diversification**: Run episodes on multiple topics
