from typing import List
import json
import os
from snackPersona.utils.data_models import PersonaGenotype

class PersonaStore:
    """
    Manages persistence of persona genotypes.
    """
    def __init__(self, storage_dir: str):
        self.storage_dir = storage_dir
        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir)

    def save_generation(self, generation_id: int, population: List[PersonaGenotype]):
        """
        Saves a list of PersonaGenotypes to a JSON file.
        """
        filename = f"gen_{generation_id}.json"
        filepath = os.path.join(self.storage_dir, filename)
        
        data = [p.model_dump() for p in population]
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
            
    def load_generation(self, generation_id: int) -> List[PersonaGenotype]:
        """
        Loads a list of PersonaGenotypes from a JSON file.
        """
        filename = f"gen_{generation_id}.json"
        filepath = os.path.join(self.storage_dir, filename)
        
        if not os.path.exists(filepath):
            return []
            
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        return [PersonaGenotype(**item) for item in data]

    def list_generations(self) -> List[int]:
        """
        Returns a sorted list of available generation IDs.
        """
        generations = []
        for filename in os.listdir(self.storage_dir):
            if filename.startswith("gen_") and filename.endswith(".json"):
                try:
                    gen_id = int(filename.split("_")[1].split(".")[0])
                    generations.append(gen_id)
                except ValueError:
                    continue
        return sorted(generations)
