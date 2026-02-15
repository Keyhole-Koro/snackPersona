"""
Island Manager - Manages topic-based clusters of personas and their accumulated content.
"""
import logging
import random
import math
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set, Tuple
from urllib.parse import urlparse
from snackPersona.utils.data_models import IslandCluster, IslandContent, PersonaGenotype
from snackPersona.llm.llm_client import LLMClient
from snackPersona.evaluation.diversity.genotype import calculate_genotype_distance

logger = logging.getLogger("snackPersona")

# Constants for faction management
MIN_WORD_LENGTH_FOR_SIGNATURE = 3
DOMAIN_DIVERSITY_WEIGHT = 0.4
QUALITY_WEIGHT = 0.6
MAX_DOMAINS_THRESHOLD = 10.0

# Constants for automatic island generation and lifecycle
DEFAULT_CONTENT_TTL_HOURS = 72
MIN_TOKEN_LENGTH = 4
AUTOGEN_SIMILARITY_THRESHOLD = 0.20
DEFAULT_LEXICAL_WEIGHT = 0.6
DEFAULT_EMBEDDING_WEIGHT = 0.4
MAX_RETENTION_ROUNDS = 2
HIGH_VALUE_VISIT_THRESHOLD = 5
GRACE_TTL_HOURS = 24
COMMON_STOP_WORDS = {
    "this", "that", "with", "from", "have", "about", "into", "been", "they", "them",
    "their", "your", "just", "also", "really", "very", "more", "most", "what", "when",
    "where", "while", "would", "could", "should", "will", "there", "here", "because",
    "than", "then", "make", "made", "many", "some", "such", "only", "over", "under",
    "after", "before", "across", "between", "through", "using", "work", "working", "life",
    "like", "love", "hate", "news", "latest", "today", "about", "person", "people",
}
TOKEN_SYNONYMS = {
    "ai": "artificialintelligence",
    "artificial": "artificialintelligence",
    "intelligence": "artificialintelligence",
    "ml": "machinelearning",
    "machinelearning": "machinelearning",
    "climatechange": "climate",
    "renewables": "renewable",
    "emissions": "emission",
    "scientist": "science",
    "researcher": "research",
    "engineer": "engineering",
    "models": "model",
    "networks": "network",
}


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

    def synchronize_resident_memberships(self, personas: List[PersonaGenotype]) -> Dict[str, int]:
        """
        Synchronize island resident sets from current persona objects.

        This avoids stale resident names after reproduction/renaming across generations.

        Args:
            personas: Current persona list (source of truth)

        Returns:
            Simple stats dict.
        """
        for island in self.islands.values():
            island.persona_ids.clear()

        assigned = 0
        unknown_island = 0
        for persona in personas:
            if not persona.island_id:
                continue
            island = self.islands.get(persona.island_id)
            if not island:
                unknown_island += 1
                persona.island_id = None
                continue
            island.persona_ids.add(persona.name)
            assigned += 1

        return {"assigned": assigned, "unknown_island": unknown_island}

    def add_content_to_island(
        self,
        island_id: str,
        url: str,
        title: Optional[str] = None,
        content_summary: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        source_persona: Optional[str] = None,
        ttl_hours: int = DEFAULT_CONTENT_TTL_HOURS,
    ) -> bool:
        """
        Add discovered content (URL) to an island.

        Args:
            island_id: ID of the island
            url: URL of the content
            title: Optional title
            content_summary: Optional content summary
            keywords: Optional keywords
            source_persona: Name of persona who discovered this
            ttl_hours: TTL (in hours) for this content

        Returns:
            True if content was added
        """
        if island_id not in self.islands:
            logger.error(f"Cannot add content to non-existent island {island_id}")
            return False

        island = self.islands[island_id]
        now = datetime.now()

        # Check if URL already exists
        existing_content = next((c for c in island.content if c.url == url), None)
        if existing_content:
            existing_content.visit_count += 1
            existing_content.last_accessed_at = now.isoformat()
            if keywords:
                existing_content.keywords = list(set(existing_content.keywords + keywords))
            if title and not existing_content.title:
                existing_content.title = title
            if content_summary and not existing_content.content_summary:
                existing_content.content_summary = content_summary
            if ttl_hours > 0:
                existing_content.ttl_hours = ttl_hours
                existing_content.expires_at = (now + timedelta(hours=ttl_hours)).isoformat()
            logger.debug(f"URL {url} already exists in island {island_id}, incremented visit count")
        else:
            # Add new content
            new_content = IslandContent(
                url=url,
                title=title,
                content_summary=content_summary,
                keywords=keywords or [],
                source_persona=source_persona,
                ttl_hours=max(1, ttl_hours),
                expires_at=(now + timedelta(hours=max(1, ttl_hours))).isoformat(),
                last_accessed_at=now.isoformat(),
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
    # Automatic Island Generation and Splitting
    # ============================================================================

    def auto_generate_islands_from_personas(
        self,
        personas: List[PersonaGenotype],
        similarity_threshold: float = AUTOGEN_SIMILARITY_THRESHOLD,
        min_cluster_size: int = 2,
        lexical_weight: float = DEFAULT_LEXICAL_WEIGHT,
        embedding_weight: float = DEFAULT_EMBEDDING_WEIGHT,
    ) -> List[IslandCluster]:
        """
        Automatically generate islands by clustering personas based on bio similarity.

        Args:
            personas: Personas to cluster
            similarity_threshold: Jaccard threshold for joining an existing cluster
            min_cluster_size: Minimum size for dedicated cluster islands

        Returns:
            List of islands that were created during this call
        """
        if not personas:
            return []

        clusters: List[List[PersonaGenotype]] = []

        for persona in personas:
            best_idx = -1
            best_sim = -1.0
            for i, cluster in enumerate(clusters):
                sims = [
                    self._hybrid_persona_similarity(
                        persona,
                        member,
                        lexical_weight=lexical_weight,
                        embedding_weight=embedding_weight,
                    )
                    for member in cluster
                ]
                sim = sum(sims) / len(sims) if sims else 0.0
                if sim > best_sim:
                    best_sim = sim
                    best_idx = i

            if best_idx >= 0 and best_sim >= similarity_threshold:
                clusters[best_idx].append(persona)
            else:
                clusters.append([persona])

        created_islands: List[IslandCluster] = []
        generated_counter = 1
        singleton_buffer: List[PersonaGenotype] = []

        for cluster in clusters:
            if len(cluster) < min_cluster_size:
                singleton_buffer.extend(cluster)
                continue

            island_id = self._next_generated_island_id(generated_counter)
            generated_counter += 1
            topic = self._generate_cluster_topic(cluster)
            island = self.create_island(
                island_id=island_id,
                topic=topic,
                description=f"Auto-generated island from persona similarity clustering: {topic}",
            )
            for persona in cluster:
                self.assign_persona_to_island(persona, island.id)
            created_islands.append(island)

        # Assign singleton personas to the nearest created island; otherwise create one extra island.
        if singleton_buffer:
            if created_islands:
                for persona in singleton_buffer:
                    best_island = max(
                        created_islands,
                        key=lambda i: self._jaccard_similarity(
                            self._extract_interest_tokens(persona.bio),
                            self._extract_interest_tokens(i.topic),
                        ),
                    )
                    self.assign_persona_to_island(persona, best_island.id)
            else:
                island_id = self._next_generated_island_id(generated_counter)
                topic = self._generate_cluster_topic(singleton_buffer)
                island = self.create_island(
                    island_id=island_id,
                    topic=topic,
                    description=f"Auto-generated island from sparse persona cluster: {topic}",
                )
                for persona in singleton_buffer:
                    self.assign_persona_to_island(persona, island.id)
                created_islands.append(island)

        logger.info(f"Auto-generated {len(created_islands)} islands from {len(personas)} personas")
        return created_islands

    def split_overcrowded_islands(
        self,
        personas: List[PersonaGenotype],
        max_residents: int = 30,
        min_cohesion: float = 0.20,
        min_split_size: int = 8,
        lexical_weight: float = DEFAULT_LEXICAL_WEIGHT,
        embedding_weight: float = DEFAULT_EMBEDDING_WEIGHT,
    ) -> List[str]:
        """
        Split islands that are overcrowded and topically incohesive.

        Args:
            personas: Full persona list used to resolve island residents
            max_residents: Resident threshold for considering split
            min_cohesion: If average pairwise similarity is below this, island can split
            min_split_size: Minimum residents required per resulting island

        Returns:
            List of newly created island IDs from splitting
        """
        persona_map = {p.name: p for p in personas}
        new_island_ids: List[str] = []

        for island in list(self.islands.values()):
            resident_personas = [persona_map[name] for name in island.persona_ids if name in persona_map]
            if len(resident_personas) <= max_residents:
                continue
            if len(resident_personas) < (min_split_size * 2):
                continue

            cohesion = self._average_pairwise_similarity(
                resident_personas,
                lexical_weight=lexical_weight,
                embedding_weight=embedding_weight,
            )
            if cohesion >= min_cohesion:
                continue

            left_cluster, right_cluster = self._bipartition_personas(
                resident_personas,
                lexical_weight=lexical_weight,
                embedding_weight=embedding_weight,
            )
            if len(left_cluster) < min_split_size or len(right_cluster) < min_split_size:
                continue

            new_id = self._next_split_island_id(island.id)
            new_topic = self._generate_cluster_topic(right_cluster, fallback_prefix=island.topic)
            self.create_island(
                island_id=new_id,
                topic=new_topic,
                description=f"Split from {island.id} due to low cohesion and high population",
            )

            for persona in right_cluster:
                self.assign_persona_to_island(persona, new_id)

            # Keep original island topic but annotate density change.
            island.last_updated = datetime.now().isoformat()
            new_island_ids.append(new_id)
            logger.info(
                "Split island '%s' into '%s' (residents=%d, cohesion=%.3f)",
                island.id,
                new_id,
                len(resident_personas),
                cohesion,
            )

        return new_island_ids

    # ============================================================================
    # TTL and Persona-Driven Content Retention
    # ============================================================================

    def run_content_retention_cycle(
        self,
        island_id: str,
        personas: List[PersonaGenotype],
        min_votes: int = 2,
        max_rounds: int = MAX_RETENTION_ROUNDS,
        high_value_visit_threshold: int = HIGH_VALUE_VISIT_THRESHOLD,
        grace_ttl_hours: int = GRACE_TTL_HOURS,
    ) -> Dict[str, int]:
        """
        Evaluate expired content and decide keep/discard with persona votes + heuristic score.

        Args:
            island_id: Island to evaluate
            personas: Personas available for voting
            min_votes: Minimum votes before hard decision applies

        Returns:
            Summary counts: kept/discarded/evaluated
        """
        if island_id not in self.islands:
            return {"kept": 0, "discarded": 0, "evaluated": 0}

        island = self.islands[island_id]
        now = datetime.now()
        resident_personas = [p for p in personas if p.name in island.persona_ids]

        kept = 0
        discarded = 0
        evaluated = 0
        survivors: List[IslandContent] = []

        for content in island.content:
            if not self._is_content_expired(content, now):
                survivors.append(content)
                continue

            evaluated += 1
            content.retention_rounds += 1
            votes = self._collect_content_votes(island, content, resident_personas)
            keep_votes = sum(1 for vote in votes if vote)
            discard_votes = len(votes) - keep_votes
            content.retention_votes += keep_votes
            content.discard_votes += discard_votes

            vote_total = keep_votes + discard_votes
            vote_score = keep_votes / vote_total if vote_total > 0 else 0.0
            heuristic_score = self._content_keep_heuristic(island, content)
            final_score = 0.6 * vote_score + 0.4 * heuristic_score

            # If there are not enough votes, avoid infinite retention:
            # keep high-value content with short grace TTL, otherwise discard after max rounds.
            if vote_total < min_votes:
                if content.retention_rounds >= max_rounds:
                    if content.visit_count >= high_value_visit_threshold:
                        content.expires_at = (now + timedelta(hours=max(1, grace_ttl_hours))).isoformat()
                        content.retention_rounds = 0
                        content.retention_votes = 0
                        content.discard_votes = 0
                        kept += 1
                        survivors.append(content)
                        logger.info(
                            "Grace-kept high-value content on island '%s': %s (visit_count=%d)",
                            island_id,
                            content.url,
                            content.visit_count,
                        )
                    else:
                        discarded += 1
                        logger.info(
                            "Discarded content due to insufficient votes after %d rounds on island '%s': %s",
                            content.retention_rounds,
                            island_id,
                            content.url,
                        )
                    continue

                # Not enough votes yet, keep temporarily and try next cycle.
                content.expires_at = (now + timedelta(hours=max(1, content.ttl_hours))).isoformat()
                kept += 1
                survivors.append(content)
                continue

            if vote_total >= min_votes and final_score < 0.5:
                discarded += 1
                logger.info(
                    "Discarded content on island '%s': %s (votes=%d/%d, score=%.2f)",
                    island_id,
                    content.url,
                    keep_votes,
                    discard_votes,
                    final_score,
                )
                continue

            # Keep content: extend expiration and reset temporary vote state.
            content.expires_at = (now + timedelta(hours=max(1, content.ttl_hours))).isoformat()
            content.retention_rounds = 0
            content.retention_votes = 0
            content.discard_votes = 0
            kept += 1
            survivors.append(content)

        island.content = survivors
        island.last_updated = now.isoformat()

        return {"kept": kept, "discarded": discarded, "evaluated": evaluated}

    def run_global_content_retention_cycle(
        self,
        personas: List[PersonaGenotype],
        min_votes: int = 2,
        max_rounds: int = MAX_RETENTION_ROUNDS,
        high_value_visit_threshold: int = HIGH_VALUE_VISIT_THRESHOLD,
        grace_ttl_hours: int = GRACE_TTL_HOURS,
    ) -> Dict[str, Dict[str, int]]:
        """Run content retention cycle for all islands."""
        result: Dict[str, Dict[str, int]] = {}
        for island_id in self.islands:
            result[island_id] = self.run_content_retention_cycle(
                island_id=island_id,
                personas=personas,
                min_votes=min_votes,
                max_rounds=max_rounds,
                high_value_visit_threshold=high_value_visit_threshold,
                grace_ttl_hours=grace_ttl_hours,
            )
        return result

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
        Uses SHA-256 for robust hashing with low collision probability.

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
            # Filter short words using constant
            filtered = [w for w in words if len(w) > MIN_WORD_LENGTH_FOR_SIGNATURE]
            all_words.update(filtered)

        # Create signature from sorted unique words
        signature_text = " ".join(sorted(all_words))
        return hashlib.sha256(signature_text.encode()).hexdigest()

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

        # Compute overall fitness (weighted combination using constants)
        normalized_domains = min(unique_domains / MAX_DOMAINS_THRESHOLD, 1.0)
        faction.fitness_score = (
            DOMAIN_DIVERSITY_WEIGHT * normalized_domains +
            QUALITY_WEIGHT * quality_score
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

    # ============================================================================
    # Internal helpers
    # ============================================================================

    def _extract_interest_tokens(self, text: str) -> Set[str]:
        tokens = re.findall(r"[a-zA-Z]{4,}", text.lower())
        return {
            self._normalize_token(token) for token in tokens
            if len(token) >= MIN_TOKEN_LENGTH and token not in COMMON_STOP_WORDS
        }

    def _jaccard_similarity(self, a: Set[str], b: Set[str]) -> float:
        if not a or not b:
            return 0.0
        union = a.union(b)
        if not union:
            return 0.0
        return len(a.intersection(b)) / len(union)

    def _average_pairwise_similarity(
        self,
        personas: List[PersonaGenotype],
        lexical_weight: float = DEFAULT_LEXICAL_WEIGHT,
        embedding_weight: float = DEFAULT_EMBEDDING_WEIGHT,
    ) -> float:
        if len(personas) < 2:
            return 1.0

        total = 0.0
        pairs = 0
        for i in range(len(personas)):
            for j in range(i + 1, len(personas)):
                total += self._hybrid_persona_similarity(
                    personas[i],
                    personas[j],
                    lexical_weight=lexical_weight,
                    embedding_weight=embedding_weight,
                )
                pairs += 1
        return total / pairs if pairs else 1.0

    def _bipartition_personas(
        self,
        personas: List[PersonaGenotype],
        lexical_weight: float = DEFAULT_LEXICAL_WEIGHT,
        embedding_weight: float = DEFAULT_EMBEDDING_WEIGHT,
    ) -> Tuple[List[PersonaGenotype], List[PersonaGenotype]]:
        # Find farthest pair as seeds.
        seed_a = personas[0]
        seed_b = personas[-1]
        min_similarity = float("inf")
        for i in range(len(personas)):
            for j in range(i + 1, len(personas)):
                sim = self._hybrid_persona_similarity(
                    personas[i],
                    personas[j],
                    lexical_weight=lexical_weight,
                    embedding_weight=embedding_weight,
                )
                if sim < min_similarity:
                    min_similarity = sim
                    seed_a, seed_b = personas[i], personas[j]

        left: List[PersonaGenotype] = [seed_a]
        right: List[PersonaGenotype] = [seed_b]

        for persona in personas:
            if persona.name in {seed_a.name, seed_b.name}:
                continue
            sim_left = self._hybrid_persona_similarity(
                persona,
                seed_a,
                lexical_weight=lexical_weight,
                embedding_weight=embedding_weight,
            )
            sim_right = self._hybrid_persona_similarity(
                persona,
                seed_b,
                lexical_weight=lexical_weight,
                embedding_weight=embedding_weight,
            )
            if sim_left >= sim_right:
                left.append(persona)
            else:
                right.append(persona)

        return left, right

    def _normalize_token(self, token: str) -> str:
        t = token.lower().strip()
        if t.endswith("ies") and len(t) > 5:
            t = t[:-3] + "y"
        elif t.endswith("ing") and len(t) > 6:
            t = t[:-3]
        elif t.endswith("ed") and len(t) > 5:
            t = t[:-2]
        elif t.endswith("s") and len(t) > 4:
            t = t[:-1]
        return TOKEN_SYNONYMS.get(t, t)

    def _hybrid_persona_similarity(
        self,
        p1: PersonaGenotype,
        p2: PersonaGenotype,
        lexical_weight: float = DEFAULT_LEXICAL_WEIGHT,
        embedding_weight: float = DEFAULT_EMBEDDING_WEIGHT,
    ) -> float:
        w_sum = lexical_weight + embedding_weight
        if w_sum <= 0:
            lexical_weight = 1.0
            embedding_weight = 0.0
            w_sum = 1.0
        lexical_weight /= w_sum
        embedding_weight /= w_sum

        t1 = self._extract_interest_tokens(p1.bio)
        t2 = self._extract_interest_tokens(p2.bio)
        lexical_sim = self._jaccard_similarity(t1, t2)

        try:
            semantic_sim = 1.0 - calculate_genotype_distance(p1, p2)
            semantic_sim = max(0.0, min(1.0, semantic_sim))
        except Exception:
            semantic_sim = lexical_sim

        return (lexical_weight * lexical_sim) + (embedding_weight * semantic_sim)

    def _next_generated_island_id(self, start: int) -> str:
        candidate = start
        while True:
            island_id = f"auto_island_{candidate}"
            if island_id not in self.islands:
                return island_id
            candidate += 1

    def _next_split_island_id(self, base_island_id: str) -> str:
        candidate = 1
        while True:
            island_id = f"{base_island_id}_split_{candidate}"
            if island_id not in self.islands:
                return island_id
            candidate += 1

    def _generate_cluster_topic(self, personas: List[PersonaGenotype], fallback_prefix: str = "") -> str:
        if not personas:
            return fallback_prefix or "General Discussion"

        combined = "\n".join([f"{p.name}: {p.bio}" for p in personas[:12]])

        if self.llm_client:
            prompt = f"""Create a short topic label (2-5 words) for this persona cluster.

Cluster personas and bios:
{combined}

Return only the topic label string."""
            try:
                response = self.llm_client.generate_text(
                    system_prompt="You generate concise topic names for persona clusters.",
                    user_prompt=prompt,
                    temperature=0.4,
                )
                topic = response.strip().replace("\n", " ").strip('"')
                if topic:
                    return topic[:80]
            except Exception as exc:
                logger.warning("Failed to generate LLM cluster topic: %s", exc)

        # Fallback: top frequent tokens
        freq: Dict[str, int] = {}
        for persona in personas:
            for token in self._extract_interest_tokens(persona.bio):
                freq[token] = freq.get(token, 0) + 1
        top = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:3]
        topic = " ".join([w.capitalize() for w, _ in top])
        if topic:
            return topic
        return fallback_prefix or "General Discussion"

    def _is_content_expired(self, content: IslandContent, now: datetime) -> bool:
        if content.expires_at:
            parsed = self._parse_datetime(content.expires_at)
            if parsed:
                return parsed <= now
        # Backward compatibility when expires_at is missing
        discovered = self._parse_datetime(content.discovered_at) or now
        return discovered + timedelta(hours=max(1, content.ttl_hours)) <= now

    def _parse_datetime(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    def _collect_content_votes(
        self,
        island: IslandCluster,
        content: IslandContent,
        personas: List[PersonaGenotype],
        max_voters: int = 5,
    ) -> List[bool]:
        if not personas:
            return []

        voters = personas if len(personas) <= max_voters else random.sample(personas, max_voters)
        return [self._persona_retention_vote(persona, island, content) for persona in voters]

    def _persona_retention_vote(self, persona: PersonaGenotype, island: IslandCluster, content: IslandContent) -> bool:
        if not self.llm_client:
            return self._heuristic_persona_vote(persona, island, content)

        prompt = f"""You are deciding whether to keep a piece of cached island information.

Persona: {persona.name}
Persona bio: {persona.bio}
Island topic: {island.topic}
Content title: {content.title or 'N/A'}
Content URL: {content.url}
Content summary: {content.content_summary or 'N/A'}
Visit count: {content.visit_count}

Should this content be kept for future reasoning?
Answer only KEEP or DISCARD."""
        try:
            response = self.llm_client.generate_text(
                system_prompt="You decide information retention for autonomous personas.",
                user_prompt=prompt,
                temperature=0.2,
            )
            return response.strip().upper().startswith("KEEP")
        except Exception:
            return self._heuristic_persona_vote(persona, island, content)

    def _heuristic_persona_vote(self, persona: PersonaGenotype, island: IslandCluster, content: IslandContent) -> bool:
        persona_tokens = self._extract_interest_tokens(persona.bio)
        island_tokens = self._extract_interest_tokens(island.topic)
        content_tokens = self._extract_interest_tokens(
            " ".join(filter(None, [content.title or "", content.content_summary or "", " ".join(content.keywords)]))
        )

        relevance_persona = self._jaccard_similarity(persona_tokens, content_tokens)
        relevance_island = self._jaccard_similarity(island_tokens, content_tokens)
        popularity = min(content.visit_count / 3.0, 1.0)
        score = 0.45 * relevance_persona + 0.35 * relevance_island + 0.20 * popularity
        return score >= 0.25

    def _content_keep_heuristic(self, island: IslandCluster, content: IslandContent) -> float:
        island_tokens = self._extract_interest_tokens(island.topic)
        content_tokens = self._extract_interest_tokens(
            " ".join(filter(None, [content.title or "", content.content_summary or "", " ".join(content.keywords)]))
        )
        topic_relevance = self._jaccard_similarity(island_tokens, content_tokens)
        popularity = min(content.visit_count / 5.0, 1.0)
        freshness = 0.0
        if content.last_accessed_at:
            last = self._parse_datetime(content.last_accessed_at)
            if last:
                hours_ago = max(0.0, (datetime.now() - last).total_seconds() / 3600.0)
                freshness = max(0.0, 1.0 - hours_ago / (max(1, content.ttl_hours) * 2))
        return 0.5 * topic_relevance + 0.3 * popularity + 0.2 * freshness
