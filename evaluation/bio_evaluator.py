"""
Evaluator for assessing the quality and style of the persona bio text itself.
"""
import json
from snackPersona.utils.data_models import PersonaGenotype
from snackPersona.llm.llm_client import LLMClient
from snackPersona.utils.logger import logger


class BioStyleEvaluator:
    """
    Evaluates the narrative quality of a persona's bio.
    Penalizes "resume-speak" (lists of attributes, goals: ..., values: ...)
    and rewards authentic, first-person storytelling.
    """
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def evaluate_bio(self, genotype: PersonaGenotype) -> float:
        """
        Rate the bio on a scale of 0.0 to 1.0 for narrative authenticity.
        """
        system_prompt = "You are a creative writing critic."
        user_prompt = f"""
        Evaluate the following persona bio for its narrative style.
        
        **Target Style (Valid):** 
        - First-person perspective ("I...")
        - Tells a micro-story or slice of life.
        - Feels like a real human introduction on a social profile.
        - Includes specific, messy details (quirks, complaints, situation).
        
        **Avoid (Invalid):**
        - Resume-speak or list format.
        - Explicit labels like "Goals:", "Core Values:", "Personality:".
        - Generic, robotic descriptions.
        
        Bio: "{genotype.bio}"
        
        Rate on a scale of 0.0 to 1.0 (1.0 = Perfect Story, 0.0 = Robotic List).
        Return ONLY a JSON object: {{"score": float}}
        """
        
        try:
            response = self.llm_client.generate_text(system_prompt, user_prompt, temperature=0.1)
            score = self._parse_score(response)
            return score
        except Exception as e:
            logger.warning(f"Bio evaluation failed for {genotype.name}: {e}")
            return 0.5 # Default fallback

    def _parse_score(self, text: str) -> float:
        try:
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            data = json.loads(text.strip())
            return float(data.get("score", 0.0))
        except:
            return 0.5
