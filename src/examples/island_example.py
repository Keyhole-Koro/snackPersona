"""
Example demonstrating the Island clustering system with persona search and crawling.

This example shows how to:
1. Create island clusters for different topics
2. Assign personas to islands
3. Generate search keywords based on persona bios
4. Execute web searches and crawling
5. Track and evolve queries to avoid site bias
6. Migrate personas between islands

Usage:
    export GEMINI_API_KEY="your-api-key"
    python -m snackPersona.examples.island_example
"""
import asyncio
import logging
from snackPersona.utils.data_models import PersonaGenotype
from snackPersona.islands import IslandManager, PersonaKeywordGenerator, IslandTravelerIntegration
from snackPersona.llm.llm_factory import create_llm_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("snackPersona")


async def main():
    """Run the island clustering example."""
    
    print("=" * 80)
    print("Island Clustering System - Example")
    print("=" * 80)
    print()
    
    # 1. Setup LLM Client
    print("1. Setting up LLM client...")
    import os
    if not os.getenv("GEMINI_API_KEY"):
        print("   WARNING: GEMINI_API_KEY not set. Using mock LLM for demonstration.")
        print("   Set GEMINI_API_KEY environment variable for full functionality.")
        print()
        # Create a simple mock LLM
        class MockLLM:
            def generate_text(self, *args, **kwargs):
                return '["keyword1", "keyword2", "keyword3"]'
        llm_client = MockLLM()
    else:
        llm_client = create_llm_client("gemini-flash")
    
    # 2. Create Island Manager
    print("2. Creating Island Manager...")
    island_manager = IslandManager(llm_client=llm_client)
    
    # 3. Create islands for different topics
    print("3. Creating topic-based islands...")
    tech_island = island_manager.create_island(
        island_id="tech_island",
        topic="AI Technology and Innovation",
        description="Island focused on artificial intelligence, machine learning, and tech innovation"
    )
    
    climate_island = island_manager.create_island(
        island_id="climate_island",
        topic="Climate Change and Sustainability",
        description="Island focused on environmental issues, climate science, and sustainable practices"
    )
    
    business_island = island_manager.create_island(
        island_id="business_island",
        topic="Business and Entrepreneurship",
        description="Island focused on startups, business strategy, and entrepreneurship"
    )
    
    print(f"   Created {len(island_manager.islands)} islands")
    print()
    
    # 4. Create personas with diverse interests
    print("4. Creating personas...")
    personas = [
        PersonaGenotype(
            name="AI_Researcher_Sarah",
            bio="I'm a machine learning researcher at a tech lab. I spend my days fine-tuning models and nights reading ArXiv papers. I'm fascinated by how AI can solve complex problems but worried about its ethical implications. Currently exploring transformer architectures."
        ),
        PersonaGenotype(
            name="Climate_Activist_Mike",
            bio="Former corporate consultant who left everything to work on climate solutions. I organize community awareness programs and follow the latest climate research obsessively. Passionate about renewable energy and carbon capture technologies. Living off-grid in Vermont."
        ),
        PersonaGenotype(
            name="Startup_Founder_Lisa",
            bio="Building my third startup after two exits. I'm all about lean methodologies, growth hacking, and building teams. I read business books obsessively and mentor young founders. Currently working on a SaaS platform for remote teams."
        ),
        PersonaGenotype(
            name="Data_Scientist_Tom",
            bio="Data scientist who loves both AI and environmental data analysis. I work on climate prediction models using deep learning. Straddling the intersection of technology and sustainability. Coffee addict and Python enthusiast."
        )
    ]
    
    print(f"   Created {len(personas)} personas")
    print()
    
    # 5. Assign personas to islands based on their interests
    print("5. Assigning personas to islands...")
    island_manager.assign_persona_to_island(personas[0], "tech_island")
    island_manager.assign_persona_to_island(personas[1], "climate_island")
    island_manager.assign_persona_to_island(personas[2], "business_island")
    island_manager.assign_persona_to_island(personas[3], "tech_island")  # Tom goes to tech initially
    
    for persona in personas:
        print(f"   {persona.name} -> {persona.island_id}")
    print()
    
    # 6. Setup Traveler Integration
    print("6. Setting up Traveler integration...")
    traveler_integration = IslandTravelerIntegration(island_manager, llm_client)
    print()
    
    # 7. Generate search keywords for each persona
    print("7. Generating search keywords for personas...")
    keyword_generator = PersonaKeywordGenerator(llm_client)
    
    for persona in personas:
        island = island_manager.get_island(persona.island_id)
        print(f"\n   {persona.name} (Island: {island.topic}):")
        
        # Generate keywords
        keywords = keyword_generator.generate_keywords(persona, topic=island.topic, num_keywords=3)
        print(f"   Keywords: {keywords}")
        
        # Generate a search query
        query = keyword_generator.generate_search_query(persona, topic=island.topic)
        print(f"   Search Query: '{query}'")
    
    print()
    
    # 8. Simulate web exploration for one persona
    print("8. Simulating web exploration for AI_Researcher_Sarah...")
    print("   (This would actually search and crawl the web if run with real API keys)")
    print()
    
    # Note: Actual web exploration would be:
    # result = traveler_integration.explore_for_persona(personas[0])
    # print(f"   Discovered {len(result.retrieved_urls)} URLs")
    # print(f"   Headlines: {result.headlines[:3]}")
    
    # For demonstration, we'll manually add some content
    island_manager.add_content_to_island(
        island_id="tech_island",
        url="https://arxiv.org/abs/example-ml-paper",
        title="Recent Advances in Transformer Models",
        keywords=["AI", "transformers", "machine learning"],
        source_persona="AI_Researcher_Sarah"
    )
    
    island_manager.add_content_to_island(
        island_id="tech_island",
        url="https://techcrunch.com/ai-news",
        title="Latest AI Developments",
        keywords=["AI", "technology", "innovation"],
        source_persona="Data_Scientist_Tom"
    )
    
    print("   Added sample content to tech_island")
    print()
    
    # 9. Check domain diversity
    print("9. Analyzing domain diversity for tech_island...")
    diversity = island_manager.get_domain_diversity("tech_island")
    print(f"   Unique domains: {diversity['unique_domains']}")
    print(f"   Max domain ratio: {diversity['max_domain_ratio']:.2f}")
    print(f"   Entropy: {diversity['entropy']:.2f}")
    print()
    
    # 10. Evolve keywords for the island
    print("10. Evolving keywords to avoid site bias...")
    evolved = island_manager.evolve_keywords_for_island("tech_island", max_keywords=5)
    if evolved:
        print(f"    Evolved keywords: {evolved}")
    else:
        print("    Keyword evolution requires LLM and content history")
    print()
    
    # 11. Check if Tom should migrate to climate island
    print("11. Checking persona migration possibilities...")
    print(f"    Tom's bio mentions both AI and climate...")
    should_migrate = island_manager.should_migrate_persona(personas[3], "climate_island")
    print(f"    Should Tom migrate to climate_island? {should_migrate}")
    
    if should_migrate:
        island_manager.migrate_persona(personas[3], "climate_island")
        print(f"    Tom migrated to {personas[3].island_id}")
    print()
    
    # 12. Display island statistics
    print("12. Island Statistics:")
    print()
    for island in island_manager.list_islands():
        print(f"   Island: {island.topic}")
        print(f"   ID: {island.id}")
        print(f"   Personas: {len(island.persona_ids)} - {list(island.persona_ids)}")
        print(f"   Content Items: {len(island.content)}")
        print(f"   Total Visits: {island.total_visits}")
        print(f"   Domains: {len(island.visited_domains)}")
        print()
    
    print("=" * 80)
    print("Example complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
