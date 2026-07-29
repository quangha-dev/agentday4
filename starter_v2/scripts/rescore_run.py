from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from run_eval import evaluate_phase_b, summarize
from security import redact_for_logging


def main() -> None:
    parser = argparse.ArgumentParser(description="Rescore stored actual calls against a revised eval rubric.")
    parser.add_argument("run", type=Path)
    parser.add_argument("--eval-cases", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    payload = json.loads(args.run.read_text(encoding="utf-8"))
    dataset_bytes = args.eval_cases.read_bytes()
    dataset = json.loads(dataset_bytes.decode("utf-8"))
    cases = {case["id"]: case for case in dataset["cases"]}
    rescored_results = []
    for stored in payload["results"]:
        case = cases[stored["id"]]
        actual_calls = stored["result"].get("actual_tool_calls", [])
        actual_text = stored["result"].get("actual_text")
        result = evaluate_phase_b(case, actual_calls, actual_text)
        rescored_results.append({
            **stored,
            "expect": case["expect"],
            "metadata": case.get("metadata", {}),
            "result": result,
        })

    now = datetime.now()
    payload.update({
        "run_id": payload["run_id"] + "_rescored_" + now.strftime("%Y%m%dT%H%M%S"),
        "eval_cases": str(args.eval_cases),
        "eval_cases_hash": hashlib.sha256(dataset_bytes).hexdigest(),
        "rescored_from": str(args.run),
        "rescored_at": now.isoformat(timespec="seconds"),
        "rescore_policy": "Actual provider calls/results are unchanged; only expectation matching was recomputed.",
        "summary": summarize(rescored_results),
        "results": rescored_results,
    })
    output = args.output or args.run.with_name(args.run.stem + "_rescored.json")
    output.write_text(
        json.dumps(redact_for_logging(payload), ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(json.dumps(payload["summary"], ensure_ascii=False))
    print(f"Saved: {output}")


if __name__ == "__main__":
    main()
