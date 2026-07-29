from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def summary(results: list[dict]) -> dict:
    measured = [item for item in results if not item["result"].get("provider_error")]
    multi = [item for item in measured if item.get("is_multiturn")]
    passed = sum(bool(item["result"].get("passed")) for item in measured)
    return {
        "total_cases": len(results),
        "measured_cases": len(measured),
        "provider_error_cases": len(results) - len(measured),
        "passed_cases": passed,
        "case_accuracy": round(passed / len(measured), 4) if measured else 0.0,
        "multiturn_accuracy": round(
            sum(bool(item["result"].get("passed")) for item in multi) / len(multi), 4
        ) if multi else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify model tool-schema 400s as measured model failures.")
    parser.add_argument("comparison_dir", type=Path)
    args = parser.parse_args()
    rows = []
    for path in sorted(args.comparison_dir.glob("v*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for item in payload["results"]:
            result = item["result"]
            if result.get("provider_error") == "BadRequestError":
                result["provider_error"] = None
                result["failures"] = ["model_tool_schema_error:BadRequestError"]
        payload["summary"] = summary(payload["results"])
        payload["normalization"] = (
            "BadRequestError from structured tool generation is a measured model/argument failure, "
            "not provider infrastructure failure; actual calls and pass/fail values are unchanged."
        )
        output = path.with_name(path.stem + "_normalized.json")
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        rows.append({"version": payload["version"], **payload["summary"], "run_file": str(output)})

    csv_path = args.comparison_dir / "comparison_normalized.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(rows, ensure_ascii=False))
    print(f"Saved: {csv_path}")


if __name__ == "__main__":
    main()
