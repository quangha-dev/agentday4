# Legal OCR Backend

Backend độc lập cho quy trình PDF → OCR → kiểm duyệt song song với PDF → JSON pháp luật → chunk theo cấu trúc → semantic search. Backend không chứa chatbot hoặc agent; LLM chỉ là bước làm sạch OCR có kiểm tra bảo toàn và luôn có bộ lọc quy tắc dự phòng.

## Chạy nhanh bằng Python

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Mặc định dữ liệu được lưu bền vững trong `data/legal_ocr.db`, file gốc trong `data/uploads` và Qdrant local trong `data/qdrant`. Với PDF scan, máy cần cài Tesseract và language pack tiếng Việt. Sao chép `.env.example` thành `.env`; nếu không có key LLM, endpoint làm sạch vẫn chạy bằng bộ lọc quy tắc an toàn.

## Chạy đầy đủ bằng Docker

```powershell
docker compose up --build
```

Cấu hình này sử dụng PostgreSQL, Qdrant, model embedding `BAAI/bge-m3` và Tesseract `vie+eng`. API mở tại `http://localhost:8000`, OpenAPI tại `http://localhost:8000/docs`.

## Luồng sử dụng

1. `POST /api/v1/documents/upload` dạng multipart, gồm PDF và đủ metadata văn bản pháp lý.
2. `POST /api/v1/documents/{id}/process`
3. Kiểm tra/sửa/xác nhận từng trang; dùng `POST /api/v1/pages/{page_id}/clean/llm` để lọc rác bằng LLM có fallback.
4. `POST /api/v1/documents/{id}/parse`
5. `POST /api/v1/documents/{id}/index`
6. `POST /api/v1/search`

`raw_text` luôn bất biến. Mọi lần làm sạch, sửa và xác nhận được lưu thành revision riêng.

Mỗi chunk dùng chiến lược `legal-hierarchy-article-clause-v1`: ưu tiên giữ nguyên Điều/Khoản/Điểm, chỉ tách khối quá dài tại ranh giới câu/đoạn và có overlap nhỏ. Chunk lưu cả số ký hiệu, ngày, loại, cơ quan, người ký, trích yếu, version, đường dẫn cấu trúc và số trang trong SQLite/PostgreSQL lẫn payload Qdrant. `GET /api/v1/documents/{id}/export/json` xuất cả cây pháp luật và các chunk đã lập chỉ mục.
