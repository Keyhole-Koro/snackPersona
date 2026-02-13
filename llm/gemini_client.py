"""
Google Gemini API client using the ``google-genai`` SDK.

Requires the ``GEMINI_API_KEY`` environment variable (or pass it directly).
"""

import os
from typing import Optional

from snackPersona.llm.llm_client import LLMClient
from snackPersona.llm.rate_limiter import RateLimiter
from snackPersona.llm.logger import logger

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None  # type: ignore[assignment]
    types = None  # type: ignore[assignment]


class GeminiClient(LLMClient):
    """
    LLM client backed by the Google Gemini API.

    Parameters
    ----------
    api_key : str, optional
        Gemini API key. Falls back to ``GEMINI_API_KEY`` env var
        (and then ``GOOGLE_API_KEY`` for backward compatibility).
    model : str
        Model name (e.g. ``gemini-2.0-flash``).
    rate_limiter : RateLimiter, optional
        Shared rate limiter instance.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.0-flash",
        rate_limiter: Optional[RateLimiter] = None,
    ):
        if genai is None:
            raise ImportError(
                "google-genai is not installed. Run: pip install google-genai"
            )

        resolved_key = (
            api_key
            or os.environ.get("GEMINI_API_KEY", "")
            or os.environ.get("GOOGLE_API_KEY", "")
        )
        if not resolved_key:
            raise ValueError(
                "Gemini API key must be provided via `api_key` arg "
                "or GEMINI_API_KEY environment variable "
                "(GOOGLE_API_KEY is also supported for backward compatibility)."
            )

        self.client = genai.Client(api_key=resolved_key)
        self.default_model = model
        self.rate_limiter = rate_limiter

    def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        model_id: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        model = model_id or self.default_model

        if self.rate_limiter:
            self.rate_limiter.acquire_sync()

        try:
            response = self.client.models.generate_content(
                model=model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=temperature,
                ),
            )
            return response.text or ""
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return ""

    async def generate_text_async(
        self,
        system_prompt: str,
        user_prompt: str,
        model_id: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        model = model_id or self.default_model

        if self.rate_limiter:
            await self.rate_limiter.acquire()

        try:
            response = await self.client.aio.models.generate_content(
                model=model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=temperature,
                ),
            )
            return response.text or ""
        except Exception as e:
            logger.error(f"Gemini API async error: {e}")
            return ""
