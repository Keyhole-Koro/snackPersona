import json
import os
from typing import Dict, List
from datetime import datetime


class SourceMemory:
    """
    Persistent memory of domain quality scores across runs.
    Stores visit counts, average authority, and last-seen timestamps.
    Data is saved as a JSON file.
    """
    def __init__(self, filepath: str = "source_memory.json"):
        self.filepath = filepath
        self.domains: Dict[str, dict] = {}
        self.load()

    def load(self):
        """Load memory from disk."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r') as f:
                    self.domains = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.domains = {}

    def save(self):
        """Persist memory to disk."""
        with open(self.filepath, 'w') as f:
            json.dump(self.domains, f, indent=2, ensure_ascii=False)

    def record_visit(self, domain: str, authority_score: float = 0.5):
        """
        Record a visit to a domain, updating its running average authority.
        """
        if domain not in self.domains:
            self.domains[domain] = {
                "visits": 0,
                "avg_authority": 0.0,
                "last_seen": ""
            }

        entry = self.domains[domain]
        old_avg = entry["avg_authority"]
        old_count = entry["visits"]

        # Incremental mean update
        new_count = old_count + 1
        entry["avg_authority"] = old_avg + (authority_score - old_avg) / new_count
        entry["visits"] = new_count
        entry["last_seen"] = datetime.now().isoformat()

    def get_domain_boost(self, domain: str) -> float:
        """
        Returns a reputation boost for a domain based on past visits.
        Range: [0.0, 0.3] — higher for frequently visited, high-authority domains.
        """
        if domain not in self.domains:
            return 0.0

        entry = self.domains[domain]
        # Boost scales with both authority and familiarity (capped visits)
        familiarity = min(entry["visits"] / 20.0, 1.0)  # cap at 20 visits
        return entry["avg_authority"] * familiarity * 0.3

    def get_preferred_domains(self, top_k: int = 10) -> List[str]:
        """Returns the top-k domains by average authority score."""
        sorted_domains = sorted(
            self.domains.items(),
            key=lambda x: x[1]["avg_authority"] * min(x[1]["visits"], 10),
            reverse=True
        )
        return [d[0] for d in sorted_domains[:top_k]]
