"""
snackPersona.llm — Shared LLM client infrastructure for the snack ecosystem.

Provides abstract and concrete LLM backends (OpenAI, Bedrock, Gemini),
a token-bucket rate limiter, and a preset-based factory.
"""

from snackPersona.llm.llm_client import (
    LLMClient,
    OpenAIClient,
    BedrockClient,
)
from snackPersona.llm.rate_limiter import RateLimiter, NoOpRateLimiter
from snackPersona.llm.llm_factory import create_llm_client, list_presets

__all__ = [
    "LLMClient",
    "OpenAIClient",
    "BedrockClient",
    "RateLimiter",
    "NoOpRateLimiter",
    "create_llm_client",
    "list_presets",
]
