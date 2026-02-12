# Media Dataset Interface and Diversity Evaluation

## Overview

This document describes the media dataset interface and diversity evaluation features added to snackPersona. These features enable agents to react to articles/media (text only) and evaluate the diversity of their reactions.

## Media Dataset Interface

### MediaItem Data Model

The `MediaItem` class represents an article or media content:

```python
from snackPersona.utils.data_models import MediaItem

media = MediaItem(
    id="article_001",
    title="The Future of AI",
    content="Artificial Intelligence has reached...",
    category="technology",
    metadata={"source": "Tech News", "date": "2026-02-01"}
)
```

### MediaDataset Class

The `MediaDataset` class manages collections of media items:

```python
from snackPersona.utils.media_dataset import MediaDataset

# Create a new dataset
dataset = MediaDataset()

# Add items
dataset.add_media_item(media)

# Save to file
dataset.save_to_file("my_dataset.json")

# Load from file
dataset = MediaDataset("my_dataset.json")

# Access items
item = dataset.get_media_item("article_001")
all_items = dataset.get_all_media_items()
tech_items = dataset.get_media_by_category("technology")
```

### JSON Format

Media datasets are stored as JSON arrays:

```json
[
  {
    "id": "article_001",
    "title": "Article Title",
    "content": "Article content...",
    "category": "technology",
    "metadata": {
      "source": "News Source",
      "date": "2026-02-01"
    }
  }
]
```

## Agent Reactions to Media

### SimulationAgent.generate_media_reaction()

Agents can now react to media items:

```python
from snackPersona.simulation.agent import SimulationAgent

agent = SimulationAgent(genotype, llm_client)
reaction = agent.generate_media_reaction(media_item)
```

### SimulationEnvironment.run_media_episode()

The environment supports media-based episodes:

```python
from snackPersona.simulation.environment import SimulationEnvironment

env = SimulationEnvironment(agents)
transcript = env.run_media_episode(media_item, rounds=2)
```

This generates:
1. Initial reactions from all agents to the media
2. Discussion rounds where agents can reply to each other's reactions

## Diversity Evaluation

### DiversityEvaluator Class

The `DiversityEvaluator` provides multiple metrics for measuring reaction diversity:

#### Lexical Diversity
Measures vocabulary richness using Type-Token Ratio:

```python
from snackPersona.evaluation.diversity import DiversityEvaluator

texts = ["reaction 1...", "reaction 2...", "reaction 3..."]
score = DiversityEvaluator.calculate_lexical_diversity(texts)
```

#### Length Diversity
Measures variation in response lengths using coefficient of variation:

```python
score = DiversityEvaluator.calculate_length_diversity(texts)
```

#### Semantic Diversity
Measures variety in reaction types (questions, agreement, disagreement, etc.):

```python
reactions = [
    {"author": "Alice", "content": "reaction text..."},
    {"author": "Bob", "content": "reaction text..."}
]
score = DiversityEvaluator.calculate_semantic_diversity(reactions)
```

#### Overall Diversity
Combined metric (weighted average):

```python
score = DiversityEvaluator.calculate_overall_diversity(reactions)
```

### Integration with Fitness Scores

The diversity metric is now included in `FitnessScores`:

```python
scores = evaluator.evaluate(genotype, transcript)
print(f"Diversity: {scores.diversity}")
```

Both `BasicEvaluator` and `LLMEvaluator` now calculate diversity scores automatically.

## Using Media Datasets in Evolution

### Command Line

Use the `--media_dataset` option to specify a media dataset:

```bash
python3 snackPersona/main.py \
  --generations 3 \
  --pop_size 6 \
  --llm mock \
  --media_dataset sample_media_dataset.json
```

### In Code

Pass a `MediaDataset` to the `EvolutionEngine`:

```python
from snackPersona.utils.media_dataset import MediaDataset
from snackPersona.orchestrator.engine import EvolutionEngine

media_dataset = MediaDataset("my_dataset.json")

engine = EvolutionEngine(
    llm_client=llm_client,
    store=store,
    evaluator=evaluator,
    mutation_op=mutation_op,
    crossover_op=crossover_op,
    population_size=10,
    generations=5,
    elite_count=2,
    media_dataset=media_dataset  # Add media dataset
)
```

## Behavior

When a media dataset is provided:

1. **Traditional Episodes**: Agents still participate in regular SNS-style conversations
2. **Media Episodes**: Agents also react to randomly selected media items
3. **Combined Evaluation**: Both types of interactions are included in fitness evaluation
4. **Diversity Scoring**: The diversity of each agent's contributions is measured and included in their fitness scores

## Sample Dataset

A sample media dataset is provided at `sample_media_dataset.json` with 5 articles covering different topics (technology, art, philosophy, news, psychology).

## Example Script

See `examples/media_dataset_example.py` for a complete working example demonstrating all features.

## Performance Considerations

- Diversity calculation requires at least 2 posts from an agent
- Semantic diversity uses heuristic pattern matching (not full NLP)
- Media episodes add to simulation time but provide richer evaluation data
- Diversity scores are normalized to 0.0-1.0 range for consistency with other fitness metrics
