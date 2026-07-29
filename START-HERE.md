# HƯỚNG DẪN GIÁM KHẢO — CÀI, CHẠY VÀ KIỂM TRA LEXFLOW TỪ A ĐẾN Z

Đây là tài liệu vận hành chính dành cho người chấm. Mọi đường dẫn bên dưới tính từ thư mục gốc của repo. Quy trình chuẩn dùng **một Python virtual environment duy nhất tại `.venv`** và ba terminal để chạy backend, Agent API và frontend.

## 1. Hệ thống gồm những gì?

| Thành phần | Thư mục | Cổng | Chức năng |
|---|---|---:|---|
| OCR/RAG backend | `legal_ocr_backend/` | 8000 | Upload PDF, OCR theo trang, lọc rác, xác nhận, parse Phần–Chương–Mục–Điều–Khoản–Điểm, chunk và lưu SQL/Qdrant |
| Tool-calling Agent | `starter_v2/` | 8502 | Chọn legal tool, lấy RAG context, kiểm tra hiệu lực/citation, chống injection và gọi model Groq/OpenRouter |
| Web UI | `legal_ocr_frontend/` | 3000 | Chat, chuyển V0/V1/V2, upload/OCR song song PDF–text và xem tài liệu đã index |

Luồng dữ liệu chính:

```text
PDF → text native hoặc Tesseract OCR → xác nhận từng trang → JSON pháp lý
    → structural chunk kèm metadata/version/page → embedding → Qdrant
    → Agent lập kế hoạch → gọi exact/RAG/effective/citation tools → câu trả lời có nguồn
```

Quy ước version:

- `starter_v0/`: baseline gốc, không bị chỉnh sửa.
- `starter_v1/`: thí nghiệm chỉ sửa prompt.
- `starter_v2/`: sản phẩm tích hợp hoàn chỉnh; contract dữ liệu luôn là `ver2`.
- Snapshot/evidence `v0`–`v3` nằm trong `starter_v2/artifacts/versions/` và `starter_v2/runs/`.
- UI cho chuyển `V0`, `V1`, `V2` theo yêu cầu demo. V3 là checkpoint hardening/evidence của bài lab, không phải một contract dữ liệu mới.

## 2. Điều kiện cần trước khi cài

- Windows 10/11 và PowerShell.
- Python **3.11**: kiểm tra bằng `py -3.11 --version`.
- Node.js **22.13+** và npm: kiểm tra bằng `node --version` và `npm --version`.
- Git.
- Tesseract 5 có language `eng` và `vie` nếu muốn thử PDF scan. Mock/vector test không cần chạy OCR.
- Ít nhất một Groq key có quyền gọi model; có thể khai báo nhiều key để xoay quota.

Từ đây, mọi lệnh bắt đầu tại repo root:

```powershell
cd <DUONG_DAN_REPO_DA_CLONE>
```

## 3. Bước A — Cài toàn bộ Python bằng một `requirements.txt`

Không tạo lại hoặc xóa `.venv` nếu môi trường đã tồn tại.

```powershell
if (-not (Test-Path .venv)) { py -3.11 -m venv .venv }
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

File [`requirements.txt`](requirements.txt) ở root cài cả Agent và OCR backend, gồm semantic embedding và dependency test. Không cần chạy thêm `pip install` trong từng thư mục con.

## 4. Bước B — Cài frontend tái hiện đúng lockfile

```powershell
cd legal_ocr_frontend
npm ci
cd ..
```

Nếu `npm ci` báo Node quá cũ, nâng Node lên phiên bản ghi trong `legal_ocr_frontend/package.json` rồi chạy lại.

## 5. Bước C — Tạo cấu hình, không ghi đè `.env`

```powershell
if (-not (Test-Path starter_v2\.env)) { Copy-Item starter_v2\.env.example starter_v2\.env }
if (-not (Test-Path legal_ocr_backend\.env)) { Copy-Item legal_ocr_backend\.env.example legal_ocr_backend\.env }
if (-not (Test-Path legal_ocr_frontend\.env)) { Copy-Item legal_ocr_frontend\.env.example legal_ocr_frontend\.env }
```

Mở `starter_v2/.env` và điền tối thiểu:

```dotenv
AGENT_PROVIDER=groq
AGENT_MODEL=openai/gpt-oss-120b
GROQ_API_KEY=<KEY_1>,<KEY_2>
```

Các cách khai báo pool key đều được hỗ trợ:

```dotenv
GROQ_API_KEY=<KEY_1>,<KEY_2>
# hoặc GROQ_API_KEYS=<KEY_1>,<KEY_2>
# hoặc GROQ_API_KEY_1=<KEY_1> và GROQ_API_KEY_2=<KEY_2>
```

Nếu `OPENROUTER_API_KEY` hiện chứa các key bắt đầu bằng `gsk_` phân cách bằng dấu phẩy, hệ thống vẫn nhận chúng vào Groq pool để tương thích cấu hình cũ. Key được khử trùng lặp và không ghi vào log. Chỉ lỗi 429/quota/rate-limit mới chuyển key; lỗi 401 yêu cầu thay key. Hai key cùng Groq organization có thể vẫn dùng chung quota ngày.

Trong `legal_ocr_backend/.env`, giữ các giá trị quan trọng:

```dotenv
CONTRACT_VERSION=ver2
OCR_LANGUAGES=vie+eng
ENABLE_TRANSFORMER_EMBEDDING=true
QDRANT_COLLECTION=legal_provisions_ver2
```

LLM cleanup có deterministic fallback nên không bắt buộc thêm provider key cho backend. Nếu cần thử cleanup bằng LLM, điền `OPENROUTER_API_KEY` hợp lệ trong `legal_ocr_backend/.env`.

## 6. Bước D — Kiểm tra Tesseract OCR

```powershell
tesseract --version
tesseract --list-langs
```

Danh sách phải có `eng` và `vie`. Nếu PowerShell không tìm thấy Tesseract, điền đường dẫn thật trong `legal_ocr_backend/.env`, ví dụ:

```dotenv
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

Nếu thiếu `vie`, cài/copy file `vie.traineddata` chính thức vào thư mục `tessdata` của Tesseract rồi chạy lại `--list-langs`. Chỉ đặt `TESSDATA_DIR` khi dùng thư mục dữ liệu riêng; đường dẫn này không nên chứa khoảng trắng trên Windows.

## 7. Bước E — Nạp dữ liệu mock trực tiếp vào SQL và Qdrant

Mock giúp giám khảo test ngay mà không chờ OCR; upload PDF vẫn là luồng chính của sản phẩm.

```powershell
cd legal_ocr_backend
..\.venv\Scripts\python.exe scripts\seed_mock_vector_data.py --rebuild
cd ..
```

Fixture: [`legal_ocr_backend/fixtures/mock_legal_document_ver2.json`](legal_ocr_backend/fixtures/mock_legal_document_ver2.json).

Kết quả mong đợi:

- Số hiệu `MOCK-01/2026/QC-LF`.
- 8 trang, 20 Điều, 57 Khoản, 31 Điểm.
- 123 structural nodes và 20 vector chunks.
- Trạng thái tài liệu `INDEXED`.

## 8. Bước F — Khởi động ba service

Mở ba cửa sổ PowerShell tại repo root.

Terminal 1 — OCR/JSON/Qdrant backend:

```powershell
cd legal_ocr_backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Terminal 2 — Agent API:

```powershell
cd starter_v2
..\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8502
```

Terminal 3 — Web UI:

```powershell
cd legal_ocr_frontend
npm run dev -- --host 127.0.0.1 --port 3000
```

Mở các trang:

- Chat và nút V0/V1/V2: <http://localhost:3000>
- Upload/OCR: <http://localhost:3000/library/upload>
- Tài liệu đã index: <http://localhost:3000/library/documents>
- Backend API docs: <http://localhost:8000/docs>
- Agent API docs: <http://localhost:8502/docs>

## 9. Bước G — Readiness bắt buộc

Chạy trong terminal thứ tư tại repo root:

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/system/readiness | ConvertTo-Json -Depth 8
Invoke-RestMethod 'http://localhost:8502/ready?probe=true' | ConvertTo-Json -Depth 8
```

PASS khi:

- Backend trả `ready=true`, `contract_version=ver2`.
- OCR có `vie` và `eng`.
- Embedding trả `semantic=true`, vector size 384.
- Agent trả `ready=true`, provider `verified=true` và đúng `key_pool_size`.

## 10. Bước H — Test nhanh toàn hệ thống

```powershell
# Agent: unit/contract/orchestration tests
cd starter_v2
..\.venv\Scripts\python.exe -m pytest -q

# Tool thật gọi backend/vector DB
..\.venv\Scripts\python.exe scripts\smoke_legal_tools.py

# Backend: upload/OCR workflow và mock fixture
cd ..\legal_ocr_backend
..\.venv\Scripts\python.exe -m pytest -q --basetemp .pytest-grader

# Frontend
cd ..\legal_ocr_frontend
npm run lint
npm run build
cd ..
```

Kết quả đã lưu ở bản nộp hiện tại: Agent 39/39, backend 5/5, tool smoke 7/7, frontend lint 0 error và production build PASS. Hai lint warning về tối ưu ảnh/export không chặn chạy.

## 11. Bước I — Chạy eval và tạo evidence mới

Các lệnh này gọi provider thật và tiêu thụ quota:

```powershell
cd starter_v2

# Provider structured tool-call preflight
..\.venv\Scripts\python.exe scripts\preflight_provider.py --provider groq

# Đúng 10 team cases: 5 single-turn + 5 multi-turn
..\.venv\Scripts\python.exe run_eval.py --provider groq --version v3 --suite group --eval-cases data\eval_group.json

# 15 adversarial/security/routing cases
..\.venv\Scripts\python.exe run_eval.py --provider groq --version v3 --suite attack --eval-cases data\eval_attack_15.json

# So sánh ba thư mục vật lý V0/V1/V2
..\.venv\Scripts\python.exe scripts\compare_versions.py --provider groq

# Chat terminal và lưu transcript nhiều lượt
..\.venv\Scripts\python.exe chat.py --provider groq --version v3
```

Chỉ dùng metric khi `provider_error_cases=0` và `measured_cases=total_cases`. Routing PASS không đảm bảo tool thực thi đúng; phải xem cả `tool_results`.

## 12. Quy trình test bằng giao diện

### Test mock/RAG nhanh

1. Mở trang chat.
2. Chọn `V2`.
3. Hỏi: `Điều 4 của MOCK-01/2026/QC-LF quy định thời hạn thông báo sự cố thế nào?`
4. Kiểm tra câu trả lời có thời hạn, Điều/Khoản/Điểm, nguồn PDF/page và tool trace.
5. Chuyển qua V0 rồi V1 để đối chiếu cách routing; mỗi lần chuyển sẽ bắt đầu hội thoại sạch.

### Test upload/OCR chính

1. Mở `/library/upload` và điền metadata văn bản.
2. Chọn PDF, chạy OCR.
3. Đối chiếu PDF và text theo cùng số trang.
4. Dùng `Xác nhận tất cả` hoặc xác nhận từng trang.
5. Lọc ký tự rác; LLM cleanup sẽ fallback sang bộ lọc quy tắc khi provider không sẵn sàng.
6. Chọn xử lý/index để tạo JSON cấu trúc và vector chunks.
7. Mở `/library/documents`, chọn Điều để kiểm tra PDF mở đúng trang nguồn.

22 câu hỏi kiểm thử tay và kết quả mong đợi nằm tại [`TEST-QUESTIONS.md`](TEST-QUESTIONS.md).

## 13. Các file giám khảo cần kiểm tra

### Hướng dẫn và mô tả

| File | Nội dung cần xem |
|---|---|
| [`START-HERE.md`](START-HERE.md) | Quy trình cài/chạy/test từ A–Z này |
| [`WORKFLOW-AND-DEFENSE.md`](WORKFLOW-AND-DEFENSE.md) | Agent plan, OCR/RAG workflow, evidence gate, chống injection và dedup |
| [`TEST-QUESTIONS.md`](TEST-QUESTIONS.md) | 22 câu test tay và kết quả mong đợi |
| [`SUBMISSION-CHECKLIST.md`](SUBMISSION-CHECKLIST.md) | Gate kỹ thuật, secrets và nộp LMS/Codelabs |
| [`TOOL-SETUP.md`](TOOL-SETUP.md) | Chi tiết provider/tool, key và Windows troubleshooting |

### Prompt, tool và report

| File | Nội dung cần xem |
|---|---|
| [`starter_v2/artifacts/system_prompt.md`](starter_v2/artifacts/system_prompt.md) | System prompt hoàn chỉnh đang dùng |
| [`starter_v2/artifacts/tools.yaml`](starter_v2/artifacts/tools.yaml) | Declaration, description và JSON schema của các tool |
| [`starter_v2/tools/LEGAL_TOOL_CONTRACT.md`](starter_v2/tools/LEGAL_TOOL_CONTRACT.md) | Input/output envelope `ver2` và RAG data contract |
| [`starter_v2/artifacts/version_log.csv`](starter_v2/artifacts/version_log.csv) | Hypothesis, hash, metric và run file V0–V3 |
| [`starter_v2/artifacts/version_status.json`](starter_v2/artifacts/version_status.json) | Trạng thái/checkpoint của từng version |
| [`starter_v2/artifacts/REPORT.md`](starter_v2/artifacts/REPORT.md) | Phần A giới thiệu và Phần B evidence/reflection |

### Test case và log thật nổi bật

| File/thư mục | Evidence |
|---|---|
| [`starter_v2/data/eval_group.json`](starter_v2/data/eval_group.json) | Đúng 10 case bắt buộc, 5 single + 5 multi |
| [`starter_v2/data/eval_attack_15.json`](starter_v2/data/eval_attack_15.json) | 15 case adversarial bổ sung |
| [`starter_v2/runs/v2_B_group_groq_20260729T225728607977_rescored.json`](starter_v2/runs/v2_B_group_groq_20260729T225728607977_rescored.json) | Group 10/10, provider errors 0; giữ nguyên actual calls/results khi rescore rubric |
| [`starter_v2/runs/v3_B_attack_groq_20260729T233210074365.json`](starter_v2/runs/v3_B_attack_groq_20260729T233210074365.json) | V3 attack 15/15, provider errors 0 |
| [`starter_v2/runs/comparisons/prompt_progress_5_20260729T231336828571/`](starter_v2/runs/comparisons/prompt_progress_5_20260729T231336828571/) | Prompt-only V0 3/5 → V1 5/5 |
| [`starter_v2/runs/comparisons/attack_15_20260729T230125666781/`](starter_v2/runs/comparisons/attack_15_20260729T230125666781/) | So sánh V0/V1/V2 trên cùng 15 case |
| [`starter_v2/runs/ver2_legal_tool_smoke_20260729T231903964744.json`](starter_v2/runs/ver2_legal_tool_smoke_20260729T231903964744.json) | Tool/backend/vector smoke 7/7 |
| [`starter_v2/transcripts/`](starter_v2/transcripts/) | Transcript chat thật, tool events và lỗi quota được giữ trung thực |
| [`starter_v2/analysis/`](starter_v2/analysis/) | CSV metric đã làm phẳng để so sánh |

### Code triển khai chính

| File/thư mục | Vai trò |
|---|---|
| [`starter_v2/api.py`](starter_v2/api.py) | API chat/readiness và chọn V0/V1/V2 |
| [`starter_v2/chat.py`](starter_v2/chat.py) | Tool loop, plan, dedup, fail-closed gates |
| [`starter_v2/providers/rotating_openai_provider.py`](starter_v2/providers/rotating_openai_provider.py) | Parse pool và xoay key theo quota |
| [`starter_v2/tools/`](starter_v2/tools/) | TOOL.md, implementation và registry legal tools |
| [`legal_ocr_backend/app/services/`](legal_ocr_backend/app/services/) | OCR, cleanup, parse/chunk, embedding, Qdrant và mock seed |
| [`legal_ocr_frontend/app/components/ChatWorkspace.tsx`](legal_ocr_frontend/app/components/ChatWorkspace.tsx) | Chat history, tool trace và nút V0/V1/V2 |
| [`legal_ocr_frontend/app/components/OcrStudio.tsx`](legal_ocr_frontend/app/components/OcrStudio.tsx) | Upload, PDF–text, xác nhận trang và xử lý/index |

## 14. Lỗi thường gặp

| Hiện tượng | Cách xử lý |
|---|---|
| `tesseract_not_found` | Điền `TESSERACT_CMD`, khởi động lại backend |
| Thiếu `vie` | Cài `vie.traineddata`, kiểm tra lại `tesseract --list-langs` |
| Agent `verified=false` / 401 | Key sai hoặc hết hiệu lực; thay key |
| 429/quota với cả hai key | Kiểm tra hai key có cùng organization/quota ngày hay không |
| `semantic=false` | Đảm bảo `ENABLE_TRANSFORMER_EMBEDDING=true` và đã cài root `requirements.txt` |
| Qdrant local bị lock | Chỉ chạy một backend/seed process dùng cùng `QDRANT_PATH` tại một thời điểm |
| Port 3000/8000/8502 đã dùng | Dừng tiến trình cũ hoặc dùng đúng port và cập nhật các URL trong `.env` |
| UI còn bundle cũ | Dừng `npm run dev`, chạy lại rồi reload trang |

## 15. Trước khi nộp

- Không commit `.env`, `.venv`, `node_modules`, cache, database/Qdrant local hoặc PDF riêng tư.
- Điền Team, Members/MSSV, repo URL và demo URL trong `starter_v2/artifacts/REPORT.md`.
- Kiểm tra `git status`, commit/push, sau đó nộp LMS và xác nhận Codelabs theo [`SUBMISSION-CHECKLIST.md`](SUBMISSION-CHECKLIST.md).
