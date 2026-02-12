from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import random
import json
import os
from snackPersona.utils.data_models import PersonaGenotype
from snackPersona.llm.llm_client import LLMClient
from snackPersona.utils.logger import logger

# Default path for mutation pools
_POOLS_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'mutation_pools.json')
_pools_cache: Optional[Dict] = None


def _load_pools() -> Dict:
    """Load mutation value pools from JSON, with caching."""
    global _pools_cache
    if _pools_cache is None:
        path = os.path.normpath(_POOLS_PATH)
        if os.path.exists(path):
            with open(path) as f:
                _pools_cache = json.load(f)
        else:
            logger.warning(f"Mutation pools not found at {path}, using empty pools")
            _pools_cache = {}
    return _pools_cache


class MutationOperator(ABC):
    @abstractmethod
    def mutate(self, genotype: PersonaGenotype) -> PersonaGenotype:
        pass


class SimpleFieldMutator(MutationOperator):
    """
    Mutates genotype fields using curated value pools and perturbation.
    
    Mutation strategies:
      - trait_perturb: adjust a personality_trait float by ±delta
      - list_swap: remove a random item from a list field, add one from pool
      - style_replace: replace communication_style or topical_focus from pool
      - age_shift: shift age by ±1‥5, clamped to [18, 80]
      - backstory_event: append a random life event to backstory
    """

    def mutate(self, genotype: PersonaGenotype) -> PersonaGenotype:
        new = genotype.model_copy(deep=True)
        pools = _load_pools()

        # Pick 1-2 mutation strategies to apply
        strategies = random.sample(
            ['trait_perturb', 'list_swap', 'style_replace', 'age_shift', 'backstory_event'],
            k=random.choice([1, 2])
        )

        for strategy in strategies:
            if strategy == 'trait_perturb':
                new = self._trait_perturb(new)
            elif strategy == 'list_swap':
                new = self._list_swap(new, pools)
            elif strategy == 'style_replace':
                new = self._style_replace(new, pools)
            elif strategy == 'age_shift':
                new = self._age_shift(new)
            elif strategy == 'backstory_event':
                new = self._backstory_event(new, pools)

        logger.debug(f"Mutated {genotype.name} with strategies: {strategies}")
        return new

    @staticmethod
    def _trait_perturb(g: PersonaGenotype) -> PersonaGenotype:
        """Perturb a random personality trait by ±0.15."""
        if not g.personality_traits:
            return g
        key = random.choice(list(g.personality_traits.keys()))
        delta = random.uniform(-0.15, 0.15)
        new_val = max(0.0, min(1.0, g.personality_traits[key] + delta))
        g.personality_traits[key] = round(new_val, 3)
        return g

    @staticmethod
    def _list_swap(g: PersonaGenotype, pools: Dict) -> PersonaGenotype:
        """Remove a random item from a list field, add one from the pool."""
        field_pool_map = {
            'hobbies': 'hobbies',
            'core_values': 'core_values',
            'goals': 'core_values',  # no dedicated goals pool, reuse values
        }
        field = random.choice(list(field_pool_map.keys()))
        current: List[str] = getattr(g, field)
        pool_key = field_pool_map[field]
        pool = pools.get(pool_key, [])

        if current and len(current) > 1:
            current.remove(random.choice(current))
        if pool:
            candidates = [v for v in pool if v not in current]
            if candidates:
                current.append(random.choice(candidates))
        setattr(g, field, current)
        return g

    @staticmethod
    def _style_replace(g: PersonaGenotype, pools: Dict) -> PersonaGenotype:
        """Replace communication_style or topical_focus from pool."""
        if random.random() < 0.5:
            styles = pools.get('communication_styles', [])
            if styles:
                g.communication_style = random.choice(styles)
        else:
            topics = pools.get('topical_focuses', [])
            if topics:
                g.topical_focus = random.choice(topics)
        return g

    @staticmethod
    def _age_shift(g: PersonaGenotype) -> PersonaGenotype:
        """Shift age by ±1..5, clamped to [18, 80]."""
        delta = random.randint(1, 5) * random.choice([-1, 1])
        g.age = max(18, min(80, g.age + delta))
        return g

    @staticmethod
    def _backstory_event(g: PersonaGenotype, pools: Dict) -> PersonaGenotype:
        """Append a random life event to backstory."""
        events = pools.get('life_events', [])
        if events:
            event = random.choice(events)
            g.backstory = g.backstory.rstrip('.') + '. ' + event
        return g


class LLMMutator(MutationOperator):
    """
    Uses an LLM to mutate the persona in meaningful ways.
    Falls back to SimpleFieldMutator on failure.
    """
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def mutate(self, genotype: PersonaGenotype) -> PersonaGenotype:
        user_prompt = f"""
        Mutate the following persona genotype to create a slightly different variation.
        You MUST give the persona a completely new, unique first name.
        Maintain the core identity but change one or two aspects (e.g. valid hobbies, or a slight shift in values).
        
        Original JSON:
        {genotype.model_dump_json()}
        
        Return ONLY valid JSON of the new PersonaGenotype.
        """
        
        response = self.llm_client.generate_text("You are a genetic algorithm mutation operator.", user_prompt)
        
        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
                
            data = json.loads(response.strip())
            return PersonaGenotype(**data)
        except Exception:
            logger.warning(f"LLMMutator failed for {genotype.name}, falling back to SimpleFieldMutator")
            return SimpleFieldMutator().mutate(genotype)


class CrossoverOperator(ABC):
    @abstractmethod
    def crossover(self, parent_a: PersonaGenotype, parent_b: PersonaGenotype) -> PersonaGenotype:
        pass


class MixTraitsCrossover(CrossoverOperator):
    """
    Simple crossover that mixes fields from two parents.
    """
    def crossover(self, parent_a: PersonaGenotype, parent_b: PersonaGenotype) -> PersonaGenotype:
        pools = _load_pools()
        names = pools.get('names', [])

        # Assign a fresh random name from the pool
        name = random.choice(names) if names else f"Child-{random.randint(100,999)}"
        age = parent_a.age if random.random() > 0.5 else parent_b.age
        
        # Mix lists
        goals = list(set(parent_a.goals[:len(parent_a.goals)//2] + parent_b.goals[len(parent_b.goals)//2:]))
        
        return PersonaGenotype(
            name=name,
            age=age,
            occupation=parent_a.occupation,
            backstory=parent_b.backstory,
            core_values=parent_a.core_values,
            hobbies=parent_b.hobbies,
            personality_traits=parent_a.personality_traits,
            communication_style=parent_b.communication_style,
            topical_focus=parent_a.topical_focus,
            interaction_policy=parent_b.interaction_policy,
            goals=goals
        )
