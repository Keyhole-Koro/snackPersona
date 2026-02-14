"""
Interactive Chat CLI for SnackPersona.
Allows users to converse directly with evolved personas.
"""

import sys
import asyncio
import os
import random

from snackPersona.persona_store.store import PersonaStore
from snackPersona.simulation.agent import SimulationAgent
from snackPersona.llm.llm_factory import create_llm_client
from snackPersona.utils.data_models import PersonaGenotype

async def async_chat():
    print("--- SnackPersona Interactive Chat ---")
    
    # 1. Setup
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found.")
        return

    llm_client = create_llm_client("gemini-flash")
    store = PersonaStore(storage_dir="persona_data")
    
    # 2. Select Persona
    gens = store.list_generations()
    population = []
    
    if gens:
        # Load from latest generation
        latest_gen = gens[-1]
        print(f"Loading personas from Generation {latest_gen}...")
        population = store.load_generation(latest_gen)
    else:
        # Load seeds if no evolution data
        print("No evolution data found. Loading seeds...")
        from snackPersona.main import create_seed_population
        population = create_seed_population()

    print("\nAvailable Personas:")
    for i, p in enumerate(population):
        print(f"{i+1}. {p.name}")
        
    choice = input("\nSelect a persona (number): ")
    try:
        idx = int(choice) - 1
        persona_genotype = population[idx]
    except (ValueError, IndexError):
        print("Invalid selection.")
        return

    # 3. Initialize Agent
    agent = SimulationAgent(persona_genotype, llm_client)
    print(f"\nConnected to {agent.genotype.name}.")
    print(f"Bio: {agent.genotype.bio[:100]}...")
    print("Type 'exit' to quit.\n")

    # 4. Chat Loop
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ["exit", "quit"]:
            break
            
        print(f"{agent.genotype.name} is typing...")
        
        # We use generate_reply logic but adapted for direct chat
        # Or we can add a specific chat method. For now, generate_reply works if we frame it right.
        response = await agent.generate_reply_async(user_input, "User")
        
        print(f"\n{agent.genotype.name}: {response}")

if __name__ == "__main__":
    asyncio.run(async_chat())
