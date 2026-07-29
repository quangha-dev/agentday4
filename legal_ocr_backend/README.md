# Legal OCR Backend

Backend độc lập cho quy trình PDF → OCR → kiểm duyệt song song với PDF → JSON pháp luật → chunk theo cấu trúc → semantic search. Backend không chứa chatbot hoặc agent; nó cung cấp API dữ liệu cho Agent service trong `starter_v2`. LLM nội bộ chỉ dùng ở bước làm sạch OCR có kiểm tra bảo toàn và luôn có bộ lọc quy tắc dự phòng.

## Chạy nhanh bằng Python

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[embedding,dev]"
uvicorn app.main:app --reload
```

Mặc định dữ liệu được lưu bền vững trong `data/legal_ocr.db`, file gốc trong `data/uploads` và Qdrant local trong `data/qdrant`. Với PDF scan, máy cần cài Tesseract và language pack tiếng Việt. Sao chép `.env.example` thành `.env`; nếu không có key LLM, endpoint làm sạch vẫn chạy bằng bộ lọc quy tắc an toàn.

## Chạy đầy đủ bằng Docker

```powershell
docker compose up --build
```

Cấu hình này sử dụng PostgreSQL, Qdrant collection `legal_provisions_ver2`, model embedding đa ngôn ngữ `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384 chiều) và Tesseract `vie+eng`. API mở tại `http://localhost:8000`, OpenAPI tại `http://localhost:8000/docs`.

## Luồng sử dụng

1. `POST /api/v1/documents/upload` dạng multipart, gồm PDF và đủ metadata văn bản pháp lý.
2. `POST /api/v1/documents/{id}/process`
3. Kiểm tra/sửa/xác nhận từng trang; dùng `POST /api/v1/pages/{page_id}/clean/llm` để lọc rác bằng LLM có fallback.
4. `POST /api/v1/documents/{id}/parse`
5. `POST /api/v1/documents/{id}/index`
6. `POST /api/v1/search`

Các endpoint tool-facing dùng chung evidence contract:

- `POST /api/v1/rag/search`: semantic context từ Qdrant.
- `POST /api/v1/rag/documents/resolve`: chuẩn hóa số hiệu/tiêu đề thành document/version.
- `POST /api/v1/rag/provision`: exact Điều/Khoản/Điểm từ SQL.
- `POST /api/v1/rag/effective-status`: hiệu lực theo version/ngày.
- `POST /api/v1/rag/compare`: so sánh hai version.
- `POST /api/v1/rag/citations/validate`: kiểm tra claim theo citation ID.
- `POST /api/v1/rag/extract`: trích trường dữ liệu từ citation đã lưu, không nhận content do model tự gửi.

`raw_text` luôn bất biến. Mọi lần làm sạch, sửa và xác nhận được lưu thành revision riêng.

Mỗi chunk dùng chiến lược `legal-hierarchy-ver2`: ưu tiên giữ nguyên Điều/Khoản/Điểm, chỉ tách khối quá dài tại ranh giới câu/đoạn và có overlap nhỏ. `text` chỉ chứa nguyên văn luật; metadata và `embedding_text` được tách riêng. Chỉ chunk có `contract_version=ver2` được truy xuất. `GET /api/v1/documents/{id}/export/json` xuất cây pháp luật, trạng thái OCR từng trang và chunk đã lập chỉ mục.

## Nạp mock trực tiếp để test parser và vector DB

Luồng này chỉ dành cho môi trường phát triển/chấm thử. Nó tạo các trang đã xác nhận từ
`fixtures/mock_legal_document_ver2.json`, sau đó gọi đúng parser, hierarchical chunker và
vector indexer `ver2` của production nhưng không chạy OCR. Luồng PDF → OCR phía trên không
bị thay đổi.

Từ thư mục `legal_ocr_backend`, chạy trực tiếp một file duy nhất:

```powershell
.venv\Scripts\python.exe scripts\seed_mock_vector_data.py
```

Lệnh có tính idempotent: nếu mock đã được index, nó chỉ trả lại kết quả và chạy truy vấn
semantic kiểm tra. Khi đã sửa fixture và muốn tạo lại đúng mock này:

```powershell
.venv\Scripts\python.exe scripts\seed_mock_vector_data.py --rebuild
```

Có thể đổi câu truy vấn smoke test bằng `--query "thời hạn lưu trữ dữ liệu"`. Không bật
hoặc gọi OCR cho luồng mock này. Nếu đang dùng Qdrant local (`QDRANT_URL` để trống), hãy
chạy seed trước khi khởi động backend vì Qdrant local chỉ cho một tiến trình giữ thư mục dữ
liệu. Với Qdrant server/Docker, script có thể chạy song song với backend.
