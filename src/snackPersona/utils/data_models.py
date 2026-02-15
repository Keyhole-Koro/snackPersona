from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Set
from datetime import datetime

# ==============================================================================
# 1. Persona Genotype and Phenotype
# Free-form description approach for realistic SNS persona simulation.
# ==============================================================================

class PersonaGenotype(BaseModel):
    """
    Represents the "genes" of a persona. This is a flexible structured object
    that can be mutated and crossed-over during evolution.
    
    The genotype now supports dynamic fields through the 'attributes' dictionary,
    allowing the LLM to define and modify the structure as needed.
    """
    # Core Identity (required for identification)
    name: str = Field(description="The persona's name (required for identification).")
    
    # Free-form bio - LLM interprets this directly
    bio: str = Field(description="Free-form text description of the persona. "
                                "This should include age, occupation, backstory, personality, "
                                "goals, and any other relevant details in natural language.")
    
    # Island assignment (for topic-based clustering)
    island_id: Optional[str] = Field(default=None, description="ID of the island (topic cluster) this persona belongs to.")



class PersonaPhenotype(BaseModel):
    """
    Represents the "phenotype" of a persona. This is the compiled,
    ready-to-use prompt that the LLM agent will execute.
    """
    system_prompt: str


# ==============================================================================
# 2. Fitness and Evaluation
# Content-based evaluation: scoring the actual posts and replies.
# ==============================================================================

class FitnessScores(BaseModel):
    """
    Content-based scorecard for evaluating SNS persona performance.
    All scores are normalized between 0.0 and 1.0.
    """
    # Content Quality
    post_quality: float = 0.0       # Are posts interesting, engaging, realistic?
    reply_quality: float = 0.0      # Are replies natural, relevant, conversational?

    # Participation
    engagement: float = 0.0         # Active participation level

    # Realism
    authenticity: float = 0.0       # Does it feel like a real SNS user?

    # Safety
    safety: float = 1.0             # Default to safe

    # Diversity
    diversity: float = 0.0          # Variety in outputs

    # Genotype Quality
    bio_quality: float = 0.0        # How well the bio adheres to narrative/authentic style vs resume-speak

    # Moto-mo-ko-mo-nai Metrics (Bluntness & Silence)
    incisiveness: float = 0.0       # Blunt, truth-telling, cutting to the chase (Moto-mo-ko-mo-nai)
    judiciousness: float = 0.0      # Smart silence; knowing when NOT to post


# ==============================================================================
# 3. Evolutionary Components
# ==============================================================================

class Individual(BaseModel):
    """
    An individual in the evolutionary population. It contains the genotype
    (the persona spec), the phenotype (the compiled prompt), and the fitness scores.
    """
    genotype: PersonaGenotype
    phenotype: PersonaPhenotype
    scores: FitnessScores = Field(default_factory=FitnessScores)
    shared_fitness: float = 0.0  # Adjusted fitness after niching


# ==============================================================================
# 4. Media and Articles
# ==============================================================================

class MediaItem(BaseModel):
    """
    Represents an article or media content (text only) that personas can react to.
    """
    id: str = Field(description="Unique identifier for the media item.")
    title: str = Field(description="Title of the article/media.")
    content: str = Field(description="The text content of the article/media.")
    category: Optional[str] = Field(default=None, description="Optional category or tag (e.g., 'tech', 'politics').")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata (e.g., source, date).")


# ==============================================================================
# 5. Island Clustering (Topic-based Persona Clusters)
# ==============================================================================

class IslandContent(BaseModel):
    """
    Content accumulated by an Island - URLs, webpage content, and metadata.
    """
    url: str = Field(description="URL of the website or content.")
    title: Optional[str] = Field(default=None, description="Title of the webpage/content.")
    content_summary: Optional[str] = Field(default=None, description="Summary or excerpt of the content.")
    discovered_at: str = Field(default_factory=lambda: datetime.now().isoformat(), 
                               description="Timestamp when this content was discovered.")
    last_accessed_at: str = Field(default_factory=lambda: datetime.now().isoformat(),
                                  description="Timestamp when this content was last accessed or revisited.")
    visit_count: int = Field(default=1, description="Number of times this URL has been visited.")
    ttl_hours: int = Field(default=72, description="Time-to-live in hours before retention review is required.")
    expires_at: Optional[str] = Field(default=None,
                                      description="Expiration timestamp (ISO format) for retention review.")
    estimated_update_frequency: Optional[str] = Field(default=None, 
                                                     description="Estimated update frequency (e.g., 'daily', 'weekly', 'monthly').")
    keywords: List[str] = Field(default_factory=list, description="Keywords associated with this content.")
    source_persona: Optional[str] = Field(default=None, description="Name of persona who discovered this content.")
    retention_votes: int = Field(default=0, description="Number of keep votes from personas in current retention cycle.")
    discard_votes: int = Field(default=0, description="Number of discard votes from personas in current retention cycle.")
    retention_rounds: int = Field(default=0, description="Number of consecutive retention reviews after TTL expiration.")


class Faction(BaseModel):
    """
    Represents a faction (sub-group) within an Island.
    Factions evolve their own queries independently and compete through natural selection.
    """
    id: str = Field(description="Unique identifier for the faction.")
    name: str = Field(description="Name of the faction.")
    
    # Members
    persona_ids: Set[str] = Field(default_factory=set, description="Personas in this faction.")
    
    # Query evolution
    evolved_queries: List[str] = Field(default_factory=list, 
                                      description="Queries evolved by this faction.")
    query_signature: Optional[str] = Field(default=None, 
                                          description="Signature hash of query patterns for similarity detection.")
    
    # Fitness metrics
    fitness_score: float = Field(default=0.0, 
                                description="Fitness score based on content discovery and diversity.")
    unique_domains_discovered: int = Field(default=0, 
                                          description="Number of unique domains discovered by this faction.")
    content_quality_score: float = Field(default=0.0, 
                                        description="Quality score of discovered content.")
    
    # Lifecycle
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(), 
                           description="Faction creation timestamp.")
    generation: int = Field(default=0, description="Generation number for evolutionary tracking.")
    parent_faction_ids: List[str] = Field(default_factory=list, 
                                         description="IDs of parent factions (for tracking lineage).")


class IslandCluster(BaseModel):
    """
    Represents a topic-based cluster (Island) where personas "live" and explore related content.
    """
    id: str = Field(description="Unique identifier for the island.")
    topic: str = Field(description="Main topic or theme of this island (e.g., 'AI Technology', 'Climate Change').")
    description: Optional[str] = Field(default=None, description="Detailed description of the island's focus.")
    
    # Personas living on this island
    persona_ids: Set[str] = Field(default_factory=set, description="Set of persona names currently on this island.")
    
    # Factions within the island
    factions: Dict[str, "Faction"] = Field(default_factory=dict, 
                                          description="Factions (sub-groups) within this island.")
    
    # Accumulated content
    content: List[IslandContent] = Field(default_factory=list, description="URLs and content accumulated by this island.")
    
    # Search queries that have been used
    search_queries: List[str] = Field(default_factory=list, description="Search queries executed for this island.")
    
    # Keywords for evolution
    evolved_keywords: List[str] = Field(default_factory=list, 
                                       description="Keywords that have evolved to avoid site bias.")
    
    # Statistics
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Island creation timestamp.")
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Last update timestamp.")
    total_visits: int = Field(default=0, description="Total number of content visits on this island.")
    
    # Domain diversity tracking
    visited_domains: Dict[str, int] = Field(default_factory=dict, 
                                            description="Count of visits per domain to track bias.")
