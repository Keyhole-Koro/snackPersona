from abc import ABC, abstractmethod
from typing import List, Tuple
import random
import json
from snackPersona.utils.data_models import PersonaGenotype
from snackPersona.llm.llm_client import LLMClient

class MutationOperator(ABC):
    @abstractmethod
    def mutate(self, genotype: PersonaGenotype) -> PersonaGenotype:
        pass

class SimpleFieldMutator(MutationOperator):
    """
    Mutates a random field by picking from a predefined list or minor perturbation.
    Current implementation is a placeholder that appends " (mutated)" to the name or backstory.
    """
    def mutate(self, genotype: PersonaGenotype) -> PersonaGenotype:
        new_genotype = genotype.model_copy(deep=True)
        
        # Randomly choose a mutation type
        mutation_type = random.choice(["name", "age", "backstory"])
        
        if mutation_type == "name":
            new_genotype.name += " II"
        elif mutation_type == "age":
            new_genotype.age += random.choice([-1, 1])
        elif mutation_type == "backstory":
            new_genotype.backstory += " [Recently changed perspective.]"
            
        return new_genotype

class LLMMutator(MutationOperator):
    """
    Uses an LLM to mutate the persona in meaningful ways.
    """
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def mutate(self, genotype: PersonaGenotype) -> PersonaGenotype:
        user_prompt = f"""
        Mutate the following persona genotype to create a slightly different variation.
        maintain the core identity but change one or two aspects (e.g. valid hobbies, or a slight shift in values).
        
        Original JSON:
        {genotype.model_dump_json()}
        
        Return ONLY valid JSON of the new PersonaGenotype.
        """
        
        response = self.llm_client.generate_text("You are a genetic algorithm mutation operator.", user_prompt)
        
        try:
             # Clean markdown
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
                
            data = json.loads(response.strip())
            return PersonaGenotype(**data)
        except Exception:
            # Fallback to simple mutator if LLM fails
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
        # 50/50 chance for each major field block
        name = parent_a.name if random.random() > 0.5 else parent_b.name
        age = parent_a.age if random.random() > 0.5 else parent_b.age
        
        # Mix lists
        goals = list(set(parent_a.goals[:len(parent_a.goals)//2] + parent_b.goals[len(parent_b.goals)//2:]))
        
        return PersonaGenotype(
            name=name,
            age=age,
            occupation=parent_a.occupation, # Simplify: take A
            backstory=parent_b.backstory,   # Simplify: take B
            core_values=parent_a.core_values,
            hobbies=parent_b.hobbies,
            personality_traits=parent_a.personality_traits,
            communication_style=parent_b.communication_style,
            topical_focus=parent_a.topical_focus,
            interaction_policy=parent_b.interaction_policy,
            goals=goals
        )
