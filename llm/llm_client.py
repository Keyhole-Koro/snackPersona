"""
Abstract LLM client and concrete backends (OpenAI, Bedrock).

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
