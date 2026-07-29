# Checklist nộp LMS/Codelabs

## Artifact bắt buộc

- [x] V0 baseline còn nguyên trong `starter_v0`.
- [x] V1 prompt-only và tool declaration tương đương V0.
- [x] V2 tích hợp OCR/RAG; có ít nhất 5 tool và nhiều tool mới của nhóm.
- [x] Snapshot/hypothesis `v0`, `v1`, `v2`, `v3` trong V2.
- [x] `artifacts/system_prompt.md`, `tools.yaml`, `version_log.csv`, `REPORT.md`.
- [x] `data/eval_group.json` đúng 10 case: 5 single, 5 multi.
- [x] Suite bổ sung `data/eval_attack_15.json` có 15 case chi tiết.
- [x] UI chat/thư viện/upload OCR có trace/version và lưu dữ liệu thật.
- [x] Tool mới có `TOOL.md`, implementation, registry, declaration và smoke script.
- [x] Live run V0–V3 có `provider_error_cases=0` trong các suite được report.
- [x] Group/attack run JSON cuối và ít nhất ba live turn được lưu trong transcript JSON.
- [x] `version_log.csv` dùng metric/hash/run thật, không còn placeholder `pending_valid_provider_run`.
- [ ] Điền tên nhóm/thành viên/repo/demo URL trong `REPORT.md`.

## Gate kỹ thuật ngay trước nộp

```powershell
cd starter_v2
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\preflight_provider.py --provider groq
.\.venv\Scripts\python.exe scripts\smoke_legal_tools.py

cd ..\legal_ocr_backend
.\.venv\Scripts\python.exe -m pytest -q --basetemp .pytest-run

cd ..\legal_ocr_frontend
npm run lint
npm run build
```

- [x] Backend readiness: OCR `vie+eng`, semantic embedding, contract ver2.
- [x] Agent readiness với `probe=true`: `ready=true`, provider verified và pool 2 key.
- [ ] Mở UI, upload PDF, xác nhận trang, parse/index, mở đúng PDF page.
- [x] Test ít nhất 3 scenario; browser smoke xác nhận V0/V1/V2 và V2 injection guard, eval kiểm tra tool trace.
- [x] Review thủ công mọi `tool_results.error` dù routing PASS; lỗi quota/malformed tool generation được giữ trong report.

## Secrets và Git

```powershell
git status --short
git check-ignore -v starter_v2/.env legal_ocr_backend/.env legal_ocr_frontend/.env
git grep -n -I -E "gsk_|sk-[A-Za-z0-9]|tvly-|fc-" -- . ':!*.env.example'
```

- [x] `.env` của ba service được Git ignore; secret scan chỉ thấy chuỗi giả cố ý trong unit test bảo mật.
- [ ] Không có key/token trong run JSON, transcript, screenshot, report hoặc terminal capture.
- [ ] Điền URL repo HTTPS và URL demo truy cập được.

## Tạo ZIP sạch sau commit cuối

Đề gốc ghi `starter_v0`, nhưng kiến trúc được yêu cầu ở đây giữ V0 nguyên và sản phẩm cuối ở V2. Xác nhận với giảng viên thư mục nộp; nếu nộp ứng dụng tích hợp, archive các file Git-tracked của repo/folder được chỉ định, không zip cả worktree có `.env`.

```powershell
git status
git add starter_v1 starter_v2 legal_ocr_backend legal_ocr_frontend START-HERE.md WORKFLOW-AND-DEFENSE.md TEST-QUESTIONS.md SUBMISSION-CHECKLIST.md README.md TOOL-SETUP.md
git diff --cached --name-only
git commit -m "Hoan thanh LexFlow Day 04"
git push origin main
```

Sau đó nộp repo/demo trên LMS, lưu xác nhận; dán URL đầy đủ vào Codelabs, xác nhận và kiểm tra lịch sử. LMS và Codelabs là hai luồng độc lập.
