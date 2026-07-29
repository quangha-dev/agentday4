from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from providers.base import Provider, ToolCall
from security import blocked_response, inspect_request, sanitize_tool_result, validate_tool_call
from tools import TOOL_FUNCTIONS


@dataclass
class AgentRun:
    text: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    security: dict[str, Any] = field(default_factory=dict)


class ResearchAgent:
    def __init__(
        self,
        provider: Provider,
        *,
        system_prompt: str,
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
    ) -> None:
        self.provider = provider
        self.system_prompt = system_prompt
        self.tools = tools or []
        self.model = model

    def run(self, user_messages: list[dict[str, str]], *, tool_choice: Any | None = None) -> AgentRun:
        latest_user_text = next(
            (message.get("content", "") for message in reversed(user_messages) if message.get("role") == "user"),
            "",
        )
        decision = inspect_request(latest_user_text)
        security = decision.to_dict()
        security.pop("normalized_text", None)
        if not decision.allowed:
            return AgentRun(text=blocked_response(decision), security=security)

        messages = [{"role": "system", "content": self.system_prompt}, *user_messages]
        response = self.provider.complete(
            messages,
            self.tools,
            model=self.model,
            temperature=0.0,
            tool_choice=tool_choice,
        )
        results: list[dict[str, Any]] = []
        for call in response.tool_calls:
            func = TOOL_FUNCTIONS.get(call.name)
            if not func:
                results.append({"tool": call.name, "error": "unknown_tool"})
                continue
            valid, validation_errors = validate_tool_call(call.name, call.args, self.tools)
            if not valid:
                results.append({
                    "tool": call.name,
                    "args": call.args,
                    "result": {"error": "tool_policy_violation", "details": validation_errors},
                })
                continue
            try:
                result = func(**call.args)
            except Exception as exc:  # keep eval robust; failures are evidence
                result = {"error": type(exc).__name__, "message": str(exc)}
            results.append({
                "tool": call.name,
                "args": call.args,
                "result": sanitize_tool_result(result),
            })
        return AgentRun(
            text=response.text,
            tool_calls=response.tool_calls,
            tool_results=results,
            security=security,
        )
