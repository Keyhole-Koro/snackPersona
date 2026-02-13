import random
from typing import Dict, Tuple

class BanditAllocator:
    """
    Selects which niche to exploit using a Thompson Sampling bandit algorithm.

    Each niche in the MAP-Elites grid is treated as an 'arm' of the bandit.
    The reward can be defined in many ways, but for this simulation, we'll
    use the 'downstream_value' from the fitness, assuming a value > 0.5 is a "success".
    """
    def __init__(self, resolution: int = 10):
        self.resolution = resolution
        # Stores the alpha and beta parameters for the Beta distribution of each arm.
        # Key is the niche coordinate tuple, e.g., (3, 7)
        self.arms: Dict[Tuple[int, int], Dict[str, int]] = {}

    def _get_or_create_arm(self, coords: Tuple[int, int]):
        """Initializes a new arm with alpha=1, beta=1 if it doesn't exist."""
        if coords not in self.arms:
            # Start with a uniform prior (Beta(1,1))
            self.arms[coords] = {'alpha': 1, 'beta': 1}

    def select_arm(self) -> Tuple[int, int]:
        """
        Selects an arm (niche) to pull based on Thompson Sampling.

        It samples a value from each arm's Beta distribution and chooses the
        arm with the highest sample. If no arms exist, it returns a random niche.
        """
        if not self.arms:
            # If no arms have been observed, pick a random one.
            return (random.randint(0, self.resolution - 1), random.randint(0, self.resolution - 1))

        max_sample = -1
        best_arm = None

        for coords, params in self.arms.items():
            sample = random.betavariate(params['alpha'], params['beta'])
            if sample > max_sample:
                max_sample = sample
                best_arm = coords
        
        return best_arm

    def update_arm(self, coords: Tuple[int, int], reward: float):
        """
        Updates the parameters of the chosen arm based on the observed reward.

        Args:
            coords: The coordinates of the arm that was pulled.
            reward: The observed reward, typically between 0 and 1.
        """
        self._get_or_create_arm(coords)
        
        # Simple binary reward: 1 if success, 0 if failure.
        # This is a common way to use Thompson Sampling with Beta distributions.
        if reward >= 0.5:
            self.arms[coords]['alpha'] += 1
        else:
            self.arms[coords]['beta'] += 1

    def __str__(self) -> str:
        return f"BanditAllocator(arms={len(self.arms)})"

