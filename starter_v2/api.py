from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from chat import ROOT, run_model_tool_loop, runtime_context_message
from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version

load_lab_env(ROOT)

PROMPT_PATH = ROOT / "artifacts" / "system_prompt.md"
TOOLS_PATH = ROOT / "artifacts" / "tools.yaml"
CHAT_VERSIONS = {
    "v0": (ROOT / "artifacts" / "versions" / "v0" / "system_prompt.md", ROOT / "artifacts" / "versions" / "v0" / "tools.yaml"),
    "v1": (ROOT / "artifacts" / "versions" / "v1" / "system_prompt.md", ROOT / "artifacts" / "versions" / "v1" / "tools.yaml"),
    "v2": (PROMPT_PATH, TOOLS_PATH),
}
PROVIDER_STATE: dict[str, object] = {"verified": None, "error": None}


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=12_000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=20)
    model: str | None = Field(default=None, max_length=200)
    artifact_version: Literal["v0", "v1", "v2"] = "v2"


@lru_cache
def agent_artifacts(version: str) -> tuple[str, list[dict], list[dict]]:
    prompt_path, tools_path = CHAT_VERSIONS[version]
    prompt = prompt_path.read_text(encoding="utf-8")
    declarations = load_tool_declarations(tools_path)
    return prompt, declarations, to_openai_tools(declarations)


app = FastAPI(
    title="LexFlow Legal Agent API",
    version="2.0.0",
    description="Tool-calling legal agent backed by the OCR/Qdrant data service.",
)
origins = [
    item.strip()
    for item in os.getenv("AGENT_FRONTEND_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
    if item.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "LexFlow Legal Agent API",
        "provider": os.getenv("AGENT_PROVIDER", "openrouter"),
        "contract_version": "ver2",
    }


@app.get("/ready")
def ready(probe: bool = False) -> dict:
    import requests

    provider_name = os.getenv("AGENT_PROVIDER", "openrouter")
    provider_instance = make_provider(provider_name)
    key_names = {
        "openrouter": "OPENROUTER_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "groq": "GROQ_API_KEY",
    }
    key_name = key_names.get(provider_name)
    provider_configured = bool(key_name and os.getenv(key_name))
    if hasattr(provider_instance, "key_count"):
        provider_configured = provider_instance.key_count > 0
    if probe and provider_configured:
        try:
            provider_instance.complete(
                [
                    {"role": "system", "content": "Provider readiness probe. Reply with OK only."},
                    {"role": "user", "content": "OK"},
                ],
                [],
                model=os.getenv("AGENT_MODEL") or None,
                temperature=0.0,
            )
            PROVIDER_STATE.update(verified=True, error=None)
        except Exception as exc:
            PROVIDER_STATE.update(verified=False, error=type(exc).__name__)
    backend_base = os.getenv("LEGAL_OCR_API_URL", "http://localhost:8000/api/v1").rstrip("/")
    try:
        backend = requests.get(f"{backend_base}/system/readiness", timeout=5).json()
        backend_ready = bool(backend.get("ready"))
    except Exception as exc:
        backend = {"ready": False, "error": type(exc).__name__}
        backend_ready = False
    return {
        "contract_version": "ver2",
        "ready": provider_configured and PROVIDER_STATE["verified"] is True and backend_ready,
        "provider": {
            "name": provider_name,
            "configured": provider_configured,
            "verified": PROVIDER_STATE["verified"],
            "error": PROVIDER_STATE["error"],
            "key_pool_size": getattr(provider_instance, "key_count", None),
        },
        "backend": backend,
    }


@app.post("/chat")
def chat(payload: ChatRequest) -> dict:
    prompt_path, tools_path = CHAT_VERSIONS[payload.artifact_version]
    prompt, _, tools = agent_artifacts(payload.artifact_version)
    provider_name = os.getenv("AGENT_PROVIDER", "openrouter")
    model = payload.model or os.getenv("AGENT_MODEL") or None
    messages = [
        {"role": "system", "content": prompt},
        runtime_context_message(),
        *[message.model_dump() for message in payload.messages],
    ]
    provider = make_provider(provider_name)
    try:
        result = run_model_tool_loop(
            provider=provider,
            messages=messages,
            tools=tools,
            model=model,
            max_tool_rounds=int(os.getenv("AGENT_MAX_TOOL_ROUNDS", "6")),
            enforce_runtime_security=payload.artifact_version == "v2",
        )
        if result.get("status") != "blocked_by_security":
            PROVIDER_STATE.update(verified=True, error=None)
    except Exception as exc:
        PROVIDER_STATE.update(verified=False, error=type(exc).__name__)
        result = {
            "status": "provider_unavailable",
            "mode": "unavailable",
            "assistant_text": (
                "Dịch vụ mô hình AI chưa sẵn sàng. Hệ thống không tự tạo câu trả lời hoặc "
                "dùng kết quả RAG thô thay thế. Vui lòng kiểm tra cấu hình provider."
            ),
            "rounds": [],
            "tool_events": [],
            "security": {},
            "execution_plan": None,
            "warning": f"Provider unavailable: {type(exc).__name__}",
        }
    artifact = build_artifact_version(payload.artifact_version, prompt_path, tools_path)
    return {
        **result,
        "requested_version": payload.artifact_version,
        "provider": provider_name,
        "model": model or getattr(provider, "default_model", None),
        **artifact_version_dict(artifact),
    }
