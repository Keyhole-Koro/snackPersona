import uuid
from typing import List, Dict, Any, Tuple, Set
from pydantic import BaseModel, Field

# -----------------
# Genome Definition
# -----------------

class SourceBias(BaseModel):
    """Bias towards certain types of information sources."""
    academic: float = Field(..., ge=-1.0, le=1.0)
    news: float = Field(..., ge=-1.0, le=1.0)
    official: float = Field(..., ge=-1.0, le=1.0)
    blogs: float = Field(..., ge=-1.0, le=1.0)

class TravelerGenome(BaseModel):
    """
    A set of parameters that defines the exploration strategy of a Traveler agent.
    Corresponds to traveler_genome_schema.json
    """
    genome_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query_diversity: float = Field(..., ge=0.0, le=1.0)
    query_template_id: str
    language_mix: float = Field(..., ge=0.0, le=1.0)
    source_bias: SourceBias
    search_depth: int = Field(..., ge=1)
    novelty_weight: float = Field(..., ge=0.0, le=1.0)

# -----------------
# Evaluation Data Models
# -----------------

class ExecutionResult(BaseModel):
    """Data returned from a traveler's execution."""
    genome_id: str
    retrieved_urls: List[str]
    generated_queries: List[str]
    log: str
    content_summary: Dict[str, Any] = {}
    headlines: List[str] = []  # Short headlines extracted for persona feed
    api_calls: int
    execution_time: float


class Fitness(BaseModel):
    """
    Multi-objective fitness scores.
    For value-related metrics, higher is better (they will be maximized).
    All metrics are now maximized.
    """
    novelty: float  # Higher is better
    coverage: float  # Higher is better
    reliability: float  # Higher is better
    uniqueness: float   # Higher is better (distinct from other agents)
    downstream_value: float # Higher is better


class FeatureDescriptors(BaseModel):
    """
    The coordinates of the traveler in the feature map (niche).
    """
    concreteness: float = Field(..., ge=0.0, le=1.0)
    authority: float = Field(..., ge=0.0, le=1.0)


class EvaluatedTraveler(BaseModel):
    """
    A container for a traveler's genome and its evaluated performance.
    This is the main object passed around after execution.
    """
    model_config = {'extra': 'allow'}

    genome: TravelerGenome
    fitness: Fitness
    features: FeatureDescriptors
    retrieved_domains: List[str] = Field(default_factory=list) # To track content diversity
    rank: int = -1  # Pareto front rank, for NSGA-II
    rank: int = -1  # Pareto front rank, for NSGA-II
    crowding_distance: float = 0.0  # for NSGA-II

    def dominates(self, other: 'EvaluatedTraveler') -> bool:
        """
        Check if this individual dominates another.
        An individual dominates another if it is no worse in all objectives
        and strictly better in at least one objective.
        
        Note: Assumes cost is to be MINIMIZED and others are to be MAXIMIZED.
        """
        is_better_or_equal = (
            self.fitness.novelty >= other.fitness.novelty and
            self.fitness.coverage >= other.fitness.coverage and
            self.fitness.reliability >= other.fitness.reliability and
            self.fitness.uniqueness >= other.fitness.uniqueness and
            self.fitness.downstream_value >= other.fitness.downstream_value
        )
        is_strictly_better = (
            self.fitness.novelty > other.fitness.novelty or
            self.fitness.coverage > other.fitness.coverage or
            self.fitness.reliability > other.fitness.reliability or
            self.fitness.uniqueness > other.fitness.uniqueness or
            self.fitness.downstream_value > other.fitness.downstream_value
        )
        return is_better_or_equal and is_strictly_better

    def get_feature_tuple(self, resolution: int = 10) -> Tuple[int, int]:
        """Discretizes the feature descriptors into grid coordinates."""
        coord1 = min(int(self.features.concreteness * resolution), resolution - 1)
        coord2 = min(int(self.features.authority * resolution), resolution - 1)
        return (coord1, coord2)
