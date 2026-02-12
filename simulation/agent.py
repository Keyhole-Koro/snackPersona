"""
SimulationAgent — wraps a persona genotype + LLM client for SNS simulation.
"""
import random
from typing import Optional
from snackPersona.utils.data_models import PersonaGenotype, MediaItem
from snackPersona.llm.llm_client import LLMClient
from snackPersona.compiler.compiler import compile_persona
from snackPersona.utils.logger import logger


class SimulationAgent:
    """An agent that participates in simulated SNS episodes."""

    def __init__(self, genotype: PersonaGenotype, llm_client: LLMClient):
        self.genotype = genotype
        self.llm_client = llm_client
        self.phenotype = compile_persona(genotype)
        self._system_prompt = self.phenotype.system_prompt
        self.memory: list = []

    # ------------------------------------------------------------------ #
    #  Synchronous methods
    # ------------------------------------------------------------------ #

    # ------------------------------------------------------------------ #
    #  Synchronous methods
    # ------------------------------------------------------------------ #

    def generate_post(self, topic: str = None) -> str:
        """Generate a new social media post, optionally guided by a topic."""
        # Step 1: Brainstorm
        brainstorm_prompt = (
            f"You are planning a new post.\n"
            f"Context: {topic if topic else 'General thoughts'}.\n\n"
            f"Brainstorm 3 distinct angles or headlines for a post. "
            f"Return ONLY a JSON list of strings, e.g. [\"Angle 1\", \"Angle 2\"]."
        )
        try:
            ideas_json = self.llm_client.generate_text(
                system_prompt=self._system_prompt,
                user_prompt=brainstorm_prompt,
                temperature=0.9
            )
            # Simple parsing cleanup
            if "```" in ideas_json:
                ideas_json = ideas_json.split("```json")[-1].split("```")[0]
            ideas_str = ideas_json.strip()
            # If not valid JSON-like, fall back to simple text
            if not ideas_str.startswith("["):
                logger.warning(f"Brainstorming failed JSON parsing: {ideas_str[:50]}")
                ideas_str = "General post idea"
        except Exception as e:
            logger.warning(f"Brainstorming failed: {e}")
            ideas_str = "General post idea"

        # Step 2: Select and Write
        user_prompt = (
            f"Here are your brainstormed ideas for a new post:\n{ideas_str}\n\n"
            f"Select the one that best fits your character and current mood.\n"
            f"Write the final post text based on that idea.\n"
            f"Output ONLY the post text."
        )

        response = self.llm_client.generate_text(
            system_prompt=self._system_prompt,
            user_prompt=user_prompt,
        )

        self.memory.append({"role": "assistant", "content": response})
        logger.debug(f"[POST] {self.genotype.name}: {response[:60]}...")
        return response

    def generate_reply(self, post_content: str, author_name: str) -> str:
        """Generate a reply to another agent's post."""
        # Step 1: Brainstorm strategies
        brainstorm_prompt = (
            f"{author_name} posted: \"{post_content}\"\n\n"
            f"Brainstorm 3 distinct strategies for replying (e.g. 'Wholeheartedly agree', 'Challenge the premise', 'Make a joke').\n"
            f"Return ONLY a JSON list of strings."
        )
        try:
            strategies_json = self.llm_client.generate_text(
                system_prompt=self._system_prompt,
                user_prompt=brainstorm_prompt,
                temperature=0.9
            )
            if "```" in strategies_json:
                strategies_json = strategies_json.split("```json")[-1].split("```")[0]
            strategies_str = strategies_json.strip()
            if not strategies_str.startswith("["):
                 strategies_str = "Reply naturally"
        except Exception:
             strategies_str = "Reply naturally"

        # Step 2: Select and Write
        user_prompt = (
            f"Target post: \"{post_content}\"\n"
            f"You considered these reply strategies:\n{strategies_str}\n\n"
            f"Select the best one for your character.\n"
            f"Write the final reply text. Output ONLY the reply."
        )
        response = self.llm_client.generate_text(
            system_prompt=self._system_prompt,
            user_prompt=user_prompt,
        )
        self.memory.append({"role": "assistant", "content": response})
        logger.debug(f"[REPLY] {self.genotype.name} -> {author_name}: {response[:60]}...")
        return response

    def should_engage(self, post_content: str, author_name: str) -> bool:
        """Decide whether this persona would reply to a given post."""
        user_prompt = (
            f"{author_name} posted: \"{post_content}\"\n\n"
            f"Would you reply to this post? "
            f"Answer only 'yes' or 'no'."
        )
        response = self.llm_client.generate_text(
            system_prompt=self._system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
        )
        decision = "yes" in response.lower()
        logger.debug(
            f"[DECIDE] {self.genotype.name} on {author_name}'s post: "
            f"{'ENGAGE' if decision else 'PASS'}"
        )
        return decision

    def generate_media_reaction(self, media_item: MediaItem) -> str:
        """Generate a reaction to a media article."""
        user_prompt = (
            f"You just read this article:\n"
            f"Title: {media_item.title}\n"
            f"Content: {media_item.content[:500]}\n\n"
            f"Write your reaction as a post."
        )
        response = self.llm_client.generate_text(
            system_prompt=self._system_prompt,
            user_prompt=user_prompt,
        )
        self.memory.append({"role": "assistant", "content": response})
        logger.debug(f"[MEDIA] {self.genotype.name} on '{media_item.title}': {response[:60]}...")
        return response

    # ------------------------------------------------------------------ #
    #  Async methods
    # ------------------------------------------------------------------ #

    async def generate_post_async(self, topic: str = None) -> str:
        """Async version of generate_post with brainstorming."""
        # Step 1: Brainstorm
        brainstorm_prompt = (
            f"You are planning a new post.\n"
            f"Context: {topic if topic else 'General thoughts'}.\n\n"
            f"Brainstorm 3 distinct angles or headlines for a post. "
            f"Return ONLY a JSON list of strings, e.g. [\"Angle 1\", \"Angle 2\"]."
        )
        try:
            ideas_json = await self.llm_client.generate_text_async(
                system_prompt=self._system_prompt,
                user_prompt=brainstorm_prompt,
                temperature=0.9
            )
            if "```" in ideas_json:
                ideas_json = ideas_json.split("```json")[-1].split("```")[0]
            ideas_str = ideas_json.strip()
            if not ideas_str.startswith("["):
                logger.warning(f"Brainstorming failed JSON parsing: {ideas_str[:50]}")
                ideas_str = "General post idea"
        except Exception as e:
            logger.warning(f"Brainstorming failed: {e}")
            ideas_str = "General post idea"

        # Step 2: Select and Write
        user_prompt = (
            f"Here are your brainstormed ideas for a new post:\n{ideas_str}\n\n"
            f"Select the one that best fits your character and current mood.\n"
            f"Write the final post text based on that idea.\n"
            f"Output ONLY the post text."
        )

        response = await self.llm_client.generate_text_async(
            system_prompt=self._system_prompt,
            user_prompt=user_prompt,
        )
        self.memory.append({"role": "assistant", "content": response})
        logger.debug(f"[POST] {self.genotype.name}: {response[:60]}...")
        return response

    async def generate_reply_async(self, post_content: str, author_name: str) -> str:
        """Async version of generate_reply with brainstorming."""
        # Step 1: Brainstorm strategies
        brainstorm_prompt = (
            f"{author_name} posted: \"{post_content}\"\n\n"
            f"Brainstorm 3 distinct strategies for replying (e.g. 'Wholeheartedly agree', 'Challenge the premise', 'Make a joke').\n"
            f"Return ONLY a JSON list of strings."
        )
        try:
            strategies_json = await self.llm_client.generate_text_async(
                system_prompt=self._system_prompt,
                user_prompt=brainstorm_prompt,
                temperature=0.9
            )
            if "```" in strategies_json:
                strategies_json = strategies_json.split("```json")[-1].split("```")[0]
            strategies_str = strategies_json.strip()
            if not strategies_str.startswith("["):
                 strategies_str = "Reply naturally"
        except Exception:
             strategies_str = "Reply naturally"

        # Step 2: Select and Write
        user_prompt = (
            f"Target post: \"{post_content}\"\n"
            f"You considered these reply strategies:\n{strategies_str}\n\n"
            f"Select the best one for your character.\n"
            f"Write the final reply text. Output ONLY the reply."
        )
        response = await self.llm_client.generate_text_async(
            system_prompt=self._system_prompt,
            user_prompt=user_prompt,
        )
        self.memory.append({"role": "assistant", "content": response})
        logger.debug(f"[REPLY] {self.genotype.name} -> {author_name}: {response[:60]}...")
        return response

    async def should_engage_async(self, post_content: str, author_name: str) -> bool:
        """Async version of should_engage."""
        user_prompt = (
            f"{author_name} posted: \"{post_content}\"\n\n"
            f"Would you reply to this post? "
            f"Answer only 'yes' or 'no'."
        )
        response = await self.llm_client.generate_text_async(
            system_prompt=self._system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
        )
        decision = "yes" in response.lower()
        logger.debug(
            f"[DECIDE] {self.genotype.name} on {author_name}'s post: "
            f"{'ENGAGE' if decision else 'PASS'}"
        )
        return decision

    async def generate_media_reaction_async(self, media_item: MediaItem) -> str:
        """Async version of generate_media_reaction."""
        user_prompt = (
            f"You just read this article:\n"
            f"Title: {media_item.title}\n"
            f"Content: {media_item.content[:500]}\n\n"
            f"Write your reaction as a post."
        )
        response = await self.llm_client.generate_text_async(
            system_prompt=self._system_prompt,
            user_prompt=user_prompt,
        )
        self.memory.append({"role": "assistant", "content": response})
        logger.debug(f"[MEDIA] {self.genotype.name} on '{media_item.title}': {response[:60]}...")
        return response
