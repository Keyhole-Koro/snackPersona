import argparse
import os
import random
from typing import List

from snackPersona.utils.data_models import PersonaGenotype
from snackPersona.llm.llm_client import MockLLMClient, OpenAIClient, BedrockClient
from snackPersona.persona_store.store import PersonaStore
from snackPersona.evaluation.evaluator import BasicEvaluator, LLMEvaluator
from snackPersona.orchestrator.operators import SimpleFieldMutator, LLMMutator, MixTraitsCrossover
from snackPersona.orchestrator.engine import EvolutionEngine

def create_seed_population() -> List[PersonaGenotype]:
    """
    Creates a small set of seed personas to start evolution.
    Now uses the flexible attributes structure.
    """
    return [
        PersonaGenotype(
            name="Alice",
            attributes={
                "age": 25,
                "occupation": "Digital Artist",
                "backstory": "Always loved drawing, now exploring generative art.",
                "core_values": ["creativity", "freedom"],
                "hobbies": ["sketching", "visiting galleries"],
                "personality_traits": {"openness": 0.9, "neuroticism": 0.4},
                "communication_style": "enthusiastic and visual",
                "topical_focus": "digital art trends",
                "interaction_policy": "compliment others' work",
                "goals": ["become famous", "inspire others"]
            }
        ),
        PersonaGenotype(
            name="Bob",
            attributes={
                "age": 35,
                "occupation": "Software Engineer",
                "backstory": "Coding since childhood, obsessed with clean code.",
                "core_values": ["logic", "efficiency"],
                "hobbies": ["coding", "chess"],
                "personality_traits": {"conscientiousness": 0.9, "extraversion": 0.2},
                "communication_style": "concise and technical",
                "topical_focus": "programming best practices",
                "interaction_policy": "correct misconceptions",
                "goals": ["teach others", "find bugs"]
            }
        ),
        PersonaGenotype(
            name="Charlie",
            attributes={
                "age": 22,
                "occupation": "Student",
                "backstory": "Studying philosophy, questions everything.",
                "core_values": ["truth", "skepticism"],
                "hobbies": ["reading", "debating"],
                "personality_traits": {"openness": 0.8, "agreeableness": 0.4},
                "communication_style": "inquisitive and verbose",
                "topical_focus": "ethics of AI",
                "interaction_policy": "ask deep questions",
                "goals": ["understand the world", "win debates"]
            }
        ),
        PersonaGenotype(
            name="Dana",
            attributes={
                "age": 40,
                "occupation": "Journalist",
                "backstory": "Investigating the truth behind the headlines.",
                "core_values": ["integrity", "justice"],
                "hobbies": ["writing", "travelling"],
                "personality_traits": {"extraversion": 0.8, "agreeableness": 0.6},
                "communication_style": "direct and probing",
                "topical_focus": "current events",
                "interaction_policy": "interview others",
                "goals": ["uncover stories", "inform the public"]
            }
        )
    ]

def main():
    parser = argparse.ArgumentParser(description="Evolutionary Persona Prompt Generation")
    parser.add_argument("--generations", type=int, default=3, help="Number of generations to evolve")
    parser.add_argument("--pop_size", type=int, default=4, help="Population size")
    parser.add_argument("--llm", type=str, choices=["mock", "openai", "bedrock"], default="mock", help="LLM backend to use")
    parser.add_argument("--store_dir", type=str, default="persona_data", help="Directory to store persona generations")
    
    args = parser.parse_args()
    
    # 1. Setup LLM Client
    if args.llm == "mock":
        print("Using Mock LLM Client...")
        llm_client = MockLLMClient()
    elif args.llm == "openai":
        print("Using OpenAI Client...")
        llm_client = OpenAIClient()
    elif args.llm == "bedrock":
        print("Using Bedrock Client...")
        llm_client = BedrockClient()
    else:
        raise ValueError("Unknown LLM backend")

    # 2. Setup Components
    store = PersonaStore(storage_dir=args.store_dir)
    
    # Use BasicEvaluator for speed/cost if mock, else LLMEvaluator
    if args.llm == "mock":
        evaluator = BasicEvaluator()
        mutation_op = SimpleFieldMutator()
    else:
        print("Using LLM-based Evaluator and Mutator...")
        evaluator = LLMEvaluator(llm_client)
        mutation_op = LLMMutator(llm_client)
        
    crossover_op = MixTraitsCrossover()
    
    # 3. Initialize Engine
    engine = EvolutionEngine(
        llm_client=llm_client,
        store=store,
        evaluator=evaluator,
        mutation_op=mutation_op,
        crossover_op=crossover_op,
        population_size=args.pop_size,
        generations=args.generations,
        elite_count=max(1, args.pop_size // 4)
    )
    
    # 4. Load or Initialize Population
    existing_gens = store.list_generations()
    if existing_gens:
        last_gen_id = existing_gens[-1]
        print(f"Loading population from generation {last_gen_id}...")
        last_gen_pop = store.load_generation(last_gen_id)
        engine.initialize_population(last_gen_pop)
    else:
        print("Initializing new seed population...")
        seeds = create_seed_population()
        # Ensure we have enough seeds or replicate
        while len(seeds) < args.pop_size:
            seeds.append(random.choice(seeds).model_copy(deep=True))
        engine.initialize_population(seeds[:args.pop_size])

    # 5. Run Evolution
    print("Starting Evolution Loop...")
    engine.run_evolution_loop()
    print("Evolution Complete!")

if __name__ == "__main__":
    main()
