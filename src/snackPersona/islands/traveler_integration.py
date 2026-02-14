"""
Integration adapter for connecting Island system with Traveler and Personas.
"""
import logging
from typing import List, Optional
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
        
        # Execute traveler with custom query
        traveler = Traveler(genome, memory=memory)
        
        # Inject custom query by temporarily modifying genome
        original_generate_query = traveler._generate_query
        traveler._generate_query = lambda: query
        
        result = traveler.execute()
        
        # Restore original method
        traveler._generate_query = original_generate_query
        
        # Add results to island if persona is on one
        if island:
            self.island_manager.add_search_query(island.id, query)
            for url in result.retrieved_urls:
                # Extract title from headlines if available
                title = None
                if result.headlines:
                    # Simple matching: use first headline as title
                    title = result.headlines[0] if len(result.headlines) > 0 else None
                
                self.island_manager.add_content_to_island(
                    island_id=island.id,
                    url=url,
                    title=title,
                    content_summary=result.content_summary.get("pages", [])[0] if result.content_summary.get("pages") else None,
                    keywords=[query],
                    source_persona=persona.name
                )
        
        logger.info(f"Exploration complete for {persona.name}: {len(result.retrieved_urls)} URLs discovered")
        return result
    
    def explore_for_island(self, island_id: str, num_personas: int = 3) -> List[ExecutionResult]:
        """
        Execute exploration sessions for multiple personas on an island.
        Uses evolved keywords from the island to guide searches.
        
        Args:
            island_id: ID of the island
            num_personas: Number of personas to use for exploration
            
        Returns:
            List of ExecutionResults
        """
        island = self.island_manager.get_island(island_id)
        if not island:
            logger.error(f"Island {island_id} not found")
            return []
        
        # Get personas on this island
        persona_names = list(island.persona_ids)
        if not persona_names:
            logger.warning(f"No personas on island {island_id}")
            return []
        
        # Select personas for exploration
        import random
        selected_personas = random.sample(persona_names, min(num_personas, len(persona_names)))
        
        # Evolve keywords for this island
        evolved_keywords = self.island_manager.evolve_keywords_for_island(island_id, max_keywords=5)
        
        results = []
        for persona_name in selected_personas:
            # Note: We need access to the actual PersonaGenotype objects
            # This method assumes we can look them up somehow
            # For now, we'll skip this and recommend using explore_for_persona directly
            logger.warning(f"Skipping exploration for {persona_name} - PersonaGenotype lookup not implemented in this method")
        
        return results
    
    def get_source_memory(self, persona: PersonaGenotype) -> SourceMemory:
        """Get or create source memory for a persona."""
        if persona.name not in self.source_memories:
            self.source_memories[persona.name] = SourceMemory(persona_id=persona.name)
        return self.source_memories[persona.name]
