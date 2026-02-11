from typing import List, Dict, Optional
import random
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

    def run_episode(self, rounds: int = 3, topic: str = "AI Technology") -> List[Dict]:
        """
        Runs a simulation episode with persona-driven engagement.

        Flow:
          1. All agents post from their interests
          2. For each round, each agent sees the feed and decides
             whether to engage (based on their persona). Only agents
             who decide "yes" generate a reply.

        Returns:
            A transcript of events.
        """
        transcript = []

        # Phase 1: All agents post
        logger.info(f"[Episode] Phase 1: {len(self.agents)} agents posting on '{topic}'")
        for agent in self.agents:
            post = agent.generate_post(topic=topic)
            event = {
                "type": "post",
                "author": agent.genotype.name,
                "content": post
            }
            self.feed.append(event)
            transcript.append(event)
            logger.debug(f"  {agent.genotype.name} posted ({len(post)} chars)")

        # Phase 2: Engagement rounds — each agent decides whether to reply
        for round_num in range(rounds):
            if not self.feed:
                break

            logger.info(f"[Episode] Phase 2, Round {round_num + 1}/{rounds}")

            # Shuffle agents so order varies each round
            shuffled_agents = self.agents.copy()
            random.shuffle(shuffled_agents)

            for agent in shuffled_agents:
                # Pick a random post to consider (not by this agent)
                candidates = [p for p in self.feed if p['author'] != agent.genotype.name]
                if not candidates:
                    candidates = self.feed
                target_post = random.choice(candidates)

                # Agent decides whether to engage
                engaged = agent.should_engage(
                    target_post['content'], target_post['author']
                )

                if not engaged:
                    event = {
                        "type": "pass",
                        "author": agent.genotype.name,
                        "target_author": target_post['author'],
                    }
                    transcript.append(event)
                    continue

                # Agent replies
                reply = agent.generate_reply(
                    target_post['content'], target_post['author']
                )
                event = {
                    "type": "reply",
                    "author": agent.genotype.name,
                    "target_author": target_post['author'],
                    "content": reply,
                    "reply_to": target_post['content']
                }
                transcript.append(event)
                self.feed.append(event)

        return transcript

    def run_media_episode(self, media_item: MediaItem, rounds: int = 2) -> List[Dict]:
        """
        Runs a simulation episode where agents react to a media item,
        then engage with each other's reactions based on persona.
        """
        transcript = []

        # Phase 1: All agents react to the media
        logger.info(f"[MediaEp] All agents reacting to '{media_item.title}'")
        for agent in self.agents:
            reaction = agent.generate_media_reaction(media_item)
            event = {
                "type": "media_reaction",
                "author": agent.genotype.name,
                "content": reaction,
                "media_id": media_item.id,
                "media_title": media_item.title
            }
            self.feed.append(event)
            transcript.append(event)

        # Phase 2: Persona-driven engagement on reactions
        for round_num in range(rounds):
            if not self.feed:
                break

            logger.info(f"[MediaEp] Discussion round {round_num + 1}/{rounds}")

            shuffled_agents = self.agents.copy()
            random.shuffle(shuffled_agents)

            for agent in shuffled_agents:
                candidates = [p for p in self.feed if p['author'] != agent.genotype.name]
                if not candidates:
                    candidates = self.feed
                target_post = random.choice(candidates)

                engaged = agent.should_engage(
                    target_post['content'], target_post['author']
                )

                if not engaged:
                    transcript.append({
                        "type": "pass",
                        "author": agent.genotype.name,
                        "target_author": target_post['author'],
                    })
                    continue

                reply = agent.generate_reply(
                    target_post['content'], target_post['author']
                )
                event = {
                    "type": "reply",
                    "author": agent.genotype.name,
                    "target_author": target_post['author'],
                    "content": reply,
                    "reply_to": target_post['content']
                }
                transcript.append(event)
                self.feed.append(event)

        return transcript

    def clear_feed(self):
        self.feed = []
        for agent in self.agents:
            agent.reset_memory()
