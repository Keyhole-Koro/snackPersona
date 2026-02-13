import unittest
import uuid

from snackPersona.traveler.utils.data_models import (
    TravelerGenome,
    SourceBias,
    Fitness,
    FeatureDescriptors,
    EvaluatedTraveler,
)

def create_mock_genome():
    """Creates a mock TravelerGenome for testing."""
    return TravelerGenome(
        genome_id=str(uuid.uuid4()),
        query_diversity=0.5,
        query_template_id="template_v1_broad",
        language_mix=0.5,
        source_bias=SourceBias(academic=0, news=0, official=0, blogs=0),
        search_depth=1,
        novelty_weight=0.5
    )

def create_mock_features():
    """Creates mock FeatureDescriptors for testing."""
    return FeatureDescriptors(concreteness=0.5, authority=0.5)

class TestDataModels(unittest.TestCase):

    def test_dominates_method(self):
        """
        Test the dominates() method of the EvaluatedTraveler class.
        """
        base_fitness = Fitness(novelty=0.5, coverage=0.5, reliability=0.5, cost=10, downstream_value=0.5)
        
        # Create a base individual
        ind1 = EvaluatedTraveler(
            genome=create_mock_genome(),
            features=create_mock_features(),
            fitness=base_fitness
        )

        # 1. Test domination: ind2 should dominate ind1
        f_better = Fitness(novelty=0.6, coverage=0.5, reliability=0.5, cost=9, downstream_value=0.5)
        ind2 = EvaluatedTraveler(genome=create_mock_genome(), features=create_mock_features(), fitness=f_better)
        self.assertTrue(ind2.dominates(ind1))
        self.assertFalse(ind1.dominates(ind2))

        # 2. Test non-domination (equal)
        ind3 = EvaluatedTraveler(genome=create_mock_genome(), features=create_mock_features(), fitness=base_fitness)
        self.assertFalse(ind1.dominates(ind3))
        self.assertFalse(ind3.dominates(ind1))

        # 3. Test non-domination (trade-off)
        f_tradeoff = Fitness(novelty=0.7, coverage=0.5, reliability=0.5, cost=11, downstream_value=0.5)
        ind4 = EvaluatedTraveler(genome=create_mock_genome(), features=create_mock_features(), fitness=f_tradeoff)
        self.assertFalse(ind1.dominates(ind4))
        self.assertFalse(ind4.dominates(ind1))

        # 4. Test domination with only one better attribute (cost)
        f_cost_better = Fitness(novelty=0.5, coverage=0.5, reliability=0.5, cost=9.9, downstream_value=0.5)
        ind5 = EvaluatedTraveler(genome=create_mock_genome(), features=create_mock_features(), fitness=f_cost_better)
        self.assertTrue(ind5.dominates(ind1))
        self.assertFalse(ind1.dominates(ind5))

    def test_get_feature_tuple(self):
        """
        Test the discretization of feature descriptors.
        """
        features = FeatureDescriptors(concreteness=0.34, authority=0.78)
        ind = EvaluatedTraveler(
            genome=create_mock_genome(),
            features=features,
            fitness=Fitness(novelty=0.5, coverage=0.5, reliability=0.5, cost=10, downstream_value=0.5)
        )

        # With resolution 10, coords should be int(val * 10)
        coords = ind.get_feature_tuple(resolution=10)
        self.assertEqual(coords, (3, 7))

        # Test edge case: 1.0
        features_edge = FeatureDescriptors(concreteness=1.0, authority=0.99)
        ind_edge = EvaluatedTraveler(genome=create_mock_genome(), features=features_edge, fitness=ind.fitness)
        coords_edge = ind_edge.get_feature_tuple(resolution=10)
        self.assertEqual(coords_edge, (9, 9)) # Should be capped at resolution - 1

if __name__ == '__main__':
    unittest.main()

