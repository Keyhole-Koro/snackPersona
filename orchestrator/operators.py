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


class SimpleFieldMutator(MutationOperator):
    """
    Mutates a random field by picking from a predefined list or minor perturbation.
    Works with the flexible attributes structure.
    """
    # Define mutation handlers for different attribute types
    MUTATION_HANDLERS = {
        'name': lambda genotype: setattr(genotype, 'name', genotype.name + " II") or genotype,
        'age': lambda genotype: genotype.attributes.update({'age': genotype.attributes.get('age', 30) + random.choice([-1, 1])}) or genotype,
        'backstory': lambda genotype: genotype.attributes.update({'backstory': genotype.attributes.get('backstory', '') + " [Recently changed perspective.]"}) or genotype,
    }
    
    def mutate(self, genotype: PersonaGenotype) -> PersonaGenotype:
        new_genotype = genotype.model_copy(deep=True)
        attrs = new_genotype.attributes
        
        # Build list of available mutations based on what exists
        available_mutations = ['name']  # name is always available
        for attr_name in ['age', 'backstory']:
            if attr_name in attrs:
                available_mutations.append(attr_name)
        
        # If only name is available and nothing else, still include age/backstory as options
        if len(available_mutations) == 1:
            available_mutations.extend(['age', 'backstory'])
        
        mutation_type = random.choice(available_mutations)
        
        if mutation_type == "name":
            new_genotype.name += " II"
        elif mutation_type == "age":
            attrs['age'] = attrs.get('age', 30) + random.choice([-1, 1])
        elif mutation_type == "backstory":
            attrs['backstory'] = attrs.get('backstory', '') + " [Recently changed perspective.]"
            
        return new_genotype

class LLMMutator(MutationOperator):
    """
    Uses an LLM to mutate the persona in meaningful ways.
    The LLM can now freely modify or add new attributes to the persona.
    """
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def mutate(self, genotype: PersonaGenotype) -> PersonaGenotype:
        user_prompt = f"""
        Mutate the following persona genotype to create a slightly different variation.
        Maintain the core identity but change one or two aspects (e.g. modify hobbies, shift values, or ADD NEW custom attributes).
        
        You can add completely new attribute fields beyond the standard ones if it makes the persona more interesting.
        For example, you could add: "favorite_quote", "pet_peeves", "speaking_accent", "secret_ambition", etc.
        
        Original JSON:
        {genotype.model_dump_json()}
        
        Return ONLY valid JSON with this structure:
        {{
            "name": "...",
            "attributes": {{
                "age": ...,
                "occupation": "...",
                ... (standard and custom fields)
            }}
        }}
        """
        
        response = self.llm_client.generate_text("You are a genetic algorithm mutation operator that creates interesting persona variations.", user_prompt)
        
        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            data = json.loads(response.strip())
            
            # Helper to construct from dict even if attributes are missing in response (robustness)
            name = data.get("name", genotype.name)
            attributes = data.get("attributes", genotype.attributes)
            
            return PersonaGenotype(
                name=name,
                attributes=attributes
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
    Simple crossover that mixes fields from two parents.
    Works with the flexible attributes structure.
    """
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def crossover(self, parent_a: PersonaGenotype, parent_b: PersonaGenotype) -> PersonaGenotype:
        # 50/50 chance for name
        name = parent_a.name if random.random() > 0.5 else parent_b.name
        
        # Mix attributes from both parents
        attrs_a = parent_a.attributes
        attrs_b = parent_b.attributes
        
        # Get all unique keys from both parents
        all_keys = set(attrs_a.keys()) | set(attrs_b.keys())
        
        # For each key, randomly pick from parent A or B (if they have it)
        child_attrs = {}
        for key in all_keys:
            if key in attrs_a and key in attrs_b:
                # Both parents have this attribute, randomly choose one
                child_attrs[key] = attrs_a[key] if random.random() > 0.5 else attrs_b[key]
            elif key in attrs_a:
                # Only parent A has it, maybe include it (70% chance)
                if random.random() > 0.3:
                    child_attrs[key] = attrs_a[key]
            else:
                # Only parent B has it, maybe include it (70% chance)
                if random.random() > 0.3:
                    child_attrs[key] = attrs_b[key]
        
        # Special handling for list attributes - merge them more carefully
        for key in ['goals', 'core_values', 'hobbies']:
            if key in attrs_a and key in attrs_b:
                if isinstance(attrs_a[key], list) and isinstance(attrs_b[key], list):
                    # Take approximately half from each parent, ensuring we don't lose elements
                    list_a = attrs_a[key]
                    list_b = attrs_b[key]
                    mid_a = (len(list_a) + 1) // 2  # Round up to avoid losing elements
                    mid_b = len(list_b) - len(list_b) // 2  # Take the remainder from b
                    merged = list_a[:mid_a] + list_b[mid_b:]
                    child_attrs[key] = list(dict.fromkeys(merged))  # Remove duplicates while preserving order
        
        return PersonaGenotype(
            name=name,
            attributes=child_attrs
        )
