from pydantic import BaseModel, Field
from typing import List, Dict, Any

# ==============================================================================
# 1. Persona Genotype and Phenotype
# As per the doc, "Structured JSON persona + fixed template" is a good choice.
# ==============================================================================

class PersonaGenotype(BaseModel):
    """
    Represents the "genes" of a persona. This is a structured object
    that can be mutated and crossed-over during evolution.
    """
    # Core Identity
    name: str = Field(description="The persona's name.")
    age: int = Field(description="The persona's age.", ge=18)
    occupation: str = Field(description="The persona's occupation.")
    backstory: str = Field(description="A brief backstory of the persona.")

    # Traits and Values
    core_values: List[str] = Field(description="A list of core values (e.g., 'honesty', 'curiosity').")
    hobbies: List[str] = Field(description="A list of hobbies and interests.")
    personality_traits: Dict[str, float] = Field(
        description="Key personality traits on a 0-1 scale (e.g., {'introversion': 0.8, 'agreeableness': 0.3})."
    )

    # Behavioral and Interaction Style
    communication_style: str = Field(description="e.g., 'formal', 'casual', 'witty', 'academic'.")
    topical_focus: str = Field(description="The main topics the persona talks about (e.g., 'tech', 'art').")
    interaction_policy: str = Field(description="How the persona interacts (e.g., 'asks questions', 'debates').")
    
    # Goals
    goals: List[str] = Field(description="The persona's goals within the SNS (e.g., 'make friends', 'share knowledge').")


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

