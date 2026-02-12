"""
Simulation environment that manages a group of agents and simulates
interactions between them.

Supports both synchronous and asynchronous execution of episodes.
"""

import asyncio
import random
from typing import List, Dict

from snackPersona.simulation.agent import SimulationAgent
from snackPersona.utils.data_models import MediaItem
from snackPersona.utils.logger import logger


class SimulationEnvironment:
    """
    Manages a group of agents and simulates interactions between them.
    """

    def __init__(self, agents: List[SimulationAgent]):
        self.agents = agents
        self.feed: List[Dict] = []

    # ================================================================== #
    #  Async episodes
    # ================================================================== #

    async def run_episode_async(
        self, rounds: int = 3, topic: str = "General"
    ) -> List[Dict]:
        """
        Async simulation episode with persona-driven engagement.

        Flow:
          1. All agents post concurrently
          2. For each round, each agent decides whether to engage
             and generates a reply if so (concurrent per round)
        """
        transcript: List[Dict] = []

        # Phase 1: All agents post concurrently
        logger.info(f"[Episode] Phase 1: {len(self.agents)} agents posting on '{topic}'")

        async def _post(agent: SimulationAgent) -> Dict:
            post = await agent.generate_post_async(topic=topic)
            return {"type": "post", "author": agent.genotype.name, "content": post}

        post_events = await asyncio.gather(*[_post(a) for a in self.agents])

        for event in post_events:
            self.feed.append(event)
            transcript.append(event)
            logger.debug(f"  {event['author']} posted ({len(event['content'])} chars)")

        # Phase 2: Engagement rounds
        for round_num in range(rounds):
            if not self.feed:
                break

            logger.info(f"[Episode] Phase 2, Round {round_num + 1}/{rounds}")

            shuffled_agents = self.agents.copy()
            random.shuffle(shuffled_agents)

            # Each agent's engagement decision + reply can run concurrently
            async def _engage(agent: SimulationAgent) -> List[Dict]:
                events: List[Dict] = []
                candidates = [p for p in self.feed if p['author'] != agent.genotype.name]
                if not candidates:
                    candidates = list(self.feed)
                target_post = random.choice(candidates)

                engaged = await agent.should_engage_async(
                    target_post['content'], target_post['author']
                )

                if not engaged:
                    events.append({
                        "type": "pass",
                        "author": agent.genotype.name,
                        "target_author": target_post['author'],
                    })
                    return events

                reply = await agent.generate_reply_async(
                    target_post['content'], target_post['author']
                )
                event = {
                    "type": "reply",
                    "author": agent.genotype.name,
                    "target_author": target_post['author'],
                    "content": reply,
                    "reply_to": target_post['content'],
                }
                events.append(event)
                return events

            round_results = await asyncio.gather(
                *[_engage(a) for a in shuffled_agents]
            )

            for agent_events in round_results:
                for event in agent_events:
                    transcript.append(event)
                    if event['type'] != 'pass':
                        self.feed.append(event)

        return transcript

    async def run_media_episode_async(
        self, media_item: MediaItem, rounds: int = 2
    ) -> List[Dict]:
        """
        Async episode where agents react to a media item, then engage
        with each other's reactions.
        """
        transcript: List[Dict] = []

        # Phase 1: All agents react concurrently
        logger.info(f"[MediaEp] All agents reacting to '{media_item.title}'")

        async def _react(agent: SimulationAgent) -> Dict:
            reaction = await agent.generate_media_reaction_async(media_item)
            return {
                "type": "media_reaction",
                "author": agent.genotype.name,
                "content": reaction,
                "media_id": media_item.id,
                "media_title": media_item.title,
            }

        reaction_events = await asyncio.gather(*[_react(a) for a in self.agents])

        for event in reaction_events:
            self.feed.append(event)
            transcript.append(event)

        # Phase 2: Persona-driven engagement on reactions
        for round_num in range(rounds):
            if not self.feed:
                break

            logger.info(f"[MediaEp] Discussion round {round_num + 1}/{rounds}")

            shuffled_agents = self.agents.copy()
            random.shuffle(shuffled_agents)

            async def _engage_media(agent: SimulationAgent) -> List[Dict]:
                events: List[Dict] = []
                candidates = [p for p in self.feed if p['author'] != agent.genotype.name]
                if not candidates:
                    candidates = list(self.feed)
                target_post = random.choice(candidates)

                engaged = await agent.should_engage_async(
                    target_post['content'], target_post['author']
                )

                if not engaged:
                    events.append({
                        "type": "pass",
                        "author": agent.genotype.name,
                        "target_author": target_post['author'],
                    })
                    return events

                reply = await agent.generate_reply_async(
                    target_post['content'], target_post['author']
                )
                event = {
                    "type": "reply",
                    "author": agent.genotype.name,
                    "target_author": target_post['author'],
                    "content": reply,
                    "reply_to": target_post['content'],
                }
                events.append(event)
                return events

            round_results = await asyncio.gather(
                *[_engage_media(a) for a in shuffled_agents]
            )

            for agent_events in round_results:
                for event in agent_events:
                    transcript.append(event)
                    if event['type'] != 'pass':
                        self.feed.append(event)

        return transcript

    # ================================================================== #
    #  Sync fallbacks (delegate to async)
    # ================================================================== #

    def run_episode(self, rounds: int = 3, topic: str = "General") -> List[Dict]:
        """Sync wrapper around run_episode_async."""
        return asyncio.run(self.run_episode_async(rounds=rounds, topic=topic))

    def run_media_episode(self, media_item: MediaItem, rounds: int = 2) -> List[Dict]:
        """Sync wrapper around run_media_episode_async."""
        return asyncio.run(self.run_media_episode_async(media_item=media_item, rounds=rounds))

    def clear_feed(self):
        """Reset the shared feed and all agent memories."""
        self.feed = []
        for agent in self.agents:
            agent.reset_memory()
