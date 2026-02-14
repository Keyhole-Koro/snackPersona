"""
Island Manager - Manages topic-based clusters of personas and their accumulated content.
"""
import logging
import random
import math
import json
from typing import List, Dict, Optional, Set
from urllib.parse import urlparse
from snackPersona.utils.data_models import IslandCluster, IslandContent, PersonaGenotype
from snackPersona.llm.llm_client import LLMClient

logger = logging.getLogger("snackPersona")


class IslandManager:
    """
    Manages Islands (topic-based clusters) where personas live and explore content.
    Handles persona assignment, migration, and content accumulation.
    """
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Initialize the Island Manager.
        
        Args:
            llm_client: Optional LLM client for topic analysis and migration decisions
        """
        self.islands: Dict[str, IslandCluster] = {}
        self.llm_client = llm_client
        
    def create_island(self, island_id: str, topic: str, description: Optional[str] = None) -> IslandCluster:
        """
        Create a new island with the given topic.
        
        Args:
            island_id: Unique identifier for the island
            topic: Main topic/theme of the island
            description: Optional detailed description
            
        Returns:
            Created IslandCluster
        """
        if island_id in self.islands:
            logger.warning(f"Island {island_id} already exists, returning existing island")
            return self.islands[island_id]
            
        island = IslandCluster(
            id=island_id,
            topic=topic,
            description=description or f"Island focused on {topic}"
        )
        self.islands[island_id] = island
        logger.info(f"Created island '{island_id}' with topic '{topic}'")
        return island
    
    def assign_persona_to_island(self, persona: PersonaGenotype, island_id: str) -> bool:
        """
        Assign a persona to an island.
        
        Args:
            persona: PersonaGenotype to assign
            island_id: ID of the target island
            
        Returns:
            True if assignment was successful
        """
        if island_id not in self.islands:
            logger.error(f"Cannot assign persona to non-existent island {island_id}")
            return False
            
        # Remove from old island if assigned
        if persona.island_id and persona.island_id in self.islands:
            old_island = self.islands[persona.island_id]
            old_island.persona_ids.discard(persona.name)
            logger.debug(f"Removed {persona.name} from island {persona.island_id}")
        
        # Add to new island
        island = self.islands[island_id]
        island.persona_ids.add(persona.name)
        persona.island_id = island_id
        
        logger.info(f"Assigned persona '{persona.name}' to island '{island_id}' (topic: {island.topic})")
        return True
    
    def add_content_to_island(self, island_id: str, url: str, title: Optional[str] = None,
                            content_summary: Optional[str] = None, keywords: Optional[List[str]] = None,
                            source_persona: Optional[str] = None) -> bool:
        """
        Add discovered content (URL) to an island.
        
        Args:
            island_id: ID of the island
            url: URL of the content
            title: Optional title
            content_summary: Optional content summary
            keywords: Optional keywords
            source_persona: Name of persona who discovered this
            
        Returns:
            True if content was added
        """
        if island_id not in self.islands:
            logger.error(f"Cannot add content to non-existent island {island_id}")
            return False
        
        island = self.islands[island_id]
        
        # Check if URL already exists
        existing_content = next((c for c in island.content if c.url == url), None)
        if existing_content:
            existing_content.visit_count += 1
            logger.debug(f"URL {url} already exists in island {island_id}, incremented visit count")
        else:
            # Add new content
            new_content = IslandContent(
                url=url,
                title=title,
                content_summary=content_summary,
                keywords=keywords or [],
                source_persona=source_persona
            )
            island.content.append(new_content)
            logger.info(f"Added new content to island {island_id}: {url}")
        
        # Update domain tracking
        domain = urlparse(url).netloc
        island.visited_domains[domain] = island.visited_domains.get(domain, 0) + 1
        island.total_visits += 1
        
        return True
    
    def add_search_query(self, island_id: str, query: str):
        """
        Record a search query executed for an island.
        
        Args:
            island_id: ID of the island
            query: Search query string
        """
        if island_id in self.islands:
            self.islands[island_id].search_queries.append(query)
    
    def get_domain_diversity(self, island_id: str) -> Dict[str, float]:
        """
        Calculate domain diversity metrics for an island.
        
        Args:
            island_id: ID of the island
            
        Returns:
            Dictionary with diversity metrics
        """
        if island_id not in self.islands:
            return {}
        
        island = self.islands[island_id]
        if not island.visited_domains:
            return {"unique_domains": 0, "max_domain_ratio": 0.0, "entropy": 0.0}
        
        total_visits = sum(island.visited_domains.values())
        unique_domains = len(island.visited_domains)
        max_visits = max(island.visited_domains.values())
        max_domain_ratio = max_visits / total_visits if total_visits > 0 else 0.0
        
        # Calculate entropy for diversity
        entropy = 0.0
        for count in island.visited_domains.values():
            p = count / total_visits
            entropy -= p * math.log2(p) if p > 0 else 0
        
        return {
            "unique_domains": unique_domains,
            "max_domain_ratio": max_domain_ratio,
            "entropy": entropy
        }
    
    def evolve_keywords_for_island(self, island_id: str, max_keywords: int = 10) -> List[str]:
        """
        Evolve keywords for an island to avoid site bias.
        Uses LLM to generate diverse search queries based on island content.
        
        Args:
            island_id: ID of the island
            max_keywords: Maximum number of keywords to generate
            
        Returns:
            List of evolved keywords
        """
        if island_id not in self.islands:
            return []
        
        island = self.islands[island_id]
        
        # If no LLM client, return random keywords from existing queries
        if not self.llm_client:
            all_words = set()
            for query in island.search_queries:
                all_words.update(query.lower().split())
            evolved = list(all_words)[:max_keywords]
            island.evolved_keywords.extend(evolved)
            return evolved
        
        # Use LLM to generate diverse keywords
        diversity_metrics = self.get_domain_diversity(island_id)
        
        # Build prompt for LLM
        recent_queries = island.search_queries[-10:] if island.search_queries else []
        top_domains = sorted(island.visited_domains.items(), key=lambda x: x[1], reverse=True)[:5]
        
        prompt = f"""Generate {max_keywords} diverse search keywords for the topic "{island.topic}".

Recent queries used: {', '.join(recent_queries)}
Current diversity: {diversity_metrics.get('unique_domains', 0)} unique domains
Top domains (to avoid bias): {', '.join([d[0] for d in top_domains])}

Generate keywords that will:
1. Explore different aspects of the topic
2. Discover content from new domains
3. Avoid repeating existing query patterns

Return only a JSON array of strings, e.g. ["keyword1", "keyword2", ...]"""
        
        try:
            response = self.llm_client.generate_text(
                system_prompt="You are a search query optimizer focused on diversity and avoiding bias.",
                user_prompt=prompt,
                temperature=0.8
            )
            
            # Parse response
            text = response.strip()
            if "```" in text:
                text = text.split("```json")[-1].split("```")[0].strip()
            keywords = json.loads(text)
            
            if isinstance(keywords, list):
                island.evolved_keywords.extend(keywords[:max_keywords])
                logger.info(f"Evolved {len(keywords)} keywords for island {island_id}")
                return keywords[:max_keywords]
                
        except Exception as e:
            logger.warning(f"Failed to evolve keywords via LLM: {e}")
        
        return []
    
    def should_migrate_persona(self, persona: PersonaGenotype, target_island_id: str) -> bool:
        """
        Decide if a persona should migrate to a different island.
        Uses LLM to analyze persona bio vs island topic fit.
        
        Args:
            persona: PersonaGenotype to evaluate
            target_island_id: ID of potential target island
            
        Returns:
            True if persona should migrate
        """
        if target_island_id not in self.islands:
            return False
        
        current_island_id = persona.island_id
        if not current_island_id or current_island_id not in self.islands:
            return True  # No current island, should join
        
        if current_island_id == target_island_id:
            return False  # Already on this island
        
        # If no LLM, use random migration with low probability
        if not self.llm_client:
            return random.random() < 0.1  # 10% chance
        
        current_island = self.islands[current_island_id]
        target_island = self.islands[target_island_id]
        
        prompt = f"""Analyze if this persona should migrate between islands.

Persona: {persona.name}
Bio: {persona.bio}

Current Island: {current_island.topic}
Target Island: {target_island.topic}

Should this persona migrate? Consider:
1. Topic alignment with persona's interests
2. Opportunity for growth and exploration
3. Current island vs target island fit

Respond with only "YES" or "NO" and a brief reason."""
        
        try:
            response = self.llm_client.generate_text(
                system_prompt="You are an expert at matching personas to topic clusters.",
                user_prompt=prompt,
                temperature=0.5
            )
            
            decision = response.strip().upper().startswith("YES")
            if decision:
                logger.info(f"Migration approved for {persona.name}: {current_island.topic} -> {target_island.topic}")
            return decision
            
        except Exception as e:
            logger.warning(f"Failed to decide migration via LLM: {e}")
            return False
    
    def migrate_persona(self, persona: PersonaGenotype, target_island_id: str) -> bool:
        """
        Migrate a persona to a different island after checking if appropriate.
        
        Args:
            persona: PersonaGenotype to migrate
            target_island_id: ID of target island
            
        Returns:
            True if migration was successful
        """
        if self.should_migrate_persona(persona, target_island_id):
            return self.assign_persona_to_island(persona, target_island_id)
        return False
    
    def get_island(self, island_id: str) -> Optional[IslandCluster]:
        """Get an island by ID."""
        return self.islands.get(island_id)
    
    def list_islands(self) -> List[IslandCluster]:
        """Get all islands."""
        return list(self.islands.values())
    
    def get_personas_on_island(self, island_id: str) -> Set[str]:
        """Get all persona names on a specific island."""
        if island_id in self.islands:
            return self.islands[island_id].persona_ids
        return set()
