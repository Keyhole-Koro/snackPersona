"""
Genetic operators for free-form persona descriptions.

Mutation and crossover operate on the description text using the LLM.
"""
from abc import ABC, abstractmethod
import random
import json
from snackPersona.utils.data_models import PersonaGenotype
from snackPersona.llm.llm_client import LLMClient
from snackPersona.utils.logger import logger


class MutationOperator(ABC):
    @abstractmethod
    def mutate(self, genotype: PersonaGenotype) -> PersonaGenotype:
        pass


class LLMMutator(MutationOperator):
    """
    Uses an LLM to mutate the persona bio in meaningful ways.
    """
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def mutate(self, genotype: PersonaGenotype) -> PersonaGenotype:
        user_prompt = f"""
        Mutate the following persona bio to create a fresh variation.
        Maintain the first-person narrative style. 
        Change specific details (e.g. key life events, current job, hobbies, or their specific complaint).
        Make the new story feel authentic and human.
        
        Name: {genotype.name}
        Bio: {genotype.bio}
        
        Return ONLY valid JSON with this structure:
        {{
            "name": "...",
            "bio": "..."
        }}
        """
        
        response = self.llm_client.generate_text("You are a genetic algorithm mutation operator that creates interesting persona variations.", user_prompt)
        
        try:
            text = response
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            data = json.loads(text.strip())
            
            return PersonaGenotype(
                name=data.get("name", genotype.name),
                bio=data.get("bio", genotype.bio)
            )
        except Exception:
            logger.warning(f"LLMMutator failed for {genotype.name}, returning original")
            return genotype


class CrossoverOperator(ABC):
    @abstractmethod
    def crossover(self, parent_a: PersonaGenotype, parent_b: PersonaGenotype) -> PersonaGenotype:
        pass


class LLMCrossover(CrossoverOperator):
    """
    Uses an LLM to mix two persona bios into a coherent child.
    """
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def crossover(self, parent_a: PersonaGenotype, parent_b: PersonaGenotype) -> PersonaGenotype:
        # 50/50 chance for name base, or ask LLM to combine names? simpler to pick one.
        name = parent_a.name if random.random() > 0.5 else parent_b.name
        
        user_prompt = f"""
        Create a new "child" persona bio that combines narrative elements from these two parent bios.
        The child should feel like a distinct person who inherited traits, backstory elements, or "vibe" from both parents.
        Write a short, first-person story (approx 300-400 chars) for this new person.
        
        Parent A ({parent_a.name}): {parent_a.bio}
        Parent B ({parent_b.name}): {parent_b.bio}
        
        Return ONLY valid JSON with this structure:
        {{
            "name": "{name} II", 
            "bio": "..."
        }}
        """
        
        response = self.llm_client.generate_text("You are a genetic algorithm crossover operator.", user_prompt)
        
        try:
            text = response
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            data = json.loads(text.strip())
            
            return PersonaGenotype(
                name=data.get("name", name + " II"),
                bio=data.get("bio", parent_a.bio) # Fallback to parent A if bio missing
            )
        except Exception:
            logger.warning(f"LLMCrossover failed, returning parent A copy")
            return parent_a.model_copy(deep=True)

