# Workflow LexFlow, AI plan và cơ chế phòng vệ

## Luồng dữ liệu chính

1. Người dùng upload PDF cùng metadata phiên bản: số ký hiệu, ngày ban hành/hiệu lực, loại văn bản, cơ quan, người ký, trích yếu và version.
2. Backend phân loại từng trang. Trang có text layer đọc trực tiếp; trang scan dùng Tesseract `vie+eng`. `raw_text` được giữ bất biến.
3. Người dùng đối chiếu PDF và text theo cùng số trang, có thể chạy lọc rác rule-based/LLM rồi xác nhận từng trang hoặc “Xác nhận tất cả”. Mỗi sửa đổi tạo revision/audit log.
4. Parser tạo cây Phần → Chương → Mục → Điều → Khoản → Điểm. Export JSON giữ metadata văn bản, page mapping và cấu trúc pháp luật.
5. Chunker `legal-hierarchy-ver2` ưu tiên một đơn vị pháp lý trọn vẹn; chỉ tách khối quá dài tại ranh giới câu/đoạn. Mỗi chunk mang metadata version, full path, Điều/Khoản/Điểm, trang PDF và `contract_version=ver2`.
6. Embedder đa ngôn ngữ tạo vector 384 chiều; Qdrant lưu collection `legal_provisions_ver2`, SQL giữ nguồn chuẩn/citation. Chỉ tài liệu đã xác nhận và trạng thái `INDEXED` được truy xuất.
7. Chat agent dùng exact lookup hoặc hybrid semantic search, kiểm tra hiệu lực, validate citation rồi mới tạo câu trả lời.

Mock fixture đi thẳng vào bước 4 để test nhanh parser/chunker/vector. Nó không thay thế và không làm thay đổi luồng OCR chính.

## Cách AI lập execution plan

Plan là danh sách thao tác quan sát được, không phải chain-of-thought:

- Câu hỏi nêu rõ Điều/Khoản/Điểm: exact lookup → effective status → citation validation.
- Câu hỏi pháp luật tự nhiên: legal RAG → effective status → extract khi cần → citation validation.
- Yêu cầu so sánh: resolve hai version → compare → effective status → citation validation.
- Thiếu giá trị chỉ user biết: clarify. Dữ kiện có thể lấy từ thư viện thì resolve/search, không hỏi lại.
- Lời chào/capability: trả lời trực tiếp, không tool.
- Ngoài phạm vi/unsafe: chặn trước model và không tool.

Runtime chỉ phát hành claim khi ledger có citation thật, document tương ứng `effective` tại ngày hỏi và `validate_citation.valid=true`. Thiếu gate nào thì fail closed.

## Tool contract ver2

| Tool | Khi dùng | Input trọng tâm | Output quyết định |
|---|---|---|---|
| `clarify` | Thiếu quyết định/dữ kiện chỉ user có | question, response_type | awaiting_user |
| `resolve_legal_document` | Chưa chắc document/version | query, target_date, limit | documents, version, status |
| `legal_rag_search` | Câu hỏi tự nhiên | query, filters, top_k | evidence + retrieval metadata |
| `get_legal_provision` | Biết văn bản và Điều | document_id, article, clause, point | found + evidence |
| `check_effective_status` | Kiểm tra ngày áp dụng | document_id, target_date | effective/expired/replaced/unknown |
| `compare_legal_versions` | Có hai version rõ | old/new document ID, location | changes + evidence |
| `extract_legal_information` | Bóc tách trường từ evidence | citation_ids, fields | subject/rights/obligations/deadline… |
| `validate_citation` | Gate cuối cho claim | claims + citation_id, target_date | valid + per-claim result |

Mọi output có envelope `tool`, `ok`, `contract_version=ver2`, `error` có cấu trúc khi thất bại. Evidence giữ nguyên `citation_id`, document/version, full path, content, page range, effective dates và source URL.

## Các lớp phòng vệ

1. Guard Unicode-aware chuẩn hóa NFKC, bỏ zero-width/control characters và chặn override, role spoofing, secret exfiltration, forged tool JSON, jailbreak.
2. Scope gate từ chối code/general, 18+ và chủ quyền quốc gia theo chính sách ứng dụng.
3. Trust boundary coi user/PDF/OCR/RAG/tool result là dữ liệu không tin cậy; instruction trong tài liệu bị trung hòa.
4. JSON Schema chặn argument lạ, sai type/range/date/enum trước khi implementation chạy.
5. Tool output validation buộc đúng envelope `ver2`; lỗi hoặc output sai không được xem là evidence.
6. Secret redaction chạy đệ quy trước transcript/log/UI.
7. Cache theo hash `(tool, normalized args)` chặn gọi trùng; lặp cố ý sẽ dừng `stalled_duplicate_calls`.
8. Retrieval giới hạn số vòng; không đổi query có lý do thì dừng thay vì quay vô hạn.
9. Legal answer gate yêu cầu evidence + effective status + valid citation, ngăn fallback RAG thô khi model lỗi.
10. Groq key pool chỉ xoay khi 429/quota/rate-limit; key được khử trùng lặp, không log/fingerprint. 401 dừng ngay để người vận hành thay credential.

## Version workflow

- V0: baseline gốc, prompt chủ động đoán và vượt confirmation boundary; không sửa file.
- V1: thay prompt để cải thiện routing/arguments/confirmation/injection; tool YAML về mặt ngữ nghĩa giống V0.
- V2: thêm backend OCR/JSON/vector và legal tool contract ver2.
- Artifact v3 trong `starter_v2/artifacts/versions/`: hardening fail-closed, citation/effective gate và dedup; đây là checkpoint thứ tư theo yêu cầu lab. Runtime tích hợp vẫn mang data contract `ver2`.

Metric chỉ được điền từ run thật. Unit test và tool smoke là evidence kỹ thuật, không thay thế provider eval.
