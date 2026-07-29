from pathlib import Path

import fitz
from fastapi.testclient import TestClient

from app.main import app


def make_native_pdf(path: Path) -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_textbox(
        fitz.Rect(50, 50, 545, 780),
        "CHUONG I\nQuy dinh chung\nDIEU 1. Pham vi dieu chinh\n"
        "1. Van ban nay quy dinh quyen va nghia vu.\n"
        "a) Quyen cua ca nhan duoc bao ve.\n"
        "Noi dung bo sung de bao dam trang PDF co lop van ban native day du.",
        fontsize=12,
    )
    document.save(path)
    document.close()


def test_upload_ocr_review_parse_and_exact_search(tmp_path: Path) -> None:
    source = tmp_path / "legal-native.pdf"
    make_native_pdf(source)

    with TestClient(app) as client:
        with source.open("rb") as stream:
            response = client.post(
                "/api/v1/documents/upload",
                files={"file": (source.name, stream, "application/pdf")},
                data={
                    "document_number": "66.24/2026/NQ-CP",
                    "issued_date": "2026-07-26",
                    "effective_date": "2026-07-26",
                    "document_type": "Nghị quyết",
                    "issuing_authority": "Chính phủ",
                    "signer": "Nguyễn Văn Thắng",
                    "summary": "Về xử lý khó khăn trong hoạt động khoa học và công nghệ",
                },
            )
        assert response.status_code == 201
        document_id = response.json()["id"]
        version_number = response.json()["version_number"]
        assert response.json()["document_number"] == "66.24/2026/NQ-CP"

        process = client.post(f"/api/v1/documents/{document_id}/process")
        assert process.status_code == 202
        assert client.get(f"/api/v1/jobs/{process.json()['id']}").json()["status"] == "COMPLETED"

        pages = client.get(f"/api/v1/documents/{document_id}/pages").json()
        assert len(pages) == 1
        assert pages[0]["classification"] == "native"

        cleaned = client.post(f"/api/v1/pages/{pages[0]['id']}/clean").json()
        verified = client.post(
            f"/api/v1/pages/{pages[0]['id']}/verify",
            json={"content": cleaned["cleaned_text"]},
        )
        assert verified.status_code == 200

        parsed = client.post(f"/api/v1/documents/{document_id}/parse")
        assert parsed.status_code == 200
        assert parsed.json()["node_count"] >= 3

        tree = client.get(f"/api/v1/documents/{document_id}/tree").json()
        assert tree
        exact = client.post(
            "/api/v1/search",
            json={"query": "Điều 1", "mode": "exact", "document_id": document_id},
        )
        assert exact.status_code == 200
        assert exact.json()[0]["marker"] == "1"

        indexed = client.post(f"/api/v1/documents/{document_id}/index")
        assert indexed.status_code == 200
        assert indexed.json()["indexed_articles"] == 1
        assert indexed.json()["indexed_chunks"] >= 1
        exported = client.get(f"/api/v1/documents/{document_id}/export/json").json()
        chunk = exported["chunks"][0]
        assert chunk["metadata"]["document_number"] == "66.24/2026/NQ-CP"
        assert chunk["metadata"]["version_number"] == version_number
        assert chunk["metadata"]["full_path"]
        assert "Số ký hiệu: 66.24/2026/NQ-CP" in chunk["text"]
        semantic = client.post(
            "/api/v1/search",
            json={"query": "quyen va nghia vu", "mode": "semantic", "document_id": document_id},
        )
        assert semantic.status_code == 200
        assert semantic.json()[0]["legal_node_id"]
