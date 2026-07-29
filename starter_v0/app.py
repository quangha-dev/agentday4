from __future__ import annotations

import csv
import difflib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from chat import now_iso, run_model_tool_loop, safe_slug, trim_history, write_transcript
from env_loader import load_lab_env
from providers import make_provider
from security import redact_secrets
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version


ROOT = Path(__file__).parent
ARTIFACTS = ROOT / "artifacts"
load_lab_env(ROOT)

PROVIDER_KEYS = {
    "openrouter": "OPENROUTER_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
}


def load_version_status() -> dict[str, Any]:
    return json.loads((ARTIFACTS / "version_status.json").read_text(encoding="utf-8"))


def version_paths(item: dict[str, Any]) -> tuple[Path, Path]:
    return ROOT / item["prompt_file"], ROOT / item["tools_file"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((ROOT / "runs").glob("*.json"), reverse=True) if (ROOT / "runs").exists() else []:
        try:
            payload = load_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        summary = payload.get("summary", {})
        rows.append({
            "file": path.name,
            "version": payload.get("version"),
            "suite": payload.get("suite"),
            "provider": payload.get("provider"),
            "case_accuracy": summary.get("case_accuracy"),
            "routing": summary.get("tool_routing_accuracy"),
            "arguments": summary.get("argument_accuracy"),
            "multiturn": summary.get("multiturn_accuracy"),
            "provider_errors": summary.get("provider_error_cases"),
            "measured": summary.get("measured_cases"),
            "total": summary.get("total_cases"),
        })
    return rows


def version_log_rows() -> list[dict[str, str]]:
    path = ARTIFACTS / "version_log.csv"
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def transcript_path() -> Path:
    return ROOT / "transcripts" / f"{st.session_state.transcript_id}.transcript.json"


def ensure_session() -> None:
    if "transcript_id" not in st.session_state:
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
        st.session_state.transcript_id = f"ui_{timestamp}"
    st.session_state.setdefault("history", [])
    st.session_state.setdefault("turns", [])


def persist_transcript(
    *,
    selected_version: str,
    artifact: Any,
    provider_name: str,
    model: str | None,
    prompt_path: Path,
    tools_path: Path,
) -> None:
    transcript = {
        "transcript_id": st.session_state.transcript_id,
        **artifact_version_dict(artifact),
        "provider": provider_name,
        "model": model,
        "system_prompt": str(prompt_path),
        "tools": str(tools_path),
        "history_window": 5,
        "max_tool_rounds": 4,
        "created_at": st.session_state.get("created_at", now_iso()),
        "updated_at": now_iso(),
        "ui_selected_version": selected_version,
        "turns": st.session_state.turns,
    }
    st.session_state.created_at = transcript["created_at"]
    write_transcript(transcript_path(), transcript)


def render_trace(turn: dict[str, Any]) -> None:
    security = turn.get("security") or {}
    with st.expander(
        f"Security: {security.get('risk_level', 'unknown')} · {security.get('action', 'not_recorded')}",
        expanded=security.get("risk_level") != "low",
    ):
        st.json(security)
    for round_item in turn.get("rounds", []):
        with st.expander(f"Round {round_item.get('round')}", expanded=True):
            if round_item.get("assistant_text"):
                st.caption(round_item["assistant_text"])
            st.markdown("Tool calls")
            st.json(round_item.get("tool_calls", []))
            st.markdown("Results / errors")
            st.json(round_item.get("tool_results", []))


st.set_page_config(page_title="Research Agent v0→v3", page_icon="🛡️", layout="wide")
ensure_session()
status = load_version_status()
versions = {item["version"]: item for item in status["versions"]}

st.title("Research Agent — routing, security và evidence")
st.caption("Một agent loop dùng chung cho UI/CLI; guard chạy ngoài model để không tạo extra tool call trong grader.")

with st.sidebar:
    st.header("Runtime")
    selected_version = st.selectbox(
        "Artifact version",
        options=list(versions),
        index=list(versions).index(status.get("active_version", "v3")),
    )
    provider_name = st.selectbox("Provider", options=list(PROVIDER_KEYS), index=0)
    model_override = st.text_input("Model override (optional)", value="").strip() or None
    key_name = PROVIDER_KEYS[provider_name]
    st.write(f"Credential `{key_name}`: {'configured' if os.getenv(key_name) else 'missing'}")
    if st.button("New clean session", use_container_width=True):
        for key in ("transcript_id", "history", "turns", "created_at"):
            st.session_state.pop(key, None)
        st.rerun()

version_item = versions[selected_version]
prompt_path, tools_path = version_paths(version_item)
system_prompt = prompt_path.read_text(encoding="utf-8")
declarations = load_tool_declarations(tools_path)
openai_tools = to_openai_tools(declarations)
artifact = build_artifact_version(selected_version, prompt_path, tools_path)

tab_chat, tab_versions, tab_evidence, tab_tests = st.tabs([
    "Chat & trace", "Prompt before/after", "Runs & metrics", "Test cases",
])

with tab_chat:
    top_a, top_b, top_c = st.columns(3)
    top_a.metric("Version", selected_version)
    top_b.metric("Declared tools", len(declarations))
    top_c.metric("Saved turns", len(st.session_state.turns))
    st.code(artifact.artifact_version, language=None)

    for turn in st.session_state.turns:
        with st.chat_message("user"):
            st.write(turn["user"])
        with st.chat_message("assistant"):
            st.write(turn.get("assistant_text") or turn.get("error") or "No response")
            render_trace(turn)

    user_text = st.chat_input("Nhập yêu cầu research hoặc prompt cần audit")
    if user_text:
        turn_record: dict[str, Any] = {
            "turn_index": len(st.session_state.turns) + 1,
            "started_at": now_iso(),
            "user": redact_secrets(user_text),
            "status": "started",
            "version": selected_version,
            **artifact_version_dict(artifact),
            "rounds": [],
            "tool_events": [],
        }
        try:
            provider = make_provider(provider_name)
            messages = [
                {"role": "system", "content": system_prompt},
                *trim_history(st.session_state.history, 5),
                {"role": "user", "content": user_text},
            ]
            result = run_model_tool_loop(
                provider=provider,
                messages=messages,
                tools=openai_tools,
                model=model_override,
                max_tool_rounds=4,
            )
            turn_record.update(result)
            st.session_state.history.extend([
                {"role": "user", "content": user_text},
                {"role": "assistant", "content": result["assistant_text"]},
            ])
        except Exception as exc:
            turn_record.update({
                "status": "provider_error",
                "error": f"{type(exc).__name__}: {redact_secrets(str(exc))}",
            })
        turn_record["ended_at"] = now_iso()
        st.session_state.turns.append(turn_record)
        persist_transcript(
            selected_version=selected_version,
            artifact=artifact,
            provider_name=provider_name,
            model=model_override,
            prompt_path=prompt_path,
            tools_path=tools_path,
        )
        st.rerun()

with tab_versions:
    left_version, right_version = st.columns(2)
    with left_version:
        before_name = st.selectbox("Before", list(versions), index=0, key="before_version")
    with right_version:
        after_name = st.selectbox("After", list(versions), index=len(versions) - 1, key="after_version")
    before_prompt = version_paths(versions[before_name])[0].read_text(encoding="utf-8")
    after_prompt = version_paths(versions[after_name])[0].read_text(encoding="utf-8")
    diff = "\n".join(difflib.unified_diff(
        before_prompt.splitlines(),
        after_prompt.splitlines(),
        fromfile=f"{before_name}/system_prompt.md",
        tofile=f"{after_name}/system_prompt.md",
        lineterm="",
    ))
    st.subheader("Prompt diff")
    st.code(diff or "No prompt difference", language="diff")
    st.subheader("Version status và hypothesis")
    st.dataframe(status["versions"], use_container_width=True)
    st.info(status["evidence_policy"])

with tab_evidence:
    st.subheader("Live run summaries")
    rows = run_rows()
    if rows:
        st.dataframe(rows, use_container_width=True)
    else:
        st.warning("Chưa có live run JSON. Không dùng offline test để giả lập metric provider.")
    st.subheader("Version log")
    log_rows = version_log_rows()
    if log_rows:
        st.dataframe(log_rows, use_container_width=True)
    else:
        st.warning("version_log.csv chưa có dòng live evidence.")
    st.caption(f"Transcript hiện tại: {transcript_path()}")

with tab_tests:
    for filename, label in (
        ("eval_base.json", "Base/public"),
        ("eval_group.json", "Group mandatory"),
        ("eval_security.json", "Security hidden-like"),
        ("eval_research_extension.json", "Optional extension"),
    ):
        payload = load_json(ROOT / "data" / filename)
        cases = payload.get("cases", [])
        single = sum("query" in case for case in cases)
        multi = sum("turns" in case for case in cases)
        with st.expander(f"{label}: {len(cases)} cases ({single} single / {multi} multi)"):
            st.dataframe([
                {
                    "id": case.get("id"),
                    "failure_type": case.get("failure_type"),
                    "what_it_tests": case.get("metadata", {}).get("what_it_tests"),
                    "expected": case.get("expect"),
                }
                for case in cases
            ], use_container_width=True)
