# Simulation — SNS Agent Simulation

**Source files:** `snackPersona/simulation/agent.py`, `snackPersona/simulation/environment.py`

## Overview

The Simulation module simulates how AI personas behave on a social network. Each persona is wrapped as a `SimulationAgent`, and a `SimulationEnvironment` manages the shared feed (timeline) where agents post and reply.

The output of this module (Transcript = conversation log) is passed to the evaluation engine for persona quality scoring.

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
        ReplyA["generate_reply()"]
    end

    subgraph AgentB["SimulationAgent: Bob"]
        GB["Genotype"]
        PB["Phenotype"]
        MB["Memory"]
    end

    RunEp --> PostA
    PostA --> Feed
    RunEp --> ReplyA
    ReplyA --> Feed

    GA -->|compile_persona| PA
    PA -->|system_prompt| PostA
```

## SimulationAgent Details

### Initialization

```python
agent = SimulationAgent(genotype=alice_genotype, llm_client=mock_client)
# Internally calls compile_persona(genotype) to produce the Phenotype
```

### `generate_post(topic: str) -> str`

Generates an SNS post based on a topic.

```mermaid
sequenceDiagram
    participant Env as Environment
    participant Agent as Agent
    participant LLM as LLMClient

    Env->>Agent: generate_post("AI Technology")
    Note over Agent: Combines system_prompt + policy_instructions
    Agent->>LLM: generate_text(full_system, "Draft a post... topic is: AI Technology")
    LLM-->>Agent: "Latest trends in AI technology..."
    Agent->>Agent: Record in memory (role: assistant)
    Agent-->>Env: Post text
```

**Prompt structure:**
```
[system_prompt]          ← Persona identity
[policy_instructions]    ← Behavioral rules
---
[user_prompt]            ← "Draft a new post... The current trending topic is: {topic}"
```

### `generate_reply(post_content: str, author_name: str) -> str`

Generates a reply to another agent's post.

**Prompt structure:**
```
[system_prompt + policy_instructions]
---
User '{author_name}' posted: "{post_content}"
Write a reply.
```

### Memory (Short-Term)

During each episode, agents accumulate their actions in a `memory` list. It is cleared via `reset_memory()` at the end of each episode.

```python
agent.memory = [
    {"role": "assistant", "content": "My first post..."},
    {"role": "user", "content": "Bob: Great post!"},
    {"role": "assistant", "content": "Thanks Bob!"},
]
```

> **Note**: The current implementation does not include memory in the LLM prompt. In the future, feeding it into the context window would enable more consistent conversations.

## SimulationEnvironment Details

### Episode Flow

```mermaid
graph TD
    A["run_episode(rounds=3, topic='AI')"] --> B["Phase 1: Posting"]
    B --> B1["Randomly select ~half the agents"]
    B1 --> B2["Selected agents generate posts"]
    B2 --> B3["Add posts to Feed"]
    B3 --> C["Phase 2: Replying (repeated 'rounds' times)"]
    C --> C1["Randomly pick a post from Feed"]
    C1 --> C2["Select an agent (excluding the post author)"]
    C2 --> C3["Generate reply"]
    C3 --> C4["Add reply to Feed (enables threading)"]
    C4 --> C5{More rounds?}
    C5 -- Yes --> C1
    C5 -- No --> D["Return Transcript"]
```

### Transcript (Output) Structure

`run_episode()` returns a `List[Dict]` transcript:

```python
transcript = [
    {
        "type": "post",
        "author": "Alice",
        "content": "Thinking about the latest AI trends..."
    },
    {
        "type": "reply",
        "author": "Bob",
        "target_author": "Alice",
        "content": "Interesting perspective! Especially...",
        "reply_to": "Thinking about the latest AI trends..."
    }
]
```

| Field | Type | Description |
|---|---|---|
| `type` | `str` | `"post"` or `"reply"` |
| `author` | `str` | Persona name of the speaker |
| `content` | `str` | Post/reply text |
| `target_author` | `str` | Name of the persona being replied to (reply only) |
| `reply_to` | `str` | Text of the original post (reply only) |

## Design Decisions

- **Random selection**: Posters and repliers are chosen randomly, producing diverse interaction patterns
- **Flat feed**: All events live in a single list. Thread-like structures are a future enhancement
- **Episode-based**: 1 episode = posts + replies on a single topic. Multiple episodes per generation can be run

## Extension Points

- **Thread structure**: Manage replies as a tree for more natural conversation flow
- **Memory utilization**: Include agent memory in LLM prompts to maintain conversational context
- **Reactions**: Add "like," "retweet," and other social actions
- **Topic diversification**: Run episodes on multiple topics to evaluate persona breadth
