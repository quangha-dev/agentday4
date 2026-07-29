import os
from unittest.mock import patch

from providers import make_provider
from providers.base import ModelResponse
from providers.groq_provider import GroqProvider


class QuotaError(RuntimeError):
    status_code = 429


def test_groq_provider_uses_official_openai_compatible_endpoint() -> None:
    with patch.dict(os.environ, {"GROQ_API_KEY": "gsk_test"}, clear=False):
        provider = make_provider("groq")
    assert provider.api_key_env == "GROQ_API_KEY"
    assert provider.base_url == "https://api.groq.com/openai/v1"
    assert provider.default_model == "openai/gpt-oss-120b"


def test_groq_provider_migrates_misplaced_key_in_memory() -> None:
    with patch.dict(
        os.environ,
        {"OPENROUTER_API_KEY": "gsk_legacy_test", "GROQ_API_KEY": ""},
        clear=False,
    ):
        make_provider("groq")
        assert os.environ["GROQ_API_KEY"] == "gsk_legacy_test"


def test_groq_provider_loads_and_deduplicates_key_pool() -> None:
    env = {
        "GROQ_API_KEY": "gsk_primary",
        "GROQ_API_KEYS": "gsk_second, gsk_primary;gsk_third",
        "GROQ_API_KEY_1": "gsk_fourth",
        "OPENROUTER_API_KEY": "not-a-groq-key",
    }
    with patch.dict(os.environ, env, clear=True):
        provider = GroqProvider()
    assert provider.key_count == 4


def test_groq_provider_splits_comma_separated_primary_and_legacy_values() -> None:
    env = {
        "GROQ_API_KEY": "gsk_first,gsk_second",
        "OPENROUTER_API_KEY": "gsk_second, gsk_third",
    }
    with patch.dict(os.environ, env, clear=True):
        provider = GroqProvider()
    assert provider.key_count == 3


def test_groq_provider_rotates_only_after_quota_error() -> None:
    env = {
        "GROQ_API_KEY": "gsk_first",
        "GROQ_API_KEY_1": "gsk_second",
    }
    attempted: list[str] = []

    def fake_complete(api_key, *_args, **_kwargs):
        attempted.append(api_key)
        if api_key == "gsk_first":
            raise QuotaError("rate_limit_exceeded")
        return ModelResponse(text="OK")

    GroqProvider._cursor = 0
    with patch.dict(os.environ, env, clear=True):
        provider = GroqProvider()
        with patch.object(provider, "_complete_with_api_key", side_effect=fake_complete):
            result = provider.complete([{"role": "user", "content": "ping"}])

    assert result.text == "OK"
    assert attempted == ["gsk_first", "gsk_second"]
    assert provider.rotation_count == 1
    assert provider.last_key_slot == 2


def test_groq_provider_does_not_rotate_on_non_quota_error() -> None:
    env = {
        "GROQ_API_KEY": "gsk_first",
        "GROQ_API_KEY_1": "gsk_second",
    }
    attempted: list[str] = []

    def fake_complete(api_key, *_args, **_kwargs):
        attempted.append(api_key)
        raise RuntimeError("invalid request schema")

    GroqProvider._cursor = 0
    with patch.dict(os.environ, env, clear=True):
        provider = GroqProvider()
        with patch.object(provider, "_complete_with_api_key", side_effect=fake_complete):
            try:
                provider.complete([{"role": "user", "content": "ping"}])
            except RuntimeError as exc:
                assert "invalid request schema" in str(exc)
            else:
                raise AssertionError("Expected non-quota error")

    assert attempted == ["gsk_first"]
    assert provider.rotation_count == 0
