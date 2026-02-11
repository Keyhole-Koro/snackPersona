from typing import List, Dict, Optional
import random
from snackPersona.simulation.agent import SimulationAgent
from snackPersona.utils.data_models import MediaItem

class SimulationEnvironment:
    """
    Manages a group of agents and simulates interactions between them.
    """
    def __init__(self, agents: List[SimulationAgent]):
        self.agents = agents
        self.feed: List[Dict] = [] # Global feed of posts

    def run_episode(self, rounds: int = 3, topic: str = "AI Technology") -> List[Dict]:
        """
        Runs a simulation episode where agents post and reply.
        Returns a transcript of events.
        """
        transcript = []
        
        # 1. Initial posts
        # Select a random subset to be "active posters" this round
        posters = random.sample(self.agents, k=min(len(self.agents), max(1, len(self.agents)//2)))
        
        for agent in posters:
            post = agent.generate_post(topic=topic)
            event = {
                "type": "post",
                "author": agent.genotype.name,
                "content": post
            }
            self.feed.append(event)
            transcript.append(event)
            
        # 2. Reply rounds
        for _ in range(rounds):
            if not self.feed:
                break
                
            # Pick a random post from the feed to reply to
            target_post = random.choice(self.feed)
            
            # Pick a random agent to reply (excluding the author if possible)
            potential_repliers = [a for a in self.agents if a.genotype.name != target_post['author']]
            if not potential_repliers:
                potential_repliers = self.agents
                
            replier = random.choice(potential_repliers)
            reply = replier.generate_reply(target_post['content'], target_post['author'])
            
            event = {
                "type": "reply",
                "author": replier.genotype.name,
                "target_author": target_post['author'],
                "content": reply,
                "reply_to": target_post['content']
            }
            transcript.append(event)
            # Add replies to feed so they can be replied to as well (threading)
            self.feed.append(event) 
            
        return transcript

    def clear_feed(self):
        self.feed = []
        for agent in self.agents:
            agent.reset_memory()
    
    def run_media_episode(self, media_item: MediaItem, rounds: int = 2) -> List[Dict]:
        """
        Runs a simulation episode where agents react to a media item.
        
        Args:
            media_item: The media item (article/content) for agents to react to.
            rounds: Number of interaction rounds after initial reactions.
            
        Returns:
            A transcript of events including initial reactions and subsequent discussions.
        """
        transcript = []
        
        # 1. All agents generate reactions to the media
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
        
        # 2. Reply rounds - agents can discuss each other's reactions
        for _ in range(rounds):
            if not self.feed:
                break
                
            # Pick a random post/reaction from the feed to reply to
            target_post = random.choice(self.feed)
            
            # Pick a random agent to reply (excluding the author if possible)
            potential_repliers = [a for a in self.agents if a.genotype.name != target_post['author']]
            if not potential_repliers:
                potential_repliers = self.agents
                
            replier = random.choice(potential_repliers)
            reply = replier.generate_reply(target_post['content'], target_post['author'])
            
            event = {
                "type": "reply",
                "author": replier.genotype.name,
                "target_author": target_post['author'],
                "content": reply,
                "reply_to": target_post['content']
            }
            transcript.append(event)
            self.feed.append(event)
            
        return transcript
