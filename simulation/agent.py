"""
SimulationAgent — wraps a persona genotype + LLM client for SNS simulation.
"""
import random
from typing import Optional
from snackPersona.utils.data_models import PersonaGenotype, MediaItem
from snackPersona.llm.llm_client import LLMClient
from snackPersona.compiler.compiler import compile_persona
from snackPersona.utils.logger import logger
# Traveler Integration
from snackPersona.traveler.executor.traveler import Traveler
from snackPersona.traveler.utils.data_models import ExecutionResult


class SimulationAgent:
    """An agent that participates in simulated SNS episodes."""

    def __init__(self, genotype: PersonaGenotype, llm_client: LLMClient, traveler: Optional[Traveler] = None):
        self.genotype = genotype
        self.llm_client = llm_client
        self.traveler = traveler
        self.phenotype = compile_persona(genotype)
        self._system_prompt = self.phenotype.system_prompt
        self.memory: list = []

    def reset_memory(self):
        """Clear the agent's short-term memory."""
        self.memory = []

    # ------------------------------------------------------------------ #
    #  Synchronous methods
    # ------------------------------------------------------------------ #

    # ------------------------------------------------------------------ #
    #  Synchronous methods
    # ------------------------------------------------------------------ #

    def generate_post(self, topic: str = None) -> Optional[str]:
        """Generate a new social media post, optionally guided by a topic."""
        # Step 1: Brainstorm
        brainstorm_prompt = (
            f"You are planning a new post.\n"
            f"Context: {topic if topic else 'General thoughts'}.\n\n"
            f"First, decide: Is this topic truly worth your time? Can you add unique value?\n"
            f"If NO, return [\"PASS\"].\n"
            f"If YES, brainstorm 3 distinct angles. Be bold, blunt, and incisive ('moto-mo-ko-mo-nai').\n"
            f"Avoid fluff. Cut to the heart of the matter.\n"
            f"Return ONLY a JSON list of strings, e.g. [\"Angle 1\", \"Angle 2\"] or [\"PASS\"]."
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

        if "PASS" in ideas_str:
            logger.debug(f"[POST] {self.genotype.name} decided to PASS on topic: {topic}")
            return None

        # Step 1.5: Research (Traveler Integration)
        research_context = ""
        if self.traveler and "Angle" in ideas_str: # Only research if we have a concrete idea
            try:
                # Use the chosen angle as a search query hint? 
                # For now, let Traveler generate its own query based on its genome templates.
                logger.info(f"[RESEARCH] {self.genotype.name} is researching topic: {topic}")
                
                # We can optionally inject the topic into the traveler's temporary state,
                # but currently Traveler generates queries based on templates.
                # Ideally, we'd pass the topic to traveler.execute(context=topic)
                # But Traveler.execute() uses self._generate_query().
                # Let's assume for now Traveler finds *something* relevant to its bias.
                
                # NOTE: In a future iteration, we should pass 'topic' to traveler.
                result = self.traveler.execute() 
                
                if result and result.headlines:
                    headlines_str = "\n".join([f"- {h}" for h in result.headlines[:3]])
                    research_context = (
                        f"\n\nYou have just researched this topic and found these headlines:\n"
                        f"{headlines_str}\n"
                        f"Use this information to support your post (or debunk it)."
                    )
            except Exception as e:
                logger.warning(f"Research failed: {e}")

        # Step 2: Select and Write
        user_prompt = (
            f"Here are your brainstormed ideas for a new post:\n{ideas_str}\n"
            f"{research_context}\n\n"
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
            f"Brainstorm 3 distinct strategies for replying.\n"
            f"Don't be afraid to be blunt ('moto-mo-ko-mo-nai') if the post is nonsense.\n"
            f"Strategies could trigger: 'Wholeheartedly agree', 'Challenge premise', 'State uncomfortable truth'.\n"
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
            f"Write your reaction as a post. Be incisive. If the article is fluff, say so.\n"
            f"If it's great, explain why with facts."
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

        # Step 1.5: Research (Async) - Placeholder until Traveler supports async
        # We'll run the sync traveler in an executor or just sync for now since Traveler isn't async yet.
        # But wait, we can't block the async loop.
        # For this iteration, we will SKIP research in async mode OR wrap it.
        # Let's assume we skip it for now to avoid blocking, OR we just let the sync call happen (blocking loop).
        # Given the user wants "Closing the Loop", we better do it.
        
        research_context = ""
        if self.traveler:
            # WARNING: This defaults to blocking call. Ideally Traveler should have execute_async.
            # We will implement execute_async in Traveler later. For now, running sync.
            try:
                # result = await asyncio.to_thread(self.traveler.execute) # Efficient way
                import asyncio
                result = await asyncio.to_thread(self.traveler.execute)
                
                if result and result.headlines:
                    headlines_str = "\n".join([f"- {h}" for h in result.headlines[:3]])
                    research_context = (
                        f"\n\nYou have just researched this topic and found these headlines:\n"
                        f"{headlines_str}\n"
                        f"Use this information to support your post (or debunk it)."
                    )
            except Exception as e:
                logger.warning(f"Async research failed: {e}")

        # Step 2: Select and Write
        user_prompt = (
            f"Here are your brainstormed ideas for a new post:\n{ideas_str}\n"
            f"{research_context}\n\n"
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
