"""
Adapter module for integrating snackPersona with snackPersona.traveler.
Translates a PersonaGenotype into a TravelerGenome.
"""
import json
import random
import uuid
from typing import Optional

from snackPersona.utils.data_models import PersonaGenotype
from snackPersona.traveler.utils.data_models import TravelerGenome, SourceBias
from snackPersona.llm.llm_client import LLMClient
from snackPersona.utils.logger import logger


class PersonaToTravelerAdapter:
    """
    Adapts a PersonaGenotype (Who) into a TravelerGenome (What/How to search).
    Uses an LLM to infer search preferences from the persona's bio.
    """
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def adapt(self, persona: PersonaGenotype) -> TravelerGenome:
        """
        Generate a TravelerGenome based on the persona's bio.
        """
        logger.info(f"Adapting persona '{persona.name}' to TravelerGenome...")
        
        system_prompt = "You are an expert at mapping personality traits to information consumption habits."
        user_prompt = f"""
        Analyze the following persona bio and determine their information seeking behavior.
        
        Persona Name: {persona.name}
        Bio: {persona.bio}
        
        Generate a JSON object representing their 'Traveler Genome' with these fields:
        
        1. "source_bias": A dictionary with keys ["academic", "news", "official", "blogs"].
           - Values between -1.0 (avoid) and 1.0 (prefer).
           - Example: A scientist might prefer "academic": 0.8, "blogs": -0.2.
           
        2. "query_templates": Choose ONE of these IDs that best fits their search style:
           - "template_v1_broad" (Broad, general topics)
           - "template_v2_specific" (Specific, technical queries)
           - "template_v3_questioning" (Ask questions like 'why is...')
           - "template_v4_news_focused" (Latest news, 'breaking...')
           
        3. "search_depth": Integer 1 (quick scan) or 2 (deep dive).
        
        4. "novelty_weight": Float 0.0 to 1.0. (How much do they like new/unusual info?)
        
        Return ONLY valid JSON.
        """
        
        try:
            response = self.llm_client.generate_text(system_prompt, user_prompt, temperature=0.3)
            data = self._parse_json(response)
            
            # Construct genome
            bias_data = data.get("source_bias", {})
            source_bias = SourceBias(
                academic=float(bias_data.get("academic", 0.0)),
                news=float(bias_data.get("news", 0.0)),
                official=float(bias_data.get("official", 0.0)),
                blogs=float(bias_data.get("blogs", 0.0))
            )
            
            return TravelerGenome(
                genome_id=str(uuid.uuid4()),
                query_diversity=random.random(), # Stochastic per instance
                query_template_id=data.get("query_templates", "template_v1_broad"),
                language_mix=0.1, # Default mostly English/Primary language
                source_bias=source_bias,
                search_depth=int(data.get("search_depth", 1)),
                novelty_weight=float(data.get("novelty_weight", 0.5))
            )
            
        except Exception as e:
            logger.error(f"Failed to adapt persona {persona.name}: {e}")
            # Fallback to random/default genome
            return self._create_fallback_genome()

    def _parse_json(self, text: str) -> dict:
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text.strip())

    def _create_fallback_genome(self) -> TravelerGenome:
        return TravelerGenome(
            genome_id=str(uuid.uuid4()),
            query_diversity=0.5,
            query_template_id="template_v1_broad",
            language_mix=0.0,
            source_bias=SourceBias(academic=0, news=0, official=0, blogs=0),
            search_depth=1,
            novelty_weight=0.5
        )
