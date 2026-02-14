"""
Example demonstrating faction-based query evolution with natural selection.

This example shows:
1. Creating factions within islands
2. Independent query evolution per faction
3. Calculating faction similarity
4. Natural selection eliminating similar low-fitness factions

Usage:
    export GEMINI_API_KEY="your-api-key"  # Optional - works with mock LLM
    python -m snackPersona.examples.faction_example
"""
import asyncio
import logging
from snackPersona.utils.data_models import PersonaGenotype
from snackPersona.islands import IslandManager
from snackPersona.llm.llm_factory import create_llm_client
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("snackPersona")


async def main():
    """Run the faction evolution example."""
    
    print("=" * 80)
    print("Faction-Based Query Evolution with Natural Selection - Example")
    print("=" * 80)
    print()
    
    # 1. Setup LLM Client
    print("1. Setting up LLM client...")
    if not os.getenv("GEMINI_API_KEY"):
        print("   Using mock LLM for demonstration.")
        class MockLLM:
            def __init__(self):
                self.call_count = 0
                
            def generate_text(self, *args, **kwargs):
                # Return different queries for different calls to simulate diversity
                queries = [
                    '["AI ethics research", "machine learning bias", "fairness in AI"]',
                    '["deep learning models", "neural architecture", "transformer optimization"]',
                    '["AI policy regulation", "ethical AI frameworks", "AI governance"]',
                    '["quantum machine learning", "AI hardware acceleration", "neuromorphic computing"]'
                ]
                result = queries[self.call_count % len(queries)]
                self.call_count += 1
                return result
        llm_client = MockLLM()
    else:
        llm_client = create_llm_client("gemini-flash")
    print()
    
    # 2. Create Island Manager
    print("2. Creating Island Manager...")
    island_manager = IslandManager(llm_client=llm_client)
    print()
    
    # 3. Create an island
    print("3. Creating AI Technology island...")
    island_manager.create_island(
        island_id="ai_island",
        topic="AI Technology and Ethics",
        description="Island focused on AI development and ethical considerations"
    )
    print()
    
    # 4. Create multiple factions with different perspectives
    print("4. Creating factions within the island...")
    
    factions_config = [
        ("ethics_faction", "AI Ethics Advocates", ["Sarah", "Mike"]),
        ("tech_faction", "Technical Innovators", ["Alice", "Tom"]),
        ("policy_faction", "Policy Makers", ["Diana", "Robert"]),
        ("research_faction", "Research Scientists", ["Emily", "David"])
    ]
    
    for faction_id, faction_name, members in factions_config:
        island_manager.create_faction("ai_island", faction_id, faction_name, members)
        print(f"   Created faction: {faction_name} with {len(members)} members")
    print()
    
    # 5. Evolve queries independently for each faction
    print("5. Evolving queries for each faction (Generation 1)...")
    for faction_id, faction_name, _ in factions_config:
        queries = island_manager.evolve_faction_queries("ai_island", faction_id, num_queries=3)
        print(f"\n   {faction_name}:")
        print(f"   Queries: {queries}")
    print()
    
    # 6. Simulate exploration results and update fitness
    print("6. Simulating exploration results and updating fitness...")
    
    fitness_results = [
        ("ethics_faction", 8, 0.85),   # High fitness
        ("tech_faction", 12, 0.90),    # Highest fitness
        ("policy_faction", 5, 0.60),   # Lower fitness
        ("research_faction", 10, 0.75) # Medium-high fitness
    ]
    
    for faction_id, domains, quality in fitness_results:
        island_manager.update_faction_fitness("ai_island", faction_id, domains, quality)
        faction = island_manager.islands["ai_island"].factions[faction_id]
        print(f"   {faction.name}: fitness={faction.fitness_score:.2f} "
              f"(domains={domains}, quality={quality:.2f})")
    print()
    
    # 7. Make some factions similar (for natural selection demo)
    print("7. Making policy_faction similar to ethics_faction...")
    island = island_manager.islands["ai_island"]
    island.factions["policy_faction"].evolved_queries = [
        "AI ethics policy", "ethical AI regulations", "AI governance ethics"
    ]
    print("   Updated policy_faction queries to overlap with ethics_faction")
    print()
    
    # 8. Calculate faction similarities
    print("8. Calculating faction similarities...")
    faction_ids = [fid for fid, _, _ in factions_config]
    
    for i in range(len(faction_ids)):
        for j in range(i + 1, len(faction_ids)):
            fid1, fid2 = faction_ids[i], faction_ids[j]
            similarity = island_manager.calculate_faction_similarity("ai_island", fid1, fid2)
            fname1 = island.factions[fid1].name
            fname2 = island.factions[fid2].name
            print(f"   {fname1} <-> {fname2}: {similarity:.2f}")
    print()
    
    # 9. Apply natural selection
    print("9. Applying natural selection (eliminating similar low-fitness factions)...")
    eliminated = island_manager.natural_selection_factions(
        "ai_island", 
        similarity_threshold=0.3
    )
    
    if eliminated:
        print(f"   Eliminated factions: {eliminated}")
        for fid in eliminated:
            matching = [name for fid2, name, _ in factions_config if fid2 == fid]
            if matching:
                print(f"   - {matching[0]} (low fitness + high similarity)")
    else:
        print("   No factions eliminated (insufficient similarity)")
    print()
    
    # 10. Show surviving factions
    print("10. Surviving factions after natural selection:")
    island = island_manager.islands["ai_island"]
    for faction_id, faction in island.factions.items():
        print(f"\n   {faction.name} (ID: {faction_id}):")
        print(f"   - Members: {len(faction.persona_ids)}")
        print(f"   - Fitness: {faction.fitness_score:.2f}")
        print(f"   - Queries: {len(faction.evolved_queries)}")
        print(f"   - Unique domains: {faction.unique_domains_discovered}")
    print()
    
    # 11. Evolve queries again (Generation 2)
    print("11. Evolving queries for surviving factions (Generation 2)...")
    for faction_id, faction in island.factions.items():
        queries = island_manager.evolve_faction_queries("ai_island", faction_id, num_queries=2)
        print(f"\n   {faction.name}:")
        print(f"   New queries: {queries}")
        print(f"   Total evolved queries: {len(faction.evolved_queries)}")
    print()
    
    # 12. Summary statistics
    print("12. Final Island Statistics:")
    print(f"   Total factions: {len(island.factions)}")
    print(f"   Total personas: {len(island.persona_ids)}")
    print(f"   Total queries evolved: {sum(len(f.evolved_queries) for f in island.factions.values())}")
    print(f"   Average faction fitness: {sum(f.fitness_score for f in island.factions.values()) / len(island.factions):.2f}")
    print()
    
    print("=" * 80)
    print("Example complete!")
    print()
    print("Key Takeaways:")
    print("1. Factions evolve queries independently based on their perspective")
    print("2. Fitness is based on domain diversity and content quality")
    print("3. Similar factions with lower fitness are eliminated (natural selection)")
    print("4. Surviving factions continue evolving in subsequent generations")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
