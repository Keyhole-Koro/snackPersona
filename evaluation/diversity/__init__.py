"""
Diversity evaluation package.

Submodules:
  - embedding : Sentence-embedding cosine-distance diversity (output & population level)
  - genotype  : Structural distance between PersonaGenotype instances

For backward compatibility, the old DiversityEvaluator interface is
re-exported here as a thin facade.
"""

from snackPersona.evaluation.diversity.embedding import (
    calculate_embedding_diversity,
    calculate_population_diversity,
)
from snackPersona.evaluation.diversity.genotype import (
    calculate_genotype_distance,
)


class DiversityEvaluator:
    """
    Facade that keeps the old DiversityEvaluator.method() call-sites working.
    All methods delegate to the split submodules.
    """

    # Per-agent output diversity
    calculate_embedding_diversity = staticmethod(calculate_embedding_diversity)
    calculate_population_diversity = staticmethod(calculate_population_diversity)
    calculate_genotype_distance = staticmethod(calculate_genotype_distance)

    @staticmethod
    def calculate_overall_diversity(reactions: list) -> float:
        """Entry point used by BasicEvaluator / LLMEvaluator."""
        if not reactions:
            return 0.0
        texts = [r.get('content', '') for r in reactions]
        return calculate_embedding_diversity(texts)
