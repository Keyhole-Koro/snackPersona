# Island Clustering System

The Island Clustering System provides topic-based organization of personas with integrated web search and crawling capabilities, including **faction-based query evolution with natural selection**.

## Overview

The Island system allows personas to:
- **Live on topic-based clusters (Islands)** - Each island represents a specific topic or theme
- **Join factions within islands** - Form sub-groups with shared perspectives
- **Generate search keywords** - Based on their bio and interests using LLM
- **Evolve queries independently** - Each faction evolves its own query strategies
- **Explore the web** - Search and crawl content relevant to their island's topic
- **Compete through natural selection** - Similar low-fitness factions are eliminated
- **Migrate between islands** - Move to different topics based on interests and exploration results
- **Avoid site bias** - Evolve queries and track domain diversity

## Core Components

### 1. IslandCluster

A topic-based cluster where personas live and explore content.

```python
from snackPersona.utils.data_models import IslandCluster

island = IslandCluster(
    id="tech_island",
    topic="AI Technology and Innovation",
    description="Island focused on AI, ML, and tech innovation"
)
```

**Key Features:**
- Track personas assigned to the island
- Manage multiple factions within the island
- Accumulate discovered URLs and content
- Record search queries and evolved keywords
- Monitor domain diversity to avoid bias

### 2. Faction

**NEW**: A sub-group within an island that evolves queries independently.

```python
from snackPersona.utils.data_models import Faction

faction = Faction(
    id="ethics_faction",
    name="AI Ethics Advocates",
    persona_ids={"Alice", "Bob"},
    fitness_score=0.85
)
```

**Key Features:**
- Independent query evolution per faction
- Fitness scoring based on domain diversity and content quality
- Query signature for similarity detection
- Natural selection eliminates similar low-fitness factions
- Generational tracking for evolutionary analysis

### 3. IslandContent

Content (URLs, webpages) accumulated by an island.

```python
from snackPersona.utils.data_models import IslandContent

content = IslandContent(
    url="https://example.com/article",
    title="AI Research Paper",
    keywords=["AI", "machine learning"],
    source_persona="AI_Researcher"
)
```

**Tracked Information:**
- URL and title
- Discovery timestamp
- Visit count
- Estimated update frequency
- Source persona who discovered it

### 3. IslandManager

Manages all islands, factions, and their operations.

```python
from snackPersona.islands import IslandManager

manager = IslandManager(llm_client=llm_client)

# Create islands
tech_island = manager.create_island("tech", "AI Technology")

# Create factions within islands
manager.create_faction("tech", "ethics_faction", "AI Ethics Group")
manager.create_faction("tech", "research_faction", "Research Scientists")

# Add personas to factions
manager.add_persona_to_faction("tech", "ethics_faction", "Alice")

# Evolve queries per faction
queries = manager.evolve_faction_queries("tech", "ethics_faction", num_queries=5)

# Update faction fitness based on exploration
manager.update_faction_fitness("tech", "ethics_faction", 
                              unique_domains=10, quality_score=0.85)

# Calculate faction similarity
similarity = manager.calculate_faction_similarity("tech", "faction1", "faction2")

# Apply natural selection
eliminated = manager.natural_selection_factions("tech", similarity_threshold=0.7)

# Traditional island operations
manager.assign_persona_to_island(persona, "tech")
manager.add_content_to_island("tech", url="https://arxiv.org/example")
diversity = manager.get_domain_diversity("tech")
keywords = manager.evolve_keywords_for_island("tech", max_keywords=10)
manager.migrate_persona(persona, "climate")
```

### 4. PersonaKeywordGenerator

Generates search keywords based on persona bio and interests.

```python
from snackPersona.islands import PersonaKeywordGenerator

generator = PersonaKeywordGenerator(llm_client)

# Generate keywords
keywords = generator.generate_keywords(
    persona, 
    topic="AI Technology", 
    num_keywords=5
)

# Generate search query
query = generator.generate_search_query(persona, topic="AI")
```

**Features:**
- LLM-based keyword generation from persona bio
- Fallback keyword extraction for offline use
- Topic-aware query generation

### 5. IslandTravelerIntegration

Integrates Island system with Traveler's web search and crawling.

```python
from snackPersona.islands import IslandTravelerIntegration

integration = IslandTravelerIntegration(island_manager, llm_client)

# Explore web for a persona
result = integration.explore_for_persona(persona)

# Results automatically added to persona's island
print(f"Discovered {len(result.retrieved_urls)} URLs")
print(f"Headlines: {result.headlines}")
```

**Capabilities:**
- Convert personas to traveler genomes
- Execute web searches with persona-generated keywords
- Crawl discovered websites
- Automatically add results to islands
- Track source memory per persona

## Usage Example

```python
import asyncio
from snackPersona.utils.data_models import PersonaGenotype
from snackPersona.islands import (
    IslandManager, 
    PersonaKeywordGenerator, 
    IslandTravelerIntegration
)
from snackPersona.llm.llm_factory import create_llm_client

async def main():
    # 1. Setup
    llm_client = create_llm_client("gemini-flash")
    island_manager = IslandManager(llm_client)
    
    # 2. Create islands
    tech_island = island_manager.create_island(
        "tech", 
        "AI Technology and Innovation"
    )
    
    # 3. Create persona
    persona = PersonaGenotype(
        name="AI_Researcher",
        bio="Machine learning researcher interested in transformers and NLP"
    )
    
    # 4. Assign to island
    island_manager.assign_persona_to_island(persona, "tech")
    
    # 5. Generate keywords and explore
    generator = PersonaKeywordGenerator(llm_client)
    keywords = generator.generate_keywords(persona, topic="AI Technology")
    print(f"Keywords: {keywords}")
    
    # 6. Web exploration (requires API keys)
    integration = IslandTravelerIntegration(island_manager, llm_client)
    result = integration.explore_for_persona(persona)
    print(f"Discovered {len(result.retrieved_urls)} URLs")
    
    # 7. Check island content
    island = island_manager.get_island("tech")
    print(f"Island has {len(island.content)} content items")
    
    # 8. Check domain diversity
    diversity = island_manager.get_domain_diversity("tech")
    print(f"Unique domains: {diversity['unique_domains']}")
    
    # 9. Evolve keywords to avoid bias
    evolved = island_manager.evolve_keywords_for_island("tech")
    print(f"Evolved keywords: {evolved}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  IslandManager                                          │
│  - Manages multiple islands                             │
│  - Handles persona assignment and migration             │
│  - Tracks domain diversity                              │
│  - Evolves keywords                                     │
└──────────────┬──────────────────────────────────────────┘
               │
       ┌───────┴────────┐
       │                │
       ▼                ▼
┌─────────────┐  ┌─────────────────────────────────┐
│ Island 1    │  │ Island 2                        │
│ Topic: AI   │  │ Topic: Climate                  │
│ ┌─────────┐ │  │ ┌─────────┐                     │
│ │Persona A│ │  │ │Persona B│                     │
│ │Persona C│ │  │ │Persona D│                     │
│ └─────────┘ │  │ └─────────┘                     │
│             │  │                                 │
│ Content:    │  │ Content:                        │
│ - URL 1     │  │ - URL 1                         │
│ - URL 2     │  │ - URL 2                         │
└──────┬──────┘  └────────┬────────────────────────┘
       │                  │
       │   ┌──────────────┘
       │   │
       ▼   ▼
┌────────────────────────────────────────────────┐
│ PersonaKeywordGenerator                        │
│ - Generates keywords from persona bio          │
│ - Creates search queries                       │
└───────────────┬────────────────────────────────┘
                │
                ▼
┌────────────────────────────────────────────────┐
│ IslandTravelerIntegration                      │
│ - Converts personas to traveler genomes        │
│ - Executes web search and crawling             │
│ - Routes results back to islands               │
└───────────────┬────────────────────────────────┘
                │
                ▼
┌────────────────────────────────────────────────┐
│ Traveler (Web Search & Crawl)                  │
│ - SerpApi / Google Search                      │
│ - Web crawler with configurable depth          │
│ - Domain scoring and novelty detection         │
└────────────────────────────────────────────────┘
```

## Key Concepts

### Topic-Based Clustering

Personas are organized into islands based on topics rather than arbitrary groups. This allows:
- Natural content discovery aligned with interests
- Focused search strategies per topic
- Better diversity in explored content

### Persona Migration

Personas can migrate between islands when:
- Their interests evolve
- They discover new topics during exploration
- Migration improves topic alignment

Migration decisions can be LLM-based or rule-based.

### Faction-Based Query Evolution

**NEW**: Within each island, personas can form factions that evolve queries independently:

**How it works:**
1. **Faction Creation** - Sub-groups form within islands based on perspective or approach
2. **Independent Evolution** - Each faction evolves its own search query strategies
3. **Fitness Scoring** - Based on domain diversity and content quality discovered
4. **Similarity Detection** - Factions are compared using query signature analysis
5. **Natural Selection** - Similar factions with lower fitness are eliminated
6. **Persona Reassignment** - Members of eliminated factions join the highest-fitness faction

**Benefits:**
- Diverse exploration strategies within a single topic
- Competition drives better query evolution
- Prevents redundant exploration patterns
- Maintains population diversity through natural selection

**Example:**
```python
# Create competing factions on an AI island
manager.create_faction("ai_island", "ethics_faction", "AI Ethics Advocates")
manager.create_faction("ai_island", "tech_faction", "Technical Innovators")

# Each evolves queries independently
ethics_queries = manager.evolve_faction_queries("ai_island", "ethics_faction")
tech_queries = manager.evolve_faction_queries("ai_island", "tech_faction")

# Update fitness based on exploration results
manager.update_faction_fitness("ai_island", "ethics_faction", 
                              unique_domains=15, quality_score=0.9)
manager.update_faction_fitness("ai_island", "tech_faction",
                              unique_domains=8, quality_score=0.7)

# Natural selection eliminates similar low-fitness factions
eliminated = manager.natural_selection_factions("ai_island", 
                                               similarity_threshold=0.7)
```

### Query Evolution

To avoid site bias, islands and factions evolve their search queries by:
- Analyzing domain distribution
- Identifying over-represented sources
- Generating diverse alternative queries
- Using LLM to create novel search angles
- Competing through natural selection (factions)

### Domain Diversity Metrics

Islands track domain diversity using:
- **Unique domains** - Count of distinct domains
- **Max domain ratio** - Proportion of most frequent domain
- **Entropy** - Information-theoretic diversity measure

High entropy = good diversity, low entropy = concentrated sources.

## Integration with Existing System

The Island system integrates with:

1. **PersonaGenotype** - Added `island_id` field for tracking assignment
2. **Traveler** - Uses existing search and crawl infrastructure
3. **LLM** - For keyword generation and migration decisions
4. **SourceMemory** - Tracks domains visited per persona

## Configuration

No additional configuration needed. The system uses:
- Existing LLM configuration (via `llm_factory`)
- Existing Traveler configuration (SerpApi keys, etc.)
- Standard Python dependencies

## Testing

Run the test suite:

```bash
cd /home/runner/work/snackPersona/snackPersona
PYTHONPATH=src:$PYTHONPATH python -m pytest src/snackPersona/islands/tests/ -v
```

Run the example:

```bash
export GEMINI_API_KEY="your-api-key"
python -m snackPersona.examples.island_example
```

## Future Enhancements

Possible future additions:
- Island merging/splitting based on topic overlap
- Persona reputation/expertise scores per island
- Cross-island content sharing
- Temporal dynamics (island lifecycle)
- Multi-hop exploration strategies
- Integration with orchestrator evolution loop
