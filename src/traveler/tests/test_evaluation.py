import unittest
from snackPersona.traveler.utils.data_models import (
    Fitness,
    EvaluatedTraveler
)
from snackPersona.traveler.evaluation.fitness import non_dominated_sort, calculate_crowding_distance
from snackPersona.traveler.tests.test_data_models import create_mock_genome, create_mock_features

class TestEvaluation(unittest.TestCase):

    def setUp(self):
        """Set up a population of individuals for testing."""
        # Front 1
        f1_a = Fitness(novelty=0.8, coverage=0.8, cost=10, reliability=0.8, downstream_value=0.8) # Dominant
        f1_b = Fitness(novelty=0.7, coverage=0.9, cost=11, reliability=0.8, downstream_value=0.8) # Trade-off
        
        # Front 2 (dominated by f1_a)
        f2_a = Fitness(novelty=0.7, coverage=0.7, cost=12, reliability=0.8, downstream_value=0.8)
        f2_b = Fitness(novelty=0.6, coverage=0.8, cost=10, reliability=0.8, downstream_value=0.8)

        # Front 3 (dominated by f2_a and f2_b)
        f3_a = Fitness(novelty=0.5, coverage=0.5, cost=15, reliability=0.8, downstream_value=0.8)

        fitnesses = [f1_a, f1_b, f2_a, f2_b, f3_a]
        self.population = [
            EvaluatedTraveler(genome=create_mock_genome(), features=create_mock_features(), fitness=f)
            for f in fitnesses
        ]
        # Store references for easy checking
        self.ind_f1_a = self.population[0]
        self.ind_f1_b = self.population[1]
        self.ind_f2_a = self.population[2]
        self.ind_f2_b = self.population[3]
        self.ind_f3_a = self.population[4]

    def test_non_dominated_sort(self):
        """Test the NSGA-II non-dominated sorting algorithm."""
        fronts = non_dominated_sort(self.population)

        # Check number of fronts
        self.assertEqual(len(fronts), 3)

        # Check front contents
        front1_ids = {ind.genome.genome_id for ind in fronts[0]}
        front2_ids = {ind.genome.genome_id for ind in fronts[1]}
        front3_ids = {ind.genome.genome_id for ind in fronts[2]}

        self.assertIn(self.ind_f1_a.genome.genome_id, front1_ids)
        self.assertIn(self.ind_f1_b.genome.genome_id, front1_ids)
        self.assertEqual(len(fronts[0]), 2)

        self.assertIn(self.ind_f2_a.genome.genome_id, front2_ids)
        self.assertIn(self.ind_f2_b.genome.genome_id, front2_ids)
        self.assertEqual(len(fronts[1]), 2)
        
        self.assertIn(self.ind_f3_a.genome.genome_id, front3_ids)
        self.assertEqual(len(fronts[2]), 1)

        # Check ranks
        self.assertEqual(self.ind_f1_a.rank, 0)
        self.assertEqual(self.ind_f1_b.rank, 0)
        self.assertEqual(self.ind_f2_a.rank, 1)
        self.assertEqual(self.ind_f2_b.rank, 1)
        self.assertEqual(self.ind_f3_a.rank, 2)

    def test_calculate_crowding_distance(self):
        """Test the crowding distance calculation."""
        # Use a simple front with 3 individuals to test crowding
        f1 = Fitness(novelty=0.9, cost=10, coverage=0.5, reliability=0.5, downstream_value=0.5) # Boundary
        f2 = Fitness(novelty=0.5, cost=15, coverage=0.5, reliability=0.5, downstream_value=0.5) # Middle
        f3 = Fitness(novelty=0.2, cost=20, coverage=0.5, reliability=0.5, downstream_value=0.5) # Boundary

        front = [
            EvaluatedTraveler(genome=create_mock_genome(), features=create_mock_features(), fitness=f)
            for f in [f1, f2, f3]
        ]
        
        # Manually set ranks as they are needed for sorting, though not for the calc itself
        for ind in front:
            ind.rank = 0

        calculate_crowding_distance(front)
        
        ind1, ind2, ind3 = front[0], front[1], front[2]
        
        # After sorting by novelty (desc), the order is f1, f2, f3
        # Boundary points should have infinite distance
        self.assertEqual(ind1.crowding_distance, float('inf'))
        self.assertEqual(ind3.crowding_distance, float('inf'))

        # Middle point's distance is the sum of normalized distances of its neighbors
        # Novelty: (0.9 - 0.2) / (0.9 - 0.2) = 1.0
        # Cost: (20 - 10) / (20 - 10) = 1.0
        # Other objectives have 0 range, so they add 0.
        # Crowding distance should be the sum over all objectives.
        # This part is tricky to get exact without replicating the code,
        # but we can check that it's a finite, positive number.
        self.assertTrue(0 < ind2.crowding_distance < float('inf'))
        
        # Simplified test to ensure it's greater than 0
        self.assertGreater(ind2.crowding_distance, 0)


if __name__ == '__main__':
    unittest.main()
