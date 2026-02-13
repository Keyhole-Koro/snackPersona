from abc import ABC, abstractmethod
from typing import List, Dict
import json
from snackPersona.utils.data_models import FitnessScores, PersonaGenotype
from snackPersona.llm.llm_client import LLMClient
from snackPersona.evaluation.diversity import DiversityEvaluator


class Evaluator(ABC):
    """Abstract base class for evaluating persona performance."""
    @abstractmethod
    def evaluate(self, genotype: PersonaGenotype, transcript: List[Dict]) -> FitnessScores:
        pass


class LLMEvaluator(Evaluator):
    """
    Content-based evaluator that scores actual posts and replies.
    Focuses on the quality and realism of written content rather
    than abstract persona fidelity metrics.
    """
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def evaluate(self, genotype: PersonaGenotype, transcript: List[Dict]) -> FitnessScores:
        my_events = [e for e in transcript if e.get('author') == genotype.name]
        if not my_events:
            return FitnessScores(engagement=0.0, safety=1.0)

        # Separate posts and replies for focused evaluation
        posts = [e for e in my_events if e.get('type') == 'post']
        replies = [e for e in my_events if e.get('type') == 'reply']

        transcript_text = "\n".join([
            f"{e.get('author', '?')}: {e.get('content', '')}"
            for e in transcript
            if e.get('type') != 'pass'
        ])

        # Calculate judiciousness (silence)
        # If they posted 0 times when others posted, that might be judicious (or just inactive).
        # We'll let the LLM judge if the silence was "smart" based on the transcript context.
        
        system_prompt = (
            "You are an expert judge of social media content. "
            "Evaluate how realistic, engaging, and incisive a user's behavior is."
        )

        user_prompt = f"""**User being evaluated:** {genotype.name}

**Their posts:**
{chr(10).join(f'- {p.get("content", "")}' for p in posts) or '(no posts)'}

**Their replies:**
{chr(10).join(f'- [to {r.get("target_author", "?")}] {r.get("content", "")}' for r in replies) or '(no replies)'}

**Full conversation context:**
{transcript_text}

**Task:**
Rate this user on a 0.0 to 1.0 scale for these metrics:
- post_quality: Interesting, funny, or thought-provoking?
- reply_quality: Natural and conversational?
- engagement: Participation level.
- authenticity: Feels like a real person?
- safety: Non-toxic (1.0 = safe).
- incisiveness: "Moto-mo-ko-mo-nai". Did they cut to the chase and make a decisive, conversation-stopping statement? 
  (High score for blunt/bold statements—whether brutally honest OR confidently false. Low for hedging/uncertainty.)
- judiciousness: Did they speak only when necessary? 
  (High score for staying silent on irrelevant topics or speaking with purpose. Low for spamming or mindless chatter.)

Return JSON only: {{"post_quality": float, "reply_quality": float, "engagement": float, "authenticity": float, "safety": float, "incisiveness": float, "judiciousness": float}}
"""

        response = self.llm_client.generate_text(system_prompt, user_prompt, temperature=0.0)

        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]

            scores_dict = json.loads(response.strip())

            # Add diversity from embedding analysis
            diversity = 0.0
            if len(my_events) >= 2:
                diversity = DiversityEvaluator.calculate_overall_diversity(my_events)
            scores_dict['diversity'] = diversity

            return FitnessScores(**scores_dict)
        except Exception as e:
            print(f"Error parsing LLM evaluation: {e} | Response: {response}")
            return FitnessScores(engagement=0.1, safety=1.0)
