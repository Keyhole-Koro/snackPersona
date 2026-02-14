"""
Integration adapter for connecting Island system with Traveler and Personas.
"""
import logging
import json
import random
from typing import List, Optional
from urllib.parse import urlparse
from snackPersona.utils.data_models import PersonaGenotype
from snackPersona.islands.island_manager import IslandManager
from snackPersona.islands.keyword_generator import PersonaKeywordGenerator
from snackPersona.traveler.executor.traveler import Traveler
from snackPersona.traveler.utils.data_models import TravelerGenome, SourceBias, ExecutionResult
from snackPersona.traveler.utils.source_memory import SourceMemory
from snackPersona.llm.llm_client import LLMClient

logger = logging.getLogger("snackPersona")


class IslandTravelerIntegration:
    """
    Integrates Island clustering with Traveler's web search and crawling capabilities.
    Allows personas to generate keywords and search for content relevant to their islands.
    """
    
    def __init__(self, island_manager: IslandManager, llm_client: LLMClient):
        """
        Initialize the integration layer.
        
        Args:
            island_manager: IslandManager instance
            llm_client: LLM client for keyword generation
        """
        self.island_manager = island_manager
        self.keyword_generator = PersonaKeywordGenerator(llm_client)
        self.source_memories: dict[str, SourceMemory] = {}  # Per-persona memory
    
    def persona_to_traveler_genome(self, persona: PersonaGenotype, island_topic: Optional[str] = None) -> TravelerGenome:
        """
        Convert a PersonaGenotype to TravelerGenome for web exploration.
        Infers search preferences from persona bio.
        
        Args:
            persona: PersonaGenotype to convert
            island_topic: Optional island topic for context
            
        Returns:
            TravelerGenome configured for this persona
        """
        bio_lower = persona.bio.lower()
        
        # Infer source bias from bio keywords
        source_bias = SourceBias(
            academic=0.3,  # Default
            news=0.3,
            official=0.2,
            blogs=0.2
        )
        
        # Adjust based on bio content
        if any(word in bio_lower for word in ["research", "phd", "professor", "academic", "scholar", "university"]):
            source_bias.academic = 0.5
            source_bias.news = 0.2
            source_bias.blogs = 0.2
            source_bias.official = 0.1
        elif any(word in bio_lower for word in ["journalist", "reporter", "news", "media"]):
            source_bias.news = 0.6
            source_bias.blogs = 0.2
            source_bias.academic = 0.1
            source_bias.official = 0.1
        elif any(word in bio_lower for word in ["blogger", "writer", "content", "influencer"]):
            source_bias.blogs = 0.5
            source_bias.news = 0.3
            source_bias.academic = 0.1
            source_bias.official = 0.1
        elif any(word in bio_lower for word in ["policy", "government", "official", "regulation"]):
            source_bias.official = 0.5
            source_bias.news = 0.3
            source_bias.academic = 0.1
            source_bias.blogs = 0.1
        
        # Infer search depth and diversity from persona characteristics
        query_diversity = 0.6  # Default
        search_depth = 2  # Default
        novelty_weight = 0.5  # Default
        
        if any(word in bio_lower for word in ["curious", "explorer", "diverse", "variety"]):
            query_diversity = 0.8
            search_depth = 3
            novelty_weight = 0.7
        elif any(word in bio_lower for word in ["focused", "specific", "specialist", "expert"]):
            query_diversity = 0.4
            search_depth = 1
            novelty_weight = 0.3
        
        # Choose query template based on island topic or persona
        query_template_id = "template_v1_broad"
        if island_topic:
            if "technology" in island_topic.lower() or "ai" in island_topic.lower():
                query_template_id = "template_v2_specific"
            elif "news" in island_topic.lower():
                query_template_id = "template_v4_news_focused"
        
        return TravelerGenome(
            genome_id=f"traveler_{persona.name}",
            query_diversity=query_diversity,
            query_template_id=query_template_id,
            search_depth=search_depth,
            source_bias=source_bias,
            novelty_weight=novelty_weight
        )
    
    def explore_for_persona(self, persona: PersonaGenotype, custom_query: Optional[str] = None) -> ExecutionResult:
        """
        Execute a web exploration session for a persona.
        Generates keywords based on persona bio and island topic, then searches and crawls.
        
        Args:
            persona: PersonaGenotype to explore for
            custom_query: Optional custom search query (otherwise generated)
            
        Returns:
            ExecutionResult with discovered URLs and content
        """
        # Get persona's island
        island = None
        if persona.island_id:
            island = self.island_manager.get_island(persona.island_id)
        
        # Generate search query
        if custom_query:
            query = custom_query
        else:
            topic = island.topic if island else None
            query = self.keyword_generator.generate_search_query(persona, topic)
            logger.info(f"Generated query for {persona.name}: {query}")
        
        # Create or get source memory for this persona
        if persona.name not in self.source_memories:
            self.source_memories[persona.name] = SourceMemory(persona_id=persona.name)
        memory = self.source_memories[persona.name]
        
        # Create traveler genome
        island_topic = island.topic if island else None
        genome = self.persona_to_traveler_genome(persona, island_topic)
        
        # Create a custom Traveler class that uses our query
        class CustomQueryTraveler(Traveler):
            def __init__(self, genome, memory, custom_q):
                super().__init__(genome, memory)
                self.custom_query = custom_q
            
            def _generate_query(self):
                return self.custom_query
        
        # Execute traveler with custom query
        traveler = CustomQueryTraveler(genome, memory, query)
        result = traveler.execute()
        
        # Add results to island if persona is on one
        if island:
            self.island_manager.add_search_query(island.id, query)
            
            # Create a mapping of URLs to titles from headlines
            # Assuming headlines correspond to URLs in order
            url_titles = {}
            for i, url in enumerate(result.retrieved_urls):
                if i < len(result.headlines):
                    url_titles[url] = result.headlines[i]
            
            # Add each URL with its corresponding content
            for i, url in enumerate(result.retrieved_urls):
                title = url_titles.get(url, None)
                
                # Get content summary for this specific URL
                content_summary = None
                if result.content_summary and "pages" in result.content_summary:
                    pages = result.content_summary["pages"]
                    if i < len(pages):
                        content_summary = pages[i]
                
                self.island_manager.add_content_to_island(
                    island_id=island.id,
                    url=url,
                    title=title,
                    content_summary=content_summary,
                    keywords=[query],
                    source_persona=persona.name
                )
        
        logger.info(f"Exploration complete for {persona.name}: {len(result.retrieved_urls)} URLs discovered")
        return result
    
    def explore_for_island(self, island_id: str, personas: List[PersonaGenotype], num_personas: int = 3) -> List[ExecutionResult]:
        """
        Execute exploration sessions for multiple personas on an island.
        Uses evolved keywords from the island to guide searches.
        
        Args:
            island_id: ID of the island
            personas: List of PersonaGenotype objects available for exploration
            num_personas: Number of personas to use for exploration
            
        Returns:
            List of ExecutionResults
        """
        island = self.island_manager.get_island(island_id)
        if not island:
            logger.error(f"Island {island_id} not found")
            return []
        
        # Filter personas that are on this island
        island_personas = [p for p in personas if p.island_id == island_id]
        if not island_personas:
            logger.warning(f"No personas on island {island_id}")
            return []
        
        # Select personas for exploration
        selected_personas = random.sample(island_personas, min(num_personas, len(island_personas)))
        
        # Evolve keywords for this island
        evolved_keywords = self.island_manager.evolve_keywords_for_island(island_id, max_keywords=5)
        
        results = []
        for persona in selected_personas:
            # Use evolved keywords as custom query if available
            custom_query = evolved_keywords[0] if evolved_keywords else None
            result = self.explore_for_persona(persona, custom_query=custom_query)
            results.append(result)
        
        return results
    
    def get_source_memory(self, persona: PersonaGenotype) -> SourceMemory:
        """Get or create source memory for a persona."""
        if persona.name not in self.source_memories:
            self.source_memories[persona.name] = SourceMemory(persona_id=persona.name)
        return self.source_memories[persona.name]
