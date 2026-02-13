import random
from typing import Dict, Tuple, List, Optional

from snackPersona.traveler.utils.data_models import EvaluatedTraveler

class EliteMap:
    """
    Manages the MAP-Elites grid.

    The grid stores the single best individual (elite) for each niche,
    defined by the feature descriptors.
    """
    def __init__(self, resolution: int = 10):
        self.resolution = resolution
        # The keys are tuples of integer coordinates, e.g., (3, 7)
        self.elites: Dict[Tuple[int, int], EvaluatedTraveler] = {}

    def _is_better(self, new: EvaluatedTraveler, old: EvaluatedTraveler) -> bool:
        """Determines if the new individual is better than the old one."""
        if new.rank < old.rank:
            return True
        if new.rank == old.rank and new.crowding_distance > old.crowding_distance:
            return True
        return False

    def add_individual(self, individual: EvaluatedTraveler) -> bool:
        """
        Attempts to add an individual to the map.

        The individual is added if its niche is empty, or if it is 'better'
        than the existing elite in that niche.

        Returns True if the map was updated, False otherwise.
        """
        coords = individual.get_feature_tuple(self.resolution)
        
        existing_elite = self.elites.get(coords)
        
        if existing_elite is None or self._is_better(individual, existing_elite):
            self.elites[coords] = individual
            return True
            
        return False

    def get_elite(self, coords: Tuple[int, int]) -> Optional[EvaluatedTraveler]:
        """Retrieves the elite from a specific niche."""
        return self.elites.get(coords)

    def get_random_elites(self, k: int) -> List[EvaluatedTraveler]:
        """Selects k random elites from the map to serve as parents."""
        if not self.elites:
            return []
        
        # Ensure we don't try to sample more than what's available
        num_to_sample = min(k, len(self.elites))
        
        return random.sample(list(self.elites.values()), num_to_sample)

    @property
    def all_elites(self) -> List[EvaluatedTraveler]:
        """Returns all elites currently in the map."""
        return list(self.elites.values())

    def __len__(self) -> int:
        return len(self.elites)
        
    def __str__(self) -> str:
        return f"EliteMap(resolution={self.resolution}, elites={len(self.elites)})"

