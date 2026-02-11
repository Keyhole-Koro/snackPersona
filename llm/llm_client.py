from abc import ABC, abstractmethod
from typing import List, Optional, Dict
import os
import random

# For OpenAI
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# For Bedrock (Boto3)
try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    boto3 = None


class LLMClient(ABC):
    """
    Abstract Base Class for LLM Clients.
    Enables switching between Mock, OpenAI, and Bedrock backends.
    """
    @abstractmethod
    def generate_text(self, system_prompt: str, user_prompt: str, model_id: Optional[str] = None, temperature: float = 0.7) -> str:
        """
        Generates text given a system prompt and a user prompt.
        """
        pass


class MockLLMClient(LLMClient):
    """
    Mock LLM Client for testing without incurring costs.
    Returns canned responses based on simple heuristics.
    """
    def generate_text(self, system_prompt: str, user_prompt: str, model_id: Optional[str] = None, temperature: float = 0.7) -> str:
        # Simulate some latency or variation if needed
        if "post" in user_prompt.lower():
            return f"Thinking about {user_prompt[:20]}... engaging post content here."
        elif "reply" in user_prompt.lower():
            return "This is a thoughtful reply to the conversation."
        elif "evaluate" in user_prompt.lower() or "score" in user_prompt.lower():
            # Return a mock JSON-like score
            return '{"coherence": 0.8, "engagement": 0.7, "consistency": 0.9}'
        elif "mutate" in user_prompt.lower():
             return '{"name": "Mutated Persona", "age": 30}' # Mock JSON
        elif "crossover" in user_prompt.lower():
            return '{"name": "Crossover Persona", "age": 25}' # Mock JSON
        else:
            return "Generic Mock LLM Response."


class OpenAIClient(LLMClient):
    """
    Client for OpenAI-compatible APIs (including local models via vLLM/Ollama).
    Requires OPENAI_API_KEY env var.
    """
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        if OpenAI is None:
            raise ImportError("OpenAI library not installed. Please install 'openai'.")
        
        self.client = OpenAI(
            api_key=api_key or os.environ.get("OPENAI_API_KEY"),
            base_url=base_url or os.environ.get("OPENAI_BASE_URL")
        )
        self.default_model = "gpt-4o" # or whatever is appropriate

    def generate_text(self, system_prompt: str, user_prompt: str, model_id: Optional[str] = None, temperature: float = 0.7) -> str:
        model = model_id or self.default_model
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            return ""


class BedrockClient(LLMClient):
    """
    Client for Amazon Bedrock using Boto3.
    """
    def __init__(self, region_name: str = "us-east-1"):
        if boto3 is None:
            raise ImportError("Boto3 library not installed. Please install 'boto3'.")
        
        self.bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name=region_name
        )
        self.default_model = "anthropic.claude-3-sonnet-20240229-v1:0" # Example model ID

    def generate_text(self, system_prompt: str, user_prompt: str, model_id: Optional[str] = None, temperature: float = 0.7) -> str:
        model = model_id or self.default_model
        
        # Bedrock's converse API is the modern standard, or direct model invocation
        # Using Converse API for simplicity if available, else standard invoke.
        # Here we use the Converse API pattern which is cleaner for chat models.
        
        try:
            response = self.bedrock_runtime.converse(
                modelId=model,
                messages=[
                    {
                        "role": "user",
                        "content": [{"text": user_prompt}]
                    }
                ],
                system=[
                    {"text": system_prompt}
                ],
                inferenceConfig={
                    "temperature": temperature
                }
            )
            return response['output']['message']['content'][0]['text']

        except ClientError as e:
            print(f"Error calling Bedrock API: {e}")
            return ""
        except Exception as e:
             # Fallback for models not supporting Converse API or other errors
             print(f"Unexpected error in Bedrock Client: {e}")
             return ""
