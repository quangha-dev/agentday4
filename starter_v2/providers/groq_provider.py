from __future__ import annotations

import os

from providers.rotating_openai_provider import RotatingOpenAIProvider, split_key_values


class GroqProvider(RotatingOpenAIProvider):
    """Groq endpoint with quota-aware rotation across all configured gsk keys."""

    def __init__(self) -> None:
        legacy_value = os.getenv("OPENROUTER_API_KEY", "")
        legacy_groq_keys = [item for item in split_key_values(legacy_value) if item.startswith("gsk_")]
        if not os.getenv("GROQ_API_KEY") and legacy_groq_keys:
            # Preserve backward compatibility expected by older local setup while
            # keeping the comma-separated pool parseable in memory.
            os.environ["GROQ_API_KEY"] = ",".join(legacy_groq_keys)
        super().__init__(
            api_key_env="GROQ_API_KEY",
            combined_key_env="GROQ_API_KEYS",
            numbered_key_prefix="GROQ_API_KEY_",
            extra_keys=legacy_groq_keys,
            key_filter=lambda item: item.startswith("gsk_"),
            base_url=os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
            default_model="openai/gpt-oss-120b",
        )
