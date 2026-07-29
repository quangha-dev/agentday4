from __future__ import annotations

import os
import re
import threading
from typing import Any, Callable, Iterable

from providers.base import ModelResponse
from providers.openai_provider import OpenAIProvider


def split_key_values(value: str) -> list[str]:
    """Parse comma/semicolon/whitespace-separated secrets without logging them."""
    return [part for part in re.split(r"[,;\s]+", value or "") if part]


class RotatingOpenAIProvider(OpenAIProvider):
    """OpenAI-compatible provider with quota-only credential failover."""

    _cursor = 0
    _cursor_lock = threading.Lock()

    def __init__(
        self,
        *,
        api_key_env: str,
        combined_key_env: str,
        numbered_key_prefix: str,
        base_url: str,
        default_model: str,
        extra_keys: Iterable[str] = (),
        key_filter: Callable[[str], bool] | None = None,
    ) -> None:
        super().__init__(api_key_env=api_key_env, base_url=base_url, default_model=default_model)
        candidates: list[str] = []
        candidates.extend(split_key_values(os.getenv(api_key_env, "")))
        candidates.extend(split_key_values(os.getenv(combined_key_env, "")))

        numbered: list[tuple[int, str]] = []
        for name, value in os.environ.items():
            match = re.fullmatch(re.escape(numbered_key_prefix) + r"(\d+)", name)
            if match:
                numbered.extend((int(match.group(1)), item) for item in split_key_values(value))
        candidates.extend(value for _, value in sorted(numbered))
        candidates.extend(item for value in extra_keys for item in split_key_values(value))
        if key_filter:
            candidates = [item for item in candidates if key_filter(item)]

        self._keys = list(dict.fromkeys(candidates))
        self.key_count = len(self._keys)
        self.last_key_slot: int | None = None
        self.rotation_count = 0

    @staticmethod
    def _is_quota_error(exc: Exception) -> bool:
        status_code = getattr(exc, "status_code", None)
        response = getattr(exc, "response", None)
        if status_code is None and response is not None:
            status_code = getattr(response, "status_code", None)
        if status_code == 429:
            return True
        safe_text = str(exc).casefold()
        return any(
            marker in safe_text
            for marker in (
                "rate limit",
                "rate_limit",
                "quota",
                "resource exhausted",
                "resource_exhausted",
                "too many requests",
            )
        )

    @classmethod
    def _starting_slot(cls, key_count: int) -> int:
        with cls._cursor_lock:
            return cls._cursor % key_count

    @classmethod
    def _remember_slot(cls, slot: int) -> None:
        with cls._cursor_lock:
            cls._cursor = slot

    def complete(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        *,
        model: str | None = None,
        temperature: float = 0.0,
        tool_choice: Any | None = None,
    ) -> ModelResponse:
        if not self._keys:
            raise RuntimeError(f"Missing API key pool for {self.api_key_env}")

        start = self._starting_slot(len(self._keys))
        last_quota_error: Exception | None = None
        for offset in range(len(self._keys)):
            slot = (start + offset) % len(self._keys)
            try:
                result = self._complete_with_api_key(
                    self._keys[slot],
                    messages,
                    tools,
                    model=model,
                    temperature=temperature,
                    tool_choice=tool_choice,
                )
                self.last_key_slot = slot + 1
                self._remember_slot(slot)
                return result
            except Exception as exc:
                if not self._is_quota_error(exc):
                    raise
                last_quota_error = exc
                self.rotation_count += 1
                self._remember_slot((slot + 1) % len(self._keys))

        assert last_quota_error is not None
        raise last_quota_error
