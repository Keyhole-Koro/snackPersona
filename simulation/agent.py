from snackPersona.utils.data_models import PersonaPhenotype, PersonaGenotype
from snackPersona.llm.llm_client import LLMClient
from snackPersona.compiler.compiler import compile_persona
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
        self.memory: List[Dict[str, str]] = [] # Simple list of messages for now

    def generate_post(self, topic: str = None) -> str:
        """
        Generates a new social media post, optionally guided by a topic.
        """
        user_prompt = "Draft a new post for your followers."
        if topic:
            user_prompt += f" The current trending topic is: {topic}."
            
        # Combine system prompt + policy + user prompt
        full_system = f"{self.phenotype.system_prompt}\n\n{self.phenotype.policy_instructions}"
        
        response = self.llm_client.generate_text(
            system_prompt=full_system,
            user_prompt=user_prompt
        )
        
        # Log to memory (self-action)
        self.memory.append({"role": "assistant", "content": response})
        return response

    def generate_reply(self, post_content: str, author_name: str) -> str:
        """
        Generates a reply to another user's post.
        """
        user_prompt = f"User '{author_name}' posted: \"{post_content}\"\nWrite a reply."
        
        full_system = f"{self.phenotype.system_prompt}\n\n{self.phenotype.policy_instructions}"
        
        response = self.llm_client.generate_text(
            system_prompt=full_system, 
            user_prompt=user_prompt
        )
        
        # Log to memory
        self.memory.append({"role": "user", "content": f"{author_name}: {post_content}"})
        self.memory.append({"role": "assistant", "content": response})
        return response

    def reset_memory(self):
        self.memory = []
