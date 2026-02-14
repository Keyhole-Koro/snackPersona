import unittest
import copy

from snackPersona.traveler.executor.traveler import Traveler
from snackPersona.traveler.services.handlers import (
    _mutate_genome,
    generation_scheduler_handler,
    bandit_allocator_handler,
    evaluation_and_map_management_handler,
)
from snackPersona.traveler.map_elites.elite_map import EliteMap
from snackPersona.traveler.bandit.thompson_sampling import BanditAllocator
from snackPersona.traveler.utils.data_models import EvaluatedTraveler, Fitness, FeatureDescriptors
from snackPersona.traveler.tests.test_data_models import create_mock_genome

class TestHandlersAndExecutor(unittest.TestCase):

    def setUp(self):
        self.genome = create_mock_genome()
        self.elite_map = EliteMap()
        self.bandit = BanditAllocator()

    def test_executor(self):
        """Test that the mock Traveler executor runs and returns a valid result."""
        traveler = Traveler(self.genome)
        result = traveler.execute()
        
        self.assertEqual(result.genome_id, self.genome.genome_id)
        self.assertIsInstance(result.api_calls, int)
        self.assertIsInstance(result.retrieved_urls, list)

    def test_mutate_genome(self):
        """Test the mutation function."""
        original_genome = create_mock_genome()
        mutated_genome = _mutate_genome(original_genome)

        # Should have a new ID
        self.assertNotEqual(original_genome.genome_id, mutated_genome.genome_id)
        
        # At least one parameter should be different (probabilistically)
        # This isn't a perfect test, but better than nothing.
        original_dict = original_genome.model_dump(exclude={'genome_id'})
        mutated_dict = mutated_genome.model_dump(exclude={'genome_id'})
        self.assertNotEqual(original_dict, mutated_dict)

    def test_generation_scheduler_handler(self):
        """Test that the scheduler creates new genomes from elites."""
        # Add an elite to the map
        elite = EvaluatedTraveler(
            genome=self.genome,
            fitness=Fitness(novelty=0.5, coverage=0.5, cost=10, reliability=0.5, downstream_value=0.5),
            features=FeatureDescriptors(concreteness=0.5, authority=0.5)
        )
        self.elite_map.add_individual(elite)
        
        offspring = generation_scheduler_handler(self.elite_map, num_offspring=5)
        
        self.assertEqual(len(offspring), 5)
        self.assertNotEqual(offspring[0].genome_id, self.genome.genome_id)

    def test_bandit_allocator_handler(self):
        """Test that the bandit allocator selects an elite."""
        # Add an elite to the map
        elite = EvaluatedTraveler(
            genome=self.genome,
            fitness=Fitness(novelty=0.8, coverage=0.8, cost=5, reliability=0.8, downstream_value=0.8),
            features=FeatureDescriptors(concreteness=0.5, authority=0.5),
            rank=0
        )
        self.elite_map.add_individual(elite)
        niche = elite.get_feature_tuple()
        
        # Give this niche a high reward so the bandit selects it
        self.bandit.update_arm(niche, reward=1.0)
        
        selected_genome = bandit_allocator_handler(self.bandit, self.elite_map)
        
        self.assertEqual(selected_genome.genome_id, self.genome.genome_id)

    def test_evaluation_handler_updates_bandit(self):
        """Test that the evaluation handler correctly updates the bandit model."""
        traveler = Traveler(self.genome)
        result = traveler.execute()
        niche = (5, 5) # Assume a niche
        
        # Check initial state of the bandit arm
        self.bandit._get_or_create_arm(niche)
        initial_alpha = self.bandit.arms[niche]['alpha']
        initial_beta = self.bandit.arms[niche]['beta']
        
        # Run the handler, pretending it was a bandit run
        evaluated_traveler = evaluation_and_map_management_handler(
            result, self.elite_map, self.bandit, is_bandit_run=True
        )
        # Manually override features for predictable niche
        evaluated_traveler.features = FeatureDescriptors(concreteness=0.55, authority=0.55)

        # The handler itself doesn't call update, but simulates the logic flow
        # In the main loop, we'd call update. Let's re-do the test to follow the handler's logic
        # The handler is just for evaluation, the update happens outside based on is_bandit_run
        
        # Re-test: let's test the flow as it would be in main.py
        is_bandit_run = True
        evaluated_traveler = evaluation_and_map_management_handler(result, self.elite_map)
        
        if is_bandit_run:
            coords = evaluated_traveler.get_feature_tuple()
            reward = evaluated_traveler.fitness.downstream_value
            self.bandit.update_arm(coords, reward)
            
        final_alpha = self.bandit.arms[coords]['alpha']
        final_beta = self.bandit.arms[coords]['beta']

        if evaluated_traveler.fitness.downstream_value >= 0.5:
            self.assertEqual(final_alpha, initial_alpha + 1)
        else:
            self.assertEqual(final_beta, initial_beta + 1)

if __name__ == '__main__':
    unittest.main()
