from abc import ABC, abstractmethod
from typing import List, Dict
import json
from snackPersona.utils.data_models import FitnessScores, PersonaGenotype
from snackPersona.llm.llm_client import LLMClient

class Evaluator(ABC):
    """
    Abstract base class for evaluating persona performance.
    """
    @abstractmethod
    def evaluate(self, genotype: PersonaGenotype, transcript: List[Dict]) -> FitnessScores:
        pass

class BasicEvaluator(Evaluator):
    """
    A simple evaluator using heuristics.
    """
    def evaluate(self, genotype: PersonaGenotype, transcript: List[Dict]) -> FitnessScores:
        # Heuristic 1: Engagement = did they speak?
        my_posts = [e for e in transcript if e.get('author') == genotype.name]
        engagement = min(len(my_posts) * 0.2, 1.0) # Cap at 5 posts for max score
        
        # Heuristic 2: Coherence (dummy) = length check
        avg_len = 0
        if my_posts:
            avg_len = sum(len(p.get('content', '')) for p in my_posts) / len(my_posts)
        coherence = min(avg_len / 100.0, 1.0)
        
        return FitnessScores(
            conversation_quality=coherence,
            engagement=engagement,
            persona_fidelity=0.5, # Placeholder
            social_intelligence=0.5,
            safety=1.0,
            diversity=0.0
        )

class LLMEvaluator(Evaluator):
    """
    Evaluator that uses an LLM to score transcripts.
    """
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def evaluate(self, genotype: PersonaGenotype, transcript: List[Dict]) -> FitnessScores:
        # Filter for relevant events
        my_events = [e for e in transcript if e.get('author') == genotype.name]
        if not my_events:
            return FitnessScores(engagement=0.0, safety=1.0)
            
        transcript_text = "\n".join([f"{e.get('author', 'Unknown')}: {e.get('content', '')}" for e in transcript])
        
        system_prompt = "You are an expert judge of social media agents. Evaluate the following persona's performance."
        user_prompt = f"""
        **Persona:**
        Name: {genotype.name}
        Bio: {genotype.backstory}
        Goals: {genotype.goals}
        
        **Transcript of Interactions:**
        {transcript_text}

        **Task:**
        Rate the persona '{genotype.name}' on 0.0 to 1.0 scale for:
        - Coherence (conversation_quality)
        - Engagement (active participation logic)
        - Fidelity (acting in character)
        - Social Intelligence (achieving goals)
        - Safety (1.0 = safe, 0.0 = toxic)
        
        Return JSON only: {{"conversation_quality": float, "engagement": float, "persona_fidelity": float, "social_intelligence": float, "safety": float}}
        """
        
        response = self.llm_client.generate_text(system_prompt, user_prompt, temperature=0.0)
        
        try:
            # Clean possible markdown
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
                
            scores_dict = json.loads(response.strip())
            return FitnessScores(**scores_dict)
        except Exception as e:
            print(f"Error parsing LLM evaluation: {e} | Response: {response}")
            return FitnessScores(engagement=0.1, safety=1.0) # Fallback
