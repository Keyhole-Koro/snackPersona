import unittest
from snackPersona.traveler.map_elites.elite_map import EliteMap
from snackPersona.traveler.utils.data_models import (
    Fitness,
    FeatureDescriptors,
    EvaluatedTraveler,
)
from snackPersona.traveler.tests.test_data_models import create_mock_genome

class TestEliteMap(unittest.TestCase):

    def setUp(self):
        """Set up a new EliteMap for each test."""
        self.elite_map = EliteMap(resolution=10)
        
        # Create some individuals for testing
        self.ind1 = EvaluatedTraveler(
            genome=create_mock_genome(),
            features=FeatureDescriptors(concreteness=0.55, authority=0.55), # Niche (5, 5)
            fitness=Fitness(novelty=0.5, coverage=0.5, cost=10, reliability=0.5, downstream_value=0.5),
            rank=1,
            crowding_distance=1.0
        )
        
        # A better individual for the same niche
        self.ind2_better = EvaluatedTraveler(
            genome=create_mock_genome(),
            features=FeatureDescriptors(concreteness=0.55, authority=0.55), # Niche (5, 5)
            fitness=Fitness(novelty=0.6, coverage=0.6, cost=9, reliability=0.6, downstream_value=0.6),
            rank=0, # Better rank
            crowding_distance=1.5
        )

        # A worse individual for the same niche
        self.ind3_worse = EvaluatedTraveler(
            genome=create_mock_genome(),
            features=FeatureDescriptors(concreteness=0.55, authority=0.55), # Niche (5, 5)
            fitness=Fitness(novelty=0.4, coverage=0.4, cost=11, reliability=0.4, downstream_value=0.4),
            rank=2, # Worse rank
            crowding_distance=0.5
        )
        
        # An individual with the same rank but higher crowding distance
        self.ind4_crowded = EvaluatedTraveler(
            genome=create_mock_genome(),
            features=FeatureDescriptors(concreteness=0.55, authority=0.55), # Niche (5, 5)
            fitness=Fitness(novelty=0.5, coverage=0.5, cost=10, reliability=0.5, downstream_value=0.5),
            rank=1, # Same rank as ind1
            crowding_distance=2.0 # Higher crowding distance
        )
        
        # An individual for a different niche
        self.ind5_other_niche = EvaluatedTraveler(
            genome=create_mock_genome(),
            features=FeatureDescriptors(concreteness=0.11, authority=0.11), # Niche (1, 1)
            fitness=Fitness(novelty=0.9, coverage=0.9, cost=5, reliability=0.9, downstream_value=0.9),
            rank=0,
            crowding_distance=float('inf')
        )

    def test_add_to_empty_niche(self):
        """Test adding an individual to an empty niche."""
        self.assertEqual(len(self.elite_map), 0)
        updated = self.elite_map.add_individual(self.ind1)
        self.assertTrue(updated)
        self.assertEqual(len(self.elite_map), 1)
        
        coords = self.ind1.get_feature_tuple()
        retrieved = self.elite_map.get_elite(coords)
        self.assertEqual(retrieved.genome.genome_id, self.ind1.genome.genome_id)

    def test_replace_with_better_rank(self):
        """Test that an elite is replaced by an individual with a better rank."""
        self.elite_map.add_individual(self.ind1)
        
        updated = self.elite_map.add_individual(self.ind2_better)
        self.assertTrue(updated)
        self.assertEqual(len(self.elite_map), 1)
        
        coords = self.ind1.get_feature_tuple()
        retrieved = self.elite_map.get_elite(coords)
        self.assertEqual(retrieved.genome.genome_id, self.ind2_better.genome.genome_id)

    def test_do_not_replace_with_worse(self):
        """Test that an elite is not replaced by a worse individual."""
        self.elite_map.add_individual(self.ind1)
        
        updated = self.elite_map.add_individual(self.ind3_worse)
        self.assertFalse(updated)
        self.assertEqual(len(self.elite_map), 1)
        
        coords = self.ind1.get_feature_tuple()
        retrieved = self.elite_map.get_elite(coords)
        self.assertEqual(retrieved.genome.genome_id, self.ind1.genome.genome_id)

    def test_replace_with_same_rank_higher_crowding(self):
        """Test replacement by an individual with same rank but higher crowding distance."""
        self.elite_map.add_individual(self.ind1)
        
        updated = self.elite_map.add_individual(self.ind4_crowded)
        self.assertTrue(updated)
        
        coords = self.ind1.get_feature_tuple()
        retrieved = self.elite_map.get_elite(coords)
        self.assertEqual(retrieved.genome.genome_id, self.ind4_crowded.genome.genome_id)

    def test_add_to_different_niches(self):
        """Test adding individuals to different niches."""
        self.elite_map.add_individual(self.ind1)
        self.elite_map.add_individual(self.ind5_other_niche)
        self.assertEqual(len(self.elite_map), 2)
        
        coords1 = self.ind1.get_feature_tuple()
        coords5 = self.ind5_other_niche.get_feature_tuple()
        
        self.assertIsNotNone(self.elite_map.get_elite(coords1))
        self.assertIsNotNone(self.elite_map.get_elite(coords5))

    def test_get_random_elites(self):
        """Test retrieving random elites."""
        self.elite_map.add_individual(self.ind1)
        self.elite_map.add_individual(self.ind5_other_niche)
        
        random_elites = self.elite_map.get_random_elites(k=1)
        self.assertEqual(len(random_elites), 1)
        
        random_elites = self.elite_map.get_random_elites(k=3) # k > num_elites
        self.assertEqual(len(random_elites), 2)
        
        all_ids = {self.ind1.genome.genome_id, self.ind5_other_niche.genome.genome_id}
        retrieved_ids = {e.genome.genome_id for e in random_elites}
        self.assertEqual(all_ids, retrieved_ids)

if __name__ == '__main__':
    unittest.main()
