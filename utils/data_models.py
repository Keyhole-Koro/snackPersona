from pydantic import BaseModel, Field
from typing import List, Dict, Any

# ==============================================================================
# 1. Persona Genotype and Phenotype
# As per the doc, "Structured JSON persona + fixed template" is a good choice.
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
    policy_instructions: str


# ==============================================================================
# 2. Fitness and Evaluation
# ==============================================================================

class FitnessScores(BaseModel):
    """
    A multi-layer scorecard for evaluating an individual persona's performance.
    All scores should be normalized, typically between 0.0 and 1.0.
    """
    # Quality & Engagement
    conversation_quality: float = 0.0
    engagement: float = 0.0
    
    # Fidelity & Consistency
    persona_fidelity: float = 0.0
    
    # Social & Goal Achievement
    social_intelligence: float = 0.0
    goal_achievement: float = 0.0

    # Safety
    safety: float = 1.0  # Default to safe

    # Diversity
    diversity: float = 0.0
    novelty: float = 0.0


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

