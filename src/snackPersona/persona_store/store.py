"""
Manages persistence of persona genotypes with file-level locking
for safe concurrent access.
"""

from typing import List
import json
import os

from filelock import FileLock

from snackPersona.utils.data_models import PersonaGenotype
from snackPersona.utils.logger import logger


class PersonaStore:
    """
    Manages persistence of persona genotypes.

    Uses ``filelock.FileLock`` so multiple processes can safely
    read/write generation files concurrently.
    """

    def __init__(self, storage_dir: str):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

    def _filepath(self, generation_id: int) -> str:
        return os.path.join(self.storage_dir, f"gen_{generation_id}.json")

    def _lockpath(self, generation_id: int) -> str:
        return self._filepath(generation_id) + ".lock"

    def save_generation(self, generation_id: int, population: List[PersonaGenotype]):
        """Save a list of PersonaGenotypes to a JSON file (with file lock)."""
        filepath = self._filepath(generation_id)
        lock = FileLock(self._lockpath(generation_id), timeout=30)

        data = [p.model_dump() for p in population]

        with lock:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)

        logger.debug(f"Saved generation {generation_id} ({len(population)} personas)")

    def load_generation(self, generation_id: int) -> List[PersonaGenotype]:
        """Load a list of PersonaGenotypes from a JSON file (with file lock)."""
        filepath = self._filepath(generation_id)

        if not os.path.exists(filepath):
            return []

        lock = FileLock(self._lockpath(generation_id), timeout=30)

        with lock:
            with open(filepath, 'r') as f:
                data = json.load(f)

        return [PersonaGenotype(**item) for item in data]

    def list_generations(self) -> List[int]:
        """Return a sorted list of available generation IDs."""
        generations = []
        if not os.path.exists(self.storage_dir):
            return generations
        for filename in os.listdir(self.storage_dir):
            if filename.startswith("gen_") and filename.endswith(".json"):
                try:
                    gen_id = int(filename.split("_")[1].split(".")[0])
                    generations.append(gen_id)
                except ValueError:
                    continue
        return sorted(generations)

    def save_transcripts(self, generation_id: int, transcripts: List[List[dict]]):
        """Save conversation transcripts for a generation.

        Parameters
        ----------
        generation_id : int
            The generation number.
        transcripts : list of list of dict
            One transcript (list of events) per group episode.
        """
        filepath = os.path.join(
            self.storage_dir, f"transcripts_gen_{generation_id}.json"
        )
        with open(filepath, "w") as f:
            json.dump(transcripts, f, indent=2, ensure_ascii=False)
        logger.debug(
            f"Saved {len(transcripts)} transcripts for generation {generation_id}"
        )
