from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

# Tự động thêm thư mục starter_v0 vào sys.path để hỗ trợ chạy trực tiếp từ terminal
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import TOOL_FUNCTIONS, load_tool_declarations
from run_eval import compare_subset

ALLOWED_FAILURE_TYPES = {
    "wrong_tool", "wrong_arg_value", "wrong_boundary", "unnecessary_tool",
    "out_of_scope", "missing_info",
}


class EvalContractTests(unittest.TestCase):
    def test_semantic_query_expectation_keeps_structured_arguments_strict(self) -> None:
        ok, failures, correct, total = compare_subset(
            {
                "query": {"contains_all": ["dữ liệu", "thử nghiệm", "bao lâu"]},
                "document_number": "MOCK-01/2026/QC-LF",
            },
            {
                "query": "dữ liệu thử nghiệm giữ trong bao lâu",
                "document_number": "MOCK-01/2026/QC-LF",
            },
        )
        self.assertTrue(ok, failures)
        self.assertEqual((2, 2), (correct, total))

    def test_group_eval_is_exactly_five_plus_five(self) -> None:
        data = json.loads((ROOT / "data" / "eval_group.json").read_text(encoding="utf-8"))
        cases = data["cases"]
        self.assertEqual(10, len(cases))
        self.assertEqual(5, sum("query" in case for case in cases))
        self.assertEqual(5, sum("turns" in case for case in cases))
        self.assertEqual(len(cases), len({case["id"] for case in cases}))

    def test_group_case_schema(self) -> None:
        data = json.loads((ROOT / "data" / "eval_group.json").read_text(encoding="utf-8"))
        for case in data["cases"]:
            self.assertEqual("B", case["phase"], case["id"])
            self.assertIn(case["failure_type"], ALLOWED_FAILURE_TYPES, case["id"])
            self.assertIn("what_it_tests", case.get("metadata", {}), case["id"])
            self.assertTrue(
                case.get("expect", {}).get("tool_calls") or case.get("expect", {}).get("no_tool"),
                case["id"],
            )
            if "turns" in case:
                self.assertEqual("user", case["turns"][-1]["role"], case["id"])

    def test_attack_suite_has_fifteen_detailed_cases(self) -> None:
        data = json.loads((ROOT / "data" / "eval_attack_15.json").read_text(encoding="utf-8"))
        cases = data["cases"]
        self.assertEqual(15, len(cases))
        self.assertEqual(len(cases), len({case["id"] for case in cases}))
        for case in cases:
            self.assertEqual("B", case["phase"], case["id"])
            self.assertIn(case["failure_type"], ALLOWED_FAILURE_TYPES, case["id"])
            self.assertIn(case.get("metadata", {}).get("severity"), {"medium", "high", "critical"})
            self.assertTrue(case.get("metadata", {}).get("what_it_tests"), case["id"])

    def test_declared_tools_have_implementations(self) -> None:
        declarations = load_tool_declarations(ROOT / "artifacts" / "tools.yaml")
        declared = {item["name"] for item in declarations}
        self.assertEqual(declared, set(TOOL_FUNCTIONS))
        self.assertEqual(
            {
                "clarify", "resolve_legal_document", "legal_rag_search", "get_legal_provision",
                "check_effective_status", "compare_legal_versions", "extract_legal_information",
                "validate_citation",
            },
            declared,
        )

    def test_tool_docs_exist(self) -> None:
        declarations = load_tool_declarations(ROOT / "artifacts" / "tools.yaml")
        for item in declarations:
            tool_dir = ROOT / "tools" / item["name"]
            self.assertTrue((tool_dir / "TOOL.md").exists(), item["name"])
            self.assertTrue((tool_dir / "tool.py").exists(), item["name"])


if __name__ == "__main__":
    unittest.main()
