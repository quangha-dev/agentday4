from __future__ import annotations

import json
import unittest
from pathlib import Path

from chat import LEGAL_MAX_TOOL_ROUNDS, recommended_max_tool_rounds
from tools import load_tool_declarations, to_openai_tools
from versioning import render_system_prompt


ROOT = Path(__file__).resolve().parents[1]
PROMPT_PATH = ROOT / "artifacts" / "versions" / "v1" / "system_prompt.md"
TOOLS_PATH = ROOT / "artifacts" / "versions" / "v1" / "tools.yaml"
CASES_PATH = ROOT / "data" / "legal_v1_test_cases.json"

EXPECTED_TOOLS = [
    "legal_rag_search",
    "get_legal_provision",
    "check_effective_status",
    "compare_legal_versions",
    "extract_legal_information",
    "validate_citation",
]


class LegalV1ArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.prompt = PROMPT_PATH.read_text(encoding="utf-8")
        cls.declarations = load_tool_declarations(TOOLS_PATH)
        cls.by_name = {item["name"]: item for item in cls.declarations}
        cls.cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))

    def test_declares_exactly_the_six_legal_tools(self) -> None:
        self.assertEqual(EXPECTED_TOOLS, [item["name"] for item in self.declarations])
        self.assertEqual(len(self.declarations), len(self.by_name))
        # Ensure the declarations can be normalized for provider APIs.
        normalized = to_openai_tools(self.declarations)
        self.assertEqual(EXPECTED_TOOLS, [item["function"]["name"] for item in normalized])

    def test_required_tool_arguments_match_contract(self) -> None:
        expected_required = {
            "legal_rag_search": {"query", "target_date", "top_k"},
            "get_legal_provision": {"document_id", "article"},
            "check_effective_status": {"document_id", "target_date"},
            "compare_legal_versions": {"old_document_id", "new_document_id", "article"},
            "extract_legal_information": {"provisions", "fields"},
            "validate_citation": {"claims", "target_date"},
        }
        for name, required in expected_required.items():
            schema = self.by_name[name]["parameters"]
            self.assertEqual(required, set(schema["required"]), name)
            self.assertFalse(schema["additionalProperties"], name)

    def test_effective_status_contract_is_complete_in_prompt(self) -> None:
        for status in (
            "not_yet_effective",
            "effective",
            "partially_effective",
            "expired",
            "replaced",
            "unknown",
        ):
            self.assertIn(f"`{status}`", self.prompt)

    def test_prompt_enforces_exact_before_rag(self) -> None:
        exact_rule = self.prompt.index("Gọi `get_legal_provision` trước")
        rag_rule = self.prompt.index("Gọi `legal_rag_search` khi câu hỏi")
        self.assertLess(exact_rule, rag_rule)
        self.assertIn("Không semantic search trước", self.prompt)

    def test_prompt_enforces_effective_check_and_validation_gate(self) -> None:
        self.assertIn("Kiểm tra hiệu lực bắt buộc", self.prompt)
        self.assertIn("Trước khi trả lời cuối cùng, bắt buộc gọi `validate_citation`", self.prompt)
        self.assertIn("Nếu `valid=false`", self.prompt)
        self.assertIn("không được lặp lại claim lỗi như một sự thật", self.prompt)

    def test_prompt_limits_evidence_retrieval_to_three_rounds(self) -> None:
        self.assertIn("Tối đa **3 vòng truy xuất bằng chứng**", self.prompt)
        self.assertIn("Sau 3 vòng vẫn thiếu bằng chứng", self.prompt)

    def test_prompt_contains_required_answer_sections(self) -> None:
        for section in (
            "**Kết luận**",
            "**Căn cứ pháp lý**",
            "**Hiệu lực**",
            "**So sánh**",
            "**Lưu ý**",
        ):
            self.assertIn(section, self.prompt)

    def test_runtime_date_placeholder_is_resolved(self) -> None:
        rendered = render_system_prompt(self.prompt, current_date="2026-07-29")
        self.assertNotIn("{{CURRENT_DATE}}", rendered)
        self.assertIn("2026-07-29", rendered)
        self.assertEqual(
            self.prompt.count("{{CURRENT_DATE}}"),
            rendered.count("2026-07-29"),
        )

    def test_runtime_allows_sequential_legal_evidence_gates(self) -> None:
        self.assertEqual(
            LEGAL_MAX_TOOL_ROUNDS,
            recommended_max_tool_rounds(self.declarations),
        )
        self.assertGreaterEqual(LEGAL_MAX_TOOL_ROUNDS, 5)

    def test_test_case_inventory_is_complete_and_unique(self) -> None:
        expected = {
            "tool_cases": [f"T{index:02d}" for index in range(1, 13)],
            "agent_cases": [f"A{index:02d}" for index in range(1, 11)],
            "e2e_cases": [f"E{index:02d}" for index in range(1, 5)],
        }
        all_ids: list[str] = []
        for group, expected_ids in expected.items():
            actual_ids = [case["id"] for case in self.cases[group]]
            self.assertEqual(expected_ids, actual_ids, group)
            all_ids.extend(actual_ids)
        self.assertEqual(len(all_ids), len(set(all_ids)))

    def test_every_tool_has_at_least_one_tool_case(self) -> None:
        covered = {case["tool"] for case in self.cases["tool_cases"]}
        self.assertEqual(set(EXPECTED_TOOLS), covered)

    def test_acceptance_thresholds_match_requirements(self) -> None:
        criteria = self.cases["acceptance_criteria"]
        self.assertGreaterEqual(criteria["exact_location_accuracy_min"], 0.95)
        self.assertGreaterEqual(criteria["rag_relevant_provision_in_top_5_min"], 0.90)
        self.assertEqual(1.0, criteria["effective_status_accuracy"])
        self.assertGreaterEqual(criteria["citation_content_match_min"], 0.95)
        self.assertEqual(0.0, criteria["fake_citation_rate"])
        self.assertEqual(3, criteria["maximum_retrieval_rounds"])
        self.assertTrue(criteria["all_supported_answers_traceable_to_source"])


if __name__ == "__main__":
    unittest.main()
