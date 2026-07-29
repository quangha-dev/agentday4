from unittest.mock import patch

from chat import ROOT, run_model_tool_loop
from providers.base import ModelResponse, ToolCall
from tools import load_tool_declarations, to_openai_tools


class RepeatingProvider:
    def complete(self, *_args, **_kwargs):
        return ModelResponse(
            text=None,
            tool_calls=[ToolCall(name="resolve_legal_document", args={"query": "Luật lao động"})],
            raw=None,
        )


def test_identical_tool_calls_use_cache_then_stop() -> None:
    tools = to_openai_tools(load_tool_declarations(ROOT / "artifacts" / "tools.yaml"))
    executions = []

    def fake_resolve(**kwargs):
        executions.append(kwargs)
        return {
            "tool": "resolve_legal_document",
            "ok": True,
            "contract_version": "ver2",
            "count": 0,
            "documents": [],
            "evidence": [],
        }

    with patch("chat.TOOL_FUNCTIONS", {"resolve_legal_document": fake_resolve}):
        result = run_model_tool_loop(
            provider=RepeatingProvider(),
            messages=[{"role": "user", "content": "Tra cứu Luật lao động"}],
            tools=tools,
            model=None,
            max_tool_rounds=6,
        )

    assert result["status"] == "stalled_duplicate_calls"
    assert executions == [{"query": "Luật lao động"}]
    assert [event["cache_hit"] for event in result["tool_events"]] == [False, True, True]
