from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from env_loader import load_lab_env
from security import redact_for_logging
from tools import TOOL_FUNCTIONS


load_lab_env(ROOT)


def compact_result(name: str, args: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    return {
        "tool": name,
        "args": args,
        "ok": result.get("ok") is True,
        "contract_version": result.get("contract_version"),
        "error": result.get("error"),
        "count": result.get("count"),
        "found": result.get("found"),
        "status": result.get("status"),
        "valid": result.get("valid"),
        "evidence_count": len(result.get("evidence") or []),
        "result": result,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute the real LexFlow ver2 legal tool contracts without a model.")
    parser.add_argument("--document", default="MOCK-01/2026/QC-LF")
    parser.add_argument("--target-date", default="2026-01-20")
    parser.add_argument("--runs-dir", type=Path, default=ROOT / "runs")
    args = parser.parse_args()

    steps: list[tuple[str, dict[str, Any]]] = [
        ("clarify", {"question": "Bạn muốn áp dụng văn bản tại ngày nào?", "response_type": "text"}),
        ("resolve_legal_document", {"query": args.document}),
        (
            "legal_rag_search",
            {"query": "thời hạn lưu dữ liệu thử nghiệm", "document_number": args.document, "top_k": 3},
        ),
        (
            "get_legal_provision",
            {"document_id": args.document, "article": "4", "clause": "1", "point": "a"},
        ),
        ("check_effective_status", {"document_id": args.document, "target_date": args.target_date}),
    ]
    records: list[dict[str, Any]] = []
    citation_id: str | None = None

    for name, kwargs in steps:
        result = TOOL_FUNCTIONS[name](**kwargs)
        records.append(compact_result(name, kwargs, result))
        if name == "get_legal_provision" and result.get("evidence"):
            citation_id = result["evidence"][0].get("citation_id")

    if citation_id:
        extract_args = {
            "citation_ids": [citation_id],
            "fields": ["subject", "obligations", "deadline"],
        }
        extract_result = TOOL_FUNCTIONS["extract_legal_information"](**extract_args)
        records.append(compact_result("extract_legal_information", extract_args, extract_result))

        validate_args = {
            "claims": [
                {
                    "claim": "Thông báo phải nêu thời điểm phát hiện sự cố.",
                    "citation_id": citation_id,
                }
            ],
            "target_date": args.target_date,
        }
        validate_result = TOOL_FUNCTIONS["validate_citation"](**validate_args)
        records.append(compact_result("validate_citation", validate_args, validate_result))

    failures = [
        item["tool"]
        for item in records
        if not item["ok"]
        or item["contract_version"] != "ver2"
        or (item["tool"] == "validate_citation" and item["valid"] is not True)
    ]
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    payload = {
        "run_id": f"ver2_legal_tool_smoke_{timestamp}",
        "suite": "legal_tool_smoke",
        "contract_version": "ver2",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "total_tools": len(records),
            "passed_tools": len(records) - len(failures),
            "failed_tools": len(failures),
            "failures": failures,
            "compare_legal_versions": "not_run_requires_two_distinct_indexed_versions",
        },
        "results": records,
    }
    args.runs_dir.mkdir(parents=True, exist_ok=True)
    output = args.runs_dir / f"{payload['run_id']}.json"
    output.write_text(
        json.dumps(redact_for_logging(payload), ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(json.dumps(payload["summary"], ensure_ascii=False))
    print(f"Saved: {output}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
