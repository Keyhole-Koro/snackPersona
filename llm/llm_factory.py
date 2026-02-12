"""
Factory for creating LLM client instances from preset configurations.

Reads ``config/llm_presets.json`` and instantiates the correct backend with
the specified model and rate-limiter settings.
"""

import json
import os
from typing import Optional

from snackPersona.llm.llm_client import LLMClient, OpenAIClient, BedrockClient
from snackPersona.llm.rate_limiter import RateLimiter, NoOpRateLimiter
from snackPersona.utils.logger import logger

_PRESETS_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'llm_presets.json')


def _load_presets(path: Optional[str] = None) -> dict:
    """Load preset definitions from JSON."""
    p = os.path.normpath(path or _PRESETS_PATH)
    if not os.path.exists(p):
        raise FileNotFoundError(f"LLM presets file not found: {p}")
    with open(p) as f:
        return json.load(f)


def list_presets(path: Optional[str] = None) -> list[str]:
    """Return a list of available preset names."""
    return list(_load_presets(path).keys())


def create_llm_client(
    preset_name: str,
    presets_path: Optional[str] = None,
) -> LLMClient:
    """
    Create an LLM client from a named preset.

    Parameters
    ----------
    preset_name : str
        Name of the preset (e.g. ``"gemini-flash"``).
    presets_path : str, optional
        Path to a custom presets JSON file.

    Returns
    -------
    LLMClient
        Configured client instance.
    """
    presets = _load_presets(presets_path)
    if preset_name not in presets:
        available = ', '.join(presets.keys())
        raise ValueError(
            f"Unknown LLM preset '{preset_name}'. Available: {available}"
        )

    cfg = presets[preset_name]
    backend = cfg["backend"]
    model = cfg.get("model")
    rl_cfg = cfg.get("rate_limit", {})

    # Build rate limiter
    if rl_cfg:
        rate_limiter = RateLimiter(
            requests_per_minute=rl_cfg.get("requests_per_minute", 60),
            tokens_per_minute=rl_cfg.get("tokens_per_minute", 150_000),
        )
    else:
        rate_limiter = RateLimiter()

    logger.info(f"Creating LLM client: preset='{preset_name}' backend='{backend}' model='{model}'")

    if backend == "gemini":
        from snackPersona.llm.gemini_client import GeminiClient
        return GeminiClient(model=model, rate_limiter=rate_limiter)

    elif backend == "openai":
        return OpenAIClient(model=model, rate_limiter=rate_limiter)

    elif backend == "bedrock":
        return BedrockClient(model=model, rate_limiter=rate_limiter)

    else:
        raise ValueError(f"Unknown backend '{backend}' in preset '{preset_name}'")
