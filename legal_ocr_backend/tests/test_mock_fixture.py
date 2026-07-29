import json
from collections import Counter
from pathlib import Path

from app.services.parser import PageText, parse_legal_structure

FIXTURE = Path(__file__).parents[1] / "fixtures" / "mock_legal_document_ver2.json"


def _flatten(nodes: list[dict]) -> list[dict]:
    return [node for item in nodes for node in [item, *_flatten(item["children"])]]


def test_mock_fixture_exercises_full_legal_hierarchy_without_ocr() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    pages = [
        PageText(page_number=item["page_number"], text=item["text"])
        for item in payload["pages"]
    ]

    nodes = _flatten(parse_legal_structure(pages))
    counts = Counter(node["node_type"] for node in nodes)

    assert counts["part"] == 4
    assert counts["chapter"] == 7
    assert counts["section"] >= 3
    assert counts["article"] == 20
    assert counts["clause"] >= 50
    assert counts["point"] >= 25
    assert all(node["full_path"] for node in nodes)
    assert {node["page_start"] for node in nodes} == set(range(1, 9))
