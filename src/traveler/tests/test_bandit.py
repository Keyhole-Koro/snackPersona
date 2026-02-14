import unittest
import random
from collections import Counter

from snackPersona.traveler.bandit.thompson_sampling import BanditAllocator

class TestBanditAllocator(unittest.TestCase):

    def setUp(self):
        """Set up a new BanditAllocator for each test."""
        self.bandit = BanditAllocator(resolution=10)
        self.niche1 = (2, 3)
        self.niche2 = (5, 8)

    def test_arm_initialization(self):
        """Test that a new arm is initialized with alpha=1, beta=1."""
        self.bandit._get_or_create_arm(self.niche1)
        self.assertIn(self.niche1, self.bandit.arms)
        self.assertEqual(self.bandit.arms[self.niche1]['alpha'], 1)
        self.assertEqual(self.bandit.arms[self.niche1]['beta'], 1)

    def test_update_arm_success(self):
        """Test updating an arm with a success (reward >= 0.5)."""
        self.bandit.update_arm(self.niche1, reward=0.8)
        self.assertEqual(self.bandit.arms[self.niche1]['alpha'], 2) # 1 (initial) + 1 (success)
        self.assertEqual(self.bandit.arms[self.niche1]['beta'], 1)

    def test_update_arm_failure(self):
        """Test updating an arm with a failure (reward < 0.5)."""
        self.bandit.update_arm(self.niche1, reward=0.2)
        self.assertEqual(self.bandit.arms[self.niche1]['alpha'], 1)
        self.assertEqual(self.bandit.arms[self.niche1]['beta'], 2) # 1 (initial) + 1 (failure)

    def test_select_arm_from_unseen(self):
        """Test that a random arm is selected when no arms have been seen."""
        # Fix the seed for predictable "random" choice
        random.seed(42)
        niche = self.bandit.select_arm()
        self.assertIsInstance(niche, tuple)
        self.assertEqual(len(niche), 2)
        self.assertTrue(0 <= niche[0] < 10)
        self.assertTrue(0 <= niche[1] < 10)

    def test_selection_bias_after_updates(self):
        """
        Test that Thompson Sampling favors the arm with a higher success rate.
        This test is probabilistic, but with a strong bias it should pass consistently.
        """
        # Give niche1 a high success rate (90%)
        for _ in range(9):
            self.bandit.update_arm(self.niche1, reward=1.0)
        self.bandit.update_arm(self.niche1, reward=0.0)
        
        # Give niche2 a low success rate (10%)
        self.bandit.update_arm(self.niche2, reward=1.0)
        for _ in range(9):
            self.bandit.update_arm(self.niche2, reward=0.0)
        
        # In 100 trials, niche1 should be selected far more often
        selections = []
        for _ in range(100):
            selections.append(self.bandit.select_arm())
            
        counts = Counter(selections)
        
        # It's highly probable that niche1 is selected more than niche2.
        # It's almost certain it's selected more than 80 times.
        self.assertGreater(counts[self.niche1], 80)
        self.assertLess(counts[self.niche2], 20)

if __name__ == '__main__':
    unittest.main()
