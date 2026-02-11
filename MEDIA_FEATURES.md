# Media Interface and Diversity Evaluation Features

## Quick Start

### Using Media Datasets

1. **Prepare a media dataset** (JSON file with articles):

```json
[
  {
    "id": "article_001",
    "title": "Article Title",
    "content": "Full article text...",
    "category": "technology",
    "metadata": {}
  }
]
```

2. **Run evolution with media dataset**:

```bash
python3 snackPersona/main.py \
  --generations 3 \
  --pop_size 6 \
  --llm mock \
  --media_dataset sample_media_dataset.json
```

3. **View results**: Agents will react to media items, and diversity scores will be included in evaluation.

## Features Added

### 1. Media Reaction Interface
- Agents can now react to articles/media (text only)
- New `generate_media_reaction()` method for agents
- New `run_media_episode()` for environments

### 2. Diversity Evaluation
- Multiple diversity metrics (lexical, length, semantic)
- Automatic diversity scoring in fitness evaluation
- Diversity scores visible in generation output

### 3. MediaDataset Management
- `MediaDataset` class for managing collections
- JSON import/export
- Category-based filtering

## Example Output

```
Using Mock LLM Client...
Loading media dataset from sample_media_dataset.json...
Loaded 5 media items.
Initializing new seed population...
Starting Evolution Loop...
--- Generation 0 ---
Agent Dana: Engagement=0.40, Coherence=0.66, Diversity=0.30
Agent Alice: Engagement=0.40, Coherence=0.66, Diversity=0.27
Agent Bob: Engagement=0.40, Coherence=0.66, Diversity=0.27
Agent Charlie: Engagement=0.60, Coherence=0.66, Diversity=0.20
```

Notice the new **Diversity** score in the output.

## Programmatic Usage

```python
from snackPersona.utils.media_dataset import MediaDataset
from snackPersona.utils.data_models import MediaItem

# Create dataset
dataset = MediaDataset()
media = MediaItem(
    id="001",
    title="Article Title",
    content="Content...",
    category="tech"
)
dataset.add_media_item(media)
dataset.save_to_file("my_dataset.json")

# Use with evolution engine
engine = EvolutionEngine(
    # ... other params ...
    media_dataset=dataset
)
```

## Documentation

- **Full Documentation**: [docs/media_and_diversity.md](docs/media_and_diversity.md)
- **Examples**: [examples/media_dataset_example.py](examples/media_dataset_example.py)
- **Sample Dataset**: [sample_media_dataset.json](sample_media_dataset.json)

## Backward Compatibility

All changes are backward compatible. If no media dataset is provided:
- The system works exactly as before
- Only traditional SNS episodes are simulated
- Diversity scores will be 0.0 for agents with <2 posts
