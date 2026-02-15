"""
Tests for Island clustering functionality.
"""
import pytest
from datetime import datetime, timedelta
from snackPersona.utils.data_models import PersonaGenotype, IslandCluster, IslandContent
from snackPersona.islands import IslandManager, PersonaKeywordGenerator


class TestIslandDataModels:
    """Test Island data models."""
    
    def test_island_cluster_creation(self):
        """Test creating an IslandCluster."""
        island = IslandCluster(
            id="test_island",
            topic="AI Technology"
        )
        assert island.id == "test_island"
        assert island.topic == "AI Technology"
        assert len(island.persona_ids) == 0
        assert len(island.content) == 0
    
    def test_island_content_creation(self):
        """Test creating IslandContent."""
        content = IslandContent(
            url="https://example.com/article",
            title="Test Article",
            keywords=["AI", "technology"]
        )
        assert content.url == "https://example.com/article"
        assert content.title == "Test Article"
        assert "AI" in content.keywords
        assert content.visit_count == 1
    
    def test_persona_with_island_id(self):
        """Test PersonaGenotype with island_id field."""
        persona = PersonaGenotype(
            name="TestUser",
            bio="A test user interested in technology",
            island_id="tech_island"
        )
        assert persona.island_id == "tech_island"


class TestIslandManager:
    """Test IslandManager functionality."""
    
    def test_create_island(self):
        """Test creating an island."""
        manager = IslandManager()
        island = manager.create_island("island1", "Technology")
        
        assert island.id == "island1"
        assert island.topic == "Technology"
        assert "island1" in manager.islands
    
    def test_assign_persona_to_island(self):
        """Test assigning a persona to an island."""
        manager = IslandManager()
        manager.create_island("island1", "Technology")
        
        persona = PersonaGenotype(
            name="TechUser",
            bio="A tech enthusiast"
        )
        
        result = manager.assign_persona_to_island(persona, "island1")
        assert result is True
        assert persona.island_id == "island1"
        assert "TechUser" in manager.islands["island1"].persona_ids
    
    def test_add_content_to_island(self):
        """Test adding content to an island."""
        manager = IslandManager()
        manager.create_island("island1", "Technology")
        
        result = manager.add_content_to_island(
            island_id="island1",
            url="https://techcrunch.com/article",
            title="Tech News",
            keywords=["AI", "ML"]
        )
        
        assert result is True
        assert len(manager.islands["island1"].content) == 1
        assert manager.islands["island1"].content[0].url == "https://techcrunch.com/article"
    
    def test_add_duplicate_content(self):
        """Test adding duplicate URL increments visit count."""
        manager = IslandManager()
        manager.create_island("island1", "Technology")
        
        url = "https://example.com/article"
        manager.add_content_to_island("island1", url, title="Article 1")
        manager.add_content_to_island("island1", url, title="Article 1 Again")
        
        island = manager.islands["island1"]
        assert len(island.content) == 1  # Still one entry
        assert island.content[0].visit_count == 2  # But visit count increased
    
    def test_domain_diversity_metrics(self):
        """Test domain diversity calculation."""
        manager = IslandManager()
        manager.create_island("island1", "Technology")
        
        # Add content from different domains
        manager.add_content_to_island("island1", "https://techcrunch.com/article1")
        manager.add_content_to_island("island1", "https://techcrunch.com/article2")
        manager.add_content_to_island("island1", "https://wired.com/article1")
        
        metrics = manager.get_domain_diversity("island1")
        assert metrics["unique_domains"] == 2
        assert metrics["max_domain_ratio"] == 2/3  # techcrunch.com has 2 of 3 visits
    
    def test_persona_migration_between_islands(self):
        """Test moving a persona between islands."""
        manager = IslandManager()
        manager.create_island("island1", "Technology")
        manager.create_island("island2", "Science")
        
        persona = PersonaGenotype(
            name="MigrantUser",
            bio="A curious person"
        )
        
        # Assign to first island
        manager.assign_persona_to_island(persona, "island1")
        assert "MigrantUser" in manager.islands["island1"].persona_ids
        assert "MigrantUser" not in manager.islands["island2"].persona_ids
        
        # Migrate to second island
        manager.assign_persona_to_island(persona, "island2")
        assert "MigrantUser" not in manager.islands["island1"].persona_ids
        assert "MigrantUser" in manager.islands["island2"].persona_ids
        assert persona.island_id == "island2"


class TestPersonaKeywordGenerator:
    """Test PersonaKeywordGenerator functionality."""
    
    def test_fallback_keywords(self):
        """Test fallback keyword generation without LLM."""
        from snackPersona.llm.llm_client import LLMClient
        
        # Create a mock LLM client that will fail
        class MockLLM:
            def generate_text(self, *args, **kwargs):
                raise Exception("Mock failure")
        
        generator = PersonaKeywordGenerator(MockLLM())
        
        persona = PersonaGenotype(
            name="TestUser",
            bio="A software engineer interested in machine learning and artificial intelligence"
        )
        
        keywords = generator.generate_keywords(persona, num_keywords=3)
        
        # Should get fallback keywords
        assert len(keywords) > 0
        assert isinstance(keywords[0], str)
    
    def test_generate_search_query(self):
        """Test generating a search query."""
        class MockLLM:
            def generate_text(self, *args, **kwargs):
                # Return invalid JSON to trigger fallback
                return "invalid json"
        
        generator = PersonaKeywordGenerator(MockLLM())
        
        persona = PersonaGenotype(
            name="TestUser",
            bio="A data scientist working on climate change models"
        )
        
        query = generator.generate_search_query(persona, topic="climate")
        
        # Should generate some query string
        assert isinstance(query, str)
        assert len(query) > 0


class TestFactionManagement:
    """Test Faction management functionality."""
    
    def test_create_faction(self):
        """Test creating a faction within an island."""
        manager = IslandManager()
        manager.create_island("island1", "Technology")
        
        result = manager.create_faction("island1", "faction1", "Early Adopters", 
                                       initial_personas=["Alice", "Bob"])
        
        assert result is True
        island = manager.get_island("island1")
        assert "faction1" in island.factions
        assert island.factions["faction1"].name == "Early Adopters"
        assert "Alice" in island.factions["faction1"].persona_ids
    
    def test_add_persona_to_faction(self):
        """Test adding a persona to a faction."""
        manager = IslandManager()
        manager.create_island("island1", "Technology")
        manager.create_faction("island1", "faction1", "Faction One")
        
        result = manager.add_persona_to_faction("island1", "faction1", "Charlie")
        
        assert result is True
        assert "Charlie" in manager.islands["island1"].factions["faction1"].persona_ids
    
    def test_evolve_faction_queries(self):
        """Test query evolution for a faction."""
        class MockLLM:
            def generate_text(self, *args, **kwargs):
                return '["query1", "query2", "query3"]'
        
        manager = IslandManager(llm_client=MockLLM())
        manager.create_island("island1", "Technology")
        manager.create_faction("island1", "faction1", "Faction One")
        
        queries = manager.evolve_faction_queries("island1", "faction1", num_queries=3)
        
        assert len(queries) > 0
        faction = manager.islands["island1"].factions["faction1"]
        assert len(faction.evolved_queries) > 0
    
    def test_calculate_faction_similarity(self):
        """Test similarity calculation between factions."""
        manager = IslandManager()
        manager.create_island("island1", "Technology")
        manager.create_faction("island1", "faction1", "Faction One")
        manager.create_faction("island1", "faction2", "Faction Two")
        
        # Add similar queries
        manager.islands["island1"].factions["faction1"].evolved_queries = [
            "AI machine learning", "deep learning neural networks"
        ]
        manager.islands["island1"].factions["faction2"].evolved_queries = [
            "AI deep learning", "machine learning models"
        ]
        
        similarity = manager.calculate_faction_similarity("island1", "faction1", "faction2")
        
        assert similarity > 0.0
        assert similarity <= 1.0
    
    def test_natural_selection_factions(self):
        """Test natural selection eliminates similar low-fitness factions."""
        manager = IslandManager()
        manager.create_island("island1", "Technology")
        manager.create_faction("island1", "faction1", "High Fitness", ["Alice"])
        manager.create_faction("island1", "faction2", "Low Fitness", ["Bob"])
        
        # Make them similar
        manager.islands["island1"].factions["faction1"].evolved_queries = [
            "AI machine learning deep learning"
        ]
        manager.islands["island1"].factions["faction2"].evolved_queries = [
            "AI deep learning machine learning"
        ]
        
        # Set different fitness scores
        manager.islands["island1"].factions["faction1"].fitness_score = 0.8
        manager.islands["island1"].factions["faction2"].fitness_score = 0.3
        
        eliminated = manager.natural_selection_factions("island1", similarity_threshold=0.5)
        
        assert len(eliminated) > 0
        assert "faction2" in eliminated
        assert "faction2" not in manager.islands["island1"].factions
    
    def test_update_faction_fitness(self):
        """Test updating faction fitness metrics."""
        manager = IslandManager()
        manager.create_island("island1", "Technology")
        manager.create_faction("island1", "faction1", "Faction One")
        
        manager.update_faction_fitness("island1", "faction1", 
                                      unique_domains=5, quality_score=0.8)
        
        faction = manager.islands["island1"].factions["faction1"]
        assert faction.unique_domains_discovered == 5
        assert faction.content_quality_score == 0.8
        assert faction.fitness_score > 0.0


class TestIslandAutomationAndLifecycle:
    """Test automatic island generation and content lifecycle controls."""

    def test_auto_generate_islands_from_personas(self):
        manager = IslandManager()
        personas = [
            PersonaGenotype(name="A", bio="AI researcher building transformer models and machine learning systems"),
            PersonaGenotype(name="B", bio="Machine learning engineer working on AI models and data pipelines"),
            PersonaGenotype(name="C", bio="Climate activist studying renewable energy and sustainability policy"),
            PersonaGenotype(name="D", bio="Environmental scientist focused on climate data and emissions"),
        ]

        islands = manager.auto_generate_islands_from_personas(personas, similarity_threshold=0.10, min_cluster_size=1)

        assert len(islands) >= 2
        assert all(p.island_id is not None for p in personas)

    def test_run_content_retention_cycle_discards_expired_low_value_content(self):
        manager = IslandManager()
        manager.create_island("island1", "AI Technology")

        persona = PersonaGenotype(name="TechUser", bio="AI engineer and data scientist", island_id="island1")
        manager.assign_persona_to_island(persona, "island1")

        manager.add_content_to_island(
            island_id="island1",
            url="https://example.com/old",
            title="Unrelated Page",
            content_summary="Cooking and travel diary entry",
            keywords=["cooking", "travel"],
            ttl_hours=1,
        )

        island = manager.get_island("island1")
        island.content[0].expires_at = (datetime.now() - timedelta(hours=2)).isoformat()

        stats = manager.run_content_retention_cycle("island1", [persona], min_votes=1)
        assert stats["evaluated"] == 1
        assert stats["discarded"] == 1
        assert len(island.content) == 0

    def test_retention_cycle_discards_after_insufficient_votes_max_rounds(self):
        manager = IslandManager()
        manager.create_island("empty_island", "General Topic")

        manager.add_content_to_island(
            island_id="empty_island",
            url="https://example.com/stale",
            title="Stale Content",
            content_summary="Low relevance memo",
            keywords=["misc"],
            ttl_hours=1,
        )

        island = manager.get_island("empty_island")
        island.content[0].expires_at = (datetime.now() - timedelta(hours=2)).isoformat()

        stats = manager.run_content_retention_cycle(
            "empty_island",
            personas=[],
            min_votes=2,
            max_rounds=1,
        )
        assert stats["evaluated"] == 1
        assert stats["discarded"] == 1
        assert len(island.content) == 0

    def test_retention_cycle_grace_keeps_high_value_content(self):
        manager = IslandManager()
        manager.create_island("empty_island", "General Topic")

        manager.add_content_to_island(
            island_id="empty_island",
            url="https://example.com/high-value",
            title="Popular Content",
            content_summary="Frequently revisited resource",
            keywords=["popular"],
            ttl_hours=1,
        )

        island = manager.get_island("empty_island")
        island.content[0].visit_count = 7
        island.content[0].expires_at = (datetime.now() - timedelta(hours=2)).isoformat()

        stats = manager.run_content_retention_cycle(
            "empty_island",
            personas=[],
            min_votes=2,
            max_rounds=1,
            high_value_visit_threshold=5,
            grace_ttl_hours=12,
        )
        assert stats["evaluated"] == 1
        assert stats["kept"] == 1
        assert len(island.content) == 1
        assert island.content[0].retention_rounds == 0

    def test_split_overcrowded_islands(self):
        manager = IslandManager()
        manager.create_island("mega", "General Mixed Topics")

        personas = []
        for i in range(8):
            p = PersonaGenotype(name=f"AI_{i}", bio="AI machine learning neural networks transformer research")
            personas.append(p)
            manager.assign_persona_to_island(p, "mega")
        for i in range(8):
            p = PersonaGenotype(name=f"CLIMATE_{i}", bio="Climate change renewable energy sustainability emissions policy")
            personas.append(p)
            manager.assign_persona_to_island(p, "mega")

        new_islands = manager.split_overcrowded_islands(
            personas=personas,
            max_residents=10,
            min_cohesion=0.55,
            min_split_size=6,
        )

        assert len(new_islands) >= 1
        assert len(manager.get_island("mega").persona_ids) < 16


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
