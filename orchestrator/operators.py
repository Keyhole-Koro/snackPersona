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
    Mutates a persona's description using an LLM.
    Asks the LLM to alter one or two aspects of the character
    while keeping the overall identity coherent.
    """
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def mutate(self, genotype: PersonaGenotype) -> PersonaGenotype:
        aspect = random.choice([
            "personality or temperament",
            "posting habits or frequency",
            "interests or hobbies",
            "communication tone or style",
            "a quirk or recurring behavior",
            "their backstory or life situation",
            "their social media goals or motivations",
        ])

        user_prompt = f"""Here is an SNS user character description:

Name: {genotype.name}
Description: {genotype.description}

Create a VARIATION of this character by changing their {aspect}.
Keep most of the original character intact but make the change feel natural.
Also give them a new, creative SNS nickname.

Return ONLY valid JSON: {{"name": "...", "description": "..."}}
"""
        response = self.llm_client.generate_text(
            "You are a creative character designer for social media simulations.",
            user_prompt,
        )

        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            data = json.loads(response.strip())
            return PersonaGenotype(
                name=data.get("name", genotype.name),
                description=data.get("description", genotype.description),
            )
        except Exception:
            logger.warning(f"LLMMutator failed for {genotype.name}, applying text perturbation")
            return self._fallback_mutate(genotype)

    @staticmethod
    def _fallback_mutate(genotype: PersonaGenotype) -> PersonaGenotype:
        """Simple fallback: append a random trait modifier to the description."""
        modifiers = [
            "Recently started getting into cooking videos.",
            "Has been posting more late at night recently.",
            "Just discovered a new favorite podcast.",
            "Going through a minimalist phase.",
            "Started working out and won't stop talking about it.",
            "Picked up photography as a hobby.",
            "Became obsessed with a new TV show.",
            "Trying to reduce screen time but failing.",
            "Just got a new pet and posts about it constantly.",
            "Going through a career change.",
        ]
        new_desc = genotype.description.rstrip() + " " + random.choice(modifiers)
        return PersonaGenotype(
            name=genotype.name + str(random.randint(10, 99)),
            description=new_desc,
        )


class CrossoverOperator(ABC):
    @abstractmethod
    def crossover(self, parent_a: PersonaGenotype, parent_b: PersonaGenotype) -> PersonaGenotype:
        pass


class LLMCrossover(CrossoverOperator):
    """
    Merges two persona descriptions into a new character using an LLM.
    Takes elements from both parents to create a coherent new persona.
    """
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def crossover(self, parent_a: PersonaGenotype, parent_b: PersonaGenotype) -> PersonaGenotype:
        user_prompt = f"""Here are two SNS user characters:

**Character A:** {parent_a.name}
{parent_a.description}

**Character B:** {parent_b.name}
{parent_b.description}

Create a NEW character that combines elements from BOTH characters.
Take some traits, habits, or interests from A and some from B.
The result should feel like a natural, coherent person — not a Frankenstein mix.
Give them a fresh, creative SNS nickname.

Return ONLY valid JSON: {{"name": "...", "description": "..."}}
"""
        response = self.llm_client.generate_text(
            "You are a creative character designer for social media simulations.",
            user_prompt,
        )

        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            data = json.loads(response.strip())
            return PersonaGenotype(
                name=data.get("name", f"Mix-{random.randint(100,999)}"),
                description=data.get("description", parent_a.description),
            )
        except Exception:
            logger.warning(
                f"LLMCrossover failed for {parent_a.name} x {parent_b.name}, "
                f"using text splice"
            )
            return self._fallback_crossover(parent_a, parent_b)

    @staticmethod
    def _fallback_crossover(a: PersonaGenotype, b: PersonaGenotype) -> PersonaGenotype:
        """Fallback: take first half of A's description, second half of B's."""
        sentences_a = a.description.split("。")
        sentences_b = b.description.split("。")

        # If Japanese-style splitting didn't work, try period
        if len(sentences_a) <= 1:
            sentences_a = a.description.split(". ")
        if len(sentences_b) <= 1:
            sentences_b = b.description.split(". ")

        mid_a = len(sentences_a) // 2
        mid_b = len(sentences_b) // 2

        # Take first half from A, second half from B
        merged = sentences_a[:max(mid_a, 1)] + sentences_b[max(mid_b, 1):]
        sep = "。" if "。" in a.description else ". "
        description = sep.join(s for s in merged if s.strip())

        return PersonaGenotype(
            name=f"Mix{random.randint(10, 99)}",
            description=description,
        )
