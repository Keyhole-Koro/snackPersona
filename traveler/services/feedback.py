import json
import os
from typing import Optional
from datetime import datetime


class FeedbackCollector:
    """
    Collects user feedback on traveler results and converts ratings to rewards.
    Feedback is stored in a JSONL file for future analysis.
    Designed for future SNS integration — ratings can come from any source.
    """
    def __init__(self, filepath: str = "feedback_log.jsonl"):
        self.filepath = filepath
        self._pending: dict = {}  # genome_id -> rating

    def record_feedback(self, genome_id: str, rating: int):
        """
        Record a user rating for a specific genome's output.
        Rating: 1 (bad) to 5 (excellent).
        """
        rating = max(1, min(5, rating))
        self._pending[genome_id] = rating

        entry = {
            "genome_id": genome_id,
            "rating": rating,
            "timestamp": datetime.now().isoformat()
        }
        with open(self.filepath, 'a') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_reward(self, genome_id: str) -> Optional[float]:
        """
        Converts a stored rating to a [0, 1] reward for the bandit model.
        Returns None if no feedback exists for this genome.
        """
        rating = self._pending.get(genome_id)
        if rating is None:
            return None
        # Map 1-5 to 0.0-1.0
        return (rating - 1) / 4.0

    def prompt_user(self, genome_id: str, headlines: list) -> Optional[int]:
        """
        Interactive CLI prompt for user feedback.
        Returns the rating (1-5), or None if skipped.
        """
        if not headlines:
            print("  [No headlines to show]")
            return None

        print(f"\n  --- Headlines from traveler {genome_id[:8]}... ---")
        for i, h in enumerate(headlines, 1):
            print(f"    {i}. {h}")

        try:
            raw = input("  Rate these results (1-5, or 's' to skip): ").strip()
            if raw.lower() == 's' or raw == '':
                return None
            rating = int(raw)
            if 1 <= rating <= 5:
                self.record_feedback(genome_id, rating)
                return rating
        except (ValueError, EOFError):
            pass
        return None
