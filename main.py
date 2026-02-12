"""
Entry point for the evolutionary persona prompt generation system.

Usage examples::

    # Mock mode (no API keys required)
    python -m snackPersona.main --llm mock --generations 3 --pop_size 4

    # Gemini Flash
    export GEMINI_API_KEY="..."
    python -m snackPersona.main --llm gemini-flash --generations 5 --pop_size 8

    # OpenAI GPT-4o
    export OPENAI_API_KEY="..."
    python -m snackPersona.main --llm openai-gpt4o

    # List available presets
    python -m snackPersona.main --list-presets
"""

import argparse
import asyncio
import json
import os
import random
import sys
from typing import List, Optional, Dict

from snackPersona.utils.data_models import PersonaGenotype
from snackPersona.llm.llm_factory import create_llm_client, list_presets
from snackPersona.persona_store.store import PersonaStore
from snackPersona.evaluation.evaluator import LLMEvaluator
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


async def generate_seed_personas_async(
    llm_client, count: int
) -> Optional[List[PersonaGenotype]]:
    """Ask the LLM to generate diverse seed personas."""
    system_prompt = "You are an expert character designer for social media simulations."
    user_prompt = f"""Generate exactly {count} diverse, unique social media personas.
Each persona must be a JSON object with these fields:
- name (string): a unique first name
- age (int, 18-65)
- occupation (string)
- backstory (string, 1-2 sentences)
- core_values (list of 2-3 strings)
- hobbies (list of 2-3 strings)
- personality_traits (object with 2-3 keys mapping to floats 0.0-1.0, e.g. openness, conscientiousness, extraversion, agreeableness, neuroticism)
- communication_style (string, e.g. "casual", "formal", "witty")
- topical_focus (string, what they mainly post about)
- interaction_policy (string, how they interact with others)
- goals (list of 2-3 strings, their SNS goals)

Make the personas diverse in age, occupation, values, and interests.
Return ONLY a JSON array of {count} objects. No markdown, no explanation."""

    try:
        response = await llm_client.generate_text_async(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.9,
        )
        text = response.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        data = json.loads(text)
        if isinstance(data, list) and len(data) > 0:
            personas = [PersonaGenotype(**item) for item in data]
            logger.info(f"LLM generated {len(personas)} seed personas")
            return personas
    except Exception as e:
        logger.warning(f"LLM seed generation failed ({e}), falling back to file")
    return None


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


async def async_main():
    parser = argparse.ArgumentParser(
        description="Evolutionary Persona Prompt Generation"
    )
    parser.add_argument("--generations", type=int, default=3,
                        help="Number of generations to evolve")
    parser.add_argument("--pop_size", type=int, default=4,
                        help="Population size")
    parser.add_argument("--llm", type=str, default="mock",
                        help="LLM preset name (see --list-presets)")
    parser.add_argument("--list-presets", action="store_true",
                        help="List available LLM presets and exit")
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
    parser.add_argument("--no-viz", action="store_true",
                        help="Skip visualization report at the end")
    parser.add_argument("--generate-seeds", action="store_true",
                        help="Generate seed personas via LLM instead of loading from file")

    args = parser.parse_args()

    # List presets and exit
    if args.list_presets:
        print("Available LLM presets:")
        for name in list_presets():
            print(f"  - {name}")
        sys.exit(0)

    # 1. Setup LLM Client via factory
    llm_client = create_llm_client(args.llm)

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

    # Choose mutator based on backend
    is_mock = (args.llm == "mock")
    evaluator = LLMEvaluator(llm_client)
    if is_mock:
        mutation_op = SimpleFieldMutator()
    else:
        logger.info("Using LLM-based Evaluator and Mutator")
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
        seeds = None

        # Try LLM-generated seeds first
        if args.generate_seeds:
            seeds = await generate_seed_personas_async(llm_client, args.pop_size)

        # Fall back to seed file
        if seeds is None:
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

    # 6. Run Evolution (async)
    logger.info("Starting Evolution Loop")
    await engine.run_evolution_loop_async()
    logger.info("Evolution Complete!")
    logger.info(f"Stats saved to {store.storage_dir}/generation_stats.jsonl")

    # 7. Generate Visualisation Report
    if not args.no_viz:
        logger.info("Generating visualisation report...")
        from snackPersona.visualization.report import generate_report
        plots = generate_report(store.storage_dir)
        if plots:
            logger.info(f"Plots saved to {store.storage_dir}/plots/")
        else:
            logger.warning("No plots generated (insufficient data)")


def main():
    """Sync entry point."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
