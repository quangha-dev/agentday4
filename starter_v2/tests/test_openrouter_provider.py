import os
from unittest.mock import patch

from providers.base import ModelResponse
from providers.openrouter_provider import OpenRouterProvider


class QuotaError(RuntimeError):
    status_code = 429


def test_openrouter_splits_and_deduplicates_key_pool() -> None:
    env = {
        "OPENROUTER_API_KEY": "key_one,key_two",
        "OPENROUTER_API_KEYS": "key_two;key_three",
        "OPENROUTER_API_KEY_1": "key_four",
    }
    with patch.dict(os.environ, env, clear=True):
        provider = OpenRouterProvider()
    assert provider.key_count == 4


def test_openrouter_rotates_on_quota() -> None:
    attempted: list[str] = []

    def fake_complete(api_key, *_args, **_kwargs):
        attempted.append(api_key)
        if api_key == "key_one":
            raise QuotaError("quota exceeded")
        return ModelResponse(text="OK")

    OpenRouterProvider._cursor = 0
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "key_one,key_two"}, clear=True):
        provider = OpenRouterProvider()
        with patch.object(provider, "_complete_with_api_key", side_effect=fake_complete):
            result = provider.complete([{"role": "user", "content": "ping"}])

    assert result.text == "OK"
    assert attempted == ["key_one", "key_two"]
    assert provider.last_key_slot == 2


def test_openrouter_stops_on_authentication_or_schema_error() -> None:
    attempted: list[str] = []

    def fake_complete(api_key, *_args, **_kwargs):
        attempted.append(api_key)
        raise RuntimeError("invalid api key")

    OpenRouterProvider._cursor = 0
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "key_one,key_two"}, clear=True):
        provider = OpenRouterProvider()
        with patch.object(provider, "_complete_with_api_key", side_effect=fake_complete):
            try:
                provider.complete([{"role": "user", "content": "ping"}])
            except RuntimeError as exc:
                assert "invalid api key" in str(exc)
            else:
                raise AssertionError("Expected non-quota error")
    assert attempted == ["key_one"]
