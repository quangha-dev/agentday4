from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# Folder names are intentionally vague to match the tool names students see.
# The imported function names are the underlying implementations (unchanged).
from .clarify.tool import ask_user
from .papers.tool import arxiv_search
from .paper_text.tool import get_arxiv_paper_text
from .timeline.tool import get_user_tweets
from .fetch.tool import read_url
from .format.tool import render_digest
from .policy.tool import search_company_policy
from .question_guard.tool import audit_question
from .social_search.tool import search_tweets
from .send.tool import send_telegram
from .lookup.tool import web_search


from .legal_rag_search.tool import legal_rag_search
from .get_legal_provision.tool import get_legal_provision
from .check_effective_status.tool import check_effective_status
from .compare_legal_versions.tool import compare_legal_versions
from .extract_legal_information.tool import extract_legal_information
from .validate_citation.tool import validate_citation


# NOTE (starter_v0): tool names here are intentionally vague. These keys are the
# names the model sees AND the names data/eval_base.json + data/eval_research_extension.json
# match against. If a team renames a tool, it MUST stay in sync across ALL of:
#   artifacts/tools.yaml  ->  this dict  ->  data/eval_base.json + data/eval_research_extension.json
# Otherwise the eval raises "not declared in tools.yaml" or scores every call as a name mismatch.
TOOL_FUNCTIONS = {
    "clarify": ask_user,
    "timeline": get_user_tweets,
    "social_search": search_tweets,
    "lookup": web_search,
    "fetch": read_url,
    "format": render_digest,
    "send": send_telegram,
    "policy": search_company_policy,
    "question_guard": audit_question,
    "papers": arxiv_search,
    "paper_text": get_arxiv_paper_text,
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
    return [{
        "type": "function",
        "function": {
            "name": item["name"],
            "description": item.get("description", ""),
            "parameters": item.get("parameters", {"type": "object", "properties": {}}),
        },
    } for item in declarations]

