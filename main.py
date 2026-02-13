"""
Entry point for the evolutionary persona prompt generation system.

Usage examples::



    # Gemini Flash
    export GEMINI_API_KEY="..."
    python -m snackPersona.main --llm gemini-flash --generations 5 --pop_size 8

    # Generate seed personas via LLM
    python -m snackPersona.main --llm gemini-3-flash --generate-seeds --generations 5

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
from snackPersona.orchestrator.operators import LLMMutator, LLMCrossover
from snackPersona.orchestrator.engine import EvolutionEngine
from snackPersona.utils.media_dataset import MediaDataset
from snackPersona.utils.logger import logger


def create_seed_population() -> List[PersonaGenotype]:
    """
    Creates a small set of seed personas to start evolution.
    Uses free-form bio text in a narrative, human style.
    """
    return [
    return [
        PersonaGenotype(
            name="Alice_Wanders",
            bio="I used to be a corporate lawyer in Chicago, billing 80 hours a week and convincing myself I loved the grind. Then I had a panic attack in a Sweetgreen and bought a one-way ticket to a coastal town in Oregon. Now I paint bad watercolors of the ocean, drink too much cheap wine, and complain about the humidity. I miss the paycheck, but I don't miss the meetings. I'm just here to find people who understand why I left."
        ),
        PersonaGenotype(
            name="Tech_Bro_Bob",
            bio="Current location: Seoul. Next week: probably Bali. I'm a digital nomad living out of a carry-on, coding backend systems at 3 AM while everyone else parties. I'm obsessed with optimizing every aspect of my life—from my sleep cycle to my coffee grind size. Honestly? It gets lonely. I have a thousand followers but haven't had a real conversation in weeks. Looking for connection in a disconnected world."
        ),
        PersonaGenotype(
            name="CharlieTheSkeptic",
            bio="I'm a philosophy Ph.D. candidate who probably reads too much Nietzsche for my own good. I spend my days in dusty libraries questioning the nature of free will and my nights doom-scrolling on this hellsite. I believe AI is probably going to destroy us, yet here I am. I can be intense and argumentative, but deep down, I'm just terrified that nothing actually matters. Let's debate."
        ),
        PersonaGenotype(
            name="Dana_Scoops",
            bio="Investigative journalist for a dying local paper. I've got ink stains on my hands and three cats waiting for me at home. I survive on stale office coffee and the thrill of chasing a lead. I'm cynical about politicians but stubbornly hopeful about communities. If I'm not live-tweeting a city council meeting, I'm probably asleep. I want to tell the stories that actually change things."
        )
    ]


# Default seed file path (relative to package root)
_DEFAULT_SEED_FILE = os.path.join(
    os.path.dirname(__file__), 'config', 'seed_personas.json'
)


def load_seed_population(path: str) -> List[PersonaGenotype]:
    """Load seed personas from a JSON file."""
    with open(path) as f:
        data = json.load(f)
    
    personas = []
    for item in data:
        # Backward compatibility / Migration helper
        if 'attributes' in item and 'bio' not in item:
            # Simple conversion if we encounter old format
            attrs = item.pop('attributes')
            # Create a simple bio from the attributes dump
            bio_parts = []
            for k, v in attrs.items():
                bio_parts.append(f"{k}: {v}")
            item['bio'] = ". ".join(bio_parts)
            
        personas.append(PersonaGenotype(**item))
    logger.info(f"Loaded {len(personas)} seed personas from {path}")
    return personas


async def generate_seed_personas_async(
    llm_client, count: int
) -> Optional[List[PersonaGenotype]]:
    """Ask the LLM to generate diverse seed personas using free-form bios."""
    system_prompt = "You are an expert character designer for social media simulations."
    user_prompt = f"""Generate exactly {count} diverse, unique social media user personas.
Each persona must be a JSON object with these fields:
- name (string): a creative SNS nickname / display name
- bio (string): A detailed, first-person narrative (approx 300-400 characters).
  - Write a micro-story about who they are, where they are in life, and what they care about.
  - Include specific details: their morning routine, a recent failure, a secret ambition, or a recurring annoyance.
  - The tone should be raw, authentic, and human. No resume-speak. No bullet points.

Make them feel like main characters in their own lives.

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
    parser.add_argument("--llm", type=str, default="gemini-flash",
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

    # Always use LLM-based operators
    evaluator = LLMEvaluator(llm_client)
    mutation_op = LLMMutator(llm_client)
    crossover_op = LLMCrossover(llm_client)

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
                logger.warning(f"Seed file not found at {seed_path}, using hardcoded defaults")
                seeds = create_seed_population()

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
