import argparse
import json
import os
import random
from typing import List, Optional, Dict

from snackPersona.utils.data_models import PersonaGenotype
from snackPersona.llm.llm_client import MockLLMClient, OpenAIClient, BedrockClient
from snackPersona.persona_store.store import PersonaStore
from snackPersona.evaluation.evaluator import BasicEvaluator, LLMEvaluator
from snackPersona.orchestrator.operators import SimpleFieldMutator, LLMMutator, MixTraitsCrossover
from snackPersona.orchestrator.engine import EvolutionEngine
from snackPersona.utils.media_dataset import MediaDataset
from snackPersona.utils.logger import logger

# Default seed file path (relative to package root)
_DEFAULT_SEED_FILE = os.path.join(
    os.path.dirname(__file__), 'config', 'seed_personas.json'
)


def load_seed_population(path: str) -> List[PersonaGenotype]:
    """Load seed personas from a JSON file."""
    with open(path) as f:
        data = json.load(f)
    personas = [PersonaGenotype(**item) for item in data]
    logger.info(f"Loaded {len(personas)} seed personas from {path}")
    return personas


def load_config(path: Optional[str]) -> Dict:
    """Load evolution config from a JSON file, or return empty dict."""
    if not path:
        return {}
    if not os.path.exists(path):
        logger.warning(f"Config file not found at {path}, using defaults")
        return {}
    with open(path) as f:
        config = json.load(f)
    logger.info(f"Loaded config from {path}")
    return config


def main():
    parser = argparse.ArgumentParser(
        description="Evolutionary Persona Prompt Generation"
    )
    parser.add_argument("--generations", type=int, default=3,
                        help="Number of generations to evolve")
    parser.add_argument("--pop_size", type=int, default=4,
                        help="Population size")
    parser.add_argument("--llm", type=str,
                        choices=["mock", "openai", "bedrock"], default="mock",
                        help="LLM backend to use")
    parser.add_argument("--store_dir", type=str, default="persona_data",
                        help="Directory for storing generation data")
    parser.add_argument("--media_dataset", type=str, default=None,
                        help="Path to JSON file containing media items")
    parser.add_argument("--seed_file", type=str, default=None,
                        help="Path to JSON file containing seed personas "
                             "(default: config/seed_personas.json)")
    parser.add_argument("--config", type=str, default=None,
                        help="Path to JSON config for evolution parameters "
                             "(default: built-in defaults)")

    args = parser.parse_args()

    # 1. Setup LLM Client
    if args.llm == "mock":
        logger.info("Using Mock LLM Client")
        llm_client = MockLLMClient()
    elif args.llm == "openai":
        logger.info("Using OpenAI Client")
        llm_client = OpenAIClient()
    elif args.llm == "bedrock":
        logger.info("Using Bedrock Client")
        llm_client = BedrockClient()
    else:
        raise ValueError("Unknown LLM backend")

    # 2. Load config
    config = load_config(args.config)

    # 3. Setup Components
    store = PersonaStore(storage_dir=args.store_dir)

    # Load media dataset if provided
    media_dataset = None
    if args.media_dataset:
        if os.path.exists(args.media_dataset):
            logger.info(f"Loading media dataset from {args.media_dataset}")
            media_dataset = MediaDataset(args.media_dataset)
            logger.info(f"Loaded {len(media_dataset)} media items")
        else:
            logger.warning(f"Media dataset file not found at {args.media_dataset}")

    # Choose evaluator & mutator based on LLM backend
    if args.llm == "mock":
        evaluator = BasicEvaluator()
        mutation_op = SimpleFieldMutator()
    else:
        logger.info("Using LLM-based Evaluator and Mutator")
        evaluator = LLMEvaluator(llm_client)
        mutation_op = LLMMutator(llm_client)

    crossover_op = MixTraitsCrossover()

    # 4. Initialize Engine
    engine = EvolutionEngine(
        llm_client=llm_client,
        store=store,
        evaluator=evaluator,
        mutation_op=mutation_op,
        crossover_op=crossover_op,
        population_size=args.pop_size,
        generations=args.generations,
        elite_count=max(1, args.pop_size // 4),
        media_dataset=media_dataset,
        config=config,
    )

    # 5. Load or Initialize Population
    existing_gens = store.list_generations()
    if existing_gens:
        last_gen_id = existing_gens[-1]
        logger.info(f"Resuming from generation {last_gen_id}")
        last_gen_pop = store.load_generation(last_gen_id)
        engine.initialize_population(last_gen_pop)
    else:
        # Load seeds from file
        seed_path = args.seed_file or _DEFAULT_SEED_FILE
        if os.path.exists(seed_path):
            seeds = load_seed_population(seed_path)
        else:
            logger.warning(f"Seed file not found at {seed_path}, using minimal defaults")
            seeds = [
                PersonaGenotype(
                    name="Default", age=25, occupation="Thinker",
                    backstory="A curious mind.",
                    core_values=["curiosity"], hobbies=["reading"],
                    personality_traits={"openness": 0.8},
                    communication_style="casual",
                    topical_focus="general",
                    interaction_policy="ask questions",
                    goals=["learn"]
                )
            ]

        # Trim or extend to match pop_size
        while len(seeds) < args.pop_size:
            seeds.append(random.choice(seeds).model_copy(deep=True))
        engine.initialize_population(seeds[:args.pop_size])

    # 6. Run Evolution
    logger.info("Starting Evolution Loop")
    engine.run_evolution_loop()
    logger.info("Evolution Complete!")
    logger.info(f"Stats saved to {store.storage_dir}/generation_stats.jsonl")


if __name__ == "__main__":
    main()
