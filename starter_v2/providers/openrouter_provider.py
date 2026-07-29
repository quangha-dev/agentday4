from __future__ import annotations

import os

from providers.rotating_openai_provider import RotatingOpenAIProvider


class OpenRouterProvider(RotatingOpenAIProvider):
    """OpenRouter endpoint with quota-aware comma/numbered key rotation."""

    def __init__(self) -> None:
        super().__init__(
            api_key_env="OPENROUTER_API_KEY",
            combined_key_env="OPENROUTER_API_KEYS",
            numbered_key_prefix="OPENROUTER_API_KEY_",
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            default_model=os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
        )
