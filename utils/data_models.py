from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

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
    
    # Flexible attributes - LLM can define any structure here
    attributes: Dict[str, Any] = Field(
        default_factory=dict,
        description="Flexible dictionary containing all persona attributes. "
                   "The LLM can define any structure here including: age, occupation, backstory, "
                   "core_values, hobbies, personality_traits, communication_style, topical_focus, "
                   "interaction_policy, goals, or any other custom fields."
    )
    
    # Helper method to get attributes with defaults
    def get(self, key: str, default: Any = None) -> Any:
        """Get an attribute value with a default fallback."""
        return self.attributes.get(key, default)
    
    # Helper method to set attributes
    def set(self, key: str, value: Any) -> None:
        """Set an attribute value."""
        self.attributes[key] = value


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
