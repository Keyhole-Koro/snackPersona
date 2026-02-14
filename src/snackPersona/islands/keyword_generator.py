"""
Persona-driven keyword generation for search queries.
"""
import logging
import json
from typing import List, Optional
from snackPersona.utils.data_models import PersonaGenotype
from snackPersona.llm.llm_client import LLMClient

logger = logging.getLogger("snackPersona")


class PersonaKeywordGenerator:
    """
    Generates search keywords based on persona bio and interests using LLM.
    """
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize the keyword generator.
        
        Args:
            llm_client: LLM client for generating keywords
        """
        self.llm_client = llm_client
    
    def generate_keywords(self, persona: PersonaGenotype, topic: Optional[str] = None,
                         num_keywords: int = 5) -> List[str]:
        """
        Generate search keywords based on persona's bio and optional topic.
        
        Args:
            persona: PersonaGenotype to analyze
            topic: Optional specific topic to focus on
            num_keywords: Number of keywords to generate
            
        Returns:
            List of search keywords
        """
        topic_context = f" related to {topic}" if topic else ""
        
        system_prompt = "You are an expert at understanding user interests and generating relevant search queries."
        
        user_prompt = f"""Based on this persona's background and interests, generate {num_keywords} diverse search keywords{topic_context}.

Persona: {persona.name}
Bio: {persona.bio}

The keywords should:
1. Reflect the persona's interests, profession, and background
2. Be specific and actionable for web search
3. Cover different aspects of their interests
4. Be phrased naturally (not just single words)

Return ONLY a JSON array of strings, e.g. ["keyword 1", "keyword 2", ...]
No explanations, no markdown formatting."""

        try:
            response = self.llm_client.generate_text(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.8
            )
            
            # Parse response
            text = response.strip()
            
            # Remove markdown code blocks if present
            if "```" in text:
                text = text.split("```json")[-1].split("```")[0].strip()
                if not text:
                    text = response.split("```")[-2].strip()
            
            keywords = json.loads(text)
            
            if isinstance(keywords, list) and len(keywords) > 0:
                logger.info(f"Generated {len(keywords)} keywords for {persona.name}")
                return keywords[:num_keywords]
            else:
                logger.warning(f"Invalid keyword format, got: {keywords}")
                return self._fallback_keywords(persona, topic, num_keywords)
                
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from LLM response: {e}. Response: {response[:200]}")
            return self._fallback_keywords(persona, topic, num_keywords)
        except Exception as e:
            logger.error(f"Failed to generate keywords for {persona.name}: {e}")
            return self._fallback_keywords(persona, topic, num_keywords)
    
    def _fallback_keywords(self, persona: PersonaGenotype, topic: Optional[str], num_keywords: int) -> List[str]:
        """
        Generate fallback keywords based on simple bio parsing.
        
        Args:
            persona: PersonaGenotype
            topic: Optional topic
            num_keywords: Number of keywords desired
            
        Returns:
            List of fallback keywords
        """
        # Extract key words from bio (simple approach)
        bio_words = persona.bio.lower().split()
        
        # Filter out common words
        stop_words = {'i', 'me', 'my', 'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                     'of', 'with', 'by', 'from', 'as', 'is', 'was', 'am', 'are', 'been', 'be', 'have', 'has',
                     'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might', 'must',
                     'can', 'that', 'this', 'these', 'those', 'it'}
        
        interesting_words = [w for w in bio_words if len(w) > 3 and w not in stop_words]
        
        # Generate simple keywords
        keywords = []
        if topic:
            keywords.append(f"{topic} news")
            keywords.append(f"{topic} trends")
        
        # Add words from bio
        for word in interesting_words[:num_keywords - len(keywords)]:
            keywords.append(word)
        
        # Pad with generic keywords if needed
        while len(keywords) < num_keywords:
            keywords.append("latest news")
        
        logger.debug(f"Using fallback keywords for {persona.name}: {keywords}")
        return keywords[:num_keywords]
    
    def generate_search_query(self, persona: PersonaGenotype, topic: Optional[str] = None) -> str:
        """
        Generate a complete search query string for a persona.
        
        Args:
            persona: PersonaGenotype
            topic: Optional topic to focus on
            
        Returns:
            Search query string
        """
        keywords = self.generate_keywords(persona, topic, num_keywords=3)
        
        # Combine keywords into a natural query
        if len(keywords) == 0:
            return "latest news" if not topic else f"{topic} news"
        
        # Join keywords with variations
        if len(keywords) == 1:
            return keywords[0]
        elif len(keywords) == 2:
            return f"{keywords[0]} {keywords[1]}"
        else:
            # For 3+ keywords, create a more natural query
            return " ".join(keywords[:3])
