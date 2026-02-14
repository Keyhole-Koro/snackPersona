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
    
    # ============================================================================
    # Faction Management Methods
    # ============================================================================
    
    def create_faction(self, island_id: str, faction_id: str, faction_name: str, 
                      initial_personas: Optional[List[str]] = None) -> bool:
        """
        Create a new faction within an island.
        
        Args:
            island_id: ID of the island
            faction_id: Unique identifier for the faction
            faction_name: Name of the faction
            initial_personas: Optional list of persona names to add to faction
            
        Returns:
            True if faction was created
        """
        from snackPersona.utils.data_models import Faction
        
        if island_id not in self.islands:
            logger.error(f"Cannot create faction in non-existent island {island_id}")
            return False
        
        island = self.islands[island_id]
        
        if faction_id in island.factions:
            logger.warning(f"Faction {faction_id} already exists in island {island_id}")
            return False
        
        faction = Faction(
            id=faction_id,
            name=faction_name,
            persona_ids=set(initial_personas or [])
        )
        
        island.factions[faction_id] = faction
        logger.info(f"Created faction '{faction_name}' in island '{island_id}'")
        return True
    
    def add_persona_to_faction(self, island_id: str, faction_id: str, persona_name: str) -> bool:
        """
        Add a persona to a faction.
        
        Args:
            island_id: ID of the island
            faction_id: ID of the faction
            persona_name: Name of the persona
            
        Returns:
            True if persona was added
        """
        if island_id not in self.islands:
            logger.error(f"Island {island_id} not found")
            return False
        
        island = self.islands[island_id]
        
        if faction_id not in island.factions:
            logger.error(f"Faction {faction_id} not found in island {island_id}")
            return False
        
        island.factions[faction_id].persona_ids.add(persona_name)
        logger.debug(f"Added {persona_name} to faction {faction_id}")
        return True
    
    def evolve_faction_queries(self, island_id: str, faction_id: str, 
                              num_queries: int = 5) -> List[str]:
        """
        Evolve queries for a specific faction independently.
        
        Args:
            island_id: ID of the island
            faction_id: ID of the faction
            num_queries: Number of queries to generate
            
        Returns:
            List of evolved queries
        """
        if island_id not in self.islands:
            logger.error(f"Island {island_id} not found")
            return []
        
        island = self.islands[island_id]
        
        if faction_id not in island.factions:
            logger.error(f"Faction {faction_id} not found")
            return []
        
        faction = island.factions[faction_id]
        
        # If no LLM, generate simple variations
        if not self.llm_client:
            base_topic = island.topic
            queries = [
                f"{base_topic} {faction.name} perspective",
                f"{base_topic} {faction.name} analysis",
                f"{base_topic} latest {faction.name}"
            ]
            faction.evolved_queries.extend(queries[:num_queries])
            return queries[:num_queries]
        
        # Use LLM to evolve queries based on faction's current queries
        recent_queries = faction.evolved_queries[-5:] if faction.evolved_queries else []
        
        prompt = f"""Generate {num_queries} diverse search queries for faction "{faction.name}" 
exploring the topic "{island.topic}".

Faction's recent queries: {', '.join(recent_queries) if recent_queries else 'None yet'}
Number of members: {len(faction.persona_ids)}

Generate queries that:
1. Build on previous queries but explore new angles
2. Are distinct from other queries
3. Reflect this faction's unique perspective

Return ONLY a JSON array of strings, e.g. ["query1", "query2", ...]"""
        
        try:
            response = self.llm_client.generate_text(
                system_prompt="You are a search query evolution specialist.",
                user_prompt=prompt,
                temperature=0.9
            )
            
            text = response.strip()
            if "```" in text:
                text = text.split("```json")[-1].split("```")[0].strip()
            queries = json.loads(text)
            
            if isinstance(queries, list):
                faction.evolved_queries.extend(queries[:num_queries])
                # Update query signature for similarity detection
                faction.query_signature = self._compute_query_signature(faction.evolved_queries)
                logger.info(f"Evolved {len(queries)} queries for faction {faction_id}")
                return queries[:num_queries]
                
        except Exception as e:
            logger.warning(f"Failed to evolve queries for faction {faction_id}: {e}")
        
        return []
    
    def _compute_query_signature(self, queries: List[str]) -> str:
        """
        Compute a signature hash for query patterns to detect similarity.
        
        Args:
            queries: List of query strings
            
        Returns:
            Signature string
        """
        import hashlib
        
        # Extract key terms from queries
        all_words = set()
        for query in queries:
            words = query.lower().split()
            # Filter common words
            filtered = [w for w in words if len(w) > 3]
            all_words.update(filtered)
        
        # Create signature from sorted unique words
        signature_text = " ".join(sorted(all_words))
        return hashlib.md5(signature_text.encode()).hexdigest()
    
    def calculate_faction_similarity(self, island_id: str, faction_id1: str, 
                                    faction_id2: str) -> float:
        """
        Calculate similarity between two factions based on their queries.
        
        Args:
            island_id: ID of the island
            faction_id1: ID of first faction
            faction_id2: ID of second faction
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        if island_id not in self.islands:
            return 0.0
        
        island = self.islands[island_id]
        
        if faction_id1 not in island.factions or faction_id2 not in island.factions:
            return 0.0
        
        faction1 = island.factions[faction_id1]
        faction2 = island.factions[faction_id2]
        
        # Extract words from queries
        words1 = set()
        for q in faction1.evolved_queries:
            words1.update(q.lower().split())
        
        words2 = set()
        for q in faction2.evolved_queries:
            words2.update(q.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        # Jaccard similarity
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def natural_selection_factions(self, island_id: str, similarity_threshold: float = 0.7,
                                  fitness_weight: float = 0.6) -> List[str]:
        """
        Apply natural selection to factions: eliminate similar low-fitness factions.
        
        Args:
            island_id: ID of the island
            similarity_threshold: Threshold for considering factions similar (0.0-1.0)
            fitness_weight: Weight for fitness vs similarity in selection (0.0-1.0)
            
        Returns:
            List of eliminated faction IDs
        """
        if island_id not in self.islands:
            logger.error(f"Island {island_id} not found")
            return []
        
        island = self.islands[island_id]
        
        if len(island.factions) < 2:
            return []  # Need at least 2 factions for selection
        
        eliminated = []
        faction_ids = list(island.factions.keys())
        
        # Compare each pair of factions
        for i in range(len(faction_ids)):
            for j in range(i + 1, len(faction_ids)):
                fid1, fid2 = faction_ids[i], faction_ids[j]
                
                # Skip if either already eliminated
                if fid1 in eliminated or fid2 in eliminated:
                    continue
                
                similarity = self.calculate_faction_similarity(island_id, fid1, fid2)
                
                if similarity >= similarity_threshold:
                    faction1 = island.factions[fid1]
                    faction2 = island.factions[fid2]
                    
                    # Compare fitness scores
                    fitness1 = faction1.fitness_score
                    fitness2 = faction2.fitness_score
                    
                    # Eliminate the lower fitness faction
                    if fitness1 < fitness2:
                        eliminated.append(fid1)
                        logger.info(f"Natural selection: eliminating faction {fid1} "
                                  f"(similarity: {similarity:.2f}, fitness: {fitness1:.2f} < {fitness2:.2f})")
                    else:
                        eliminated.append(fid2)
                        logger.info(f"Natural selection: eliminating faction {fid2} "
                                  f"(similarity: {similarity:.2f}, fitness: {fitness2:.2f} < {fitness1:.2f})")
        
        # Remove eliminated factions
        for fid in eliminated:
            # Reassign personas from eliminated faction to remaining factions
            if fid in island.factions:
                orphaned_personas = island.factions[fid].persona_ids
                if orphaned_personas and island.factions:
                    # Find highest fitness remaining faction
                    remaining_factions = [f for f in island.factions.values() if f.id not in eliminated]
                    if remaining_factions:
                        best_faction = max(remaining_factions, key=lambda f: f.fitness_score)
                        best_faction.persona_ids.update(orphaned_personas)
                        logger.debug(f"Reassigned {len(orphaned_personas)} personas from {fid} to {best_faction.id}")
                
                del island.factions[fid]
        
        return eliminated
    
    def update_faction_fitness(self, island_id: str, faction_id: str, 
                              unique_domains: int, quality_score: float):
        """
        Update fitness metrics for a faction based on exploration results.
        
        Args:
            island_id: ID of the island
            faction_id: ID of the faction
            unique_domains: Number of unique domains discovered
            quality_score: Quality score of content (0.0-1.0)
        """
        if island_id not in self.islands:
            return
        
        island = self.islands[island_id]
        
        if faction_id not in island.factions:
            return
        
        faction = island.factions[faction_id]
        faction.unique_domains_discovered = unique_domains
        faction.content_quality_score = quality_score
        
        # Compute overall fitness (weighted combination)
        faction.fitness_score = (
            0.4 * min(unique_domains / 10.0, 1.0) +  # Domain diversity (normalized)
            0.6 * quality_score  # Content quality
        )
        
        logger.debug(f"Updated fitness for faction {faction_id}: {faction.fitness_score:.2f}")
    
    # ============================================================================
    # End Faction Management
    # ============================================================================
    
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
