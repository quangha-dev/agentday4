from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

# Active LexFlow ver2 tool registry. Only these functions are exposed to the model.
from .clarify.tool import ask_user
from .legal_rag_search.tool import legal_rag_search
from .resolve_legal_document.tool import resolve_legal_document
from .get_legal_provision.tool import get_legal_provision
from .check_effective_status.tool import check_effective_status
from .compare_legal_versions.tool import compare_legal_versions
from .extract_legal_information.tool import extract_legal_information
from .validate_citation.tool import validate_citation


TOOL_FUNCTIONS = {
    "clarify": ask_user,
    "resolve_legal_document": resolve_legal_document,
    "legal_rag_search": legal_rag_search,
    "get_legal_provision": get_legal_provision,
    "check_effective_status": check_effective_status,
    "compare_legal_versions": compare_legal_versions,
    "extract_legal_information": extract_legal_information,
    "validate_citation": validate_citation,
}


def load_tool_declarations(path: Path) -> list[dict[str, Any]]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))["tools"]


def to_openai_tools(declarations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    for item in declarations:
        parameters = deepcopy(item.get("parameters", {"type": "object", "properties": {}}))
        if parameters.get("type") == "object":
            parameters.setdefault("additionalProperties", False)
        tools.append({
            "type": "function",
            "function": {
                "name": item["name"],
                "description": item.get("description", ""),
                "parameters": parameters,
            },
        })
    return tools

