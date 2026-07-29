from unittest.mock import patch

from pydantic import ValidationError

from api import ChatMessage, ChatRequest, agent_artifacts, chat


class FakeProvider:
    default_model = "fake-model"


def test_version_artifacts_are_distinct_and_v2_has_legal_tools() -> None:
    v0_prompt, v0_declarations, _ = agent_artifacts("v0")
    v1_prompt, v1_declarations, _ = agent_artifacts("v1")
    v2_prompt, v2_declarations, _ = agent_artifacts("v2")
    assert v0_prompt != v1_prompt != v2_prompt
    assert {item["name"] for item in v0_declarations} == {item["name"] for item in v1_declarations}
    assert "legal_rag_search" in {item["name"] for item in v2_declarations}
    assert "legal_rag_search" not in {item["name"] for item in v0_declarations}


def test_chat_request_rejects_unknown_version() -> None:
    try:
        ChatRequest(messages=[ChatMessage(role="user", content="xin chào")], artifact_version="v9")
    except ValidationError:
        pass
    else:
        raise AssertionError("Unknown artifact version must be rejected")


def test_chat_returns_requested_version_and_matching_artifact_hash() -> None:
    payload = ChatRequest(
        messages=[ChatMessage(role="user", content="Xin chào")],
        artifact_version="v1",
    )
    fake_result = {
        "status": "answered",
        "assistant_text": "hello",
        "rounds": [],
        "tool_events": [],
        "security": {},
        "execution_plan": {},
    }
    with patch("api.make_provider", return_value=FakeProvider()), patch(
        "api.run_model_tool_loop", return_value=fake_result
    ) as loop:
        result = chat(payload)
    assert result["requested_version"] == "v1"
    assert result["artifact_version"].startswith("v1+")
    assert loop.call_args.kwargs["enforce_runtime_security"] is False
