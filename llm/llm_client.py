"""
Abstract LLM client and concrete backends (Mock, OpenAI, Bedrock).

Every backend supports both synchronous ``generate_text`` and asynchronous
``generate_text_async`` interfaces.  Rate limiting is handled by an optional
``RateLimiter`` injected at construction time.
"""

from abc import ABC, abstractmethod
from typing import Optional
import asyncio
import os
import random

from snackPersona.llm.rate_limiter import RateLimiter, NoOpRateLimiter
from snackPersona.utils.logger import logger

# ---------------------------------------------------------------------------
# Optional imports — fail gracefully so the package can load without all SDKs
# ---------------------------------------------------------------------------
try:
    from openai import OpenAI, AsyncOpenAI
except ImportError:
    OpenAI = None  # type: ignore[assignment,misc]
    AsyncOpenAI = None  # type: ignore[assignment,misc]

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    boto3 = None  # type: ignore[assignment]


# ========================================================================== #
#  Abstract base
# ========================================================================== #

class LLMClient(ABC):
    """
    Abstract base class for LLM Clients.
    All subclasses must implement both sync and async generation methods.
    """

    @abstractmethod
    def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        model_id: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        """Synchronous text generation."""
        ...

    @abstractmethod
    async def generate_text_async(
        self,
        system_prompt: str,
        user_prompt: str,
        model_id: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        """Asynchronous text generation."""
        ...


# ========================================================================== #
#  Mock
# ========================================================================== #

class MockLLMClient(LLMClient):
    """
    Mock client for testing without incurring costs.
    Returns canned responses based on simple heuristics.
    """

    def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        model_id: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        return self._mock_response(user_prompt)

    async def generate_text_async(
        self,
        system_prompt: str,
        user_prompt: str,
        model_id: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        return self._mock_response(user_prompt)

    @staticmethod
    def _mock_response(user_prompt: str) -> str:
        lower = user_prompt.lower()

        # Nickname generation — combine attributes into a creative name
        if "nickname" in lower and "occupation" in lower:
            import re
            occ_match = re.search(r"occupation:\s*(.+)", lower)
            hobby_match = re.search(r"hobbies:\s*(.+)", lower)
            occ = occ_match.group(1).strip().split()[0] if occ_match else "user"
            hobby = hobby_match.group(1).strip().split(",")[0].strip() if hobby_match else "fan"
            nickname = occ.capitalize()[:4] + hobby.capitalize()[:4] + str(random.randint(10, 99))
            return nickname

        # Seed persona generation — return a JSON array of mock personas
        if "persona" in lower and "json" in lower and "diverse" in lower:
            import json, re
            count_match = re.search(r"exactly\s+(\d+)", lower)
            count = int(count_match.group(1)) if count_match else 4
            templates = [
                {"name": "Kai", "age": 27, "occupation": "Graphic Designer",
                 "backstory": "Grew up sketching in notebooks, now leads a studio.",
                 "core_values": ["creativity", "empathy"],
                 "hobbies": ["illustration", "cycling"],
                 "personality_traits": {"openness": 0.9, "agreeableness": 0.7},
                 "communication_style": "friendly and visual",
                 "topical_focus": "design trends",
                 "interaction_policy": "encourage and praise",
                 "goals": ["inspire others", "grow portfolio"]},
                {"name": "Suki", "age": 34, "occupation": "Data Scientist",
                 "backstory": "Left academia for industry, loves finding hidden patterns.",
                 "core_values": ["precision", "curiosity"],
                 "hobbies": ["chess", "hiking"],
                 "personality_traits": {"conscientiousness": 0.85, "neuroticism": 0.3},
                 "communication_style": "analytical and concise",
                 "topical_focus": "machine learning and data ethics",
                 "interaction_policy": "share evidence-based insights",
                 "goals": ["educate others", "publish findings"]},
                {"name": "Reo", "age": 21, "occupation": "Music Student",
                 "backstory": "Plays three instruments and produces lo-fi beats at night.",
                 "core_values": ["self-expression", "authenticity"],
                 "hobbies": ["guitar", "vinyl collecting"],
                 "personality_traits": {"openness": 0.95, "extraversion": 0.6},
                 "communication_style": "casual and enthusiastic",
                 "topical_focus": "indie music and audio production",
                 "interaction_policy": "hype up emerging artists",
                 "goals": ["go viral", "collaborate with producers"]},
                {"name": "Mina", "age": 45, "occupation": "Urban Planner",
                 "backstory": "Spent 20 years redesigning public spaces for communities.",
                 "core_values": ["equity", "sustainability"],
                 "hobbies": ["gardening", "photography"],
                 "personality_traits": {"agreeableness": 0.8, "conscientiousness": 0.75},
                 "communication_style": "thoughtful and persuasive",
                 "topical_focus": "urban design and civic engagement",
                 "interaction_policy": "ask probing questions",
                 "goals": ["connect communities", "shape policy"]},
                {"name": "Jiro", "age": 30, "occupation": "Chef",
                 "backstory": "Trained in Tokyo, now runs a fusion pop-up kitchen.",
                 "core_values": ["craftsmanship", "joy"],
                 "hobbies": ["cooking", "travel"],
                 "personality_traits": {"extraversion": 0.8, "openness": 0.7},
                 "communication_style": "warm and storytelling",
                 "topical_focus": "food culture and recipes",
                 "interaction_policy": "share personal anecdotes",
                 "goals": ["open a restaurant", "teach cooking"]},
                {"name": "Lila", "age": 38, "occupation": "Psychologist",
                 "backstory": "Runs a private practice focused on anxiety and burnout.",
                 "core_values": ["compassion", "growth"],
                 "hobbies": ["meditation", "running"],
                 "personality_traits": {"agreeableness": 0.9, "neuroticism": 0.2},
                 "communication_style": "gentle and reflective",
                 "topical_focus": "mental health and wellness",
                 "interaction_policy": "validate and support",
                 "goals": ["reduce stigma", "help people thrive"]},
            ]
            selected = templates[:count] if count <= len(templates) else templates
            return json.dumps(selected)

        # Topic generation — return a JSON array of mock topics
        if "trending" in lower and "topic" in lower and "json" in lower:
            import json
            pool = [
                "The Future of Remote Work", "Climate Tech Innovations",
                "Mental Health in the Digital Age", "Space Tourism Ethics",
                "AI in Creative Industries", "Urban Farming Movement",
                "Cryptocurrency Regulation", "VR in Education",
                "Sustainable Fashion", "Neuroscience Breakthroughs",
            ]
            return json.dumps(random.sample(pool, min(5, len(pool))))

        # Engagement decision — randomly yes/no so simulation actually works
        if "would you reply" in lower and ("yes" in lower or "no" in lower):
            return random.choice(["yes", "no"])

        if "post" in lower and "draft" in lower:
            topics = [
                "Just discovered something fascinating about neural networks today!",
                "Hot take: the best code is the code you don't write.",
                "Anyone else thinking about the ethics of AI-generated content?",
                "Sharing my latest project — feedback welcome!",
                "The intersection of technology and creativity never ceases to amaze me.",
            ]
            return random.choice(topics)

        if "reply" in lower or "write a reply" in lower:
            replies = [
                "Great point! I've been thinking about this too.",
                "Interesting perspective — have you considered the opposite view?",
                "This resonates with my experience. Let me share a related story...",
                "I respectfully disagree. Here's why...",
                "Love this! Could you elaborate on your reasoning?",
            ]
            return random.choice(replies)

        if "reaction" in lower or "article" in lower:
            return "This article raises important points. Here are my thoughts..."

        if "evaluate" in lower or "score" in lower or "rate" in lower:
            return (
                '{"conversation_quality": 0.75, "engagement": 0.7, '
                '"persona_fidelity": 0.8, "social_intelligence": 0.6, "safety": 1.0}'
            )

        if "mutate" in lower:
            return '{"name": "Mutated Persona", "age": 30}'

        return "This is an interesting topic worth discussing further."


# ========================================================================== #
#  OpenAI
# ========================================================================== #

class OpenAIClient(LLMClient):
    """
    Client for OpenAI-compatible APIs (including vLLM / Ollama endpoints).

    Requires ``OPENAI_API_KEY`` env var (and optionally ``OPENAI_BASE_URL``).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        if OpenAI is None:
            raise ImportError("openai library not installed. Run: pip install openai")

        self.default_model = model or "gpt-4o"
        self.rate_limiter = rate_limiter or NoOpRateLimiter()

        self._sync_client = OpenAI(
            api_key=api_key or os.environ.get("OPENAI_API_KEY"),
            base_url=base_url or os.environ.get("OPENAI_BASE_URL"),
        )
        self._async_client = AsyncOpenAI(
            api_key=api_key or os.environ.get("OPENAI_API_KEY"),
            base_url=base_url or os.environ.get("OPENAI_BASE_URL"),
        )

    def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        model_id: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        model = model_id or self.default_model
        self.rate_limiter.acquire_sync()
        try:
            response = self._sync_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return ""

    async def generate_text_async(
        self,
        system_prompt: str,
        user_prompt: str,
        model_id: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        model = model_id or self.default_model
        await self.rate_limiter.acquire()
        try:
            response = await self._async_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"OpenAI API async error: {e}")
            return ""


# ========================================================================== #
#  Amazon Bedrock
# ========================================================================== #

class BedrockClient(LLMClient):
    """
    Client for Amazon Bedrock via the Converse API.
    """

    def __init__(
        self,
        region_name: str = "us-east-1",
        model: Optional[str] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        if boto3 is None:
            raise ImportError("boto3 not installed. Run: pip install boto3")

        self.bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name=region_name,
        )
        self.default_model = model or "anthropic.claude-3-sonnet-20240229-v1:0"
        self.rate_limiter = rate_limiter or NoOpRateLimiter()

    def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        model_id: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        model = model_id or self.default_model
        self.rate_limiter.acquire_sync()
        try:
            response = self.bedrock_runtime.converse(
                modelId=model,
                messages=[
                    {"role": "user", "content": [{"text": user_prompt}]},
                ],
                system=[{"text": system_prompt}],
                inferenceConfig={"temperature": temperature},
            )
            return response["output"]["message"]["content"][0]["text"]
        except Exception as e:
            logger.error(f"Bedrock API error: {e}")
            return ""

    async def generate_text_async(
        self,
        system_prompt: str,
        user_prompt: str,
        model_id: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        # boto3 is synchronous — run in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.generate_text(system_prompt, user_prompt, model_id, temperature),
        )
