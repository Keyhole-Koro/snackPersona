from snackPersona.utils.data_models import PersonaPhenotype, PersonaGenotype, MediaItem
from snackPersona.llm.llm_client import LLMClient
from snackPersona.compiler.compiler import compile_persona
from snackPersona.utils.logger import logger
from typing import List, Dict, Optional


class SimulationAgent:
    """
    Wraps a persona, phenotype, and LLM client into an interactive agent.
    Maintains short-term memory of the current episode (conversation history).
    """
    def __init__(self, genotype: PersonaGenotype, llm_client: LLMClient):
        self.genotype = genotype
        self.phenotype = compile_persona(genotype)
        self.llm_client = llm_client
        self.memory: List[Dict[str, str]] = []

    @property
    def _system_prompt(self) -> str:
        return f"{self.phenotype.system_prompt}\n\n{self.phenotype.policy_instructions}"

    def generate_post(self, topic: str = None) -> str:
        """Generates a new social media post, optionally guided by a topic."""
        user_prompt = "Draft a new post for your followers."
        if topic:
            user_prompt += f" The current trending topic is: {topic}."

        response = self.llm_client.generate_text(
            system_prompt=self._system_prompt,
            user_prompt=user_prompt
        )

        self.memory.append({"role": "assistant", "content": response})
        logger.debug(f"[POST] {self.genotype.name}: {response[:60]}...")
        return response

    def generate_reply(self, post_content: str, author_name: str) -> str:
        """Generates a reply to another user's post."""
        user_prompt = f"User '{author_name}' posted: \"{post_content}\"\nWrite a reply."

        response = self.llm_client.generate_text(
            system_prompt=self._system_prompt,
            user_prompt=user_prompt
        )

        self.memory.append({"role": "user", "content": f"{author_name}: {post_content}"})
        self.memory.append({"role": "assistant", "content": response})
        logger.debug(f"[REPLY] {self.genotype.name} -> {author_name}: {response[:60]}...")
        return response

    def should_engage(self, post_content: str, author_name: str) -> bool:
        """
        Decides whether this persona would engage with a given post.

        Uses the LLM to make a persona-consistent decision.
        For mock LLM: uses keyword heuristics based on topical_focus.
        """
        user_prompt = (
            f"User '{author_name}' posted: \"{post_content}\"\n\n"
            f"Based on your persona, would you reply to this post? "
            f"Consider your interests ({self.genotype.topical_focus}), "
            f"your interaction style ({self.genotype.interaction_policy}), "
            f"and whether this content is relevant to you.\n\n"
            f"Answer with ONLY 'yes' or 'no'."
        )

        response = self.llm_client.generate_text(
            system_prompt=self._system_prompt,
            user_prompt=user_prompt,
            temperature=0.3
        )

        engaged = 'yes' in response.lower()
        logger.debug(
            f"[DECIDE] {self.genotype.name} on {author_name}'s post: "
            f"{'ENGAGE' if engaged else 'PASS'}"
        )
        return engaged

    def generate_media_reaction(self, media_item: MediaItem) -> str:
        """Generates a reaction/post in response to a media item."""
        user_prompt = f"""You are reading an article titled "{media_item.title}".

Article content:
{media_item.content}

Write a post sharing your reaction, thoughts, or commentary on this article."""

        response = self.llm_client.generate_text(
            system_prompt=self._system_prompt,
            user_prompt=user_prompt
        )

        self.memory.append({"role": "user", "content": f"Article: {media_item.title}"})
        self.memory.append({"role": "assistant", "content": response})
        logger.debug(f"[MEDIA] {self.genotype.name} on '{media_item.title}': {response[:60]}...")
        return response

    def reset_memory(self):
        self.memory = []
